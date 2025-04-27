from typing import Dict, Any, List
import google.generativeai as genai
from dotenv import load_dotenv
import os
import logging

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def generate_plan(perception: Dict[str, Any], memories: List[Dict[str, Any]], tool_descriptions: Dict[str, Any]) -> str:
    """Generate a plan based on perception and memories"""
    try:
        logger.info("Generating plan")
        logger.debug(f"Input perception: {perception}")
        logger.debug(f"Memories: {len(memories)} items")
        logger.debug(f"Tool descriptions: {len(tool_descriptions)} items")

        # Format tool descriptions for prompt
        tools_prompt = "\n".join([
            f"- {name}: {desc['description']}" 
            for name, desc in tool_descriptions.items()
        ])

        # Format memories for prompt
        memories_prompt = "\n".join([
            f"Memory {i+1}:\n{memory['text']}\n"
            for i, memory in enumerate(memories)
        ])

        # Build prompt
        prompt = f"""
        Given the following context:
        
        User Intent: {perception['intent']}
        Tool Hint: {perception['tool_hint']}
        
        Available Tools:
        {tools_prompt}
        
        Relevant Memories:
        {memories_prompt}
        
        Decide what to do next. You can:
        1. Use a tool by responding with: USE_TOOL: <tool_name> WITH <args>
        2. Give a final answer by responding with: FINAL_ANSWER: <your answer>
        
        Your response:
        """

        logger.debug("Sending request to Gemini API")
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        logger.debug("Received response from Gemini API")

        plan = response.text.strip()
        logger.debug(f"Raw Gemini response: {plan}")
        logger.info(f"Generated plan: {plan}")
        return plan

    except Exception as e:
        logger.error(f"Error generating plan: {e}", exc_info=True)
        return f"FINAL_ANSWER: Error generating plan: {str(e)}"
