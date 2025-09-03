#!/usr/bin/env python3
"""
Minimal MCP server test
"""

import asyncio
import json
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent

class MinimalMCPServer:
    """Minimal MCP server for testing"""
    
    def __init__(self):
        self.server = Server("minimal-test")
        self._register_tools()
    
    def _register_tools(self):
        """Register tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List tools"""
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
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            if name == "test_tool":
                return CallToolResult(
                    content=[TextContent(type="text", text="Test tool called successfully")]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                )
    
    async def run(self):
        """Run the server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="minimal-test",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities=None,
                    ),
                ),
            )

async def main():
    """Main entry point"""
    server = MinimalMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())









