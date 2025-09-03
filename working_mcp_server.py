#!/usr/bin/env python3
"""
Exact copy of working persona-manager pattern
"""

import asyncio
import logging
import sys
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkingMCPServer:
    """Working MCP server using exact persona-manager pattern"""
    
    def __init__(self):
        self.server = Server("working-test")
        self._register_tools()
    
    def _register_tools(self):
        """Register tools using exact persona-manager pattern"""
        
        @self.server.list_tools()
        async def handle_list_tools():
            """List all available tools - exact persona-manager pattern"""
            tools = [
                Tool(
                    name="test_tool",
                    description="A test tool",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            return CallToolResult(
                content=[TextContent(type="text", text=f"Hello from {name}!")]
            )
    
    async def run(self):
        """Run the MCP server"""
        try:
            logger.info("🚀 Starting Working MCP Server...")
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="working-test",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities=None,
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"❌ Error running MCP server: {e}")
            raise

async def main():
    """Main entry point"""
    try:
        server = WorkingMCPServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
