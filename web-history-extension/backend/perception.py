import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from dotenv import load_dotenv
import os
from pydantic import BaseModel

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class PerceptionResult(BaseModel):
    intent: str
    entities: List[str]
    tool_hint: Optional[str] = None

async def extract_perception(query: str) -> Dict[str, Any]:
    """Extract intent, entities, and tool hints from a query using Gemini API"""
    try:
        logger.info(f"Extracting perception from query: {query}")
        
        # Use Gemini API to analyze the query
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""Analyze this query and extract:
        1. Primary intent (e.g., search, index, filter)
        2. Key entities (e.g., dates, urls, keywords)
        3. Tool hints (e.g., which tools might be useful)
        
        Query: {query}
        
        Return as JSON."""
        
        logger.debug("Sending query to Gemini API")
        response = await model.generate_content_async(prompt)
        logger.debug("Received response from Gemini API")
        
        # Parse the response
        perception = {
            "intent": "unknown",
            "entities": [],
            "tool_hints": []
        }
        
        try:
            # Try to parse the response as JSON
            result = response.text
            logger.debug(f"Raw Gemini response: {result}")
            
            # TODO: Parse the response into perception dict
            # This is a placeholder - we'll implement proper parsing later
            perception["raw_response"] = result
            
        except Exception as parse_error:
            logger.error(f"Error parsing Gemini response: {parse_error}", exc_info=True)
            perception["error"] = str(parse_error)
        
        logger.info(f"Extracted perception: {perception}")
        return perception
        
    except Exception as e:
        logger.error(f"Error in extract_perception: {e}", exc_info=True)
        return {
            "error": str(e),
            "intent": "error",
            "entities": [],
            "tool_hints": []
        }
