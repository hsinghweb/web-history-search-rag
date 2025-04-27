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
            f"Memory {i+1}:\n{memory.get('content_snippet', '')}\n"
            for i, memory in enumerate(memories)
        ])

        # Build prompt
        tool_hint = perception.get('tool_hint')
        if not tool_hint:
            tool_hint = ', '.join(perception.get('tool_hints', []))
        prompt = f"""
        Given the following context:
        
        User Intent: {perception.get('intent', '')}
        Tool Hint: {tool_hint}
        
        Available Tools:
        {tools_prompt}
        
        Relevant Memories:
        {memories_prompt}
        
        Decide what to do next. You can:
        1. Use a tool by responding with: USE_TOOL: <tool_name> WITH <args>
        2. Give a final answer by responding with: FINAL_ANSWER: <your answer>
        
        Your response:
        """

        logger.debug("Sending request to Gemini LLM (decision step)")
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        logger.debug("Received response from Gemini LLM (decision step)")

        plan = response.text.strip()
        logger.debug(f"Raw Gemini LLM response: {plan}")
        logger.info(f"Generated plan from Gemini LLM: {plan}")
        return plan

    except Exception as e:
        logger.error(f"Error generating plan: {e}", exc_info=True)
        return f"FINAL_ANSWER: Error generating plan: {str(e)}"
