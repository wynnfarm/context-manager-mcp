#!/usr/bin/env python3
"""
Debug MCP server with enhanced logging
"""

import asyncio
import logging
import sys
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent, ListToolsRequest

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DebugMCPServer:
    """Debug MCP server with enhanced logging"""
    
    def __init__(self):
        self.server = Server("debug-test")
        self._register_tools()
    
    def _register_tools(self):
        """Register a simple test tool with debug logging"""
        
        @self.server.list_tools()
        async def handle_list_tools():
            """List available tools - returns list[Tool]"""
            logger.info("🎯 LIST_TOOLS called!")
            logger.debug("🎯 LIST_TOOLS handler executed")
            try:
                tool = Tool(
                    name="test_tool",
                    description="A simple test tool",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
                logger.info(f"📋 Returning 1 tool: {tool.name}")
                logger.debug(f"📋 Tool details: {tool}")
                return [tool]  # Return list[Tool], not ListToolsResult
            except Exception as e:
                logger.error(f"❌ Error in handle_list_tools: {e}")
                logger.exception("Full traceback:")
                raise
        
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
            logger.info("🚀 Starting Debug MCP Server...")
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="debug-test",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities=None,
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"❌ Error running MCP server: {e}")
            logger.exception("Full traceback:")
            raise

async def main():
    """Main entry point"""
    try:
        server = DebugMCPServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
