#!/usr/bin/env python3
"""
Test with different server pattern
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

class DifferentMCPServer:
    """Different MCP server pattern"""
    
    def __init__(self):
        self.server = Server("different-test")
        self._register_tools()
    
    def _register_tools(self):
        """Register tools with different pattern"""
        
        # Try registering tools directly without decorator
        async def list_tools_handler():
            """List available tools"""
            logger.info("🎯 LIST_TOOLS called!")
            tool = Tool(
                name="test_tool",
                description="A test tool",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
            logger.info(f"📋 Returning 1 tool: {tool.name}")
            return [tool]
        
        # Register the handler directly
        self.server.request_handlers[type('ListToolsRequest', (), {})] = list_tools_handler
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            logger.info(f"🎯 CALL_TOOL called: {name}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Hello from {name}!")]
            )
    
    async def run(self):
        """Run the MCP server"""
        try:
            logger.info("🚀 Starting Different MCP Server...")
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="different-test",
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
        server = DifferentMCPServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
