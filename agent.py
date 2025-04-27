import asyncio
import time
import os
import datetime
from perception import extract_perception
from memory import MemoryManager, MemoryItem
from decision import generate_plan
from action import execute_tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import shutil
import sys
import signal
import warnings
import asyncio.proactor_events
import atexit

def log(stage: str, msg: str, error: bool = False):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    if error:
        print(f"[{now}] [error] {msg}", file=sys.stderr)
    else:
        print(f"[{now}] [{stage}] {msg}")

max_steps = 3

# Suppress all ResourceWarnings and RuntimeWarnings during shutdown
warnings.filterwarnings('ignore', category=ResourceWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

def custom_exception_handler(loop, context):
    """Custom exception handler to make shutdown messages more informational."""
    # Don't show exceptions during shutdown
    if loop.is_closed() or 'Event loop is closed' in str(context.get('exception', '')):
        return
    
    # Show other exceptions normally
    exception = context.get('exception')
    if exception:
        log('error', str(exception), error=True)

async def cleanup_transports(loop):
    """Clean up any remaining transports."""
    try:
        if hasattr(loop, '_proactor'):
            for transport in list(getattr(loop._proactor, '_unregistered', [])):
                if hasattr(transport, 'close'):
                    transport.close()
    except Exception:
        pass  # Suppress cleanup errors

def cleanup_on_exit():
    """Handle any final cleanup when the program exits."""
    # Suppress any remaining warnings or errors
    try:
        loop = asyncio._get_running_loop()
        if loop and not loop.is_closed():
            loop.close()
    except Exception:
        pass

async def main(user_input: str):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(custom_exception_handler)
    
    try:
        log("agent", "Starting agent...")
        log("agent", f"Current working directory: {os.getcwd()}")
        
        server_params = StdioServerParameters(
            command="python",
            args=["mcp-tools.py"],
            cwd=os.getcwd()
        )

        async with stdio_client(server_params) as (read, write):
            log("agent", "Connection established, creating session...")
            async with ClientSession(read, write) as session:
                log("agent", "Session created, initializing...")
                await session.initialize()
                log("agent", "MCP session initialized")

                # Get available tools
                tools_result = await session.list_tools()
                tools = tools_result.tools
                tool_descriptions = "\n".join(
                    f"- {tool.name}: {getattr(tool, 'description', 'No description')}" 
                    for tool in tools
                )

                log("agent", f"{len(tools)} tools loaded")

                memory = MemoryManager()
                session_id = f"session-{int(time.time())}"
                query = user_input  # Store original intent
                step = 0

                while step < max_steps:
                    log("loop", f"Step {step + 1} started")

                    perception = extract_perception(user_input)
                    log("perception", f"Intent: {perception.intent}, Tool hint: {perception.tool_hint}")

                    retrieved = memory.retrieve(query=user_input, top_k=3, session_filter=session_id)
                    log("memory", f"Retrieved {len(retrieved)} relevant memories")

                    plan = generate_plan(perception, retrieved, tool_descriptions=tool_descriptions)
                    log("plan", f"Plan generated: {plan}")

                    if plan.startswith("FINAL_ANSWER:"):
                        log("agent", f"✅ FINAL RESULT: {plan}")
                        break

                    try:
                        result = await execute_tool(session, tools, plan)
                        log("tool", f"{result.tool_name} returned: {result.result}")

                        memory.add(MemoryItem(
                            text=f"Tool call: {result.tool_name} with {result.arguments}, got: {result.result}",
                            type="tool_output",
                            tool_name=result.tool_name,
                            user_query=user_input,
                            tags=[result.tool_name],
                            session_id=session_id
                        ))

                        user_input = f"Original task: {query}\nPrevious output: {result.result}\nWhat should I do next?"

                    except Exception as e:
                        log("error", f"Tool execution failed: {e}", error=True)
                        break

                    step += 1

    except Exception as e:
        log("error", str(e), error=True)
    finally:
        log("agent", "Starting graceful shutdown...")
        # Clean up any remaining tasks
        pending = [task for task in asyncio.all_tasks(loop) 
                  if task is not asyncio.current_task(loop)]
        if pending:
            for task in pending:
                task.cancel()
            try:
                await asyncio.wait(pending, timeout=1)
            except Exception:
                pass
        
        # Clean up transports
        await cleanup_transports(loop)
        log("agent", "Shutdown complete ✓")

def handle_sigint(signum, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    log("agent", "Received interrupt signal, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register cleanup handler
    atexit.register(cleanup_on_exit)
    
    # Set up signal handler
    signal.signal(signal.SIGINT, handle_sigint)
    
    try:
        query = input("🧑 What do you want to solve today? → ")
        asyncio.run(main(query))
    except KeyboardInterrupt:
        log("agent", "Received keyboard interrupt, shutting down...")
    except Exception as e:
        log("error", str(e), error=True)

# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?