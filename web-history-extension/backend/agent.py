import asyncio
import time
import os
import datetime
from perception import extract_perception
from memory import MemoryManager, MemoryItem
from decision import generate_plan
from action import execute_tool
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path
from tools import WebPage, SearchQuery, SearchResult, SearchResponse, process_webpage, get_embedding
from mcp.server.fastmcp import FastMCP

# Configure paths
ROOT = Path(__file__).parent.parent.resolve()
INDEX_DIR = ROOT / "faiss_index"
INDEX_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class AgentRequest(BaseModel):
    search_query: Optional[str] = None
    webpage: Optional[WebPage] = None

class AgentResponse(BaseModel):
    results: List[SearchResult] = []
    error: Optional[str] = None
    query: Optional[str] = None

class Agent:
    def __init__(self, mcp_server: FastMCP):
        logger.info("Initializing Agent with MCP server")
        self.mcp = mcp_server
        self.memory = MemoryManager(index_dir=str(INDEX_DIR))
        logger.info("Agent initialized successfully")

    async def process_query(self, request: AgentRequest) -> AgentResponse:
        try:
            if request.webpage:
                # Handle webpage indexing
                logger.info(f"Processing webpage: {request.webpage.url}")
                logger.debug(f"Webpage content length: {len(request.webpage.content)}")
                
                # Process webpage using MCP
                logger.debug("Invoking process_webpage tool")
                chunks = await process_webpage(request.webpage)
                logger.info(f"Got {len(chunks)} chunks from webpage")
                
                # Get embeddings and store in memory
                for i, chunk in enumerate(chunks):
                    logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
                    embedding = await get_embedding(chunk)
                    logger.debug(f"Got embedding for chunk {i+1}")
                    
                    self.memory.add_with_embedding(
                        chunk,
                        embedding,
                        {
                            "url": request.webpage.url,
                            "title": request.webpage.title,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                    )
                    logger.debug(f"Added chunk {i+1} to memory")
                
                logger.info("Successfully indexed webpage")
                return AgentResponse()
            
            elif request.search_query:
                # Handle search query
                logger.info(f"Processing search query: {request.search_query}")
                query = SearchQuery(query=request.search_query)
                
                # Get query embedding
                logger.debug("Getting query embedding")
                query_embedding = await get_embedding(query.query)
                logger.debug("Got query embedding")
                
                # Search memory
                logger.debug("Searching memory with embedding")
                results = self.memory.search_by_embedding(query_embedding)
                logger.info(f"Found {len(results)} results")
                
                return AgentResponse(
                    results=results,
                    query=request.search_query
                )
            
            else:
                logger.warning("Invalid request: no webpage or search query provided")
                return AgentResponse(error="Invalid request: must provide either webpage or search query")

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return AgentResponse(error=str(e))

    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        logger.debug("Getting memory stats")
        stats = self.memory.get_stats()
        logger.debug(f"Memory stats: {stats}")
        return stats

    async def clear_index(self):
        """Clear the entire index"""
        logger.info("Clearing memory index")
        self.memory.clear()
        logger.info("Memory index cleared")
