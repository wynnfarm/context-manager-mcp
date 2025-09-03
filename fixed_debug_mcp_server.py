#!/usr/bin/env python3
"""
Fixed Debug MCP Server - Following Working Pattern
"""

import asyncio
import json
import logging
import sys
import time
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent, ListToolsRequest

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FixedDebugMCPServer:
    """Fixed Debug MCP server following working pattern"""
    
    def __init__(self):
        self.server = Server("fixed-debug-test")
        self._register_tools()
    
    def _register_tools(self):
        """Register a simple test tool"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools"""
            logger.info("🎯 LIST_TOOLS called!")
            tools = [
                Tool(
                    name="debug_tool",
                    description="A debug tool to test Cursor IDE integration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "test_message": {
                                "type": "string",
                                "description": "Test message to echo back"
                            }
                        },
                        "required": ["test_message"]
                    }
                )
            ]
            logger.info(f"📋 Returning {len(tools)} tools")
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            logger.info(f"🎯 CALL_TOOL called: {name}")
            logger.info(f"📝 Arguments: {arguments}")
            if name == "debug_tool":
                message = arguments.get("test_message", "No message provided")
                logger.info(f"✅ Echoing back: {message}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"✅ Debug Echo: {message}")]
                )
            else:
                logger.warning(f"❌ Unknown tool: {name}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True
                )
    
    async def run(self):
        """Run the MCP server"""
        try:
            logger.info("🚀 Starting Fixed Debug MCP Server...")
            logger.info("📡 Waiting for connections...")
            async with stdio_server() as (read_stream, write_stream):
                logger.info("✅ stdio_server initialized")
                logger.info("🔄 Starting server.run()...")
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="fixed-debug-test",
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
        logger.info("🎯 Initializing Fixed Debug MCP Server...")
        server = FixedDebugMCPServer()
        logger.info("✅ Server initialized, starting...")
        await server.run()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
