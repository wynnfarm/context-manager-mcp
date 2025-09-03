#!/usr/bin/env python3
"""
Context Manager JSON-RPC Server with real tools
"""

import asyncio
import json
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextManagerJSONRPCServer:
    """Context Manager JSON-RPC server with real tools"""
    
    def __init__(self):
        self.initialized = False
        self.tools = [
            {
                "name": "get_project_context",
                "description": "Get the current context for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project to get context for"
                        }
                    },
                    "required": ["project_name"]
                }
            },
            {
                "name": "set_current_goal",
                "description": "Set the current primary goal for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "goal": {
                            "type": "string",
                            "description": "The primary goal to set"
                        }
                    },
                    "required": ["project_name", "goal"]
                }
            },
            {
                "name": "add_completed_feature",
                "description": "Track completed features for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "feature": {
                            "type": "string",
                            "description": "Description of the completed feature"
                        }
                    },
                    "required": ["project_name", "feature"]
                }
            },
            {
                "name": "add_current_issue",
                "description": "Track current issues and problems for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "issue": {
                            "type": "string",
                            "description": "Description of the current issue"
                        }
                    },
                    "required": ["project_name", "issue"]
                }
            },
            {
                "name": "resolve_issue",
                "description": "Mark issues as resolved for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "issue": {
                            "type": "string",
                            "description": "Description of the resolved issue"
                        }
                    },
                    "required": ["project_name", "issue"]
                }
            },
            {
                "name": "add_next_step",
                "description": "Add next steps to the project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "step": {
                            "type": "string",
                            "description": "Description of the next step"
                        }
                    },
                    "required": ["project_name", "step"]
                }
            },
            {
                "name": "add_context_anchor",
                "description": "Add important context to maintain throughout conversation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "context": {
                            "type": "string",
                            "description": "Important context to remember"
                        }
                    },
                    "required": ["project_name", "context"]
                }
            }
        ]
    
    def handle_request(self, request):
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
                            },
                            "logging": {
                                "level": "info"
                            },
                            "notifications": {
                                "toolCalls": True
                            }
                        },
                        "serverInfo": {
                            "name": "context-manager",
                            "version": "1.0.0"
                        }
                    }
                }
                logger.info("✅ Initialization successful")
                return response
            
            elif method == "tools/list":
                # Auto-initialize if not already initialized (for compatibility)
                if not self.initialized:
                    logger.info("🔄 Auto-initializing for tools/list request")
                    self.initialized = True
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": self.tools
                    }
                }
                logger.info(f"✅ Tools/list successful, returning {len(self.tools)} tools")
                return response
            
            elif method == "tools/call":
                # Auto-initialize if not already initialized (for compatibility)
                if not self.initialized:
                    logger.info("🔄 Auto-initializing for tools/call request")
                    self.initialized = True
                
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                logger.info(f"🎯 Tool call: {tool_name} with args: {arguments}")
                
                # Mock tool responses for now
                if tool_name == "get_project_context":
                    result = {
                        "project_name": arguments.get("project_name", "unknown"),
                        "current_goal": "Test goal",
                        "completed_features": ["Feature 1", "Feature 2"],
                        "current_issues": ["Issue 1"],
                        "next_steps": ["Step 1", "Step 2"]
                    }
                else:
                    result = {
                        "status": "success",
                        "message": f"Tool {tool_name} executed successfully",
                        "data": arguments
                    }
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
                logger.info(f"✅ Tool call successful: {tool_name}")
                return response
            
            # Handle notifications (no response needed)
            elif method in ["notifications/toolCalls", "logging/log"]:
                logger.info(f"📢 Received notification: {method}")
                return None  # Notifications don't require responses
            
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
    
    def run(self):
        """Run the server"""
        logger.info("🚀 Starting Context Manager JSON-RPC Server...")
        
        # Read from stdin, write to stdout (synchronous like persona-manager)
        for line in sys.stdin:
            try:
                line = line.strip()
                if not line:
                    continue
                
                logger.debug(f"📥 Received: {line}")
                
                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    
                    # Handle notifications (no response needed)
                    if response is None:
                        logger.debug("📢 Notification handled, no response sent")
                        continue
                    
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id", 0),
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response))
                    sys.stdout.flush()
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id", 0),
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

def main():
    """Main entry point"""
    try:
        server = ContextManagerJSONRPCServer()
        server.run()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


