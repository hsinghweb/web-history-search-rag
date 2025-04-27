from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json
from pathlib import Path
import faiss
import numpy as np
import google.generativeai as genai
import logging
from tools import SearchResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class MemoryItem(BaseModel):
    text: str
    type: str  # "tool_output", "user_query", "system_message", "webpage_chunk"
    tool_name: Optional[str] = None
    user_query: Optional[str] = None
    tags: List[str] = []
    session_id: str
    timestamp: str = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)

class MemoryManager:
    def __init__(self, index_dir: str = "memory_index"):
        logger.info(f"Initializing MemoryManager with index directory: {index_dir}")
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)
        self.index_file = self.index_dir / "faiss.index"
        self.metadata_file = self.index_dir / "metadata.json"
        self.cache_file = self.index_dir / "url_cache.json"
        
        self.metadata: List[Dict] = []
        self.url_cache: Dict[str, str] = {}
        self.index = None
        
        self._load_or_create_index()
        logger.info(f"Memory Manager initialized with {len(self.metadata)} items")

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding using Gemini API"""
        try:
            logger.debug(f"Getting embedding for text: {text[:50]}...")
            model = "models/embedding-001"
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="retrieval_document"
            )
            return np.array(result["embedding"], dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise

    def _load_or_create_index(self):
        """Load existing index or create new one"""
        try:
            logger.debug("Loading or creating index...")
            if self.index_file.exists() and self.metadata_file.exists():
                logger.info("Loading existing FAISS index")
                self.index = faiss.read_index(str(self.index_file))
                self.metadata = json.loads(self.metadata_file.read_text())
                if self.cache_file.exists():
                    self.url_cache = json.loads(self.cache_file.read_text())
                logger.info(f"Loaded existing index with {self.index.ntotal} vectors")
            else:
                logger.info("Creating new empty index")
                # Initialize empty index with correct dimensions
                sample_embedding = self._get_embedding("sample text")
                self.index = faiss.IndexFlatL2(len(sample_embedding))
                self.metadata = []
                self.url_cache = {}
                logger.info("Created new empty index")
        except Exception as e:
            logger.error(f"Error loading/creating index: {e}")
            raise

    def _save_index(self):
        """Save index and metadata to disk"""
        try:
            logger.debug("Saving index and metadata to disk...")
            if self.index and self.index.ntotal > 0:
                faiss.write_index(self.index, str(self.index_file))
                self.metadata_file.write_text(json.dumps(self.metadata))
                self.cache_file.write_text(json.dumps(self.url_cache))
                logger.debug("Saved index and metadata to disk")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise

    def add(self, item: MemoryItem):
        """Add a new memory item to the index"""
        try:
            logger.debug(f"Adding new memory item: {item.text[:50]}...")
            embedding = self._get_embedding(item.text)
            self.add_with_embedding(item.text, embedding, item.dict())
            self._save_index()
        except Exception as e:
            logger.error(f"Error adding memory item: {e}")
            raise

    def add_with_embedding(self, text: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """Add a new item with pre-computed embedding"""
        try:
            # Check for duplicate chunk text (optional, prevents exact duplicates)
            if any(item["text"] == text for item in self.metadata):
                logger.info("Chunk already indexed (duplicate text). Skipping.")
                return
            
            # Add to index
            logger.debug(f"Adding item with text: {text[:50]}...")
            
            # Add embedding to FAISS index
            self.index.add(np.array([embedding]).astype('float32'))
            
            # Add metadata
            metadata["text"] = text
            metadata["index"] = len(self.metadata)
            self.metadata.append(metadata)
            
            # Update URL cache (for stats only)
            url = metadata.get("url")
            if url:
                self.url_cache[url] = datetime.now().isoformat()
                logger.debug(f"Added URL to cache: {url}")
            
            # Save changes
            self._save_index()
            logger.info(f"Successfully added item. Total items: {len(self.metadata)}")
            
        except Exception as e:
            logger.error(f"Error adding item with embedding: {e}")
            raise

    def retrieve(self, query: str, top_k: int = 3, session_filter: Optional[str] = None) -> List[MemoryItem]:
        """Retrieve relevant memories based on query"""
        if not self.index or self.index.ntotal == 0:
            logger.debug("No memories to retrieve from")
            return []

        try:
            logger.debug(f"Retrieving memories for query: {query[:50]}...")
            query_embedding = self._get_embedding(query)
            D, I = self.index.search(query_embedding.reshape(1, -1), top_k)
            
            results = []
            for idx in I[0]:
                if idx >= len(self.metadata):  # Skip invalid indices
                    continue
                    
                memory_data = self.metadata[idx]
                if session_filter and memory_data.get("session_id") != session_filter:
                    continue
                    
                results.append(MemoryItem(**memory_data))
            
            logger.debug(f"Retrieved {len(results)} memories for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []

    def search_by_embedding(self, embedding: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        """Search for similar items using embedding"""
        try:
            logger.debug(f"Searching memory with k={top_k}")
            if self.index is None or self.index.ntotal == 0:
                logger.warning("No items in memory to search")
                return []
            
            # Search FAISS index
            query_array = np.array([embedding]).astype('float32')
            distances, indices = self.index.search(query_array, top_k)
            
            # Convert to SearchResults
            results = []
            seen_texts = set()
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    item = self.metadata[idx]
                    text = item["text"]
                    if text in seen_texts:
                        continue  # Skip duplicate text
                    seen_texts.add(text)
                    result = SearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        content_snippet=text[:200] + "...",
                        score=float(1.0 / (1.0 + dist)),
                        chunk_id=str(idx)
                    )
                    logger.info(
                        f"Matched chunk #{i}: idx={idx}, score={result.score:.4f}, dist={dist:.4f}, url={result.url}, title={result.title}, text={text[:100].replace(chr(10), ' ')}..."
                    )
                    results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error searching memory: {e}", exc_info=True)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            logger.debug("Getting memory statistics")
            unique_urls = set()
            for item in self.metadata:
                if "url" in item:
                    unique_urls.add(item["url"])
                    
            stats = {
                "indexed_urls": len(unique_urls),
                "total_chunks": len(self.metadata),
                "index_size": self.index_file.stat().st_size if self.index_file.exists() else 0
            }
            logger.debug(f"Memory stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}", exc_info=True)
            return {"error": str(e)}

    def clear(self):
        """Clear the entire index"""
        try:
            logger.info("Clearing memory index")
            self.index = None
            self.metadata = []
            self.url_cache = {}
            
            # Remove files
            if self.index_file.exists():
                self.index_file.unlink()
            self.metadata_file.write_text(json.dumps([]))
            self.cache_file.write_text(json.dumps({}))
            
            # Reinitialize empty index
            sample_embedding = self._get_embedding("sample text")
            self.index = faiss.IndexFlatL2(len(sample_embedding))
            logger.info("Index cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing index: {e}", exc_info=True)
            raise
