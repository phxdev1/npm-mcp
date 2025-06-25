"""
Desktop MCP Server with zero-configuration plugin system.

Simply run the server and it automatically discovers and loads all available plugins.
"""

import asyncio
import logging
from typing import Any, Dict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .core.auto_discovery import ZeroConfigRegistry

logger = logging.getLogger(__name__)


class DesktopMCPServer:
    """Main Desktop MCP server with automatic plugin discovery."""
    
    def __init__(self):
        self.server = Server("desktop-mcp")
        self.registry = ZeroConfigRegistry()
        self.tools: Dict[str, Tool] = {}
        
    async def initialize(self) -> None:
        """Initialize the server and auto-load all plugins."""
        logger.info("Starting Desktop MCP Server...")
        
        # Auto-discover and load all plugins
        load_results = await self.registry.auto_load_all()
        
        successful_plugins = [name for name, success in load_results.items() if success]
        failed_plugins = [name for name, success in load_results.items() if not success]
        
        logger.info(f"Successfully loaded {len(successful_plugins)} plugins: {successful_plugins}")
        if failed_plugins:
            logger.warning(f"Failed to load {len(failed_plugins)} plugins: {failed_plugins}")
            
        # Register all plugin functions as MCP tools
        await self._register_plugin_tools()
        
        # Register server handlers
        self._setup_server_handlers()
        
        logger.info("Desktop MCP Server initialized successfully!")
        
    async def _register_plugin_tools(self) -> None:
        """Register all plugin functions as MCP tools."""
        for plugin_name, plugin in self.registry.loaded_plugins.items():
            try:
                if hasattr(plugin, 'get_mcp_functions'):
                    functions = plugin.get_mcp_functions()
                    for func_name, func in functions.items():
                        await self._register_tool(func_name, func, plugin)
                        
            except Exception as e:
                logger.error(f"Error registering tools for plugin {plugin_name}: {e}")
                
    async def _register_tool(self, func_name: str, func: callable, plugin: Any) -> None:
        """Register a single function as an MCP tool."""
        try:
            # Create tool schema (simplified for auto-discovery)
            # Use MCP naming convention that Claude expects
            mcp_tool_name = f"mcp__desktop-mcp__{func_name}"
            
            tool = Tool(
                name=mcp_tool_name,
                description=getattr(func, '__doc__', f"Function from {plugin.metadata.name} plugin"),
                inputSchema={
                    "type": "object",
                    "properties": {},  # Auto-detected plugins use flexible schemas
                    "additionalProperties": True
                }
            )
            
            self.tools[mcp_tool_name] = tool
            logger.info(f"Registered MCP tool: {func_name}")
                        
        except Exception as e:
            logger.error(f"Error registering tool {func_name}: {e}")
            
    def _setup_server_handlers(self) -> None:
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return list(self.tools.values())
            
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            """Call a tool by name."""
            # Strip MCP prefix to get actual function name
            actual_func_name = name
            if name.startswith("mcp__desktop-mcp__"):
                actual_func_name = name.replace("mcp__desktop-mcp__", "")
            
            # Find the plugin and function for this tool
            for plugin_name, plugin in self.registry.loaded_plugins.items():
                try:
                    if hasattr(plugin, 'get_mcp_functions'):
                        functions = plugin.get_mcp_functions()
                        if actual_func_name in functions:
                            func = functions[actual_func_name]
                            result = await func(**arguments)
                            return [TextContent(
                                type="text",
                                text=str(result)
                            )]
                except Exception as e:
                    return [TextContent(
                        type="text", 
                        text=f"Error calling {name}: {str(e)}"
                    )]
            
            return [TextContent(
                type="text",
                text=f"Tool {name} not found"
            )]
            
        @self.server.list_resources()
        async def list_resources():
            """List available resources."""
            return []
            
        @self.server.read_resource()
        async def read_resource(uri: str):
            """Read a resource."""
            return []
            
    async def run(self) -> None:
        """Run the MCP server."""
        await self.initialize()
        
        # Run stdio server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = DesktopMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())