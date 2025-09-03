#!/usr/bin/env python3
"""
Secure AWS Lambda Handler for MCP Server

This handler adapts the MCP server to work with AWS Lambda and API Gateway.
It includes authentication, rate limiting, and security features.
"""

import json
import logging
import os
import sys
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add the Lambda package directory to Python path
sys.path.insert(0, '/opt/python/lib/python3.11/site-packages')

# Import MCP server components
try:
    from centralized_mcp_server import CentralizedMCPServer
except ImportError:
    # Fallback for local testing
    sys.path.insert(0, str(Path(__file__).parent))
    from centralized_mcp_server import CentralizedMCPServer


class SecureLambdaMCPServer:
    """Secure Lambda-compatible MCP Server wrapper"""
    
    def __init__(self):
        self.server = CentralizedMCPServer()
        self.api_key = os.environ.get('API_KEY')
        self.rate_limit_per_minute = int(os.environ.get('RATE_LIMIT_PER_MINUTE', 100))
        self.rate_limit_cache = {}
        logger.info("Secure Lambda MCP Server initialized")
    
    def authenticate_request(self, event: Dict[str, Any]) -> bool:
        """Authenticate the request using API key"""
        if not self.api_key:
            logger.warning("No API key configured, skipping authentication")
            return True
        
        headers = event.get('headers', {})
        api_key = headers.get('X-API-Key') or headers.get('x-api-key')
        
        if not api_key:
            logger.warning("No API key provided in request")
            return False
        
        if api_key != self.api_key:
            logger.warning("Invalid API key provided")
            return False
        
        return True
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if the client is within rate limits"""
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Clean old entries
        self.rate_limit_cache = {
            ip: timestamps for ip, timestamps in self.rate_limit_cache.items()
            if any(ts > minute_ago for ts in timestamps)
        }
        
        # Get client's request timestamps
        client_requests = self.rate_limit_cache.get(client_ip, [])
        client_requests = [ts for ts in client_requests if ts > minute_ago]
        
        # Check if client is within limit
        if len(client_requests) >= self.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return False
        
        # Add current request
        client_requests.append(current_time)
        self.rate_limit_cache[client_ip] = client_requests
        
        return True
    
    def get_client_ip(self, event: Dict[str, Any]) -> str:
        """Extract client IP from the event"""
        headers = event.get('headers', {})
        
        # Try various headers for client IP
        for header in ['X-Forwarded-For', 'X-Real-IP', 'X-Client-IP']:
            if header in headers:
                return headers[header].split(',')[0].strip()
        
        # Fallback to source IP
        return event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    
    def add_security_headers(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Add security headers to the response"""
        headers = response.get('headers', {})
        
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        headers.update(security_headers)
        response['headers'] = headers
        return response
    
    def handle_mcp_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol requests via HTTP with security checks"""
        
        try:
            # Get client IP for rate limiting
            client_ip = self.get_client_ip(event)
            
            # Check rate limit
            if not self.check_rate_limit(client_ip):
                return {
                    'statusCode': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests, please try again later'
                    })
                }
            
            # Authenticate request
            if not self.authenticate_request(event):
                return {
                    'statusCode': 401,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Unauthorized',
                        'message': 'Invalid or missing API key'
                    })
                }
            
            # Parse the request body
            body = event.get('body', '{}')
            if isinstance(body, str):
                body = json.loads(body)
            
            # Extract MCP protocol information
            method = body.get('method')
            params = body.get('params', {})
            id = body.get('id')
            
            logger.info(f"Handling MCP request: {method} from IP: {client_ip}")
            
            # Route to appropriate handler
            if method == 'tools/list':
                result = self._handle_list_tools()
            elif method == 'tools/call':
                result = self._handle_call_tool(params)
            else:
                result = {
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }
            
            # Return JSON-RPC response with security headers
            response = {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'jsonrpc': '2.0',
                    'id': id,
                    'result': result
                })
            }
            
            return self.add_security_headers(response)
            
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'jsonrpc': '2.0',
                    'id': id if 'id' in locals() else None,
                    'error': {
                        'code': -32603,
                        'message': f'Internal error: {str(e)}'
                    }
                })
            }
    
    def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list method"""
        try:
            # Get tools from the centralized server
            tools = []
            
            # Context Manager Tools
            tools.extend([
                {
                    'name': 'context_manager.get_project_context',
                    'description': 'Get the current context for a project',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'project_name': {
                                'type': 'string',
                                'description': 'Name of the project to get context for'
                            }
                        },
                        'required': ['project_name']
                    }
                },
                {
                    'name': 'context_manager.set_current_goal',
                    'description': 'Set the current primary goal for a project',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'project_name': {
                                'type': 'string',
                                'description': 'Name of the project'
                            },
                            'goal': {
                                'type': 'string',
                                'description': 'The primary goal to set'
                            }
                        },
                        'required': ['project_name', 'goal']
                    }
                },
                {
                    'name': 'context_manager.add_completed_feature',
                    'description': 'Add a completed feature to the project status',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'project_name': {
                                'type': 'string',
                                'description': 'Name of the project'
                            },
                            'feature': {
                                'type': 'string',
                                'description': 'Description of the completed feature'
                            }
                        },
                        'required': ['project_name', 'feature']
                    }
                },
                {
                    'name': 'context_manager.add_current_issue',
                    'description': 'Add a current issue to track in the project',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'project_name': {
                                'type': 'string',
                                'description': 'Name of the project'
                            },
                            'issue': {
                                'type': 'string',
                                'description': 'Description of the current issue'
                            }
                        },
                        'required': ['project_name', 'issue']
                    }
                },
                {
                    'name': 'context_manager.get_project_status',
                    'description': 'Get comprehensive project status including goals, features, and issues',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'project_name': {
                                'type': 'string',
                                'description': 'Name of the project'
                            }
                        },
                        'required': ['project_name']
                    }
                },
                {
                    'name': 'context_manager.create_project',
                    'description': 'Create a new project context',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'project_name': {
                                'type': 'string',
                                'description': 'Name of the new project'
                            },
                            'description': {
                                'type': 'string',
                                'description': 'Description of the project'
                            }
                        },
                        'required': ['project_name', 'description']
                    }
                }
            ])
            
            # System Tools
            tools.extend([
                {
                    'name': 'system.list_available_tools',
                    'description': 'List all available tools in the centralized server',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                },
                {
                    'name': 'system.server_status',
                    'description': 'Get the status of the centralized MCP server',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                }
            ])
            
            return {'tools': tools}
            
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise
    
    def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call method"""
        try:
            name = params.get('name')
            arguments = params.get('arguments', {})
            
            if not name:
                raise ValueError("Tool name is required")
            
            # Route to appropriate handler
            if name.startswith('context_manager.'):
                result = self._handle_context_manager_tool(name, arguments)
            elif name.startswith('system.'):
                result = self._handle_system_tool(name, arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
            
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': result
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error calling tool: {e}")
            raise
    
    def _handle_context_manager_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle context manager specific tools"""
        
        tool_name = name.replace('context_manager.', '')
        project_name = arguments.get('project_name')
        
        # Ensure context manager exists for the project
        if project_name and project_name not in self.server.context_managers:
            self.server.context_managers[project_name] = self.server.context_managers.get(project_name, None)
            if not self.server.context_managers[project_name]:
                # Create new context manager
                from core import ContextManager
                self.server.context_managers[project_name] = ContextManager(project_name)
        
        if tool_name == 'get_project_context':
            if not project_name:
                raise ValueError("project_name is required")
            
            context_manager = self.server.context_managers[project_name]
            context = context_manager.get_current_context()
            return json.dumps(context, indent=2)
        
        elif tool_name == 'set_current_goal':
            if not project_name or 'goal' not in arguments:
                raise ValueError("project_name and goal are required")
            
            context_manager = self.server.context_managers[project_name]
            context_manager.set_current_goal(arguments['goal'])
            return f"Goal set for {project_name}: {arguments['goal']}"
        
        elif tool_name == 'add_completed_feature':
            if not project_name or 'feature' not in arguments:
                raise ValueError("project_name and feature are required")
            
            context_manager = self.server.context_managers[project_name]
            context_manager.add_completed_feature(arguments['feature'])
            return f"Feature added to {project_name}: {arguments['feature']}"
        
        elif tool_name == 'add_current_issue':
            if not project_name or 'issue' not in arguments:
                raise ValueError("project_name and issue are required")
            
            context_manager = self.server.context_managers[project_name]
            context_manager.add_current_issue(arguments['issue'])
            return f"Issue added to {project_name}: {arguments['issue']}"
        
        elif tool_name == 'get_project_status':
            if not project_name:
                raise ValueError("project_name is required")
            
            context_manager = self.server.context_managers[project_name]
            status = context_manager.get_project_status()
            return json.dumps(status, indent=2)
        
        elif tool_name == 'create_project':
            if not project_name or 'description' not in arguments:
                raise ValueError("project_name and description are required")
            
            from core import ContextManager
            context_manager = ContextManager(project_name)
            context_manager.set_project_description(arguments['description'])
            self.server.context_managers[project_name] = context_manager
            
            return f"Project created: {project_name}"
        
        else:
            raise ValueError(f"Unknown context manager tool: {tool_name}")
    
    def _handle_system_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle system-level tools"""
        
        tool_name = name.replace('system.', '')
        
        if tool_name == 'list_available_tools':
            tools_list = [
                'context_manager.get_project_context',
                'context_manager.set_current_goal', 
                'context_manager.add_completed_feature',
                'context_manager.add_current_issue',
                'context_manager.get_project_status',
                'context_manager.create_project',
                'system.list_available_tools',
                'system.server_status'
            ]
            return json.dumps(tools_list, indent=2)
        
        elif tool_name == 'server_status':
            status = {
                'server': 'Secure Lambda MCP Server',
                'status': 'running',
                'active_projects': list(self.server.context_managers.keys()),
                'timestamp': datetime.now().isoformat(),
                'environment': os.environ.get('ENVIRONMENT', 'unknown'),
                'security': {
                    'authentication': 'enabled' if self.api_key else 'disabled',
                    'rate_limiting': f'{self.rate_limit_per_minute} requests/minute'
                }
            }
            return json.dumps(status, indent=2)
        
        else:
            raise ValueError(f"Unknown system tool: {tool_name}")


# Global instance for Lambda
mcp_server = SecureLambdaMCPServer()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function with security features"""
    
    # Handle CORS preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': ''
        }
    
    # Handle MCP requests
    if event.get('httpMethod') == 'POST':
        return mcp_server.handle_mcp_request(event)
    
    # Handle unsupported methods
    return {
        'statusCode': 405,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': 'Method not allowed'
        })
    }
