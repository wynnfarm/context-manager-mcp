#!/usr/bin/env python3
"""
Enhanced API endpoints for Context Manager

This module adds improved API responses with metadata, better error handling,
and enhanced functionality.
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, Request
from pydantic import BaseModel
from pathlib import Path
from context_manager.context_manager import ContextManager
from context_manager.storage import Storage

# Enhanced response models
class EnhancedResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    timestamp: str
    request_id: str

class ProjectSummary(BaseModel):
    name: str
    current_goal: Optional[str]
    features_count: int
    issues_count: int
    steps_count: int
    last_updated: str
    status: str = "active"

class SearchResult(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    search_time_ms: float

# Enhanced endpoints
def create_enhanced_response(
    success: bool,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    request_id: str = None
) -> Dict[str, Any]:
    """Create a standardized enhanced response."""
    return {
        "success": success,
        "message": message,
        "data": data,
        "metadata": {
            "version": "2.0.0",
            "storage_type": os.getenv("STORAGE_TYPE", "file"),
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id or str(uuid.uuid4())
        }
    }

async def enhanced_list_projects(request: Request):
    """Enhanced projects listing with metadata and filtering."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Get query parameters
        filter_status = request.query_params.get("status", "all")
        sort_by = request.query_params.get("sort", "updated_at")
        limit = int(request.query_params.get("limit", 50))
        
        storage = Storage()
        context_manager = ContextManager()
        
        if not storage and not context_manager:
            raise HTTPException(status_code=500, detail="Context Manager not initialized")
        
        if storage:
            # Use PostgreSQL storage
            projects = storage.list_projects()
            
            # Apply filters and sorting
            if filter_status != "all":
                # Filter by status (would need status field in database)
                pass
            
            # Get project summaries
            project_summaries = []
            for project_name in projects[:limit]:
                project_data = storage.load_project(project_name)
                if project_data:
                    summary = ProjectSummary(
                        name=project_name,
                        current_goal=project_data.get("current_goal"),
                        features_count=len(project_data.get("completed_features", [])),
                        issues_count=len(project_data.get("current_issues", [])),
                        steps_count=len(project_data.get("next_steps", [])),
                        last_updated=project_data.get("updated_at", ""),
                        status="active"
                    )
                    project_summaries.append(summary.dict())
            
            search_time = (time.time() - start_time) * 1000
            
            return create_enhanced_response(
                success=True,
                message=f"Found {len(project_summaries)} projects",
                data={
                    "projects": project_summaries,
                    "total_count": len(projects),
                    "filtered_count": len(project_summaries),
                    "filters_applied": {
                        "status": filter_status,
                        "sort_by": sort_by,
                        "limit": limit
                    }
                },
                request_id=request_id
            )
        else:
            # Use file-based storage (existing logic)
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            projects = []
            
            for context_file in Path(storage_path).glob("*_context_cache.json"):
                project_name = context_file.stem.replace("_context_cache", "")
                projects.append(project_name)
            
            return create_enhanced_response(
                success=True,
                message=f"Found {len(projects)} projects",
                data={
                    "projects": projects,
                    "total_count": len(projects),
                    "storage": "file"
                },
                request_id=request_id
            )
            
    except Exception as e:
        return create_enhanced_response(
            success=False,
            message=f"Failed to list projects: {str(e)}",
            request_id=request_id
        )

