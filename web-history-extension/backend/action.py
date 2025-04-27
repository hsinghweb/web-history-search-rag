from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
import ast
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ToolResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    error: Optional[str] = None

async def execute_tool(plan: str, tools_config: Dict[str, Any]) -> ToolResult:
    """Execute a tool based on the plan"""
    try:
        logger.info(f"Executing plan: {plan}")
        logger.debug(f"Tools config: {tools_config}")
        
        # Extract tool name and arguments from plan
        if plan.startswith("USE_TOOL:"):
            parts = plan.split("WITH", 1)
            if len(parts) != 2:
                raise ValueError("Invalid tool call format")
                
            tool_name = parts[0].replace("USE_TOOL:", "").strip()
            args_str = parts[1].strip()
            
            logger.debug(f"Tool name: {tool_name}")
            logger.debug(f"Arguments string: {args_str}")
            
            # Parse arguments
            args = {}
            for match in re.finditer(r'(\w+)=([^,}]+)(?:,|$)', args_str):
                key, value = match.groups()
                try:
                    args[key] = ast.literal_eval(value)
                except:
                    args[key] = value.strip('"\'')
            
            logger.debug(f"Parsed arguments: {args}")
            
            # Execute tool
            if tool_name not in tools_config:
                raise ValueError(f"Unknown tool: {tool_name}")
                
            tool = tools_config[tool_name]
            logger.debug(f"Invoking tool {tool_name} with arguments {args}")
            result = await tool(**args)
            logger.debug(f"Tool result: {result}")
            
            return ToolResult(
                tool_name=tool_name,
                arguments=args,
                result=result
            )
        else:
            raise ValueError(f"Invalid plan format: {plan}")
            
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return ToolResult(
            tool_name="unknown",
            arguments={},
            result=None,
            error=str(e)
        )
