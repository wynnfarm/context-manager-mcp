#!/usr/bin/env python3
"""
Context Manager REST API Server

This server exposes the context manager functionality via HTTP API,
allowing other services to manage context remotely.
"""

import os
import json
import logging
import uuid
import time
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from core import ContextManager
from utils import get_project_info, quick_status_check

# Import PostgreSQL storage if available
try:
    from postgres_storage import PostgreSQLStorage
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        # Active connections by project
        self.project_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        # Global connections for system-wide updates
        self.global_connections: List[WebSocket] = []
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, project_name: str = None, user_id: str = None):
        await websocket.accept()
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "project_name": project_name,
            "user_id": user_id or str(uuid.uuid4()),
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        
        if project_name:
            self.project_connections[project_name].append(websocket)
            logger.info(f"WebSocket connected to project '{project_name}' (user: {user_id})")
        else:
            self.global_connections.append(websocket)
            logger.info(f"WebSocket connected globally (user: {user_id})")
    
    async def disconnect(self, websocket: WebSocket):
        metadata = self.connection_metadata.get(websocket, {})
        project_name = metadata.get("project_name")
        user_id = metadata.get("user_id")
        
        if project_name and websocket in self.project_connections[project_name]:
            self.project_connections[project_name].remove(websocket)
            if not self.project_connections[project_name]:
                del self.project_connections[project_name]
            logger.info(f"WebSocket disconnected from project '{project_name}' (user: {user_id})")
        elif websocket in self.global_connections:
            self.global_connections.remove(websocket)
            logger.info(f"WebSocket disconnected globally (user: {user_id})")
        
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
    
    async def send_to_project(self, project_name: str, message: dict):
        if project_name in self.project_connections:
            disconnected = []
            for websocket in self.project_connections[project_name]:
                try:
                    await websocket.send_text(json.dumps(message))
                    # Update last activity
                    if websocket in self.connection_metadata:
                        self.connection_metadata[websocket]["last_activity"] = datetime.now().isoformat()
                except Exception as e:
                    logger.warning(f"Failed to send message to project '{project_name}': {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected:
                await self.disconnect(websocket)
    
    async def send_global(self, message: dict):
        disconnected = []
        for websocket in self.global_connections:
            try:
                await websocket.send_text(json.dumps(message))
                # Update last activity
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["last_activity"] = datetime.now().isoformat()
            except Exception as e:
                logger.warning(f"Failed to send global message: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    def get_connection_stats(self) -> dict:
        return {
            "total_connections": len(self.connection_metadata),
            "project_connections": {k: len(v) for k, v in self.project_connections.items()},
            "global_connections": len(self.global_connections),
            "active_projects": list(self.project_connections.keys())
        }

# Real-time Change Tracker
class ChangeTracker:
    def __init__(self):
        self.change_history: Dict[str, List[dict]] = defaultdict(list)
        self.last_change_id: Dict[str, int] = defaultdict(int)
    
    def record_change(self, project_name: str, change_type: str, data: dict, user_id: str = None):
        change_id = self.last_change_id[project_name] + 1
        self.last_change_id[project_name] = change_id
        
        change_record = {
            "id": change_id,
            "type": change_type,
            "project_name": project_name,
            "data": data,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "change_id": str(uuid.uuid4())
        }
        
        self.change_history[project_name].append(change_record)
        
        # Keep only last 100 changes per project
        if len(self.change_history[project_name]) > 100:
            self.change_history[project_name] = self.change_history[project_name][-100:]
        
        return change_record
    
    def get_changes_since(self, project_name: str, since_change_id: int = 0) -> List[dict]:
        if project_name not in self.change_history:
            return []
        
        return [change for change in self.change_history[project_name] 
                if change["id"] > since_change_id]
    
    def get_latest_change_id(self, project_name: str) -> int:
        return self.last_change_id[project_name]

# Initialize real-time components
connection_manager = ConnectionManager()
change_tracker = ChangeTracker()

# Context Validation and Quality System
class ContextValidator:
    def __init__(self):
        self.validation_rules = {
            "goal_clarity": {
                "min_length": 10,
                "max_length": 500,
                "required_keywords": ["build", "create", "develop", "implement", "design", "establish"],
                "forbidden_words": ["TODO", "FIXME", "TBD", "???"]
            },
            "issue_quality": {
                "min_length": 15,
                "max_length": 200,
                "required_elements": ["problem", "impact", "urgency"],
                "suggested_format": "What: [problem] | Impact: [impact] | Urgency: [level]"
            },
            "feature_completeness": {
                "min_length": 5,
                "max_length": 100,
                "required_elements": ["action", "outcome"],
                "suggested_format": "[Action] that [Outcome]"
            },
            "step_clarity": {
                "min_length": 10,
                "max_length": 150,
                "required_elements": ["action", "deliverable"],
                "suggested_format": "[Action] to [Deliverable]"
            }
        }
    
    def validate_project_context(self, project_data: dict) -> dict:
        """Comprehensive validation of project context."""
        validation_results = {
            "overall_score": 0,
            "goal_validation": self.validate_goal(project_data.get("current_goal", "")),
            "issues_validation": self.validate_issues(project_data.get("current_issues", [])),
            "features_validation": self.validate_features(project_data.get("completed_features", [])),
            "steps_validation": self.validate_steps(project_data.get("next_steps", [])),
            "freshness_validation": self.validate_freshness(project_data),
            "completeness_validation": self.validate_completeness(project_data),
            "recommendations": []
        }
        
        # Calculate overall score
        scores = [
            validation_results["goal_validation"]["score"],
            validation_results["issues_validation"]["score"],
            validation_results["features_validation"]["score"],
            validation_results["steps_validation"]["score"],
            validation_results["freshness_validation"]["score"],
            validation_results["completeness_validation"]["score"]
        ]
        validation_results["overall_score"] = sum(scores) / len(scores)
        
        # Generate recommendations
        validation_results["recommendations"] = self.generate_recommendations(validation_results)
        
        return validation_results
    
    def validate_goal(self, goal: str) -> dict:
        """Validate project goal clarity and quality."""
        if not goal:
            return {
                "score": 0,
                "status": "missing",
                "issues": ["Project goal is missing"],
                "suggestions": ["Add a clear, specific project goal"]
            }
        
        issues = []
        suggestions = []
        score = 100
        
        # Length validation
        if len(goal) < self.validation_rules["goal_clarity"]["min_length"]:
            issues.append("Goal is too short (minimum 10 characters)")
            suggestions.append("Expand the goal with more specific details")
            score -= 30
        elif len(goal) > self.validation_rules["goal_clarity"]["max_length"]:
            issues.append("Goal is too long (maximum 500 characters)")
            suggestions.append("Make the goal more concise and focused")
            score -= 20
        
        # Keyword validation
        goal_lower = goal.lower()
        has_action_keyword = any(keyword in goal_lower for keyword in self.validation_rules["goal_clarity"]["required_keywords"])
        if not has_action_keyword:
            issues.append("Goal lacks action-oriented language")
            suggestions.append("Use action words like 'build', 'create', 'develop', or 'implement'")
            score -= 25
        
        # Forbidden words check
        has_forbidden = any(word in goal.upper() for word in self.validation_rules["goal_clarity"]["forbidden_words"])
        if has_forbidden:
            issues.append("Goal contains placeholder text")
            suggestions.append("Replace placeholder text with specific, actionable content")
            score -= 40
        
        # Specificity check
        if goal.count(" ") < 3:
            issues.append("Goal lacks sufficient detail")
            suggestions.append("Add more specific details about what will be accomplished")
            score -= 20
        
        return {
            "score": max(0, score),
            "status": "good" if score >= 80 else "needs_improvement" if score >= 60 else "poor",
            "issues": issues,
            "suggestions": suggestions,
            "word_count": len(goal.split()),
            "character_count": len(goal)
        }
    
    def validate_issues(self, issues: list) -> dict:
        """Validate current issues quality and completeness."""
        if not issues:
            return {
                "score": 100,
                "status": "good",
                "issues": [],
                "suggestions": [],
                "count": 0
            }
        
        total_score = 0
        all_issues = []
        all_suggestions = []
        
        for i, issue in enumerate(issues):
            issue_score = 100
            issue_problems = []
            issue_suggestions = []
            
            # Length validation
            if len(issue) < self.validation_rules["issue_quality"]["min_length"]:
                issue_problems.append(f"Issue {i+1} is too brief")
                issue_suggestions.append("Add more detail about the problem and its impact")
                issue_score -= 30
            elif len(issue) > self.validation_rules["issue_quality"]["max_length"]:
                issue_problems.append(f"Issue {i+1} is too verbose")
                issue_suggestions.append("Make the issue description more concise")
                issue_score -= 20
            
            # Format validation
            issue_lower = issue.lower()
            has_problem = any(word in issue_lower for word in ["problem", "issue", "bug", "error", "fails", "broken"])
            has_impact = any(word in issue_lower for word in ["affects", "prevents", "blocks", "causes", "results"])
            has_urgency = any(word in issue_lower for word in ["urgent", "critical", "high", "immediate", "blocking"])
            
            if not has_problem:
                issue_problems.append(f"Issue {i+1} doesn't clearly describe the problem")
                issue_suggestions.append("Clearly state what the problem is")
                issue_score -= 25
            
            if not has_impact:
                issue_problems.append(f"Issue {i+1} doesn't describe the impact")
                issue_suggestions.append("Explain how this affects the project")
                issue_score -= 20
            
            if not has_urgency:
                issue_problems.append(f"Issue {i+1} doesn't indicate urgency")
                issue_suggestions.append("Specify the urgency level (low/medium/high/critical)")
                issue_score -= 15
            
            total_score += max(0, issue_score)
            all_issues.extend(issue_problems)
            all_suggestions.extend(issue_suggestions)
        
        avg_score = total_score / len(issues) if issues else 100
        
        return {
            "score": avg_score,
            "status": "good" if avg_score >= 80 else "needs_improvement" if avg_score >= 60 else "poor",
            "issues": all_issues,
            "suggestions": all_suggestions,
            "count": len(issues),
            "detailed_validation": [
                {
                    "issue": issue,
                    "score": max(0, 100 - (30 if len(issue) < 15 else 0) - (25 if not any(word in issue.lower() for word in ["problem", "issue", "bug", "error"]) else 0)),
                    "problems": []
                }
                for issue in issues
            ]
        }
    
    def validate_features(self, features: list) -> dict:
        """Validate completed features quality."""
        if not features:
            return {
                "score": 50,  # Neutral score for no features
                "status": "neutral",
                "issues": ["No completed features recorded"],
                "suggestions": ["Consider adding completed features to track progress"],
                "count": 0
            }
        
        total_score = 0
        all_issues = []
        all_suggestions = []
        
        for i, feature in enumerate(features):
            feature_score = 100
            feature_problems = []
            feature_suggestions = []
            
            # Length validation
            if len(feature) < self.validation_rules["feature_completeness"]["min_length"]:
                feature_problems.append(f"Feature {i+1} is too brief")
                feature_suggestions.append("Add more detail about what was accomplished")
                feature_score -= 30
            elif len(feature) > self.validation_rules["feature_completeness"]["max_length"]:
                feature_problems.append(f"Feature {i+1} is too verbose")
                feature_suggestions.append("Make the feature description more concise")
                feature_score -= 20
            
            # Action-outcome validation
            feature_lower = feature.lower()
            has_action = any(word in feature_lower for word in ["implemented", "created", "built", "developed", "added", "completed"])
            has_outcome = any(word in feature_lower for word in ["allows", "enables", "provides", "supports", "handles", "manages"])
            
            if not has_action:
                feature_problems.append(f"Feature {i+1} doesn't clearly state what was done")
                feature_suggestions.append("Use action words like 'implemented', 'created', or 'built'")
                feature_score -= 25
            
            if not has_outcome:
                feature_problems.append(f"Feature {i+1} doesn't describe the benefit")
                feature_suggestions.append("Explain what this feature enables or provides")
                feature_score -= 20
            
            total_score += max(0, feature_score)
            all_issues.extend(feature_problems)
            all_suggestions.extend(feature_suggestions)
        
        avg_score = total_score / len(features) if features else 50
        
        return {
            "score": avg_score,
            "status": "good" if avg_score >= 80 else "needs_improvement" if avg_score >= 60 else "poor",
            "issues": all_issues,
            "suggestions": all_suggestions,
            "count": len(features)
        }
    
    def validate_steps(self, steps: list) -> dict:
        """Validate next steps clarity and actionability."""
        if not steps:
            return {
                "score": 30,  # Low score for no next steps
                "status": "poor",
                "issues": ["No next steps defined"],
                "suggestions": ["Add clear, actionable next steps to maintain project momentum"],
                "count": 0
            }
        
        total_score = 0
        all_issues = []
        all_suggestions = []
        
        for i, step in enumerate(steps):
            step_score = 100
            step_problems = []
            step_suggestions = []
            
            # Length validation
            if len(step) < self.validation_rules["step_clarity"]["min_length"]:
                step_problems.append(f"Step {i+1} is too brief")
                step_suggestions.append("Add more detail about what needs to be done")
                step_score -= 30
            elif len(step) > self.validation_rules["step_clarity"]["max_length"]:
                step_problems.append(f"Step {i+1} is too verbose")
                step_suggestions.append("Make the step description more concise")
                step_score -= 20
            
            # Actionability validation
            step_lower = step.lower()
            has_action = any(word in step_lower for word in ["implement", "create", "build", "develop", "design", "set up", "configure", "test", "deploy"])
            has_deliverable = any(word in step_lower for word in ["system", "feature", "component", "module", "interface", "documentation", "test", "deployment"])
            
            if not has_action:
                step_problems.append(f"Step {i+1} lacks clear action")
                step_suggestions.append("Use action verbs like 'implement', 'create', or 'build'")
                step_score -= 30
            
            if not has_deliverable:
                step_problems.append(f"Step {i+1} doesn't specify deliverable")
                step_suggestions.append("Specify what will be created or delivered")
                step_score -= 25
            
            # Timeframe validation
            has_timeframe = any(word in step_lower for word in ["by", "within", "next", "first", "then", "after", "before"])
            if not has_timeframe:
                step_problems.append(f"Step {i+1} lacks timeframe context")
                step_suggestions.append("Add timeframe or priority context")
                step_score -= 15
            
            total_score += max(0, step_score)
            all_issues.extend(step_problems)
            all_suggestions.extend(step_suggestions)
        
        avg_score = total_score / len(steps) if steps else 30
        
        return {
            "score": avg_score,
            "status": "good" if avg_score >= 80 else "needs_improvement" if avg_score >= 60 else "poor",
            "issues": all_issues,
            "suggestions": all_suggestions,
            "count": len(steps)
        }
    
    def validate_freshness(self, project_data: dict) -> dict:
        """Validate context freshness and recency."""
        now = datetime.now()
        created_at = project_data.get("created_at")
        updated_at = project_data.get("updated_at")
        
        if not created_at and not updated_at:
            return {
                "score": 0,
                "status": "unknown",
                "issues": ["No timestamp information available"],
                "suggestions": ["Ensure project has creation and update timestamps"]
            }
        
        try:
            if updated_at:
                last_update = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                days_since_update = (now - last_update).days
            else:
                days_since_update = 999  # Very old if no update timestamp
            
            score = 100
            issues = []
            suggestions = []
            
            if days_since_update > 30:
                score = 20
                issues.append("Project hasn't been updated in over 30 days")
                suggestions.append("Review and update project context regularly")
            elif days_since_update > 14:
                score = 50
                issues.append("Project hasn't been updated in over 2 weeks")
                suggestions.append("Consider updating project status and next steps")
            elif days_since_update > 7:
                score = 75
                issues.append("Project hasn't been updated in over a week")
                suggestions.append("Regular updates help maintain project momentum")
            
            return {
                "score": score,
                "status": "fresh" if days_since_update <= 7 else "stale" if days_since_update <= 30 else "outdated",
                "issues": issues,
                "suggestions": suggestions,
                "days_since_update": days_since_update,
                "last_update": updated_at
            }
            
        except Exception as e:
            return {
                "score": 50,
                "status": "error",
                "issues": [f"Error parsing timestamps: {str(e)}"],
                "suggestions": ["Check timestamp format"]
            }
    
    def validate_completeness(self, project_data: dict) -> dict:
        """Validate overall project context completeness."""
        has_goal = bool(project_data.get("current_goal"))
        has_issues = bool(project_data.get("current_issues"))
        has_features = bool(project_data.get("completed_features"))
        has_steps = bool(project_data.get("next_steps"))
        has_anchors = bool(project_data.get("context_anchors"))
        
        completeness_score = 0
        issues = []
        suggestions = []
        
        if has_goal:
            completeness_score += 25
        else:
            issues.append("Missing project goal")
            suggestions.append("Define a clear project goal")
        
        if has_issues:
            completeness_score += 15
        else:
            issues.append("No current issues identified")
            suggestions.append("Identify and document current challenges")
        
        if has_features:
            completeness_score += 25
        else:
            issues.append("No completed features recorded")
            suggestions.append("Track completed features to show progress")
        
        if has_steps:
            completeness_score += 25
        else:
            issues.append("No next steps defined")
            suggestions.append("Define clear next steps to maintain momentum")
        
        if has_anchors:
            completeness_score += 10
        else:
            issues.append("No context anchors defined")
            suggestions.append("Add key context anchors for important information")
        
        return {
            "score": completeness_score,
            "status": "complete" if completeness_score >= 90 else "mostly_complete" if completeness_score >= 70 else "incomplete",
            "issues": issues,
            "suggestions": suggestions,
            "completeness_percentage": completeness_score,
            "missing_elements": [issue for issue in issues]
        }
    
    def generate_recommendations(self, validation_results: dict) -> list:
        """Generate actionable recommendations based on validation results."""
        recommendations = []
        
        # Goal recommendations
        if validation_results["goal_validation"]["score"] < 70:
            recommendations.append({
                "priority": "high",
                "category": "goal",
                "title": "Improve Project Goal",
                "description": "Your project goal needs improvement for better clarity and direction",
                "actions": validation_results["goal_validation"]["suggestions"]
            })
        
        # Issues recommendations
        if validation_results["issues_validation"]["score"] < 70:
            recommendations.append({
                "priority": "medium",
                "category": "issues",
                "title": "Enhance Issue Descriptions",
                "description": "Issue descriptions could be more detailed and actionable",
                "actions": validation_results["issues_validation"]["suggestions"]
            })
        
        # Features recommendations
        if validation_results["features_validation"]["score"] < 70:
            recommendations.append({
                "priority": "medium",
                "category": "features",
                "title": "Improve Feature Documentation",
                "description": "Completed features need better documentation",
                "actions": validation_results["features_validation"]["suggestions"]
            })
        
        # Steps recommendations
        if validation_results["steps_validation"]["score"] < 70:
            recommendations.append({
                "priority": "high",
                "category": "steps",
                "title": "Clarify Next Steps",
                "description": "Next steps need to be more specific and actionable",
                "actions": validation_results["steps_validation"]["suggestions"]
            })
        
        # Freshness recommendations
        if validation_results["freshness_validation"]["score"] < 70:
            recommendations.append({
                "priority": "medium",
                "category": "freshness",
                "title": "Update Project Context",
                "description": "Project context is getting stale and needs updating",
                "actions": validation_results["freshness_validation"]["suggestions"]
            })
        
        # Completeness recommendations
        if validation_results["completeness_validation"]["score"] < 70:
            recommendations.append({
                "priority": "high",
                "category": "completeness",
                "title": "Complete Project Context",
                "description": "Project context is missing important elements",
                "actions": validation_results["completeness_validation"]["suggestions"]
            })
        
        return recommendations

# Initialize context validator
context_validator = ContextValidator()

# Predefined project templates
PROJECT_TEMPLATES = {
    "web-app": {
        "id": "web-app",
        "name": "Web Application",
        "description": "Template for building web applications with frontend and backend components",
        "category": "development",
        "template_data": {
            "current_goal": "Build a modern web application with responsive UI and robust backend",
            "completed_features": [],
            "current_issues": [
                "Need to define technology stack",
                "Require user authentication system",
                "Need database design"
            ],
            "next_steps": [
                "Set up development environment",
                "Design database schema",
                "Implement user authentication",
                "Create responsive UI components",
                "Set up testing framework"
            ],
            "context_anchors": {
                "tech_stack": "To be determined",
                "target_users": "General public",
                "deployment": "Cloud-based"
            }
        }
    },
    "api-service": {
        "id": "api-service",
        "name": "API Service",
        "description": "Template for building RESTful API services and microservices",
        "category": "development",
        "template_data": {
            "current_goal": "Develop a scalable API service with comprehensive documentation and testing",
            "completed_features": [],
            "current_issues": [
                "Need to define API endpoints",
                "Require authentication and authorization",
                "Need rate limiting strategy"
            ],
            "next_steps": [
                "Design API specification",
                "Implement core endpoints",
                "Add authentication middleware",
                "Set up API documentation",
                "Implement rate limiting",
                "Add comprehensive testing"
            ],
            "context_anchors": {
                "api_version": "v1",
                "authentication": "JWT-based",
                "documentation": "OpenAPI/Swagger"
            }
        }
    },
    "data-science": {
        "id": "data-science",
        "name": "Data Science Project",
        "description": "Template for data analysis, machine learning, and research projects",
        "category": "research",
        "template_data": {
            "current_goal": "Conduct comprehensive data analysis and develop predictive models",
            "completed_features": [],
            "current_issues": [
                "Need to understand data structure",
                "Require data cleaning pipeline",
                "Need model validation strategy"
            ],
            "next_steps": [
                "Data exploration and analysis",
                "Data preprocessing and cleaning",
                "Feature engineering",
                "Model development and training",
                "Model validation and testing",
                "Results documentation and visualization"
            ],
            "context_anchors": {
                "data_source": "To be specified",
                "analysis_type": "Exploratory and predictive",
                "tools": "Python, Jupyter, scikit-learn"
            }
        }
    },
    "mobile-app": {
        "id": "mobile-app",
        "name": "Mobile Application",
        "description": "Template for developing mobile applications (iOS/Android)",
        "category": "development",
        "template_data": {
            "current_goal": "Create a cross-platform mobile application with native performance",
            "completed_features": [],
            "current_issues": [
                "Need to choose development framework",
                "Require app store optimization",
                "Need offline functionality strategy"
            ],
            "next_steps": [
                "Choose development framework (React Native, Flutter, etc.)",
                "Design app architecture",
                "Implement core features",
                "Add offline functionality",
                "Optimize for app stores",
                "Implement analytics and monitoring"
            ],
            "context_anchors": {
                "platform": "Cross-platform",
                "target_audience": "Mobile users",
                "deployment": "App stores"
            }
        }
    },
    "documentation": {
        "id": "documentation",
        "name": "Documentation Project",
        "description": "Template for creating comprehensive documentation and knowledge bases",
        "category": "content",
        "template_data": {
            "current_goal": "Create comprehensive, user-friendly documentation with clear structure",
            "completed_features": [],
            "current_issues": [
                "Need to define documentation structure",
                "Require content review process",
                "Need search and navigation system"
            ],
            "next_steps": [
                "Define documentation architecture",
                "Create content templates",
                "Write core documentation",
                "Set up review and approval process",
                "Implement search functionality",
                "Add interactive examples"
            ],
            "context_anchors": {
                "format": "Markdown/HTML",
                "audience": "End users and developers",
                "hosting": "Static site generator"
            }
        }
    }
}

# Initialize FastAPI app
app = FastAPI(
    title="Context Manager API",
    description="REST API for managing project context across services",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Global storage instance
storage: Optional[PostgreSQLStorage] = None
context_manager: Optional[ContextManager] = None

# Pydantic models for API
class ProjectContext(BaseModel):
    project_name: str
    current_goal: Optional[str] = None
    current_issue: Optional[str] = None
    next_step: Optional[str] = None
    anchors: Dict[str, str] = {}
    features: List[str] = []
    state: Optional[str] = None

class ContextUpdate(BaseModel):
    goal: Optional[str] = None
    issue: Optional[str] = None
    next_step: Optional[str] = None
    anchor_key: Optional[str] = None
    anchor_value: Optional[str] = None
    feature: Optional[str] = None
    state: Optional[str] = None

class ContextResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class FeatureCompletion(BaseModel):
    feature: str

class ProjectTemplate(BaseModel):
    id: str
    name: str
    description: str
    category: str
    template_data: Dict[str, Any]
    created_at: str = None
    updated_at: str = None

class TemplateApplication(BaseModel):
    template_id: str
    project_name: str
    customizations: Dict[str, Any] = {}

class FeatureDetail(BaseModel):
    name: str
    description: str
    status: str = "completed"  # completed, in_progress, planned
    priority: str = "medium"   # low, medium, high, critical
    category: str = "general"  # ui, api, database, integration, etc.
    completion_date: Optional[str] = None
    estimated_effort: Optional[str] = None  # e.g., "2 days", "1 week"
    dependencies: List[str] = []
    notes: List[str] = []
    related_issues: List[str] = []
    related_features: List[str] = []

class IssueResolution(BaseModel):
    issue: str

class StepAddition(BaseModel):
    step: str

class TaskCompletion(BaseModel):
    task: str
    result: str
    persona_used: str
    completion_type: str = "general"  # feature, issue_resolution, step_addition, general

class SearchQuery(BaseModel):
    query: str
    project: Optional[str] = None
    fields: Optional[List[str]] = None
    limit: Optional[int] = 10

class SearchResult(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    search_time_ms: float

class AnalyticsRequest(BaseModel):
    project: Optional[str] = None
    timeframe: Optional[str] = "all"  # all, week, month, year
    include_history: bool = True

# Enhanced response function
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

# Search functionality
def search_in_project(project_data: Dict[str, Any], query: str, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Search within a project's data."""
    results = []
    query_lower = query.lower()
    
    # Define searchable fields
    searchable_fields = fields or ["current_goal", "current_issues", "completed_features", "next_steps", "context_anchors"]
    
    for field in searchable_fields:
        if field == "current_goal":
            if query_lower in project_data.get("current_goal", "").lower():
                results.append({
                    "field": "current_goal",
                    "match": project_data.get("current_goal", ""),
                    "relevance": "high",
                    "project": project_data.get("name", "unknown")
                })
        
        elif field == "current_issues":
            for issue in project_data.get("current_issues", []):
                if query_lower in issue.lower():
                    results.append({
                        "field": "current_issues",
                        "match": issue,
                        "relevance": "medium",
                        "project": project_data.get("name", "unknown")
                    })
        
        elif field == "completed_features":
            for feature in project_data.get("completed_features", []):
                if query_lower in feature.lower():
                    results.append({
                        "field": "completed_features",
                        "match": feature,
                        "relevance": "medium",
                        "project": project_data.get("name", "unknown")
                    })
        
        elif field == "next_steps":
            for step in project_data.get("next_steps", []):
                if query_lower in step.lower():
                    results.append({
                        "field": "next_steps",
                        "match": step,
                        "relevance": "medium",
                        "project": project_data.get("name", "unknown")
                    })
        
        elif field == "context_anchors":
            context_anchors = project_data.get("context_anchors", {})
            if isinstance(context_anchors, dict):
                for key, value in context_anchors.items():
                    if query_lower in str(key).lower() or query_lower in str(value).lower():
                        results.append({
                            "field": "context_anchors",
                            "match": f"{key}: {value}",
                            "relevance": "medium",
                            "project": project_data.get("name", "unknown")
                        })
            elif isinstance(context_anchors, list):
                for anchor in context_anchors:
                    if query_lower in str(anchor).lower():
                        results.append({
                            "field": "context_anchors",
                            "match": str(anchor),
                            "relevance": "medium",
                            "project": project_data.get("name", "unknown")
                        })
    
    return results

def calculate_search_relevance(text: str, query: str) -> float:
    """Calculate relevance score for search results."""
    if not text or not query:
        return 0.0
    
    text_lower = text.lower()
    query_lower = query.lower()
    
    # Simple relevance calculation
    words = query_lower.split()
    matches = sum(1 for word in words if word in text_lower)
    
    return matches / len(words) if words else 0.0

# Analytics functionality
def calculate_project_health(project_data: Dict[str, Any]) -> float:
    """Calculate project health score based on various factors."""
    try:
        # Base health score
        health_score = 100.0
        
        # Penalize for high number of issues
        issues_count = len(project_data.get('current_issues', []))
        if issues_count > 0:
            health_score -= min(issues_count * 10, 50)  # Max 50 point penalty
        
        # Penalize for no progress (no completed features)
        completed_features = len(project_data.get('completed_features', []))
        if completed_features == 0:
            health_score -= 20
        
        # Bonus for having clear goals
        if project_data.get('current_goal'):
            health_score += 5
        
        # Bonus for having next steps
        if project_data.get('next_steps'):
            health_score += 5
        
        # Ensure health score is between 0 and 100
        return max(0.0, min(100.0, health_score))
        
    except Exception:
        return 50.0  # Default health score

def calculate_project_progress(project_data: Dict[str, Any]) -> float:
    """Calculate project completion percentage."""
    total_features = len(project_data.get("completed_features", []))
    total_steps = len(project_data.get("next_steps", []))
    
    # Calculate completion percentage
    if total_features + total_steps > 0:
        completion_percentage = (total_features / (total_features + total_steps)) * 100
    else:
        completion_percentage = 0.0
    
    return completion_percentage

def generate_project_insights(project_data: Dict[str, Any]) -> List[str]:
    """Generate insights about a project."""
    insights = []
    
    # Goal analysis
    if not project_data.get("current_goal"):
        insights.append("⚠️ No current goal defined - consider setting a clear objective")
    
    # Issue analysis
    issues = project_data.get("current_issues", [])
    if len(issues) > 3:
        insights.append(f"⚠️ High number of issues ({len(issues)}) - consider prioritizing and resolving")
    elif len(issues) == 0:
        insights.append("✅ No current issues - project is running smoothly")
    
    # Progress analysis
    completed = len(project_data.get("completed_features", []))
    steps = len(project_data.get("next_steps", []))
    
    if completed == 0 and steps > 0:
        insights.append("🚀 Project is in planning phase - ready to start implementation")
    elif completed > steps:
        insights.append("🎉 Excellent progress - more features completed than steps remaining")
    elif steps > completed * 2:
        insights.append("📋 Many steps ahead - consider breaking down into smaller tasks")
    
    # Context analysis
    anchors = project_data.get("context_anchors", {})
    if len(anchors) == 0:
        insights.append("💡 No context anchors defined - consider adding key reference points")
    
    return insights

def calculate_overall_metrics(all_projects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate overall metrics across all projects."""
    total_projects = len(all_projects)
    if total_projects == 0:
        return {
            "total_projects": 0,
            "average_completion": 0,
            "average_health": 0,
            "total_features": 0,
            "total_issues": 0,
            "total_steps": 0
        }
    
    total_completion = 0
    total_health = 0
    total_features = 0
    total_issues = 0
    total_steps = 0
    
    for project in all_projects:
        progress = calculate_project_progress(project)
        health = calculate_project_health(project)
        total_completion += progress
        total_health += health
        total_features += len(project.get("completed_features", []))
        total_issues += len(project.get("current_issues", []))
        total_steps += len(project.get("next_steps", []))
    
    return {
        "total_projects": total_projects,
        "average_completion": round(total_completion / total_projects, 1),
        "average_health": round(total_health / total_projects, 1),
        "total_features": total_features,
        "total_issues": total_issues,
        "total_steps": total_steps,
        "projects_with_goals": sum(1 for p in all_projects if p.get("current_goal")),
        "projects_with_issues": sum(1 for p in all_projects if p.get("current_issues"))
    }

@app.on_event("startup")
async def startup_event():
    """Initialize the context manager on startup."""
    global storage, context_manager
    try:
        # Check if we should use PostgreSQL storage
        storage_type = os.getenv("STORAGE_TYPE", "file")
        project_name = os.getenv("CONTEXT_PROJECT_NAME", "default")
        
        if storage_type == "postgresql" and POSTGRES_AVAILABLE:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable is required for PostgreSQL storage")
            
            # Initialize PostgreSQL storage
            storage = PostgreSQLStorage(database_url)
            logger.info(f"PostgreSQL storage initialized for project: {project_name}")
            logger.info(f"Database URL: {database_url}")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            context_manager = ContextManager(project_name, storage_path)
            logger.info(f"File-based Context Manager initialized for project: {project_name}")
        
        # Start the real-time connection manager
        await connection_manager.start()
        logger.info("Real-time connection manager started")
            
    except Exception as e:
        logger.error(f"Failed to initialize Context Manager: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    try:
        # Stop the real-time connection manager
        await connection_manager.stop()
        logger.info("Real-time connection manager stopped")
    except Exception as e:
        logger.error(f"Failed to stop connection manager: {e}")

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return create_enhanced_response(
        success=True,
        message="Context Manager API is running",
        data={
            "service": "Context Manager API",
            "version": "2.0.0",
            "status": "running"
        }
    )

@app.get("/dashboard")
async def dashboard():
    """Serve the analytics dashboard."""
    try:
        return FileResponse("static/react-dashboard.html")
    except Exception as e:
        return create_enhanced_response(
            success=False,
            message="Dashboard not available",
            data={"error": str(e)}
        )

@app.get("/dashboard/enhanced")
async def enhanced_dashboard():
    """Serve the enhanced analytics dashboard."""
    try:
        return FileResponse("static/react-dashboard-enhanced.html")
    except Exception as e:
        return create_enhanced_response(
            success=False,
            message="Enhanced dashboard not available",
            data={"error": str(e)}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return create_enhanced_response(
        success=True,
        message="Context Manager is healthy",
        data={
            "status": "healthy", 
            "context_manager": context_manager is not None,
            "storage_type": "postgresql" if storage else "file"
        }
    )

@app.get("/status")
async def get_status():
    """Get current context status."""
    if not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        status = quick_status_check()
        return {"status": "success", "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/project/{project_name}")
async def get_project_context(project_name: str):
    """Get context for a specific project."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            context_data = storage.load_project(project_name)
            if context_data:
                return create_enhanced_response(
                    success=True,
                    message=f"Context retrieved for project '{project_name}'",
                    data={
                        "project": project_name,
                        "context": context_data,
                        "storage": "postgresql"
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Project context not found")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            
            # Check if context file exists
            if temp_cm.context_file.exists():
                context_data = json.loads(temp_cm.context_file.read_text())
                return create_enhanced_response(
                    success=True,
                    message=f"Context retrieved for project '{project_name}'",
                    data={
                        "project": project_name,
                        "context": context_data,
                        "storage": "file"
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Project context not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Project not found: {e}")

@app.get("/project/{project_name}/feature/{feature_name}")
async def get_feature_details(project_name: str, feature_name: str):
    """Get detailed information about a specific feature."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            project_data = storage.load_project(project_name)
            if not project_data:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Look for the feature in completed_features
            completed_features = project_data.get("completed_features", [])
            # Check both top-level and current_state for feature_details
            feature_details = project_data.get("feature_details", {})
            if not feature_details and "current_state" in project_data:
                feature_details = project_data["current_state"].get("feature_details", {})
            
            # Find the feature by name (case-insensitive partial match)
            matching_feature = None
            for feature in completed_features:
                if feature_name.lower() in feature.lower():
                    matching_feature = feature
                    break
            
            if not matching_feature:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            # Get detailed information if available
            feature_key = matching_feature
            detailed_info = feature_details.get(feature_key, {})
            
            # Create feature detail response
            feature_detail = {
                "name": matching_feature,
                "description": detailed_info.get("description", matching_feature),
                "status": detailed_info.get("status", "completed"),
                "priority": detailed_info.get("priority", "medium"),
                "category": detailed_info.get("category", "general"),
                "completion_date": detailed_info.get("completion_date"),
                "estimated_effort": detailed_info.get("estimated_effort"),
                "dependencies": detailed_info.get("dependencies", []),
                "notes": detailed_info.get("notes", []),
                "related_issues": detailed_info.get("related_issues", []),
                "related_features": detailed_info.get("related_features", [])
            }
            
            return create_enhanced_response(
                success=True,
                message=f"Feature '{feature_name}' details retrieved successfully",
                data={"feature": feature_detail}
            )
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            
            if not temp_cm.context_file.exists():
                raise HTTPException(status_code=404, detail="Project not found")
            
            context_data = json.loads(temp_cm.context_file.read_text())
            completed_features = context_data.get("completed_features", [])
            # Check both top-level and current_state for feature_details
            feature_details = context_data.get("feature_details", {})
            if not feature_details and "current_state" in context_data:
                feature_details = context_data["current_state"].get("feature_details", {})
            
            matching_feature = None
            for feature in completed_features:
                if feature_name.lower() in feature.lower():
                    matching_feature = feature
                    break
            
            if not matching_feature:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            feature_key = matching_feature
            detailed_info = feature_details.get(feature_key, {})
            
            feature_detail = {
                "name": matching_feature,
                "description": detailed_info.get("description", matching_feature),
                "status": detailed_info.get("status", "completed"),
                "priority": detailed_info.get("priority", "medium"),
                "category": detailed_info.get("category", "general"),
                "completion_date": detailed_info.get("completion_date"),
                "estimated_effort": detailed_info.get("estimated_effort"),
                "dependencies": detailed_info.get("dependencies", []),
                "notes": detailed_info.get("notes", []),
                "related_issues": detailed_info.get("related_issues", []),
                "related_features": detailed_info.get("related_features", [])
            }
            
            return create_enhanced_response(
                success=True,
                message=f"Feature '{feature_name}' details retrieved successfully",
                data={"feature": feature_detail}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving feature details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contexts")
async def get_all_contexts():
    """Get all available contexts/projects."""
    try:
        if storage:
            # Use PostgreSQL storage
            projects = storage.list_projects()
            contexts = []
            for project_name in projects:
                project_data = storage.load_project(project_name)
                if project_data:
                    contexts.append({
                        "id": project_name,
                        "name": project_name,
                        "status": project_data.get("status", "active"),
                        "description": project_data.get("current_goal", "No description"),
                        "created_at": project_data.get("created_at", datetime.now().isoformat()),
                        "updated_at": project_data.get("updated_at", datetime.now().isoformat()),
                        "features": project_data.get("completed_features", []),
                        "current_goal": project_data.get("current_goal", ""),
                        "completed_features_count": len(project_data.get("completed_features", [])),
                        "pending_issues_count": len(project_data.get("pending_issues", []))
                    })
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            contexts = []
            
            if os.path.exists(storage_path):
                for filename in os.listdir(storage_path):
                    if filename.endswith("_CONTEXT_STATUS.md"):
                        project_name = filename.replace("_CONTEXT_STATUS.md", "")
                        context_file = os.path.join(storage_path, filename)
                        
                        try:
                            with open(context_file, 'r') as f:
                                content = f.read()
                                # Parse JSON from the markdown file
                                if content.strip().startswith('{'):
                                    context_data = json.loads(content)
                                else:
                                    # Skip non-JSON files
                                    continue
                            
                            contexts.append({
                                "id": project_name,
                                "name": project_name,
                                "status": context_data.get("status", "active"),
                                "description": context_data.get("description", context_data.get("current_goal", "No description")),
                                "created_at": context_data.get("created_at", datetime.now().isoformat()),
                                "updated_at": context_data.get("updated_at", datetime.now().isoformat()),
                                "features": context_data.get("features", []),
                                "current_goal": context_data.get("current_goal", ""),
                                "completed_features_count": context_data.get("completed_features_count", 0),
                                "pending_issues_count": context_data.get("pending_issues_count", 0)
                            })
                        except Exception as e:
                            logger.warning(f"Error loading context for {project_name}: {e}")
                            continue
        
        return create_enhanced_response(
            success=True,
            message=f"Retrieved {len(contexts)} contexts",
            data=contexts
        )
    except Exception as e:
        logger.error(f"Error retrieving contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contexts/{context_id}")
async def get_context_by_id(context_id: str):
    """Get a specific context by ID."""
    try:
        if storage:
            # Use PostgreSQL storage
            project_data = storage.load_project(context_id)
            if not project_data:
                raise HTTPException(status_code=404, detail="Context not found")
            
            context = {
                "id": context_id,
                "name": context_id,
                "status": project_data.get("status", "active"),
                "description": project_data.get("current_goal", "No description"),
                "created_at": project_data.get("created_at", datetime.now().isoformat()),
                "updated_at": project_data.get("updated_at", datetime.now().isoformat()),
                "features": project_data.get("completed_features", []),
                "current_goal": project_data.get("current_goal", ""),
                "completed_features_count": len(project_data.get("completed_features", [])),
                "pending_issues_count": len(project_data.get("pending_issues", [])),
                "current_state": project_data.get("current_state", {}),
                "completed_features": project_data.get("completed_features", []),
                "pending_issues": project_data.get("pending_issues", [])
            }
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            context_file = os.path.join(storage_path, context_id, "context.json")
            
            if not os.path.exists(context_file):
                raise HTTPException(status_code=404, detail="Context not found")
            
            with open(context_file, 'r') as f:
                context_data = json.load(f)
            
            context = {
                "id": context_id,
                "name": context_id,
                "status": context_data.get("status", "active"),
                "description": context_data.get("current_goal", "No description"),
                "created_at": context_data.get("created_at", datetime.now().isoformat()),
                "updated_at": context_data.get("updated_at", datetime.now().isoformat()),
                "features": context_data.get("completed_features", []),
                "current_goal": context_data.get("current_goal", ""),
                "completed_features_count": len(context_data.get("completed_features", [])),
                "pending_issues_count": len(context_data.get("pending_issues", [])),
                "current_state": context_data.get("current_state", {}),
                "completed_features": context_data.get("completed_features", []),
                "pending_issues": context_data.get("pending_issues", [])
            }
        
        return create_enhanced_response(
            success=True,
            message=f"Context '{context_id}' retrieved successfully",
            data=context
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving context {context_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/init")
async def init_project(project_name: str):
    """Initialize context for a new project."""
    if not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
        temp_cm = ContextManager(project_name, storage_path)
        # Initialize by setting a default goal
        temp_cm.set_current_goal("Project initialized")
        
        return {
            "success": True,
            "message": f"Project '{project_name}' initialized",
            "project": project_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/goal")
async def set_goal(project_name: str, goal: str):
    """Set the current goal for a project."""
    if not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
        temp_cm = ContextManager(project_name, storage_path)
        
        # Get old goal for comparison
        old_goal = temp_cm.status.current_goal if temp_cm.status else ""
        
        # Update the goal
        temp_cm.set_current_goal(goal)
        
        # Send real-time notification
        if old_goal != goal:
            message = create_goal_changed_message(project_name, "system", old_goal or "None", goal)
            await connection_manager.queue_message(message)
        
        return {
            "success": True,
            "message": f"Goal set for project '{project_name}'",
            "goal": goal
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/issue")
async def add_issue(project_name: str, issue: str):
    """Add an issue for a project."""
    if not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
        temp_cm = ContextManager(project_name, storage_path)
        temp_cm.add_current_issue(issue)
        
        # Send real-time notification for context update
        message = create_context_updated_message(project_name, "system", {
            "action": "issue_added",
            "issue": issue,
            "total_issues": len(temp_cm.status.current_issues) if temp_cm.status else 0
        })
        await connection_manager.queue_message(message)
        
        return {
            "success": True,
            "message": f"Issue added for project '{project_name}'",
            "issue": issue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/resolve")
async def resolve_issue(project_name: str, issue: str):
    """Resolve an issue for a project."""
    if not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
        temp_cm = ContextManager(project_name, storage_path)
        temp_cm.resolve_issue(issue)
        
        # Send real-time notification for issue resolution
        message = create_issue_resolved_message(project_name, "system", issue)
        await connection_manager.queue_message(message)
        
        return {
            "success": True,
            "message": f"Issue resolved for project '{project_name}'",
            "issue": issue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/next")
async def add_next_step(project_name: str, next_step: str):
    """Add a next step for a project."""
    if not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
        temp_cm = ContextManager(project_name, storage_path)
        temp_cm.add_next_step(next_step)
        
        # Send real-time notification for context update
        message = create_context_updated_message(project_name, "system", {
            "action": "next_step_added",
            "next_step": next_step,
            "total_steps": len(temp_cm.status.next_steps) if temp_cm.status else 0
        })
        await connection_manager.queue_message(message)
        
        return {
            "success": True,
            "message": f"Next step added for project '{project_name}'",
            "next_step": next_step
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/anchor")
async def add_anchor(project_name: str, key: str, value: str):
    """Add a context anchor for a project."""
    if not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
        temp_cm = ContextManager(project_name, storage_path)
        temp_cm.add_context_anchor(key, value)
        
        # Send real-time notification for context update
        message = create_context_updated_message(project_name, "system", {
            "action": "anchor_added",
            "key": key,
            "value": value,
            "total_anchors": len(temp_cm.status.context_anchors) if temp_cm.status else 0
        })
        await connection_manager.queue_message(message)
        
        return {
            "success": True,
            "message": f"Anchor added for project '{project_name}'",
            "key": key,
            "value": value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced Context Update Endpoints for PostgreSQL Storage
@app.post("/project/{project_name}/update")
async def update_project_context(project_name: str, update_data: ContextUpdate):
    """Update project context with multiple fields."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            current_data = storage.load_project(project_name)
            if not current_data:
                # Create new project if it doesn't exist
                current_data = {
                    "name": project_name,
                    "current_goal": "",
                    "current_issues": [],
                    "next_steps": [],
                    "completed_features": [],
                    "context_anchors": {},
                    "conversation_history": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            
            # Update fields
            if update_data.goal:
                current_data["current_goal"] = update_data.goal
            if update_data.issue:
                current_data["current_issues"].append(update_data.issue)
            if update_data.next_step:
                current_data["next_steps"].append(update_data.next_step)
            if update_data.anchor_key and update_data.anchor_value:
                if "context_anchors" not in current_data:
                    current_data["context_anchors"] = {}
                current_data["context_anchors"][update_data.anchor_key] = update_data.anchor_value
            if update_data.feature:
                current_data["completed_features"].append(update_data.feature)
            if update_data.state:
                try:
                    # Parse the state as JSON to update the entire project data
                    state_data = json.loads(update_data.state)
                    current_data.update(state_data)
                except json.JSONDecodeError:
                    # If not valid JSON, treat as simple state string
                    current_data["current_state"] = update_data.state
            
            # Save updated data
            success = storage.save_project(project_name, current_data)
            if success:
                # Record the change for real-time synchronization
                updated_fields = [k for k, v in update_data.dict().items() if v is not None]
                
                # Send real-time notifications based on what was updated
                if update_data.goal:
                    message = create_goal_changed_message(project_name, "system", "Previous Goal", update_data.goal)
                    await connection_manager.queue_message(message)
                
                if update_data.feature:
                    message = create_feature_completed_message(project_name, "system", update_data.feature)
                    await connection_manager.queue_message(message)
                
                if update_data.issue:
                    message = create_context_updated_message(project_name, "system", {
                        "action": "issue_added",
                        "issue": update_data.issue
                    })
                    await connection_manager.queue_message(message)
                
                if update_data.next_step:
                    message = create_context_updated_message(project_name, "system", {
                        "action": "next_step_added",
                        "next_step": update_data.next_step
                    })
                    await connection_manager.queue_message(message)
                
                if update_data.anchor_key and update_data.anchor_value:
                    message = create_context_updated_message(project_name, "system", {
                        "action": "anchor_added",
                        "key": update_data.anchor_key,
                        "value": update_data.anchor_value
                    })
                    await connection_manager.queue_message(message)
                
                return {
                    "success": True,
                    "message": f"Project '{project_name}' context updated successfully",
                    "updated_fields": updated_fields
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save project context")
        else:
            # Use file-based storage (existing logic)
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            
            if update_data.goal:
                temp_cm.set_current_goal(update_data.goal)
            if update_data.issue:
                temp_cm.add_current_issue(update_data.issue)
            if update_data.next_step:
                temp_cm.add_next_step(update_data.next_step)
            if update_data.anchor_key and update_data.anchor_value:
                temp_cm.add_context_anchor(update_data.anchor_key, update_data.anchor_value)
            if update_data.feature:
                temp_cm.add_completed_feature(update_data.feature)
            
            # Send real-time notifications based on what was updated
            updated_fields = [k for k, v in update_data.dict().items() if v is not None]
            
            if update_data.goal:
                message = create_goal_changed_message(project_name, "system", "Previous Goal", update_data.goal)
                await connection_manager.queue_message(message)
            
            if update_data.feature:
                message = create_feature_completed_message(project_name, "system", update_data.feature)
                await connection_manager.queue_message(message)
            
            if update_data.issue:
                message = create_context_updated_message(project_name, "system", {
                    "action": "issue_added",
                    "issue": update_data.issue
                })
                await connection_manager.queue_message(message)
            
            if update_data.next_step:
                message = create_context_updated_message(project_name, "system", {
                    "action": "next_step_added",
                    "next_step": update_data.next_step
                })
                await connection_manager.queue_message(message)
            
            if update_data.anchor_key and update_data.anchor_value:
                message = create_context_updated_message(project_name, "system", {
                    "action": "anchor_added",
                    "key": update_data.anchor_key,
                    "value": update_data.anchor_value
                })
                await connection_manager.queue_message(message)
            
            return {
                "success": True,
                "message": f"Project '{project_name}' context updated successfully",
                "updated_fields": updated_fields
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/project/{project_name}")
async def delete_project(project_name: str):
    """Delete a project."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            success = storage.delete_project(project_name)
            if success:
                return create_enhanced_response(
                    success=True,
                    message=f"Project '{project_name}' deleted successfully"
                )
            else:
                raise HTTPException(status_code=404, detail="Project not found")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            context_file = Path(storage_path) / f"{project_name}_context_cache.json"
            if context_file.exists():
                context_file.unlink()
                return create_enhanced_response(
                    success=True,
                    message=f"Project '{project_name}' deleted successfully"
                )
            else:
                raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/complete-feature")
async def complete_feature(project_name: str, feature_data: FeatureCompletion):
    """Mark a feature as completed."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        feature = feature_data.feature
        if storage:
            # Use PostgreSQL storage
            current_data = storage.load_project(project_name)
            if not current_data:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Add to completed features
            if feature not in current_data.get("completed_features", []):
                current_data["completed_features"].append(feature)
            
            # Remove from next steps if it exists there
            if "next_steps" in current_data and feature in current_data["next_steps"]:
                current_data["next_steps"].remove(feature)
            
            # Save updated data
            success = storage.save_project(project_name, current_data)
            if success:
                # Send real-time notification for feature completion
                message = create_feature_completed_message(project_name, "system", feature)
                await connection_manager.queue_message(message)
                
                return {
                    "success": True,
                    "message": f"Feature '{feature}' completed for project '{project_name}'",
                    "feature": feature
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save project context")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            temp_cm.add_completed_feature(feature)
            
            # Send real-time notification for feature completion
            message = create_feature_completed_message(project_name, "system", feature)
            await connection_manager.queue_message(message)
            
            return {
                "success": True,
                "message": f"Feature '{feature}' completed for project '{project_name}'",
                "feature": feature
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/resolve-issue")
async def resolve_issue_enhanced(project_name: str, issue_data: IssueResolution):
    """Resolve an issue and update context."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        issue = issue_data.issue
        if storage:
            # Use PostgreSQL storage
            current_data = storage.load_project(project_name)
            if not current_data:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Remove from current issues
            if "current_issues" in current_data and issue in current_data["current_issues"]:
                current_data["current_issues"].remove(issue)
            
            # Add to completed features or create a resolution note
            resolution_note = f"Resolved: {issue}"
            if "completed_features" not in current_data:
                current_data["completed_features"] = []
            current_data["completed_features"].append(resolution_note)
            
            # Save updated data
            success = storage.save_project(project_name, current_data)
            if success:
                # Send real-time notification for issue resolution
                message = create_issue_resolved_message(project_name, "system", issue)
                await connection_manager.queue_message(message)
                
                return {
                    "success": True,
                    "message": f"Issue '{issue}' resolved for project '{project_name}'",
                    "issue": issue
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save project context")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            temp_cm.resolve_issue(issue)
            
            # Send real-time notification for issue resolution
            message = create_issue_resolved_message(project_name, "system", issue)
            await connection_manager.queue_message(message)
            
            return {
                "success": True,
                "message": f"Issue '{issue}' resolved for project '{project_name}'",
                "issue": issue
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/add-step")
async def add_step_enhanced(project_name: str, step_data: StepAddition):
    """Add a next step to the project."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        step = step_data.step
        if storage:
            # Use PostgreSQL storage
            current_data = storage.load_project(project_name)
            if not current_data:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Add to next steps
            if "next_steps" not in current_data:
                current_data["next_steps"] = []
            if step not in current_data["next_steps"]:
                current_data["next_steps"].append(step)
            
            # Save updated data
            success = storage.save_project(project_name, current_data)
            if success:
                return {
                    "success": True,
                    "message": f"Step '{step}' added for project '{project_name}'",
                    "step": step
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save project context")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            temp_cm.add_next_step(step)
            
            return {
                "success": True,
                "message": f"Step '{step}' added for project '{project_name}'",
                "step": step
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/task/complete")
async def complete_task(project_name: str, task_data: TaskCompletion):
    """Complete a task and update project context accordingly."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            current_data = storage.load_project(project_name)
            if not current_data:
                raise HTTPException(status_code=404, detail="Project not found")
            
            task_lower = task_data.task.lower()
            completion_type = task_data.completion_type
            
            # Determine completion type if not specified
            if completion_type == "general":
                if any(keyword in task_lower for keyword in ["implement", "complete", "finish", "done", "build", "create"]):
                    completion_type = "feature"
                elif any(keyword in task_lower for keyword in ["fix", "resolve", "solve", "address", "debug"]):
                    completion_type = "issue_resolution"
                elif any(keyword in task_lower for keyword in ["plan", "next", "should", "need to", "add"]):
                    completion_type = "step_addition"
            
            # Update context based on completion type
            if completion_type == "feature":
                # Add to completed features
                if "completed_features" not in current_data:
                    current_data["completed_features"] = []
                if task_data.task not in current_data["completed_features"]:
                    current_data["completed_features"].append(task_data.task)
                
                # Remove from next steps if it exists there
                if "next_steps" in current_data and task_data.task in current_data["next_steps"]:
                    current_data["next_steps"].remove(task_data.task)
            
            elif completion_type == "issue_resolution":
                # Try to find and remove matching issue
                matching_issue = None
                for issue in current_data.get("current_issues", []):
                    if any(keyword in issue.lower() for keyword in task_lower.split()):
                        matching_issue = issue
                        break
                
                if matching_issue:
                    current_data["current_issues"].remove(matching_issue)
                    # Add resolution note to completed features
                    resolution_note = f"Resolved: {matching_issue}"
                    if "completed_features" not in current_data:
                        current_data["completed_features"] = []
                    current_data["completed_features"].append(resolution_note)
            
            elif completion_type == "step_addition":
                # Add to next steps
                if "next_steps" not in current_data:
                    current_data["next_steps"] = []
                if task_data.task not in current_data["next_steps"]:
                    current_data["next_steps"].append(task_data.task)
            
            # Log the interaction
            if "conversation_history" not in current_data:
                current_data["conversation_history"] = []
            
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "type": "task_completion",
                "task": task_data.task,
                "result": task_data.result,
                "persona_used": task_data.persona_used,
                "completion_type": completion_type
            }
            current_data["conversation_history"].append(interaction)
            
            # Update timestamp
            current_data["updated_at"] = datetime.now().isoformat()
            
            # Save updated data
            success = storage.save_project(project_name, current_data)
            if success:
                return create_enhanced_response(
                    success=True,
                    message=f"Task completed and context updated for project '{project_name}'",
                    data={
                        "task": task_data.task,
                        "completion_type": completion_type,
                        "persona_used": task_data.persona_used,
                        "interaction_logged": True
                    }
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to save project context")
        else:
            # Use file-based storage (simplified version)
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            
            # For file-based storage, we'll just log the completion
            # Note: This is a simplified implementation
            return create_enhanced_response(
                success=True,
                message=f"Task completion logged for project '{project_name}' (file-based storage)",
                data={
                    "task": task_data.task,
                    "completion_type": task_data.completion_type,
                    "persona_used": task_data.persona_used,
                    "note": "Full context updates require PostgreSQL storage"
                }
            )
    except Exception as e:
        logger.error(f"Error completing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/{project_name}/log-interaction")
async def log_interaction(project_name: str, interaction: Dict[str, Any]):
    """Log an interaction in the conversation history."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            current_data = storage.load_project(project_name)
            if not current_data:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Add to conversation history
            if "conversation_history" not in current_data:
                current_data["conversation_history"] = []
            
            # Add timestamp if not provided
            if "timestamp" not in interaction:
                interaction["timestamp"] = datetime.now().isoformat()
            
            current_data["conversation_history"].append(interaction)
            
            # Save updated data
            success = storage.save_project(project_name, current_data)
            if success:
                return {
                    "success": True,
                    "message": f"Interaction logged for project '{project_name}'",
                    "interaction_id": len(current_data["conversation_history"])
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save project context")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            # Note: ContextManager doesn't have conversation history, so we'll skip this for file-based
            return {
                "success": True,
                "message": f"Interaction logged for project '{project_name}' (file-based storage)",
                "note": "Conversation history not supported in file-based storage"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_projects(query: str, project: Optional[str] = None, fields: Optional[str] = None, limit: int = 10):
    """Search across projects for specific content."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    start_time = time.time()
    
    try:
        results = []
        
        if storage:
            # Use PostgreSQL storage
            if project:
                # Search in specific project
                project_data = storage.load_project(project)
                if project_data:
                    field_list = fields.split(",") if fields else None
                    project_results = search_in_project(project_data, query, field_list)
                    results.extend(project_results)
            else:
                # Search across all projects
                all_projects = storage.list_projects()
                for project_name in all_projects[:limit]:
                    project_data = storage.load_project(project_name)
                    if project_data:
                        field_list = fields.split(",") if fields else None
                        project_results = search_in_project(project_data, query, field_list)
                        results.extend(project_results)
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            
            if project:
                # Search in specific project
                temp_cm = ContextManager(project, storage_path)
                if temp_cm.context_file.exists():
                    project_data = json.loads(temp_cm.context_file.read_text())
                    field_list = fields.split(",") if fields else None
                    project_results = search_in_project(project_data, query, field_list)
                    results.extend(project_results)
            else:
                # Search across all projects
                for context_file in Path(storage_path).glob("*_context_cache.json"):
                    project_name = context_file.stem.replace("_context_cache", "")
                    project_data = json.loads(context_file.read_text())
                    field_list = fields.split(",") if fields else None
                    project_results = search_in_project(project_data, query, field_list)
                    results.extend(project_results)
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x.get("relevance", "low"), 1), reverse=True)
        results = results[:limit]
        
        search_time = (time.time() - start_time) * 1000
        
        return create_enhanced_response(
            success=True,
            message=f"Search completed for '{query}'",
            data={
                "query": query,
                "results": results,
                "total_count": len(results),
                "search_time_ms": search_time,
                "project_filter": project,
                "fields_filter": fields
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/advanced")
async def advanced_search(search_data: SearchQuery):
    """Advanced search with more options."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    start_time = time.time()
    
    try:
        results = []
        
        if storage:
            # Use PostgreSQL storage
            if search_data.project:
                # Search in specific project
                project_data = storage.load_project(search_data.project)
                if project_data:
                    project_results = search_in_project(project_data, search_data.query, search_data.fields)
                    results.extend(project_results)
            else:
                # Search across all projects
                all_projects = storage.list_projects()
                for project_name in all_projects[:search_data.limit]:
                    project_data = storage.load_project(project_name)
                    if project_data:
                        project_results = search_in_project(project_data, search_data.query, search_data.fields)
                        results.extend(project_results)
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            
            if search_data.project:
                # Search in specific project
                temp_cm = ContextManager(search_data.project, storage_path)
                if temp_cm.context_file.exists():
                    project_data = json.loads(temp_cm.context_file.read_text())
                    project_results = search_in_project(project_data, search_data.query, search_data.fields)
                    results.extend(project_results)
            else:
                # Search across all projects
                for context_file in Path(storage_path).glob("*_context_cache.json"):
                    project_name = context_file.stem.replace("_context_cache", "")
                    project_data = json.loads(context_file.read_text())
                    project_results = search_in_project(project_data, search_data.query, search_data.fields)
                    results.extend(project_results)
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x.get("relevance", "low"), 1), reverse=True)
        results = results[:search_data.limit]
        
        search_time = (time.time() - start_time) * 1000
        
        return create_enhanced_response(
            success=True,
            message=f"Advanced search completed for '{search_data.query}'",
            data={
                "query": search_data.query,
                "results": results,
                "total_count": len(results),
                "search_time_ms": search_time,
                "project_filter": search_data.project,
                "fields_filter": search_data.fields
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/suggestions")
async def get_search_suggestions(query: str, limit: int = 5):
    """Get search suggestions based on query."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        suggestions = []
        
        if storage:
            # Use PostgreSQL storage
            all_projects = storage.list_projects()
            for project_name in all_projects:
                project_data = storage.load_project(project_name)
                if project_data:
                    # Extract potential suggestions from project data
                    goal = project_data.get("current_goal", "")
                    if query.lower() in goal.lower():
                        suggestions.append(f"Goal: {goal[:50]}...")
                    
                    for issue in project_data.get("current_issues", []):
                        if query.lower() in issue.lower():
                            suggestions.append(f"Issue: {issue[:50]}...")
                    
                    for feature in project_data.get("completed_features", []):
                        if query.lower() in feature.lower():
                            suggestions.append(f"Feature: {feature[:50]}...")
                    
                    for step in project_data.get("next_steps", []):
                        if query.lower() in step.lower():
                            suggestions.append(f"Step: {step[:50]}...")
                    
                    if len(suggestions) >= limit:
                        break
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            for context_file in Path(storage_path).glob("*_context_cache.json"):
                project_data = json.loads(context_file.read_text())
                
                # Extract potential suggestions
                goal = project_data.get("current_goal", "")
                if query.lower() in goal.lower():
                    suggestions.append(f"Goal: {goal[:50]}...")
                
                for issue in project_data.get("current_issues", []):
                    if query.lower() in issue.lower():
                        suggestions.append(f"Issue: {issue[:50]}...")
                
                for feature in project_data.get("completed_features", []):
                    if query.lower() in feature.lower():
                        suggestions.append(f"Feature: {feature[:50]}...")
                
                for step in project_data.get("next_steps", []):
                    if query.lower() in step.lower():
                        suggestions.append(f"Step: {step[:50]}...")
                
                if len(suggestions) >= limit:
                    break
        
        return create_enhanced_response(
            success=True,
            message=f"Search suggestions for '{query}'",
            data={
                "query": query,
                "suggestions": suggestions[:limit],
                "total_suggestions": len(suggestions)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/project/{project_name}")
async def get_project_analytics(project_name: str):
    """Get analytics for a specific project."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            project_data = storage.load_project(project_name)
            if not project_data:
                raise HTTPException(status_code=404, detail="Project not found")
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            temp_cm = ContextManager(project_name, storage_path)
            if not temp_cm.context_file.exists():
                raise HTTPException(status_code=404, detail="Project not found")
            project_data = json.loads(temp_cm.context_file.read_text())
        
        # Calculate analytics
        progress = calculate_project_progress(project_data)
        insights = generate_project_insights(project_data)
        
        return create_enhanced_response(
            success=True,
            message=f"Analytics retrieved for project '{project_name}'",
            data={
                "project": project_name,
                "progress": progress,
                "insights": insights,
                "last_updated": project_data.get("updated_at", "unknown")
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/overview")
async def get_overall_analytics():
    """Get overall analytics across all projects."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        all_projects = []
        
        if storage:
            # Use PostgreSQL storage
            project_names = storage.list_projects()
            for project_name in project_names:
                project_data = storage.load_project(project_name)
                if project_data:
                    all_projects.append(project_data)
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            for context_file in Path(storage_path).glob("*_context_cache.json"):
                project_data = json.loads(context_file.read_text())
                all_projects.append(project_data)
        
        # Calculate overall metrics
        overall_metrics = calculate_overall_metrics(all_projects)
        
        # Generate project summaries
        project_summaries = []
        for project in all_projects:
            progress = calculate_project_progress(project)
            health = calculate_project_health(project)
            project_summaries.append({
                "name": project.get("project_name", "unknown"),
                "completion": progress,
                "health": health,
                "features": len(project.get("completed_features", [])),
                "issues": len(project.get("current_issues", [])),
                "steps": len(project.get("next_steps", []))
            })
        
        return create_enhanced_response(
            success=True,
            message="Overall analytics retrieved",
            data={
                "overall_metrics": overall_metrics,
                "project_summaries": project_summaries,
                "total_projects_analyzed": len(all_projects)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics/compare")
async def compare_projects(project_names: List[str]):
    """Compare multiple projects."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        project_data_list = []
        
        if storage:
            # Use PostgreSQL storage
            for project_name in project_names:
                project_data = storage.load_project(project_name)
                if project_data:
                    project_data_list.append(project_data)
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            for project_name in project_names:
                temp_cm = ContextManager(project_name, storage_path)
                if temp_cm.context_file.exists():
                    project_data = json.loads(temp_cm.context_file.read_text())
                    project_data_list.append(project_data)
        
        # Calculate comparison metrics
        comparison_data = []
        for project_data in project_data_list:
            progress = calculate_project_progress(project_data)
            insights = generate_project_insights(project_data)
            
            comparison_data.append({
                "name": project_data.get("name", "unknown"),
                "progress": progress,
                "insights": insights,
                "goal": project_data.get("current_goal", ""),
                "issues": project_data.get("current_issues", []),
                "features": project_data.get("completed_features", [])
            })
        
        return create_enhanced_response(
            success=True,
            message=f"Comparison completed for {len(project_names)} projects",
            data={
                "projects": comparison_data,
                "comparison_summary": {
                    "best_completion": max(comparison_data, key=lambda x: x["progress"]["completion_percentage"])["name"],
                    "best_health": max(comparison_data, key=lambda x: x["progress"]["health_score"])["name"],
                    "most_issues": max(comparison_data, key=lambda x: x["progress"]["total_issues"])["name"],
                    "most_features": max(comparison_data, key=lambda x: x["progress"]["total_features"])["name"]
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/trends")
async def get_analytics_trends():
    """Get analytics trends over time."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        # Get all projects and their conversation history
        all_projects = []
        if storage:
            project_names = storage.list_projects()
            for project_name in project_names:
                project_data = storage.load_project(project_name)
                if project_data:
                    all_projects.append(project_data)
        
        # Analyze trends
        trends = {
            "activity_timeline": [],
            "feature_completion_trends": [],
            "issue_resolution_trends": [],
            "most_active_projects": [],
            "context_change_frequency": {}
        }
        
        # Process conversation history for trends
        for project in all_projects:
            project_name = project.get("name", "unknown")
            conversation_history = project.get("conversation_history", [])
            
            # Count activities by date
            daily_activities = {}
            for interaction in conversation_history:
                timestamp = interaction.get("timestamp", "")
                if timestamp:
                    date = timestamp.split("T")[0]  # Get date part
                    daily_activities[date] = daily_activities.get(date, 0) + 1
            
            # Add to trends
            for date, count in daily_activities.items():
                trends["activity_timeline"].append({
                    "date": date,
                    "project": project_name,
                    "activities": count
                })
            
            # Track context changes
            trends["context_change_frequency"][project_name] = len(conversation_history)
        
        # Sort by activity
        trends["most_active_projects"] = sorted(
            trends["context_change_frequency"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return create_enhanced_response(
            success=True,
            message="Analytics trends retrieved successfully",
            data=trends
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/insights")
async def get_analytics_insights():
    """Get advanced analytics insights and recommendations."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        # Get overall analytics
        all_projects = []
        if storage:
            project_names = storage.list_projects()
            for project_name in project_names:
                project_data = storage.load_project(project_name)
                if project_data:
                    all_projects.append(project_data)
        
        insights = {
            "project_health_insights": [],
            "productivity_insights": [],
            "recommendations": [],
            "risk_indicators": [],
            "success_patterns": []
        }
        
        # Analyze project health
        for project in all_projects:
            project_name = project.get("name", "unknown")
            issues = len(project.get("current_issues", []))
            features = len(project.get("completed_features", []))
            steps = len(project.get("next_steps", []))
            
            # Health insights
            if issues > 3:
                insights["risk_indicators"].append({
                    "type": "high_issues",
                    "project": project_name,
                    "message": f"Project has {issues} open issues - consider prioritizing resolution"
                })
            
            if features == 0 and steps > 0:
                insights["productivity_insights"].append({
                    "type": "planning_phase",
                    "project": project_name,
                    "message": "Project is in planning phase - ready to start implementation"
                })
            
            if features > steps * 2:
                insights["success_patterns"].append({
                    "type": "high_productivity",
                    "project": project_name,
                    "message": f"Excellent progress - {features} features completed vs {steps} remaining steps"
                })
        
        # Generate recommendations
        if len(insights["risk_indicators"]) > 0:
            insights["recommendations"].append({
                "priority": "high",
                "action": "Address high-priority issues",
                "description": "Focus on resolving issues in projects with high issue counts"
            })
        
        if len(insights["success_patterns"]) > 0:
            insights["recommendations"].append({
                "priority": "medium",
                "action": "Replicate success patterns",
                "description": "Apply successful project strategies to other projects"
            })
        
        return create_enhanced_response(
            success=True,
            message="Analytics insights retrieved successfully",
            data=insights
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_projects(
    query: str = "",
    project_name: str = "",
    status: str = "",
    priority: str = "",
    has_issues: bool = None,
    has_features: bool = None,
    date_from: str = "",
    date_to: str = "",
    limit: int = 50
):
    """Advanced search across all projects and contexts."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        all_projects = []
        if storage:
            project_names = storage.list_projects()
            for name in project_names:
                project_data = storage.load_project(name)
                if project_data:
                    all_projects.append(project_data)
        
        # Apply filters
        filtered_projects = []
        
        for project in all_projects:
            # Text search
            if query:
                search_text = f"{project.get('name', '')} {project.get('current_goal', '')} {' '.join(project.get('current_issues', []))} {' '.join(project.get('completed_features', []))}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Project name filter
            if project_name and project_name.lower() not in project.get('name', '').lower():
                continue
            
            # Status filter (based on completion percentage)
            if status:
                progress = calculate_project_progress(project)
                if status == "healthy" and progress < 80:
                    continue
                elif status == "warning" and (progress < 50 or progress >= 80):
                    continue
                elif status == "critical" and progress >= 50:
                    continue
            
            # Priority filter (based on issues count)
            if priority:
                issues_count = len(project.get('current_issues', []))
                if priority == "high" and issues_count < 3:
                    continue
                elif priority == "medium" and (issues_count < 1 or issues_count >= 3):
                    continue
                elif priority == "low" and issues_count >= 1:
                    continue
            
            # Has issues filter
            if has_issues is not None:
                has_issues_bool = len(project.get('current_issues', [])) > 0
                if has_issues != has_issues_bool:
                    continue
            
            # Has features filter
            if has_features is not None:
                has_features_bool = len(project.get('completed_features', [])) > 0
                if has_features != has_features_bool:
                    continue
            
            # Date filters
            if date_from or date_to:
                updated_at = project.get('updated_at', '')
                if updated_at:
                    try:
                        from datetime import datetime
                        project_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        
                        if date_from:
                            from_date = datetime.fromisoformat(date_from)
                            if project_date < from_date:
                                continue
                        
                        if date_to:
                            to_date = datetime.fromisoformat(date_to)
                            if project_date > to_date:
                                continue
                    except:
                        pass  # Skip date filtering if parsing fails
            
            filtered_projects.append(project)
        
        # Sort by relevance (completion percentage, then by name)
        filtered_projects.sort(key=lambda p: (calculate_project_progress(p), p.get('name', '')), reverse=True)
        
        # Apply limit
        filtered_projects = filtered_projects[:limit]
        
        # Format results
        search_results = []
        for project in filtered_projects:
            progress = calculate_project_progress(project)
            health = calculate_project_health(project)
            
            search_results.append({
                "name": project.get('name', ''),
                "completion": progress,
                "health": health,
                "features": len(project.get('completed_features', [])),
                "issues": len(project.get('current_issues', [])),
                "steps": len(project.get('next_steps', [])),
                "updated_at": project.get('updated_at', ''),
                "current_goal": project.get('current_goal', ''),
                "snippet": project.get('current_goal', '')[:200] + "..." if len(project.get('current_goal', '')) > 200 else project.get('current_goal', '')
            })
        
        return create_enhanced_response(
            success=True,
            message=f"Found {len(search_results)} projects matching search criteria",
            data={
                "results": search_results,
                "total_found": len(search_results),
                "search_params": {
                    "query": query,
                    "project_name": project_name,
                    "status": status,
                    "priority": priority,
                    "has_issues": has_issues,
                    "has_features": has_features,
                    "date_from": date_from,
                    "date_to": date_to,
                    "limit": limit
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/projects")
async def export_projects(
    format: str = "json",
    include_details: bool = True,
    project_name: str = ""
):
    """Export project data in various formats."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        all_projects = []
        if storage:
            project_names = storage.list_projects()
            for name in project_names:
                if project_name and project_name.lower() not in name.lower():
                    continue
                project_data = storage.load_project(name)
                if project_data:
                    all_projects.append(project_data)
        
        if format.lower() == "csv":
            # Generate CSV export
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # CSV headers
            headers = ["Project Name", "Completion %", "Health %", "Features", "Issues", "Steps", "Updated At"]
            if include_details:
                headers.extend(["Current Goal", "Completed Features", "Current Issues", "Next Steps"])
            
            writer.writerow(headers)
            
            # CSV data
            for project in all_projects:
                progress = calculate_project_progress(project)
                health = calculate_project_health(project)
                
                row = [
                    project.get('name', ''),
                    f"{progress:.1f}",
                    f"{health:.1f}",
                    len(project.get('completed_features', [])),
                    len(project.get('current_issues', [])),
                    len(project.get('next_steps', [])),
                    project.get('updated_at', '')
                ]
                
                if include_details:
                    row.extend([
                        project.get('current_goal', ''),
                        '; '.join(project.get('completed_features', [])),
                        '; '.join(project.get('current_issues', [])),
                        '; '.join(project.get('next_steps', []))
                    ])
                
                writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=projects_export.csv"}
            )
        
        else:  # JSON format
            export_data = {
                "export_info": {
                    "timestamp": datetime.now().isoformat(),
                    "format": "json",
                    "total_projects": len(all_projects),
                    "include_details": include_details
                },
                "projects": []
            }
            
            for project in all_projects:
                project_export = {
                    "name": project.get('name', ''),
                    "completion": calculate_project_progress(project),
                    "health": calculate_project_health(project),
                    "features_count": len(project.get('completed_features', [])),
                    "issues_count": len(project.get('current_issues', [])),
                    "steps_count": len(project.get('next_steps', [])),
                    "updated_at": project.get('updated_at', '')
                }
                
                if include_details:
                    project_export.update({
                        "current_goal": project.get('current_goal', ''),
                        "completed_features": project.get('completed_features', []),
                        "current_issues": project.get('current_issues', []),
                        "next_steps": project.get('next_steps', []),
                        "context_anchors": project.get('context_anchors', []),
                        "conversation_history": project.get('conversation_history', [])
                    })
                
                export_data["projects"].append(project_export)
            
            return create_enhanced_response(
                success=True,
                message=f"Exported {len(all_projects)} projects in JSON format",
                data=export_data
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/analytics")
async def export_analytics(format: str = "json"):
    """Export analytics data in various formats."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        # Get analytics data
        all_projects = []
        if storage:
            project_names = storage.list_projects()
            for name in project_names:
                project_data = storage.load_project(name)
                if project_data:
                    all_projects.append(project_data)
        
        # Calculate analytics
        overall_metrics = calculate_overall_metrics(all_projects)
        
        if format.lower() == "csv":
            # Generate CSV export
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Overall metrics
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Projects", overall_metrics["total_projects"]])
            writer.writerow(["Average Completion", f"{overall_metrics['average_completion']:.1f}%"])
            writer.writerow(["Average Health", f"{overall_metrics['average_health']:.1f}%"])
            writer.writerow(["Total Features", overall_metrics["total_features"]])
            writer.writerow(["Total Issues", overall_metrics["total_issues"]])
            writer.writerow(["Total Steps", overall_metrics["total_steps"]])
            writer.writerow(["Projects with Goals", overall_metrics["projects_with_goals"]])
            writer.writerow(["Projects with Issues", overall_metrics["projects_with_issues"]])
            
            # Project details
            writer.writerow([])  # Empty row
            writer.writerow(["Project Name", "Completion %", "Health %", "Features", "Issues", "Steps"])
            
            for project in all_projects:
                progress = calculate_project_progress(project)
                health = calculate_project_health(project)
                writer.writerow([
                    project.get('name', ''),
                    f"{progress:.1f}",
                    f"{health:.1f}",
                    len(project.get('completed_features', [])),
                    len(project.get('current_issues', [])),
                    len(project.get('next_steps', []))
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=analytics_export.csv"}
            )
        
        else:  # JSON format
            analytics_data = {
                "export_info": {
                    "timestamp": datetime.now().isoformat(),
                    "format": "json",
                    "type": "analytics"
                },
                "overall_metrics": overall_metrics,
                "project_summaries": []
            }
            
            for project in all_projects:
                progress = calculate_project_progress(project)
                health = calculate_project_health(project)
                
                analytics_data["project_summaries"].append({
                    "name": project.get('name', ''),
                    "completion": progress,
                    "health": health,
                    "features": len(project.get('completed_features', [])),
                    "issues": len(project.get('current_issues', [])),
                    "steps": len(project.get('next_steps', []))
                })
            
            return create_enhanced_response(
                success=True,
                message="Analytics data exported successfully",
                data=analytics_data
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/report")
async def generate_report(
    report_type: str = "summary",
    project_name: str = "",
    format: str = "json"
):
    """Generate comprehensive project reports."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        all_projects = []
        if storage:
            project_names = storage.list_projects()
            for name in project_names:
                if project_name and project_name.lower() not in name.lower():
                    continue
                project_data = storage.load_project(name)
                if project_data:
                    all_projects.append(project_data)
        
        if report_type == "summary":
            # Generate summary report
            overall_metrics = calculate_overall_metrics(all_projects)
            
            # Identify top performers and areas of concern
            top_performers = []
            areas_of_concern = []
            
            for project in all_projects:
                progress = calculate_project_progress(project)
                health = calculate_project_health(project)
                issues_count = len(project.get('current_issues', []))
                
                if progress >= 80 and health >= 80:
                    top_performers.append({
                        "name": project.get('name', ''),
                        "completion": progress,
                        "health": health
                    })
                
                if progress < 50 or issues_count >= 3:
                    areas_of_concern.append({
                        "name": project.get('name', ''),
                        "completion": progress,
                        "health": health,
                        "issues": issues_count,
                        "reason": "Low progress" if progress < 50 else "High issue count"
                    })
            
            report_data = {
                "report_info": {
                    "timestamp": datetime.now().isoformat(),
                    "type": "summary",
                    "total_projects": len(all_projects),
                    "generated_by": "Context Manager API"
                },
                "executive_summary": {
                    "overall_metrics": overall_metrics,
                    "top_performers": top_performers[:5],  # Top 5
                    "areas_of_concern": areas_of_concern[:5],  # Top 5 concerns
                    "recommendations": [
                        "Focus on resolving high-priority issues in projects with low completion rates",
                        "Replicate successful strategies from top-performing projects",
                        "Consider resource reallocation to address areas of concern"
                    ]
                },
                "detailed_analysis": {
                    "project_breakdown": []
                }
            }
            
            # Add detailed project analysis
            for project in all_projects:
                progress = calculate_project_progress(project)
                health = calculate_project_health(project)
                
                report_data["detailed_analysis"]["project_breakdown"].append({
                    "name": project.get('name', ''),
                    "completion": progress,
                    "health": health,
                    "features_completed": len(project.get('completed_features', [])),
                    "issues_open": len(project.get('current_issues', [])),
                    "steps_remaining": len(project.get('next_steps', [])),
                    "status": "Excellent" if progress >= 80 and health >= 80 else
                             "Good" if progress >= 60 and health >= 60 else
                             "Needs Attention" if progress >= 40 and health >= 40 else
                             "Critical",
                    "last_updated": project.get('updated_at', '')
                })
            
            if format.lower() == "csv":
                # Generate CSV report
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Executive summary
                writer.writerow(["EXECUTIVE SUMMARY"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Projects", overall_metrics["total_projects"]])
                writer.writerow(["Average Completion", f"{overall_metrics['average_completion']:.1f}%"])
                writer.writerow(["Average Health", f"{overall_metrics['average_health']:.1f}%"])
                writer.writerow([])
                
                # Top performers
                writer.writerow(["TOP PERFORMERS"])
                writer.writerow(["Project Name", "Completion %", "Health %"])
                for performer in top_performers[:5]:
                    writer.writerow([performer["name"], f"{performer['completion']:.1f}", f"{performer['health']:.1f}"])
                writer.writerow([])
                
                # Areas of concern
                writer.writerow(["AREAS OF CONCERN"])
                writer.writerow(["Project Name", "Completion %", "Health %", "Issues", "Reason"])
                for concern in areas_of_concern[:5]:
                    writer.writerow([concern["name"], f"{concern['completion']:.1f}", f"{concern['health']:.1f}", concern["issues"], concern["reason"]])
                writer.writerow([])
                
                # Detailed breakdown
                writer.writerow(["DETAILED PROJECT BREAKDOWN"])
                writer.writerow(["Project Name", "Completion %", "Health %", "Features", "Issues", "Steps", "Status", "Last Updated"])
                for project in report_data["detailed_analysis"]["project_breakdown"]:
                    writer.writerow([
                        project["name"],
                        f"{project['completion']:.1f}",
                        f"{project['health']:.1f}",
                        project["features_completed"],
                        project["issues_open"],
                        project["steps_remaining"],
                        project["status"],
                        project["last_updated"]
                    ])
                
                csv_content = output.getvalue()
                output.close()
                
                return Response(
                    content=csv_content,
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=project_summary_report.csv"}
                )
            
            else:  # JSON format
                return create_enhanced_response(
                    success=True,
                    message="Summary report generated successfully",
                    data=report_data
                )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid report type. Supported types: summary")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/persona/analytics")
async def get_persona_analytics():
    """Get persona analytics from the persona-manager service."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        # Try to fetch persona analytics from persona-manager service
        persona_manager_url = os.getenv("PERSONA_MANAGER_URL", "http://persona-manager-http:8002")
        
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{persona_manager_url}/analytics")
                if response.status_code == 200:
                    persona_data = response.json()
                    return create_enhanced_response(
                        success=True,
                        message="Persona analytics retrieved successfully",
                        data=persona_data
                    )
        except Exception as e:
            logger.warning(f"Could not fetch persona analytics: {e}")
        
        # Return empty data if persona-manager is not available
        empty_persona_data = {
            "total_selections": 0,
            "average_confidence": 0.0,
            "persona_usage": {},
            "auto_generated_used": 0,
            "task_categories": {},
            "domains": {},
            "recent_selections": []
        }
        
        return create_enhanced_response(
            success=True,
            message="Persona analytics not available",
            data=empty_persona_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    """Compare multiple projects."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        project_data_list = []
        
        if storage:
            # Use PostgreSQL storage
            for project_name in project_names:
                project_data = storage.load_project(project_name)
                if project_data:
                    project_data_list.append(project_data)
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            for project_name in project_names:
                temp_cm = ContextManager(project_name, storage_path)
                if temp_cm.context_file.exists():
                    project_data = json.loads(temp_cm.context_file.read_text())
                    project_data_list.append(project_data)
        
        # Calculate comparison metrics
        comparison_data = []
        for project_data in project_data_list:
            progress = calculate_project_progress(project_data)
            insights = generate_project_insights(project_data)
            
            comparison_data.append({
                "name": project_data.get("name", "unknown"),
                "progress": progress,
                "insights": insights,
                "goal": project_data.get("current_goal", ""),
                "issues": project_data.get("current_issues", []),
                "features": project_data.get("completed_features", [])
            })
        
        return create_enhanced_response(
            success=True,
            message=f"Comparison completed for {len(project_names)} projects",
            data={
                "projects": comparison_data,
                "comparison_summary": {
                    "best_completion": max(comparison_data, key=lambda x: x["progress"]["completion_percentage"])["name"],
                    "best_health": max(comparison_data, key=lambda x: x["progress"]["health_score"])["name"],
                    "most_issues": max(comparison_data, key=lambda x: x["progress"]["total_issues"])["name"],
                    "most_features": max(comparison_data, key=lambda x: x["progress"]["total_features"])["name"]
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects")
async def list_projects():
    """List all available projects."""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        if storage:
            # Use PostgreSQL storage
            projects = storage.list_projects()
            return {
                "projects": projects,
                "count": len(projects),
                "storage": "postgresql"
            }
        else:
            # Use file-based storage
            storage_path = os.getenv("CONTEXT_STORAGE_PATH", "/app/contexts")
            projects = []
            
            # Scan for project context files
            for context_file in Path(storage_path).glob("*_context_cache.json"):
                project_name = context_file.stem.replace("_context_cache", "")
                projects.append(project_name)
            
            return {
                "projects": projects,
                "count": len(projects),
                "storage": "file"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Template Management Endpoints - REMOVED (duplicates exist later in file)

# OLD TEMPLATE ENDPOINTS REMOVED - Using new template system below

# WebSocket Endpoints for Real-time Synchronization

@app.websocket("/ws/context/{project_name}")
async def websocket_project_updates(websocket: WebSocket, project_name: str):
    """WebSocket endpoint for real-time project updates."""
    user_id = None
    try:
        # Get user_id from query parameters if provided
        user_id = websocket.query_params.get("user_id")
        
        # Connect to the project
        await connection_manager.connect(websocket, project_name, user_id)
        
        # Send initial project state
        if storage:
            project_data = storage.load_project(project_name)
            if project_data:
                await websocket.send_text(json.dumps({
                    "type": "initial_state",
                    "project_name": project_name,
                    "data": project_data,
                    "timestamp": datetime.now().isoformat()
                }))
        
        # Send any missed changes since last connection
        last_change_id = int(websocket.query_params.get("since", 0))
        missed_changes = change_tracker.get_changes_since(project_name, last_change_id)
        if missed_changes:
            await websocket.send_text(json.dumps({
                "type": "missed_changes",
                "project_name": project_name,
                "changes": missed_changes,
                "timestamp": datetime.now().isoformat()
            }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                elif message.get("type") == "get_changes":
                    since_id = message.get("since", 0)
                    changes = change_tracker.get_changes_since(project_name, since_id)
                    await websocket.send_text(json.dumps({
                        "type": "changes",
                        "project_name": project_name,
                        "changes": changes,
                        "timestamp": datetime.now().isoformat()
                    }))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for project '{project_name}': {e}")
    finally:
        await connection_manager.disconnect(websocket)

@app.websocket("/ws/updates")
async def websocket_global_updates(websocket: WebSocket):
    """WebSocket endpoint for global system updates."""
    user_id = None
    try:
        # Get user_id from query parameters if provided
        user_id = websocket.query_params.get("user_id")
        
        # Connect globally
        await connection_manager.connect(websocket, None, user_id)
        
        # Send initial system state
        if storage:
            all_projects = storage.get_all_projects()
            await websocket.send_text(json.dumps({
                "type": "initial_system_state",
                "projects": all_projects,
                "timestamp": datetime.now().isoformat()
            }))
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "user_joined",
            "project_name": None,
            "user_id": user_id,
            "data": {
                "message": "Connected to real-time updates",
                "project_name": None,
                "connected_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat(),
            "message_id": f"{time.time()}_{id(websocket)}"
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client with timeout
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    message = json.loads(data)
                    
                    # Handle different message types
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                    elif message.get("type") == "get_stats":
                        stats = connection_manager.get_connection_stats()
                        await websocket.send_text(json.dumps({
                            "type": "connection_stats",
                            "stats": stats,
                            "timestamp": datetime.now().isoformat()
                        }))
                    elif message.get("type") == "heartbeat":
                        # Send heartbeat response
                        await websocket.send_text(json.dumps({
                            "type": "heartbeat_response",
                            "timestamp": datetime.now().isoformat()
                        }))
                
                except asyncio.TimeoutError:
                    # Send periodic heartbeat to keep connection alive
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat()
                    }))
                    continue
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling global WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Global WebSocket error: {e}")
    finally:
        await connection_manager.disconnect(websocket)

@app.websocket("/ws/collaboration/{project_name}")
async def websocket_collaboration(websocket: WebSocket, project_name: str):
    """WebSocket endpoint for real-time collaboration on a project."""
    user_id = None
    try:
        # Get user_id from query parameters if provided
        user_id = websocket.query_params.get("user_id")
        
        # Connect to the project for collaboration
        await connection_manager.connect(websocket, project_name, user_id)
        
        # Notify other collaborators about new user
        await connection_manager.send_to_project(project_name, {
            "type": "user_joined",
            "project_name": project_name,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send current collaborators list
        project_connections = connection_manager.project_connections.get(project_name, [])
        collaborators = []
        for ws in project_connections:
            metadata = connection_manager.connection_metadata.get(ws, {})
            if metadata.get("user_id"):
                collaborators.append({
                    "user_id": metadata["user_id"],
                    "connected_at": metadata.get("connected_at"),
                    "last_activity": metadata.get("last_activity")
                })
        
        await websocket.send_text(json.dumps({
            "type": "collaborators_list",
            "project_name": project_name,
            "collaborators": collaborators,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle collaboration-specific message types
                if message.get("type") == "cursor_position":
                    # Broadcast cursor position to other collaborators
                    await connection_manager.send_to_project(project_name, {
                        "type": "cursor_position",
                        "user_id": user_id,
                        "position": message.get("position"),
                        "timestamp": datetime.now().isoformat()
                    })
                elif message.get("type") == "typing_indicator":
                    # Broadcast typing indicator to other collaborators
                    await connection_manager.send_to_project(project_name, {
                        "type": "typing_indicator",
                        "user_id": user_id,
                        "is_typing": message.get("is_typing"),
                        "timestamp": datetime.now().isoformat()
                    })
                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling collaboration message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Collaboration WebSocket error for project '{project_name}': {e}")
    finally:
        # Notify other collaborators about user leaving
        await connection_manager.send_to_project(project_name, {
            "type": "user_left",
            "project_name": project_name,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        await connection_manager.disconnect(websocket)

# Real-time API endpoints

@app.get("/realtime/stats")
async def get_realtime_stats():
    """Get real-time connection statistics."""
    try:
        stats = connection_manager.get_connection_stats()
        return create_enhanced_response(
            success=True,
            message="Real-time statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        logger.error(f"Error getting real-time stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/realtime/changes/{project_name}")
async def get_project_changes(project_name: str, since: int = 0):
    """Get changes for a project since a specific change ID."""
    try:
        changes = change_tracker.get_changes_since(project_name, since)
        return create_enhanced_response(
            success=True,
            message=f"Retrieved {len(changes)} changes for project '{project_name}'",
            data={
                "project_name": project_name,
                "changes": changes,
                "latest_change_id": change_tracker.get_latest_change_id(project_name)
            }
        )
    except Exception as e:
        logger.error(f"Error getting project changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Context Validation API Endpoints

@app.get("/validate/{project_name}")
async def validate_project_context(project_name: str):
    """Validate project context quality and completeness."""
    if not storage:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    
    try:
        # Load project data
        project_data = storage.load_project(project_name)
        if not project_data:
            raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
        
        # Run comprehensive validation
        validation_results = context_validator.validate_project_context(project_data)
        
        return create_enhanced_response(
            success=True,
            message=f"Project '{project_name}' validation completed",
            data={
                "project_name": project_name,
                "validation_results": validation_results,
                "validated_at": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating project context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/validate/all")
async def validate_all_projects():
    """Validate all projects and return quality summary."""
    if not storage:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    
    try:
        all_projects = storage.get_all_projects()
        validation_summary = {
            "total_projects": len(all_projects),
            "validation_results": [],
            "overall_quality_score": 0,
            "quality_distribution": {
                "excellent": 0,  # 90-100
                "good": 0,       # 80-89
                "fair": 0,       # 70-79
                "poor": 0,       # 60-69
                "critical": 0    # 0-59
            },
            "common_issues": [],
            "top_recommendations": []
        }
        
        all_scores = []
        all_recommendations = []
        issue_counts = defaultdict(int)
        
        for project in all_projects:
            project_name = project.get("name", "unknown")
            validation_results = context_validator.validate_project_context(project)
            
            # Add to summary
            validation_summary["validation_results"].append({
                "project_name": project_name,
                "overall_score": validation_results["overall_score"],
                "status": _get_quality_status(validation_results["overall_score"]),
                "key_issues": len(validation_results["recommendations"]),
                "last_updated": project.get("updated_at", "unknown")
            })
            
            all_scores.append(validation_results["overall_score"])
            all_recommendations.extend(validation_results["recommendations"])
            
            # Count common issues
            for rec in validation_results["recommendations"]:
                issue_counts[rec["category"]] += 1
        
        # Calculate overall quality score
        if all_scores:
            validation_summary["overall_quality_score"] = sum(all_scores) / len(all_scores)
        
        # Quality distribution
        for score in all_scores:
            if score >= 90:
                validation_summary["quality_distribution"]["excellent"] += 1
            elif score >= 80:
                validation_summary["quality_distribution"]["good"] += 1
            elif score >= 70:
                validation_summary["quality_distribution"]["fair"] += 1
            elif score >= 60:
                validation_summary["quality_distribution"]["poor"] += 1
            else:
                validation_summary["quality_distribution"]["critical"] += 1
        
        # Common issues
        validation_summary["common_issues"] = [
            {"category": category, "count": count, "percentage": (count / len(all_projects)) * 100}
            for category, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Top recommendations
        rec_counts = defaultdict(int)
        for rec in all_recommendations:
            rec_counts[rec["title"]] += 1
        
        validation_summary["top_recommendations"] = [
            {"title": title, "count": count, "percentage": (count / len(all_projects)) * 100}
            for title, count in sorted(rec_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return create_enhanced_response(
            success=True,
            message=f"Validated {len(all_projects)} projects",
            data=validation_summary
        )
        
    except Exception as e:
        logger.error(f"Error validating all projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quality/{project_name}")
async def get_project_quality_score(project_name: str):
    """Get project quality score and quick recommendations."""
    if not storage:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    
    try:
        # Load project data
        project_data = storage.load_project(project_name)
        if not project_data:
            raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
        
        # Run validation
        validation_results = context_validator.validate_project_context(project_data)
        
        # Create quality summary
        quality_summary = {
            "project_name": project_name,
            "overall_score": validation_results["overall_score"],
            "quality_status": _get_quality_status(validation_results["overall_score"]),
            "component_scores": {
                "goal": validation_results["goal_validation"]["score"],
                "issues": validation_results["issues_validation"]["score"],
                "features": validation_results["features_validation"]["score"],
                "steps": validation_results["steps_validation"]["score"],
                "freshness": validation_results["freshness_validation"]["score"],
                "completeness": validation_results["completeness_validation"]["score"]
            },
            "priority_recommendations": [
                rec for rec in validation_results["recommendations"] 
                if rec["priority"] == "high"
            ],
            "quick_fixes": _get_quick_fixes(validation_results),
            "quality_trend": "stable",  # Could be calculated from historical data
            "last_validated": datetime.now().isoformat()
        }
        
        return create_enhanced_response(
            success=True,
            message=f"Quality assessment for '{project_name}' completed",
            data=quality_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_quality_status(score: float) -> str:
    """Convert numeric score to quality status."""
    if score >= 90:
        return "excellent"
    elif score >= 80:
        return "good"
    elif score >= 70:
        return "fair"
    elif score >= 60:
        return "poor"
    else:
        return "critical"

def _get_quick_fixes(validation_results: dict) -> list:
    """Get quick actionable fixes for immediate improvement."""
    quick_fixes = []
    
    # Goal quick fixes
    if validation_results["goal_validation"]["score"] < 70:
        if "Goal is too short" in validation_results["goal_validation"]["issues"]:
            quick_fixes.append("Add more detail to your project goal")
        if "Goal lacks action-oriented language" in validation_results["goal_validation"]["issues"]:
            quick_fixes.append("Use action words like 'build' or 'create' in your goal")
    
    # Steps quick fixes
    if validation_results["steps_validation"]["score"] < 70:
        if "No next steps defined" in validation_results["steps_validation"]["issues"]:
            quick_fixes.append("Add at least 2-3 specific next steps")
        if any("lacks clear action" in issue for issue in validation_results["steps_validation"]["issues"]):
            quick_fixes.append("Make next steps more action-oriented")
    
    # Completeness quick fixes
    if validation_results["completeness_validation"]["score"] < 70:
        if "Missing project goal" in validation_results["completeness_validation"]["issues"]:
            quick_fixes.append("Define a clear project goal")
        if "No next steps defined" in validation_results["completeness_validation"]["issues"]:
            quick_fixes.append("Add actionable next steps")
    
    return quick_fixes[:3]  # Return top 3 quick fixes


# ============================================================================
# TEMPLATE ENDPOINTS
# ============================================================================

# Import template manager
from templates import template_manager

# Import real-time sync
from realtime_sync import connection_manager, create_context_updated_message, create_feature_completed_message, create_issue_resolved_message, create_goal_changed_message


@app.get("/templates/list")
async def list_templates():
    """List all available project templates"""
    try:
        templates = template_manager.list_templates()
        
        return create_enhanced_response(
            success=True,
            message=f"Found {len(templates)} available templates",
            data={
                "templates": templates,
                "total_count": len(templates)
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates/search")
async def search_templates(query: str):
    """Search templates by name, description, or tags"""
    try:
        if not query or len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
        templates = template_manager.search_templates(query.strip())
        
        # Convert templates to dict format
        template_data = {
            template_id: {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags
            }
            for template_id, template in templates.items()
        }
        
        return create_enhanced_response(
            success=True,
            message=f"Found {len(templates)} templates matching '{query}'",
            data={
                "query": query,
                "templates": template_data,
                "total_count": len(templates)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get detailed information about a specific template"""
    try:
        template = template_manager.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
        
        # Convert template to dict for JSON serialization
        template_data = {
            "id": template_id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "default_goal": template.default_goal,
            "suggested_features": template.suggested_features,
            "common_issues": template.common_issues,
            "suggested_steps": template.suggested_steps,
            "context_anchors": template.context_anchors,
            "key_files": template.key_files,
            "tags": template.tags
        }
        
        return create_enhanced_response(
            success=True,
            message=f"Template '{template_id}' retrieved successfully",
            data=template_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates/category/{category}")
async def get_templates_by_category(category: str):
    """Get all templates in a specific category"""
    try:
        templates = template_manager.get_templates_by_category(category)
        
        if not templates:
            return create_enhanced_response(
                success=True,
                message=f"No templates found in category '{category}'",
                data={
                    "category": category,
                    "templates": {},
                    "total_count": 0
                }
            )
        
        # Convert templates to dict format
        template_data = {
            template_id: {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags
            }
            for template_id, template in templates.items()
        }
        
        return create_enhanced_response(
            success=True,
            message=f"Found {len(templates)} templates in category '{category}'",
            data={
                "category": category,
                "templates": template_data,
                "total_count": len(templates)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting templates by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TemplateApplicationRequest(BaseModel):
    template_id: str
    project_name: str
    customizations: Optional[Dict[str, Any]] = {}


@app.post("/templates/apply")
async def apply_template(request: TemplateApplicationRequest):
    """Apply a template to create initial context for a project"""
    if not storage and not context_manager:
        raise HTTPException(status_code=500, detail="Context Manager not initialized")
    
    try:
        # Validate template exists
        template = template_manager.get_template(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")
        
        # Apply template to create context
        context_data = template_manager.apply_template_to_context(
            request.template_id, 
            request.project_name
        )
        
        # Apply any customizations
        if request.customizations:
            if "goal" in request.customizations:
                context_data["current_goal"] = request.customizations["goal"]
            if "additional_steps" in request.customizations:
                context_data["next_steps"].extend(request.customizations["additional_steps"])
            if "additional_anchors" in request.customizations:
                for anchor in request.customizations["additional_anchors"]:
                    context_data["context_anchors"].append({
                        "key": anchor["key"],
                        "value": anchor["value"],
                        "description": anchor["description"],
                        "priority": anchor.get("priority", 2),
                        "created_at": datetime.now().isoformat()
                    })
        
        # Save the context using the storage system
        if storage:
            # Use PostgreSQL storage
            storage.save_project_context(request.project_name, context_data)
        else:
            # File-based storage - save to contexts directory
            contexts_dir = Path("contexts")
            contexts_dir.mkdir(exist_ok=True)
            context_file = contexts_dir / f"{request.project_name}_context_cache.json"
            with open(context_file, 'w') as f:
                json.dump(context_data, f, indent=2, default=str)
        
        return create_enhanced_response(
            success=True,
            message=f"Template '{request.template_id}' applied to project '{request.project_name}'",
            data={
                "project_name": request.project_name,
                "template_id": request.template_id,
                "template_name": template.name,
                "context_created": True,
                "customizations_applied": bool(request.customizations)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CustomTemplateRequest(BaseModel):
    name: str
    description: str
    category: str
    default_goal: str
    suggested_features: Optional[List[str]] = []
    common_issues: Optional[List[str]] = []
    suggested_steps: Optional[List[str]] = []
    context_anchors: Optional[List[Dict[str, Any]]] = []
    key_files: Optional[List[str]] = []
    tags: Optional[List[str]] = []


@app.post("/templates/create")
async def create_custom_template(request: CustomTemplateRequest):
    """Create a custom template from provided data"""
    try:
        # Validate required fields
        if not request.name or not request.description or not request.category or not request.default_goal:
            raise HTTPException(
                status_code=400, 
                detail="Name, description, category, and default_goal are required"
            )
        
        # Create template data dict
        template_data = {
            "name": request.name,
            "description": request.description,
            "category": request.category,
            "default_goal": request.default_goal,
            "suggested_features": request.suggested_features,
            "common_issues": request.common_issues,
            "suggested_steps": request.suggested_steps,
            "context_anchors": request.context_anchors,
            "key_files": request.key_files,
            "tags": request.tags
        }
        
        # Create the custom template
        template_id = template_manager.create_custom_template(template_data)
        
        return create_enhanced_response(
            success=True,
            message=f"Custom template '{request.name}' created successfully",
            data={
                "template_id": template_id,
                "name": request.name,
                "category": request.category,
                "created_at": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINTS FOR REAL-TIME SYNCHRONIZATION
# ============================================================================

@app.websocket("/ws/context/{project_name}")
async def websocket_project_context(websocket: WebSocket, project_name: str):
    """WebSocket endpoint for project-specific real-time updates"""
    try:
        # Extract user ID from query parameters or headers
        user_id = websocket.query_params.get("user_id", "anonymous")
        
        # Connect to the project
        await connection_manager.connect(websocket, project_name=project_name, user_id=user_id)
        
        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                    message_type = message_data.get("type", "heartbeat")
                    
                    if message_type == "heartbeat":
                        # Update last heartbeat time
                        if websocket in connection_manager.connection_info:
                            connection_manager.connection_info[websocket].last_heartbeat = datetime.now()
                    
                    # Echo back for testing (in production, you'd process the message)
                    await websocket.send_text(json.dumps({
                        "type": "echo",
                        "received": message_data,
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    }))
                    
        except WebSocketDisconnect:
            await connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket error for project {project_name}: {e}")
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws/updates")
async def websocket_global_updates(websocket: WebSocket):
    """WebSocket endpoint for global system updates"""
    try:
        # Extract user ID from query parameters or headers
        user_id = websocket.query_params.get("user_id", "anonymous")
        
        # Connect to global updates
        await connection_manager.connect(websocket, user_id=user_id)
        
        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                    message_type = message_data.get("type", "heartbeat")
                    
                    if message_type == "heartbeat":
                        # Update last heartbeat time
                        if websocket in connection_manager.connection_info:
                            connection_manager.connection_info[websocket].last_heartbeat = datetime.now()
                    
                    # Echo back for testing
                    await websocket.send_text(json.dumps({
                        "type": "echo",
                        "received": message_data,
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    }))
                    
        except WebSocketDisconnect:
            await connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"Global WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


@app.get("/realtime/stats")
async def get_realtime_stats():
    """Get real-time connection statistics"""
    try:
        stats = connection_manager.get_connection_stats()
        
        return create_enhanced_response(
            success=True,
            message="Real-time connection statistics retrieved",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting real-time stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INTEGRATE REAL-TIME UPDATES WITH EXISTING ENDPOINTS
# ============================================================================

# Override existing endpoints to include real-time updates
async def _notify_context_update(project_name: str, user_id: str, changes: Dict[str, Any]):
    """Notify all connected clients about context updates"""
    try:
        message = create_context_updated_message(project_name, user_id, changes)
        await connection_manager.queue_message(message)
    except Exception as e:
        logger.error(f"Failed to notify context update: {e}")


async def _notify_feature_completed(project_name: str, user_id: str, feature: str):
    """Notify all connected clients about feature completion"""
    try:
        message = create_feature_completed_message(project_name, user_id, feature)
        await connection_manager.queue_message(message)
    except Exception as e:
        logger.error(f"Failed to notify feature completion: {e}")


async def _notify_issue_resolved(project_name: str, user_id: str, issue: str):
    """Notify all connected clients about issue resolution"""
    try:
        message = create_issue_resolved_message(project_name, user_id, issue)
        await connection_manager.queue_message(message)
    except Exception as e:
        logger.error(f"Failed to notify issue resolution: {e}")


async def _notify_goal_changed(project_name: str, user_id: str, old_goal: str, new_goal: str):
    """Notify all connected clients about goal changes"""
    try:
        message = create_goal_changed_message(project_name, user_id, old_goal, new_goal)
        await connection_manager.queue_message(message)
    except Exception as e:
        logger.error(f"Failed to notify goal change: {e}")


if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Context Manager API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
