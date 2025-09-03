#!/usr/bin/env python3
"""
AWS MCP Proxy Server
This acts as a local MCP server that forwards requests to our AWS Lambda endpoint.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSMCPProxy:
    def __init__(self):
        self.api_url = "https://gzpp3ch0mc.execute-api.us-east-1.amazonaws.com/dev/mcp"
        self.api_key = "7ed6f60abbe0444755d1b4bddcca70213e05ab2560d31bc4fbdb890c82803ad7"
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        await self.http_client.aclose()
    
    async def forward_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Forward MCP request to AWS Lambda endpoint"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            
            response = await self.http_client.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return result["result"]
                elif "error" in result:
                    logger.error(f"AWS Error: {result['error']}")
                    raise Exception(f"AWS Error: {result['error']}")
                else:
                    raise Exception("Invalid response format from AWS")
            else:
                logger.error(f"HTTP Error: {response.status_code} - {response.text}")
                raise Exception(f"HTTP Error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            raise

async def main():
    """Main function to run the MCP proxy server"""
    proxy = AWSMCPProxy()
    
    # Create MCP server
    server = Server("aws-mcp-proxy")
    
    @server.list_tools()
    async def handle_list_tools() -> ListToolsResult:
        """List available tools by forwarding to AWS"""
        try:
            result = await proxy.forward_request("tools/list", {})
            tools = []
            for tool_data in result.get("tools", []):
                tools.append(Tool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    inputSchema=tool_data.get("inputSchema", {})
                ))
            return ListToolsResult(tools=tools)
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            # Return basic tools as fallback
            return ListToolsResult(tools=[
                Tool(
                    name="system.server_status",
                    description="Get the status of the MCP server",
                    inputSchema={"type": "object", "properties": {}, "required": []}
                ),
                Tool(
                    name="system.list_available_tools", 
                    description="List all available tools",
                    inputSchema={"type": "object", "properties": {}, "required": []}
                )
            ])
    
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Call a tool by forwarding to AWS"""
        try:
            result = await proxy.forward_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
            
            content = []
            if "content" in result:
                for item in result["content"]:
                    if item["type"] == "text":
                        content.append(TextContent(type="text", text=item["text"]))
            
            return CallToolResult(content=content)
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return CallToolResult(content=[
                TextContent(type="text", text=f"Error: {str(e)}")
            ])
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="aws-mcp-proxy",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions()
                )
            )
        )
    
    await proxy.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
