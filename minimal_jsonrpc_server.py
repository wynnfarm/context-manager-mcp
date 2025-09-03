#!/usr/bin/env python3
"""
Minimal JSON-RPC server without MCP library
"""

import asyncio
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinimalJSONRPCServer:
    """Minimal JSON-RPC server without MCP library"""
    
    def __init__(self):
        self.initialized = False
        self.tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    async def handle_request(self, request):
        """Handle JSON-RPC request"""
        try:
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})
            
            logger.info(f"🎯 Handling request: {method}")
            
            if method == "initialize":
                self.initialized = True
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {
                                "listChanged": False
                            }
                        },
                        "serverInfo": {
                            "name": "minimal-jsonrpc",
                            "version": "1.0.0"
                        }
                    }
                }
                logger.info("✅ Initialization successful")
                return response
            
            elif method == "tools/list":
                if not self.initialized:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32002,
                            "message": "Server not initialized",
                            "data": ""
                        }
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": self.tools
                        }
                    }
                    logger.info(f"✅ Tools/list successful, returning {len(self.tools)} tools")
                return response
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": ""
                    }
                }
                return response
                
        except Exception as e:
            logger.error(f"❌ Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def run(self):
        """Run the server"""
        logger.info("🚀 Starting Minimal JSON-RPC Server...")
        
        # Read from stdin, write to stdout
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                logger.debug(f"📥 Received: {line}")
                
                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)
                    response_line = json.dumps(response) + "\n"
                    await asyncio.get_event_loop().run_in_executor(None, sys.stdout.write, response_line)
                    await asyncio.get_event_loop().run_in_executor(None, sys.stdout.flush)
                    logger.debug(f"📤 Sent: {response_line.strip()}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                            "data": str(e)
                        }
                    }
                    error_line = json.dumps(error_response) + "\n"
                    await asyncio.get_event_loop().run_in_executor(None, sys.stdout.write, error_line)
                    await asyncio.get_event_loop().run_in_executor(None, sys.stdout.flush)
                    
            except Exception as e:
                logger.error(f"❌ Error reading input: {e}")
                break

async def main():
    """Main entry point"""
    try:
        server = MinimalJSONRPCServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
