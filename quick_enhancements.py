#!/usr/bin/env python3
"""
Quick Enhancements for Context Manager

These are immediate improvements that can be implemented right away
to enhance the context_manager functionality.
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, Request
from pydantic import BaseModel

# Enhanced response model
class EnhancedResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    timestamp: str
    request_id: str

def create_enhanced_response(
    success: bool,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    request_id: str = None
) -> Dict[str, Any]:
    """Create a standardized enhanced response with metadata."""
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

# Enhanced project summary
def create_project_summary(project_name: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a summary of project data."""
    return {
        "name": project_name,
        "current_goal": context_data.get("current_goal", "Not set"),
        "features_count": len(context_data.get("completed_features", [])),
        "issues_count": len(context_data.get("current_issues", [])),
        "steps_count": len(context_data.get("next_steps", [])),
        "last_updated": context_data.get("updated_at", "Unknown"),
        "completion_rate": len(context_data.get("completed_features", [])) / max(len(context_data.get("completed_features", [])) + len(context_data.get("next_steps", [])), 1) * 100,
        "status": "active"
    }

# Search functionality
def search_in_project(project_data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Search within a project's data."""
    results = []
    query_lower = query.lower()
    
    # Search in current goal
    if query_lower in project_data.get("current_goal", "").lower():
        results.append({
            "field": "current_goal",
            "match": project_data.get("current_goal", ""),
            "relevance": "high"
        })
    
    # Search in issues
    for issue in project_data.get("current_issues", []):
        if query_lower in issue.lower():
            results.append({
                "field": "current_issues",
                "match": issue,
                "relevance": "medium"
            })
    
    # Search in features
    for feature in project_data.get("completed_features", []):
        if query_lower in feature.lower():
            results.append({
                "field": "completed_features",
                "match": feature,
                "relevance": "medium"
            })
    
    # Search in next steps
    for step in project_data.get("next_steps", []):
        if query_lower in step.lower():
            results.append({
                "field": "next_steps",
                "match": step,
                "relevance": "medium"
            })
    
    return results

# Analytics calculation
def calculate_project_analytics(project_name: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate analytics for a project."""
    try:
        created_at = datetime.fromisoformat(context_data.get("created_at", datetime.now().isoformat()))
        updated_at = datetime.fromisoformat(context_data.get("updated_at", datetime.now().isoformat()))
        age_days = (datetime.now() - created_at).days
        days_since_update = (datetime.now() - updated_at).days
    except:
        age_days = 0
        days_since_update = 0
    
    return {
        "project_info": {
            "name": project_name,
            "age_days": age_days,
            "days_since_update": days_since_update,
            "last_updated": context_data.get("updated_at", "Unknown")
        },
        "progress_metrics": {
            "features_completed": len(context_data.get("completed_features", [])),
            "features_pending": len(context_data.get("next_steps", [])),
            "issues_open": len(context_data.get("current_issues", [])),
            "completion_percentage": len(context_data.get("completed_features", [])) / max(len(context_data.get("completed_features", [])) + len(context_data.get("next_steps", [])), 1) * 100
        },
        "activity_metrics": {
            "total_items": len(context_data.get("completed_features", [])) + len(context_data.get("current_issues", [])) + len(context_data.get("next_steps", [])),
            "update_frequency": "daily" if days_since_update <= 1 else "weekly" if days_since_update <= 7 else "monthly"
        }
    }

# Export functionality
def export_project_data(project_name: str, context_data: Dict[str, Any], format_type: str = "json") -> Dict[str, Any]:
    """Export project data in different formats."""
    if format_type == "json":
        return {
            "format": "json",
            "project": project_name,
            "exported_at": datetime.now().isoformat(),
            "data": context_data
        }
    elif format_type == "summary":
        return {
            "format": "summary",
            "project": project_name,
            "exported_at": datetime.now().isoformat(),
            "summary": create_project_summary(project_name, context_data),
            "analytics": calculate_project_analytics(project_name, context_data)
        }
    elif format_type == "markdown":
        # Create markdown format
        markdown_content = f"""# Project: {project_name}

## Current Goal
{context_data.get("current_goal", "Not set")}

## Completed Features
{chr(10).join([f"- {feature}" for feature in context_data.get("completed_features", [])])}

## Current Issues
{chr(10).join([f"- {issue}" for issue in context_data.get("current_issues", [])])}

## Next Steps
{chr(10).join([f"- {step}" for step in context_data.get("next_steps", [])])}

## Context Anchors
{chr(10).join([f"- **{key}**: {value}" for key, value in context_data.get("context_anchors", {}).items()])}

---
*Exported on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        return {
            "format": "markdown",
            "project": project_name,
            "exported_at": datetime.now().isoformat(),
            "content": markdown_content
        }
    else:
        raise ValueError(f"Unsupported export format: {format_type}")

# Batch operations
def batch_operation_summary(operations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a summary of batch operations."""
    successful = [op for op in operations if op.get("success", False)]
    failed = [op for op in operations if not op.get("success", False)]
    
    return {
        "total_operations": len(operations),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(operations) * 100 if operations else 0,
        "operations": operations
    }

# Error handling utilities
def create_error_response(error: Exception, request_id: str = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    return create_enhanced_response(
        success=False,
        message=str(error),
        data={
            "error_type": type(error).__name__,
            "error_details": str(error)
        },
        request_id=request_id
    )

def validate_project_name(project_name: str) -> bool:
    """Validate project name format."""
    if not project_name or len(project_name.strip()) == 0:
        return False
    if len(project_name) > 255:
        return False
    # Add more validation rules as needed
    return True

# Performance monitoring
def measure_execution_time(func):
    """Decorator to measure function execution time."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000
        
        # Add execution time to response if it's a dict
        if isinstance(result, dict):
            result["execution_time_ms"] = execution_time
        
        return result
    return wrapper
