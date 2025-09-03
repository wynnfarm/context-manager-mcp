#!/usr/bin/env python3
"""
Simple AWS Lambda Handler for MCP Server

This is a simplified version that works without complex dependencies.
"""

import json
import logging
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """AWS Lambda handler function with security features"""
    
    # Get API key from environment
    api_key = os.environ.get('API_KEY')
    
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
        try:
            # Authenticate request
            headers = event.get('headers', {})
            request_api_key = headers.get('X-API-Key') or headers.get('x-api-key')
            
            if api_key and request_api_key != api_key:
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
            
            logger.info(f"Handling MCP request: {method}")
            
            # Route to appropriate handler
            if method == 'tools/list':
                result = handle_list_tools()
            elif method == 'tools/call':
                result = handle_call_tool(params)
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
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'X-Content-Type-Options': 'nosniff',
                    'X-Frame-Options': 'DENY',
                    'X-XSS-Protection': '1; mode=block',
                    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                    'Content-Security-Policy': "default-src 'self'",
                    'Referrer-Policy': 'strict-origin-when-cross-origin'
                },
                'body': json.dumps({
                    'jsonrpc': '2.0',
                    'id': id,
                    'result': result
                })
            }
            
            return response
            
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

def handle_list_tools():
    """Handle tools/list method"""
    tools = [
        {
            'name': 'system.server_status',
            'description': 'Get the status of the MCP server',
            'inputSchema': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        },
        {
            'name': 'system.list_available_tools',
            'description': 'List all available tools',
            'inputSchema': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    ]
    return {'tools': tools}

def handle_call_tool(params):
    """Handle tools/call method"""
    try:
        name = params.get('name')
        arguments = params.get('arguments', {})
        
        if not name:
            raise ValueError("Tool name is required")
        
        if name == 'system.server_status':
            status = {
                'server': 'Secure Lambda MCP Server',
                'status': 'running',
                'timestamp': datetime.now().isoformat(),
                'environment': os.environ.get('ENVIRONMENT', 'unknown'),
                'security': {
                    'authentication': 'enabled' if os.environ.get('API_KEY') else 'disabled',
                    'rate_limiting': f'{os.environ.get("RATE_LIMIT_PER_MINUTE", "100")} requests/minute'
                }
            }
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps(status, indent=2)
                    }
                ]
            }
        
        elif name == 'system.list_available_tools':
            tools_list = [
                'system.server_status',
                'system.list_available_tools'
            ]
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps(tools_list, indent=2)
                    }
                ]
            }
        
        else:
            raise ValueError(f"Unknown tool: {name}")
        
    except Exception as e:
        logger.error(f"Error calling tool: {e}")
        raise
