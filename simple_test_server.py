#!/usr/bin/env python3
"""
Simple MCP Server for Cursor IDE Testing
"""

import asyncio
import json
import logging
import sys
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMCPServer:
    """Simple MCP server for testing Cursor IDE integration"""
    
    def __init__(self):
        self.server = Server("simple-test")
        self._register_tools()
    
    def _register_tools(self):
        """Register a simple test tool"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools"""
            logger.info("Listing tools...")
            tools = [
                Tool(
                    name="test_tool",
                    description="A simple test tool for Cursor IDE",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Message to echo back"
                            }
                        },
                        "required": ["message"]
                    }
                )
            ]
            logger.info(f"Returning {len(tools)} tools")
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            logger.info(f"Handling tool call: {name} with arguments: {arguments}")
            if name == "test_tool":
                message = arguments.get("message", "No message provided")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"✅ Echo: {message}")]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True
                )
    
    async def run(self):
        """Run the MCP server"""
        try:
            logger.info("Starting simple MCP server...")
            async with stdio_server() as (read_stream, write_stream):
                logger.info("stdio_server initialized")
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="simple-test",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities=None,
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"Error running MCP server: {e}")
            raise

async def main():
    """Main entry point"""
    try:
        logger.info("Initializing Simple MCP Server...")
        server = SimpleMCPServer()
        logger.info("Server initialized, starting...")
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())























