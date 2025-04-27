import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
from agent import Agent, AgentRequest
from tools import WebPage, SearchQuery, SearchResult, mcp

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_history_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Web History Search API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = Agent(mcp)

@app.post("/search")
async def search(query: SearchQuery):
    try:
        request = AgentRequest(search_query=query.query)
        response = await agent.process_query(request)
        return {"query": query.query, "results": response.results}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index")
async def index_webpage(webpage: WebPage):
    try:
        request = AgentRequest(webpage=webpage)
        response = await agent.process_query(request)
        return {"status": "success", "message": "Webpage indexed successfully"}
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    try:
        stats = await agent.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear")
async def clear_index():
    try:
        await agent.clear_index()
        return {"status": "success", "message": "Index cleared successfully"}
    except Exception as e:
        logger.error(f"Clear index error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
