#!/usr/bin/env python3
"""
Simple AWS MCP Proxy Server
A minimal MCP server that forwards requests to AWS Lambda
"""

import json
import sys
import httpx
import asyncio
from typing import Dict, Any

class SimpleMCPProxy:
    def __init__(self):
        self.api_url = "https://gzpp3ch0mc.execute-api.us-east-1.amazonaws.com/dev/mcp"
        self.api_key = "7ed6f60abbe0444755d1b4bddcca70213e05ab2560d31bc4fbdb890c82803ad7"
        
    async def forward_to_aws(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Forward request to AWS Lambda"""
        async with httpx.AsyncClient(timeout=30.0) as client:
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
            
            response = await client.post(self.api_url, headers=headers, json=payload)
            return response.json()

async def handle_mcp_protocol():
    """Handle MCP protocol via stdio"""
    proxy = SimpleMCPProxy()
    
    # Send initialization
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "aws-mcp-proxy",
                "version": "1.0.0"
            }
        }
    }
    
    print(json.dumps(init_message))
    sys.stdout.flush()
    
    # Handle incoming messages
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            message = json.loads(line.strip())
            method = message.get("method")
            params = message.get("params", {})
            msg_id = message.get("id")
            
            if method == "tools/list":
                # Forward to AWS
                result = await proxy.forward_to_aws("tools/list", {})
                
                # Send response
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result.get("result", {"tools": []})
                }
                print(json.dumps(response))
                sys.stdout.flush()
                
            elif method == "tools/call":
                # Forward to AWS
                result = await proxy.forward_to_aws("tools/call", params)
                
                # Send response
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result.get("result", {"content": []})
                }
                print(json.dumps(response))
                sys.stdout.flush()
                
        except Exception as e:
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    try:
        asyncio.run(handle_mcp_protocol())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
