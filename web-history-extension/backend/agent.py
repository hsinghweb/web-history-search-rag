import asyncio
import time
import os
import datetime
from perception import extract_perception, PerceptionResult
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
            # Step 1: Perception (intent/entity/tool extraction)
            user_query = request.search_query or (request.webpage.title if request.webpage else None)
            if not user_query:
                logger.warning("Invalid request: no webpage or search query provided")
                return AgentResponse(error="Invalid request: must provide either webpage or search query")

            logger.info(f"Calling perception module for query: {user_query}")
            perception = await extract_perception(user_query)
            logger.info(f"Perception result: {perception}")

            # Step 2: If webpage, check for private domains before indexing
            if request.webpage:
                url = request.webpage.url.lower()
                if any(domain in url for domain in ["mail.google.com", "gmail.com", "web.whatsapp.com", "whatsapp.com"]):
                    logger.warning(f"Rejected private page for indexing: {url}")
                    return AgentResponse(error="Cannot index private pages like Gmail or WhatsApp.")

                logger.info(f"Processing webpage: {request.webpage.url}")
                logger.debug(f"Webpage content length: {len(request.webpage.content)}")

                # Process webpage using MCP
                logger.debug("Invoking process_webpage tool")
                chunks = await process_webpage(request.webpage)
                logger.info(f"Got {len(chunks)} chunks from webpage")

                # Get embeddings and store in memory
                for i, chunk in enumerate(chunks):
                    logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
                    logger.info("Calling embedding model (Ollama)")
                    embedding = await get_embedding(chunk)
                    logger.debug(f"Got embedding for chunk {i+1} from Ollama")

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

                logger.info("Successfully indexed webpage with Ollama embeddings")
                return AgentResponse()

            # Step 3: If search query, use perception, memory, decision, action
            if request.search_query:
                logger.info(f"Processing search query: {request.search_query}")
                query = request.search_query

                logger.info("Calling embedding model (Ollama)")
                query_embedding = await get_embedding(query)
                logger.debug("Got query embedding from Ollama")

                logger.debug("Searching memory with embedding")
                results = self.memory.search_by_embedding(query_embedding)
                logger.info(f"Found {len(results)} results")

                # Decision step: generate plan
                logger.info("Calling decision module (Gemini LLM)")
                plan = generate_plan(perception, [r.__dict__ for r in results], {"search": {"description": "Search indexed content"}})  # Example, expand as needed
                logger.info(f"Plan from decision module: {plan}")

                # Action step: execute tool if needed
                if plan.startswith("USE_TOOL:"):
                    logger.info("Calling action module to execute tool")
                    tool_result = await execute_tool(plan, {"search": {"description": "Search indexed content"}})  # Example, expand as needed
                    logger.info(f"Tool execution result: {tool_result}")
                    return AgentResponse(results=results, query=query)
                else:
                    return AgentResponse(results=results, query=query)

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
