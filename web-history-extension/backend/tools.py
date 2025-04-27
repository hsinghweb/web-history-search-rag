from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from mcp import types
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class WebPage(BaseModel):
    url: str
    title: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

class SearchQuery(BaseModel):
    query: str
    max_results: int = 5

class SearchResult(BaseModel):
    url: str
    title: str
    content_snippet: str
    score: float
    chunk_id: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int

# Initialize MCP server
mcp = FastMCP("WebHistoryTools")
logger.info("Initialized MCP server with name: WebHistoryTools")

@mcp.tool()
async def get_embedding(text: str) -> List[float]:
    """Get embedding for text using Ollama locally (e.g., 'nomic-embed-text')."""
    try:
        logger.debug(f"Getting embedding for text of length {len(text)} using Ollama")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            logger.debug("Successfully generated embedding with Ollama")
            return data["embedding"]
    except Exception as e:
        logger.error(f"Error getting embedding from Ollama: {e}")
        raise

@mcp.tool()
async def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """Split text into chunks of roughly equal size"""
    try:
        logger.debug(f"Chunking text of length {len(text)} with chunk_size {chunk_size}")
        # Simple chunking by sentences
        sentences = text.split(". ")
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append(". ".join(current_chunk) + ".")
                current_chunk = []
                current_size = 0
            current_chunk.append(sentence)
            current_size += sentence_size
            
        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")
            
        logger.debug(f"Successfully chunked text into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error chunking text: {e}")
        raise

@mcp.tool()
async def process_webpage(webpage: WebPage) -> List[str]:
    """Process a webpage and split it into chunks"""
    try:
        logger.info(f"Processing webpage: {webpage.url}")
        logger.debug(f"Webpage content length: {len(webpage.content)}")
        chunks = await chunk_text(webpage.content)
        logger.info(f"Successfully processed webpage into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error processing webpage: {e}")
        raise
