#!/usr/bin/env python3
"""
Context Manager Client Library

This client library allows other services to interact with the Context Manager API
without needing to know the HTTP details.
"""

import os
import logging
from typing import Dict, List, Optional, Any
import httpx
import json

logger = logging.getLogger(__name__)

class ContextManagerClient:
    """Client for interacting with the Context Manager API."""
    
    def __init__(self, base_url: str = None, project_name: str = None):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the Context Manager API (defaults to environment variable)
            project_name: Default project name for operations
        """
        self.base_url = base_url or os.getenv("CONTEXT_MANAGER_URL", "http://localhost:8001")
        self.project_name = project_name or os.getenv("CONTEXT_PROJECT_NAME", "default")
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Remove trailing slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the Context Manager API is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current context status."""
        try:
            response = await self.client.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise
    
    async def get_project_context(self, project_name: str = None) -> Dict[str, Any]:
        """Get context for a specific project."""
        project = project_name or self.project_name
        try:
            response = await self.client.get(f"{self.base_url}/project/{project}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get project context: {e}")
            raise
    
    async def init_project(self, project_name: str = None) -> Dict[str, Any]:
        """Initialize context for a new project."""
        project = project_name or self.project_name
        try:
            response = await self.client.post(f"{self.base_url}/project/{project}/init")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to initialize project: {e}")
            raise
    
    async def set_goal(self, goal: str, project_name: str = None) -> Dict[str, Any]:
        """Set the current goal for a project."""
        project = project_name or self.project_name
        try:
            response = await self.client.post(
                f"{self.base_url}/project/{project}/goal",
                params={"goal": goal}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to set goal: {e}")
            raise
    
    async def add_issue(self, issue: str, project_name: str = None) -> Dict[str, Any]:
        """Add an issue for a project."""
        project = project_name or self.project_name
        try:
            response = await self.client.post(
                f"{self.base_url}/project/{project}/issue",
                params={"issue": issue}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add issue: {e}")
            raise
    
    async def resolve_issue(self, issue: str, project_name: str = None) -> Dict[str, Any]:
        """Resolve an issue for a project."""
        project = project_name or self.project_name
        try:
            response = await self.client.post(
                f"{self.base_url}/project/{project}/resolve",
                params={"issue": issue}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to resolve issue: {e}")
            raise
    
    async def add_next_step(self, next_step: str, project_name: str = None) -> Dict[str, Any]:
        """Add a next step for a project."""
        project = project_name or self.project_name
        try:
            response = await self.client.post(
                f"{self.base_url}/project/{project}/next",
                params={"next_step": next_step}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add next step: {e}")
            raise
    
    async def add_anchor(self, key: str, value: str, project_name: str = None) -> Dict[str, Any]:
        """Add a context anchor for a project."""
        project = project_name or self.project_name
        try:
            response = await self.client.post(
                f"{self.base_url}/project/{project}/anchor",
                params={"key": key, "value": value}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add anchor: {e}")
            raise
    
    async def list_projects(self) -> Dict[str, Any]:
        """List all available projects."""
        try:
            response = await self.client.get(f"{self.base_url}/projects")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Synchronous wrapper for easier use
class ContextManagerClientSync:
    """Synchronous wrapper for the Context Manager Client."""
    
    def __init__(self, base_url: str = None, project_name: str = None):
        self.base_url = base_url or os.getenv("CONTEXT_MANAGER_URL", "http://localhost:8001")
        self.project_name = project_name or os.getenv("CONTEXT_PROJECT_NAME", "default")
        self.client = httpx.Client(timeout=30.0)
        
        # Remove trailing slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the Context Manager API is healthy."""
        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current context status."""
        try:
            response = self.client.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise
    
    def get_project_context(self, project_name: str = None) -> Dict[str, Any]:
        """Get context for a specific project."""
        project = project_name or self.project_name
        try:
            response = self.client.get(f"{self.base_url}/project/{project}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get project context: {e}")
            raise
    
    def init_project(self, project_name: str = None) -> Dict[str, Any]:
        """Initialize context for a new project."""
        project = project_name or self.project_name
        try:
            response = self.client.post(f"{self.base_url}/project/{project}/init")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to initialize project: {e}")
            raise
    
    def set_goal(self, goal: str, project_name: str = None) -> Dict[str, Any]:
        """Set the current goal for a project."""
        project = project_name or self.project_name
        try:
            response = self.client.post(
                f"{self.base_url}/project/{project}/goal",
                params={"goal": goal}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to set goal: {e}")
            raise
    
    def add_issue(self, issue: str, project_name: str = None) -> Dict[str, Any]:
        """Add an issue for a project."""
        project = project_name or self.project_name
        try:
            response = self.client.post(
                f"{self.base_url}/project/{project}/issue",
                params={"issue": issue}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add issue: {e}")
            raise
    
    def resolve_issue(self, issue: str, project_name: str = None) -> Dict[str, Any]:
        """Resolve an issue for a project."""
        project = project_name or self.project_name
        try:
            response = self.client.post(
                f"{self.base_url}/project/{project}/resolve",
                params={"issue": issue}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to resolve issue: {e}")
            raise
    
    def add_next_step(self, next_step: str, project_name: str = None) -> Dict[str, Any]:
        """Add a next step for a project."""
        project = project_name or self.project_name
        try:
            response = self.client.post(
                f"{self.base_url}/project/{project}/next",
                params={"next_step": next_step}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add next step: {e}")
            raise
    
    def add_anchor(self, key: str, value: str, project_name: str = None) -> Dict[str, Any]:
        """Add a context anchor for a project."""
        project = project_name or self.project_name
        try:
            response = self.client.post(
                f"{self.base_url}/project/{project}/anchor",
                params={"key": key, "value": value}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add anchor: {e}")
            raise
    
    def list_projects(self) -> Dict[str, Any]:
        """List all available projects."""
        try:
            response = self.client.get(f"{self.base_url}/projects")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()

# Convenience function for quick usage
def get_context_client(project_name: str = None, base_url: str = None) -> ContextManagerClientSync:
    """Get a context manager client instance."""
    return ContextManagerClientSync(base_url=base_url, project_name=project_name)
