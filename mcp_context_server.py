#!/usr/bin/env python3
"""
MCP Server for Context Manager

This server exposes context management functionality via MCP protocol,
allowing AI assistants to manage project context and conversation state.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent

from core import ContextManager, ContextAnchor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContextMCPServer:
    """MCP Server for Context Manager functionality"""
    
    def __init__(self):
        self.server = Server("context-manager")
        self.context_managers: Dict[str, ContextManager] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools with the MCP server."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List all available tools."""
            tools = [
                Tool(
                    name="get_project_context",
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
                    name="set_current_goal",
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
                    name="add_completed_feature",
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
                    name="add_current_issue",
                    description="Add a current issue to track in the project",
                    inputSchema={
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
                ),
                Tool(
                    name="resolve_issue",
                    description="Mark an issue as resolved",
                    inputSchema={
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
                ),
                Tool(
                    name="add_next_step",
                    description="Add a next step to the project",
                    inputSchema={
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
                ),
                Tool(
                    name="add_context_anchor",
                    description="Add a context anchor to maintain throughout the conversation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the project"
                            },
                            "key": {
                                "type": "string",
                                "description": "Key identifier for the context anchor"
                            },
                            "value": {
                                "type": "string",
                                "description": "Value/content of the context anchor"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of what this anchor represents"
                            },
                            "priority": {
                                "type": "integer",
                                "description": "Priority level (1=high, 2=medium, 3=low)"
                            }
                        },
                        "required": ["project_name", "key", "value", "description"]
                    }
                ),
                Tool(
                    name="list_projects",
                    description="List all projects with active context",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if name == "get_project_context":
                    return await self._get_project_context(arguments)
                elif name == "set_current_goal":
                    return await self._set_current_goal(arguments)
                elif name == "add_completed_feature":
                    return await self._add_completed_feature(arguments)
                elif name == "add_current_issue":
                    return await self._add_current_issue(arguments)
                elif name == "resolve_issue":
                    return await self._resolve_issue(arguments)
                elif name == "add_next_step":
                    return await self._add_next_step(arguments)
                elif name == "add_context_anchor":
                    return await self._add_context_anchor(arguments)
                elif name == "list_projects":
                    return await self._list_projects(arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                        isError=True
                    )
            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    def _get_context_manager(self, project_name: str) -> ContextManager:
        """Get or create a context manager for a project"""
        if project_name not in self.context_managers:
            self.context_managers[project_name] = ContextManager(project_name)
        return self.context_managers[project_name]
    
    async def _get_project_context(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Get the current context for a project"""
        project_name = arguments["project_name"]
        cm = self._get_context_manager(project_name)
        
        # Load the current status
        cm.load_status()
        
        if not cm.status:
            return CallToolResult(
                content=[TextContent(type="text", text=f"No context found for project '{project_name}'")]
            )
        
        context_info = {
            "project_name": cm.status.name,
            "current_goal": cm.status.current_goal,
            "completed_features": cm.status.completed_features,
            "current_issues": cm.status.current_issues,
            "next_steps": cm.status.next_steps,
            "context_anchors": [
                {
                    "key": anchor.key,
                    "value": anchor.value,
                    "description": anchor.description,
                    "priority": anchor.priority
                }
                for anchor in cm.status.context_anchors
            ],
            "last_updated": cm.status.last_updated.isoformat()
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(context_info, indent=2))]
        )
    
    async def _set_current_goal(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Set the current primary goal for a project"""
        project_name = arguments["project_name"]
        goal = arguments["goal"]
        
        cm = self._get_context_manager(project_name)
        cm.set_current_goal(goal)
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"✅ Set current goal for '{project_name}': {goal}")]
        )
    
    async def _add_completed_feature(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Add a completed feature to the project status"""
        project_name = arguments["project_name"]
        feature = arguments["feature"]
        
        cm = self._get_context_manager(project_name)
        cm.add_completed_feature(feature)
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"✅ Added completed feature to '{project_name}': {feature}")]
        )
    
    async def _add_current_issue(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Add a current issue to track in the project"""
        project_name = arguments["project_name"]
        problem = arguments["problem"]
        location = arguments.get("location", "")
        root_cause = arguments.get("root_cause", "")
        status = arguments.get("status", "open")
        
        cm = self._get_context_manager(project_name)
        cm.add_current_issue(problem, location, root_cause, status)
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"✅ Added issue to '{project_name}': {problem}")]
        )
    
    async def _resolve_issue(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Mark an issue as resolved"""
        project_name = arguments["project_name"]
        problem = arguments["problem"]
        
        cm = self._get_context_manager(project_name)
        cm.resolve_issue(problem)
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"✅ Resolved issue in '{project_name}': {problem}")]
        )
    
    async def _add_next_step(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Add a next step to the project"""
        project_name = arguments["project_name"]
        step = arguments["step"]
        
        cm = self._get_context_manager(project_name)
        cm.add_next_step(step)
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"✅ Added next step to '{project_name}': {step}")]
        )
    
    async def _add_context_anchor(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Add a context anchor to maintain throughout the conversation"""
        project_name = arguments["project_name"]
        key = arguments["key"]
        value = arguments["value"]
        description = arguments["description"]
        priority = arguments.get("priority", 1)
        
        cm = self._get_context_manager(project_name)
        cm.add_context_anchor(key, value, description, priority)
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"✅ Added context anchor to '{project_name}': {key}")]
        )
    
    async def _list_projects(self, arguments: Dict[str, Any]) -> CallToolResult:
        """List all projects with active context"""
        projects = list(self.context_managers.keys())
        
        if not projects:
            return CallToolResult(
                content=[TextContent(type="text", text="No projects with active context found")]
            )
        
        project_info = []
        for project_name in projects:
            cm = self.context_managers[project_name]
            cm.load_status()
            
            info = {
                "name": project_name,
                "has_goal": bool(cm.status and cm.status.current_goal),
                "completed_features_count": len(cm.status.completed_features) if cm.status else 0,
                "open_issues_count": len([i for i in cm.status.current_issues if i.get("status") == "open"]) if cm.status else 0,
                "next_steps_count": len(cm.status.next_steps) if cm.status else 0
            }
            project_info.append(info)
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(project_info, indent=2))]
        )
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="context-manager",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities=None,
                    ),
                ),
            )


async def main():
    """Main entry point."""
    server = ContextMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 