async def enhanced_get_project(project_name: str, request: Request):
    """Enhanced project retrieval with detailed metadata."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        storage = Storage()
        context_manager = ContextManager()
        
        if not storage and not context_manager:
            raise HTTPException(status_code=500, detail="Context Manager not initialized")
        
        if storage:
            # Use PostgreSQL storage
            context_data = storage.load_project(project_name)
            if context_data:
                # Calculate additional metadata
                metadata = {
                    "project_age_days": (datetime.now() - datetime.fromisoformat(context_data.get("created_at", datetime.now().isoformat()))).days,
                    "last_activity": context_data.get("updated_at"),
                    "completion_rate": len(context_data.get("completed_features", [])) / max(len(context_data.get("completed_features", [])) + len(context_data.get("next_steps", [])), 1) * 100,
                    "issue_resolution_rate": 0,  # Would need to track resolved issues
                    "team_size": len(context_data.get("team_members", [])),
                    "priority": context_data.get("priority", 3)
                }
                
                search_time = (time.time() - start_time) * 1000
                
                return create_enhanced_response(
                    success=True,
                    message=f"Retrieved context for project '{project_name}'",
                    data={
                        "project": project_name,
                        "context": context_data,
                        "analytics": metadata,
                        "storage": "postgresql"
                    },
                    request_id=request_id
                )
            else:
                return create_enhanced_response(
                    success=False,
                    message=f"Project '{project_name}' not found",
                    request_id=request_id
                )
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            
            if temp_cm.context_file.exists():
                context_data = json.loads(temp_cm.context_file.read_text())
                return create_enhanced_response(
                    success=True,
                    message=f"Retrieved context for project '{project_name}'",
                    data={
                        "project": project_name,
                        "context": context_data,
                        "storage": "file"
                    },
                    request_id=request_id
                )
            else:
                return create_enhanced_response(
                    success=False,
                    message=f"Project '{project_name}' not found",
                    request_id=request_id
                )
                
    except Exception as e:
        return create_enhanced_response(
            success=False,
            message=f"Failed to retrieve project: {str(e)}",
            request_id=request_id
        )

async def search_projects(query: str, search_type: str = "all", request: Request):
    """Search projects by various criteria."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        storage = Storage()
        context_manager = ContextManager()
        
        if not storage and not context_manager:
            raise HTTPException(status_code=500, detail="Context Manager not initialized")
        
        results = []
        
        if storage:
            # Use PostgreSQL storage
            projects = storage.list_projects()
            
            for project_name in projects:
                project_data = storage.load_project(project_name)
                if project_data:
                    # Search in different fields based on search_type
                    if search_type == "all" or search_type == "goal":
                        if query.lower() in project_data.get("current_goal", "").lower():
                            results.append({
                                "project": project_name,
                                "match_type": "goal",
                                "match_text": project_data.get("current_goal", ""),
                                "relevance_score": 1.0
                            })
                    
                    if search_type == "all" or search_type == "issue":
                        for issue in project_data.get("current_issues", []):
                            if query.lower() in issue.lower():
                                results.append({
                                    "project": project_name,
                                    "match_type": "issue",
                                    "match_text": issue,
                                    "relevance_score": 0.8
                                })
                    
                    if search_type == "all" or search_type == "feature":
                        for feature in project_data.get("completed_features", []):
                            if query.lower() in feature.lower():
                                results.append({
                                    "project": project_name,
                                    "match_type": "feature",
                                    "match_text": feature,
                                    "relevance_score": 0.6
                                })
        
        search_time = (time.time() - start_time) * 1000
        
        return create_enhanced_response(
            success=True,
            message=f"Search completed in {search_time:.2f}ms",
            data={
                "query": query,
                "search_type": search_type,
                "results": results,
                "total_count": len(results),
                "search_time_ms": search_time
            },
            request_id=request_id
        )
        
    except Exception as e:
        return create_enhanced_response(
            success=False,
            message=f"Search failed: {str(e)}",
            request_id=request_id
        )

async def get_project_analytics(project_name: str, request: Request):
    """Get detailed analytics for a project."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        storage = Storage()
        context_manager = ContextManager()
        
        if not storage and not context_manager:
            raise HTTPException(status_code=500, detail="Context Manager not initialized")
        
        if storage:
            project_data = storage.load_project(project_name)
            if project_data:
                # Calculate analytics
                analytics = {
                    "project_info": {
                        "name": project_name,
                        "created_at": project_data.get("created_at"),
                        "last_updated": project_data.get("updated_at"),
                        "age_days": (datetime.now() - datetime.fromisoformat(project_data.get("created_at", datetime.now().isoformat()))).days
                    },
                    "progress_metrics": {
                        "features_completed": len(project_data.get("completed_features", [])),
                        "features_pending": len(project_data.get("next_steps", [])),
                        "issues_open": len(project_data.get("current_issues", [])),
                        "completion_percentage": len(project_data.get("completed_features", [])) / max(len(project_data.get("completed_features", [])) + len(project_data.get("next_steps", [])), 1) * 100
                    },
                    "activity_metrics": {
                        "total_updates": 0,  # Would need to track from context_changes table
                        "last_activity": project_data.get("updated_at"),
                        "update_frequency": "daily"  # Would calculate from history
                    },
                    "team_metrics": {
                        "team_size": len(project_data.get("team_members", [])),
                        "owner": project_data.get("owner", "Unknown")
                    }
                }
                
                return create_enhanced_response(
                    success=True,
                    message=f"Analytics for project '{project_name}'",
                    data=analytics,
                    request_id=request_id
                )
            else:
                return create_enhanced_response(
                    success=False,
                    message=f"Project '{project_name}' not found",
                    request_id=request_id
                )
        else:
            return create_enhanced_response(
                success=False,
                message="Analytics only available with PostgreSQL storage",
                request_id=request_id
            )
            
    except Exception as e:
        return create_enhanced_response(
            success=False,
            message=f"Analytics failed: {str(e)}",
            request_id=request_id
        )
