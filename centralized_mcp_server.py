#!/usr/bin/env python3
"""
Centralized MCP Tool Server

This server hosts multiple MCP tools in a single process, making it easy to
manage and deploy multiple tools from one location.
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

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import our tools
from core import ContextManager, ContextAnchor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CentralizedMCPServer:
    """Centralized MCP Server hosting multiple tools"""
    
    def __init__(self):
        self.server = Server("centralized-mcp-server")
        self.context_managers: Dict[str, ContextManager] = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools with the MCP server."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List all available tools from all services."""
            tools = []
            
            # Context Manager Tools
            tools.extend([
                Tool(
                    name="context_manager.get_project_context",
                    description="Get the current context for a project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the project to get context for"
                            }
                        },
                        "required": ["project_name"]
                    }
                ),
                Tool(
                    name="context_manager.set_current_goal",
                    description="Set the current primary goal for a project",
                    inputSchema={
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
                ),
                Tool(
                    name="context_manager.add_completed_feature",
                    description="Add a completed feature to the project status",
                    inputSchema={
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
                ),
                Tool(
                    name="context_manager.add_current_issue",
                    description="Add a current issue to track in the project",
                    inputSchema={
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
                ),
                Tool(
                    name="context_manager.get_project_status",
                    description="Get comprehensive project status including goals, features, and issues",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the project"
                            }
                        },
                        "required": ["project_name"]
                    }
                ),
                Tool(
                    name="context_manager.create_project",
                    description="Create a new project context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the new project"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the project"
                            }
                        },
                        "required": ["project_name", "description"]
                    }
                )
            ])
            
            # System Tools
            tools.extend([
                Tool(
                    name="system.list_available_tools",
                    description="List all available tools in the centralized server",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="system.server_status",
                    description="Get the status of the centralized MCP server",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ])
            
            return ListToolsResult(tools=tools)
        
        # Context Manager Tool Handlers
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls with service prefix routing."""
            
            try:
                if name.startswith("context_manager."):
                    return await self._handle_context_manager_tool(name, arguments)
                elif name.startswith("system."):
                    return await self._handle_system_tool(name, arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                    )
                    
            except Exception as e:
                logger.error(f"Error handling tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
    
    async def _handle_context_manager_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle context manager specific tools."""
        
        tool_name = name.replace("context_manager.", "")
        project_name = arguments.get("project_name")
        
        # Ensure context manager exists for the project
        if project_name and project_name not in self.context_managers:
            self.context_managers[project_name] = ContextManager(project_name)
        
        if tool_name == "get_project_context":
            if not project_name:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: project_name is required")]
                )
            
            context_manager = self.context_managers[project_name]
            context = context_manager.get_current_context()
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(context, indent=2))]
            )
        
        elif tool_name == "set_current_goal":
            if not project_name or "goal" not in arguments:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: project_name and goal are required")]
                )
            
            context_manager = self.context_managers[project_name]
            context_manager.set_current_goal(arguments["goal"])
            return CallToolResult(
                content=[TextContent(type="text", text=f"Goal set for {project_name}: {arguments['goal']}")]
            )
        
        elif tool_name == "add_completed_feature":
            if not project_name or "feature" not in arguments:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: project_name and feature are required")]
                )
            
            context_manager = self.context_managers[project_name]
            context_manager.add_completed_feature(arguments["feature"])
            return CallToolResult(
                content=[TextContent(type="text", text=f"Feature added to {project_name}: {arguments['feature']}")]
            )
        
        elif tool_name == "add_current_issue":
            if not project_name or "issue" not in arguments:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: project_name and issue are required")]
                )
            
            context_manager = self.context_managers[project_name]
            context_manager.add_current_issue(arguments["issue"])
            return CallToolResult(
                content=[TextContent(type="text", text=f"Issue added to {project_name}: {arguments['issue']}")]
            )
        
        elif tool_name == "get_project_status":
            if not project_name:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: project_name is required")]
                )
            
            context_manager = self.context_managers[project_name]
            status = context_manager.get_project_status()
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(status, indent=2))]
            )
        
        elif tool_name == "create_project":
            if not project_name or "description" not in arguments:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: project_name and description are required")]
                )
            
            context_manager = ContextManager(project_name)
            context_manager.set_project_description(arguments["description"])
            self.context_managers[project_name] = context_manager
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Project created: {project_name}")]
            )
        
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown context manager tool: {tool_name}")]
            )
    
    async def _handle_system_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle system-level tools."""
        
        tool_name = name.replace("system.", "")
        
        if tool_name == "list_available_tools":
            tools_list = [
                "context_manager.get_project_context",
                "context_manager.set_current_goal", 
                "context_manager.add_completed_feature",
                "context_manager.add_current_issue",
                "context_manager.get_project_status",
                "context_manager.create_project",
                "system.list_available_tools",
                "system.server_status"
            ]
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(tools_list, indent=2))]
            )
        
        elif tool_name == "server_status":
            status = {
                "server": "Centralized MCP Server",
                "status": "running",
                "active_projects": list(self.context_managers.keys()),
                "timestamp": datetime.now().isoformat()
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(status, indent=2))]
            )
        
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown system tool: {tool_name}")]
            )


async def main():
    """Main entry point for the centralized MCP server."""
    try:
        server = CentralizedMCPServer()
        logger.info("🚀 Starting Centralized MCP Server...")
        logger.info("📋 Available services: context_manager, system")
        
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="centralized-mcp-server",
                    server_version="1.0.0",
                    capabilities=server.server.get_capabilities(
                        notification_options=NotificationOptions()
                    )
                )
            )
            
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
