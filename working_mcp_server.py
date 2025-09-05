#!/usr/bin/env python3
"""
Working MCP Server - Direct JSON-RPC Implementation
Bypasses MCP library issues by implementing the protocol directly
"""

import asyncio
import json
import sys
import logging
from typing import Dict, List, Any

from core import ContextManager, ContextAnchor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkingMCPServer:
    """Working MCP Server using direct JSON-RPC implementation"""
    
    def __init__(self):
        self.context_managers: Dict[str, ContextManager] = {}
        self.initialized = False
    
    def _get_context_manager(self, project_name: str) -> ContextManager:
        """Get or create a context manager for a project"""
        if project_name not in self.context_managers:
            self.context_managers[project_name] = ContextManager(project_name)
        return self.context_managers[project_name]
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC requests"""
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        
        logger.info(f"Handling request: {method}")
        
        try:
            if method == "initialize":
                return {
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
                            "name": "context-manager",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "notifications/initialized":
                self.initialized = True
                return None  # Notification, no response
            
            elif method == "tools/list":
                tools = [
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
                        "description": "Add a completed feature to the project status",
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
                        "description": "Add a current issue to track in the project",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "project_name": {
                                    "type": "string",
                                    "description": "Name of the project"
                                },
                                "problem": {
                                    "type": "string",
                                    "description": "Description of the problem"
                                },
                                "location": {
                                    "type": "string",
                                    "description": "Where the problem occurs"
                                },
                                "root_cause": {
                                    "type": "string",
                                    "description": "Root cause of the problem"
                                },
                                "status": {
                                    "type": "string",
                                    "description": "Status of the issue (open/resolved)"
                                }
                            },
                            "required": ["project_name", "problem"]
                        }
                    },
                    {
                        "name": "resolve_issue",
                        "description": "Mark an issue as resolved",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "project_name": {
                                    "type": "string",
                                    "description": "Name of the project"
                                },
                                "problem": {
                                    "type": "string",
                                    "description": "Description of the problem to resolve"
                                }
                            },
                            "required": ["project_name", "problem"]
                        }
                    },
                    {
                        "name": "add_next_step",
                        "description": "Add a next step to the project",
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
                        "description": "Add a context anchor to maintain important information",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "project_name": {
                                    "type": "string",
                                    "description": "Name of the project"
                                },
                                "key": {
                                    "type": "string",
                                    "description": "Key identifier for the anchor"
                                },
                                "value": {
                                    "type": "string",
                                    "description": "Value/content of the anchor"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Description of what this anchor represents"
                                },
                                "priority": {
                                    "type": "integer",
                                    "description": "Priority level (1=high, 2=medium, 3=low)",
                                    "default": 1
                                }
                            },
                            "required": ["project_name", "key", "value", "description"]
                        }
                    },
                    {
                        "name": "list_projects",
                        "description": "List all available projects",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": tools
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "get_project_context":
                    return await self._get_project_context(request_id, arguments)
                elif tool_name == "set_current_goal":
                    return await self._set_current_goal(request_id, arguments)
                elif tool_name == "add_completed_feature":
                    return await self._add_completed_feature(request_id, arguments)
                elif tool_name == "add_current_issue":
                    return await self._add_current_issue(request_id, arguments)
                elif tool_name == "resolve_issue":
                    return await self._resolve_issue(request_id, arguments)
                elif tool_name == "add_next_step":
                    return await self._add_next_step(request_id, arguments)
                elif tool_name == "add_context_anchor":
                    return await self._add_context_anchor(request_id, arguments)
                elif tool_name == "list_projects":
                    return await self._list_projects(request_id, arguments)
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }
        
        except Exception as e:
            logger.error(f"Error handling request {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _get_project_context(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get project context"""
        project_name = arguments["project_name"]
        context_manager = self._get_context_manager(project_name)
        
        # Load existing context
        context_manager.load_status()
        
        if context_manager.status:
            project_info = {
                "project_name": context_manager.status.name,
                "current_goal": context_manager.status.current_goal,
                "completed_features": context_manager.status.completed_features,
                "current_issues": context_manager.status.current_issues,
                "next_steps": context_manager.status.next_steps,
                "context_anchors": [
                    {
                        "key": anchor.key,
                        "value": anchor.value,
                        "description": anchor.description,
                        "priority": anchor.priority
                    }
                    for anchor in context_manager.status.context_anchors
                ],
                "last_updated": context_manager.status.last_updated.isoformat()
            }
        else:
            project_info = {
                "project_name": project_name,
                "current_goal": "No goal set",
                "completed_features": [],
                "current_issues": [],
                "next_steps": [],
                "context_anchors": [],
                "last_updated": "Never"
            }
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(project_info, indent=2)
                    }
                ]
            }
        }
    
    async def _set_current_goal(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Set current goal"""
        project_name = arguments["project_name"]
        goal = arguments["goal"]
        
        context_manager = self._get_context_manager(project_name)
        context_manager.set_current_goal(goal)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Set goal for {project_name}: {goal}"
                    }
                ]
            }
        }
    
    async def _add_completed_feature(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add completed feature"""
        project_name = arguments["project_name"]
        feature = arguments["feature"]
        
        context_manager = self._get_context_manager(project_name)
        context_manager.add_completed_feature(feature)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Added completed feature to {project_name}: {feature}"
                    }
                ]
            }
        }
    
    async def _add_current_issue(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add current issue"""
        project_name = arguments["project_name"]
        problem = arguments["problem"]
        location = arguments.get("location", "Unknown")
        root_cause = arguments.get("root_cause", "Unknown")
        status = arguments.get("status", "open")
        
        context_manager = self._get_context_manager(project_name)
        context_manager.add_current_issue(problem, location, root_cause, status)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Added issue to {project_name}: {problem}"
                    }
                ]
            }
        }
    
    async def _resolve_issue(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve issue"""
        project_name = arguments["project_name"]
        problem = arguments["problem"]
        
        context_manager = self._get_context_manager(project_name)
        context_manager.resolve_issue(problem)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Resolved issue in {project_name}: {problem}"
                    }
                ]
            }
        }
    
    async def _add_next_step(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add next step"""
        project_name = arguments["project_name"]
        step = arguments["step"]
        
        context_manager = self._get_context_manager(project_name)
        context_manager.add_next_step(step)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Added next step to {project_name}: {step}"
                    }
                ]
            }
        }
    
    async def _add_context_anchor(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add context anchor"""
        project_name = arguments["project_name"]
        key = arguments["key"]
        value = arguments["value"]
        description = arguments["description"]
        priority = arguments.get("priority", 1)
        
        context_manager = self._get_context_manager(project_name)
        context_manager.add_context_anchor(key, value, description, priority)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Added context anchor to {project_name}: {key}"
                    }
                ]
            }
        }
    
    async def _list_projects(self, request_id: int, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all projects"""
        from pathlib import Path
        
        # Get all context files in the current directory
        current_dir = Path.cwd()
        context_files = list(current_dir.glob("*_context_cache.json"))
        
        projects = []
        for context_file in context_files:
            project_name = context_file.stem.replace("_context_cache", "")
            projects.append(project_name)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(projects, indent=2)
                    }
                ]
            }
        }
    
    async def run(self):
        """Run the server"""
        logger.info("Starting Working MCP Server...")
        
        while True:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue
                
                # Handle the request
                response = await self.handle_request(request)
                
                # Send response if there is one (notifications don't have responses)
                if response is not None:
                    print(json.dumps(response))
                    sys.stdout.flush()
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                break

async def main():
    """Main entry point"""
    server = WorkingMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())