import os
import json
import numpy as np
import faiss
import requests
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Web History Search API")

# Add CORS middleware to allow requests from Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 256
CHUNK_OVERLAP = 40
ROOT = Path(__file__).parent.parent.resolve()
INDEX_DIR = ROOT / "faiss_index"
INDEX_DIR.mkdir(exist_ok=True)
INDEX_FILE = INDEX_DIR / "index.bin"
METADATA_FILE = INDEX_DIR / "metadata.json"
CACHE_FILE = INDEX_DIR / "url_cache.json"

# Initialize cache
if CACHE_FILE.exists():
    URL_CACHE = json.loads(CACHE_FILE.read_text())
else:
    URL_CACHE = {}
    CACHE_FILE.write_text(json.dumps(URL_CACHE))

# Initialize metadata
if METADATA_FILE.exists():
    METADATA = json.loads(METADATA_FILE.read_text())
else:
    METADATA = []
    METADATA_FILE.write_text(json.dumps(METADATA))

# Initialize FAISS index
if INDEX_FILE.exists():
    INDEX = faiss.read_index(str(INDEX_FILE))
else:
    INDEX = None

# Models
class WebPage(BaseModel):
    url: str
    title: str
    content: str
    timestamp: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    top_k: int = 5

class SearchResult(BaseModel):
    url: str
    title: str
    content_snippet: str
    score: float
    chunk_id: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str

def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Nomic via Ollama API"""
    try:
        response = requests.post(
            EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text}
        )
        response.raise_for_status()
        return np.array(response.json()["embedding"], dtype=np.float32)
    except Exception as e:
        print(f"Error getting embedding: {e}")
        # Fallback to Gemini embeddings if Ollama is not available
        model = "models/embedding-001"
        result = genai.embed_content(
            model=model,
            content=text,
            task_type="retrieval_document"
        )
        return np.array(result["embedding"], dtype=np.float32)

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into chunks with overlap"""
    words = text.split()
    for i in range(0, len(words), size - overlap):
        yield " ".join(words[i:i+size])

def save_index():
    """Save FAISS index and metadata to disk"""
    global INDEX, METADATA
    if INDEX and INDEX.ntotal > 0:
        faiss.write_index(INDEX, str(INDEX_FILE))
        METADATA_FILE.write_text(json.dumps(METADATA))
        CACHE_FILE.write_text(json.dumps(URL_CACHE))

@app.post("/index", status_code=201)
async def index_webpage(webpage: WebPage):
    """Index a webpage in FAISS"""
    global INDEX, METADATA
    
    # Skip if URL is already indexed and hasn't changed
    url_hash = webpage.url
    if url_hash in URL_CACHE:
        return {"status": "skipped", "message": "URL already indexed"}
    
    # Set timestamp
    if not webpage.timestamp:
        webpage.timestamp = datetime.now().isoformat()
    
    # Process content into chunks
    chunks = list(chunk_text(webpage.content))
    if not chunks:
        raise HTTPException(status_code=400, detail="No content to index")
    
    # Get embeddings for each chunk
    embeddings = []
    new_metadata = []
    
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        embeddings.append(embedding)
        new_metadata.append({
            "url": webpage.url,
            "title": webpage.title,
            "chunk": chunk,
            "chunk_id": f"{url_hash.replace('/', '_').replace(':', '_')}_{i}",
            "timestamp": webpage.timestamp
        })
    
    # Initialize or update FAISS index
    if not embeddings:
        raise HTTPException(status_code=400, detail="Failed to generate embeddings")
    
    if INDEX is None:
        dim = len(embeddings[0])
        INDEX = faiss.IndexFlatL2(dim)
    
    # Add embeddings to index
    INDEX.add(np.stack(embeddings))
    METADATA.extend(new_metadata)
    
    # Update cache
    URL_CACHE[url_hash] = webpage.timestamp
    
    # Save to disk
    save_index()
    
    return {"status": "success", "chunks_indexed": len(chunks)}

@app.post("/search", response_model=SearchResponse)
async def search(search_query: SearchQuery):
    """Search for webpages matching the query"""
    global INDEX, METADATA
    
    if INDEX is None or INDEX.ntotal == 0:
        raise HTTPException(status_code=404, detail="No index available")
    
    # Get embedding for query
    query_vec = get_embedding(search_query.query).reshape(1, -1)
    
    # Search FAISS index
    D, I = INDEX.search(query_vec, search_query.top_k)
    
    # Format results
    results = []
    for i, idx in enumerate(I[0]):
        if idx >= len(METADATA):
            continue
            
        data = METADATA[idx]
        results.append(SearchResult(
            url=data["url"],
            title=data["title"],
            content_snippet=data["chunk"],
            score=float(D[0][i]),
            chunk_id=data["chunk_id"]
        ))
    
    return SearchResponse(results=results, query=search_query.query)

@app.get("/stats")
async def get_stats():
    """Get index statistics"""
    return {
        "indexed_urls": len(URL_CACHE),
        "total_chunks": len(METADATA),
        "index_size": os.path.getsize(INDEX_FILE) if INDEX_FILE.exists() else 0
    }

@app.delete("/clear")
async def clear_index():
    """Clear the entire index"""
    global INDEX, METADATA, URL_CACHE
    
    if INDEX is not None:
        INDEX = None
    
    METADATA = []
    URL_CACHE = {}
    
    # Remove files
    if INDEX_FILE.exists():
        os.remove(INDEX_FILE)
    
    METADATA_FILE.write_text(json.dumps([]))
    CACHE_FILE.write_text(json.dumps({}))
    
    return {"status": "success", "message": "Index cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
