from typing import Dict, List, Tuple
from contextlib import AsyncExitStack

from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def load_mcp_server_tools(configs: Dict[str, Dict[str, any]]) -> Tuple[AsyncExitStack, Dict, List]:
    """
    Load tools from multiple MCP servers with stateful sessions.
    
    This function initializes connections to multiple MCP servers and loads their tools
    into a unified interface. Each server maintains a persistent session throughout
    the execution lifecycle.
    
    Args:
        configs: Dictionary mapping server names to their configurations.
                Each config should contain:
                - command: str - The command to run the MCP server
                - args: List[str] - Arguments for the command
                - env: Optional[Dict] - Environment variables
                
                Example:
                {
                    "playwright": {
                        "command": "npx",
                        "args": ["-y", "@playwright/mcp@latest", "--isolated"]
                    },
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/workspace"]
                    }
                }
    
    Returns:
        Tuple containing:
        - AsyncExitStack: Context manager that must be kept alive to maintain sessions
        - Dict: Sessions dictionary with server info and tools per server
                Format: {server_name: {"session": ClientSession, "tools": List[Tool]}}
        - List: Combined list of all tools from all servers
    
    Raises:
        Exception: If any server fails to initialize
    
    Example:
        >>> configs = {
        ...     "playwright": {
        ...         "command": "npx",
        ...         "args": ["-y", "@playwright/mcp@latest", "--isolated"]
        ...     }
        ... }
        >>> stack, sessions, tools = await load_mcp_server_tools(configs)
        >>> async with stack:
        ...     # Use tools here
        ...     pass
    """
    stack = AsyncExitStack()
    sessions = {}
    all_tools = []
    
    for server_name, config in configs.items():
        try:
            server_params = StdioServerParameters(
                command=config["command"],
                args=config["args"],
                env=None
            )
            
            # Open client connection
            read, write = await stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # Create session
            session = await stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # Initialize session
            await session.initialize()
            
            # Load tools from this session
            tools = await load_mcp_tools(session)

            # Remove $schema and additionalProperties from args_schema
            # because the bind_tools function does not support these keys
            for tool in tools:
                if hasattr(tool, "args_schema") and isinstance(tool.args_schema, dict):
                    tool.args_schema.pop("$schema", None)
                    tool.args_schema.pop("additionalProperties", None)
            
            # Store session and tools
            sessions[server_name] = {
                "session": session,
                "tools": tools
            }
            all_tools.extend(tools)
            
            print(f"Loaded {len(tools)} tools from {server_name}")
            
        except Exception as e:
            print(f"Failed to load tools from {server_name}: {e}")
            raise

    return stack, sessions, all_tools

