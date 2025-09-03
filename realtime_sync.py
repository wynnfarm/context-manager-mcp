"""
Real-time Context Synchronization Module

This module provides WebSocket support for real-time context updates,
enabling live collaboration and instant synchronization across multiple clients.
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect


class MessageType(Enum):
    """Types of real-time messages"""
    CONTEXT_UPDATED = "context_updated"
    FEATURE_COMPLETED = "feature_completed"
    ISSUE_RESOLVED = "issue_resolved"
    GOAL_CHANGED = "goal_changed"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class RealtimeMessage:
    """Structure for real-time messages"""
    type: MessageType
    project_name: Optional[str] = None
    user_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: Optional[str] = None


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection"""
    websocket: WebSocket
    user_id: Optional[str] = None
    project_name: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionManager:
    """Manages WebSocket connections and real-time messaging"""
    
    def __init__(self):
        # Project-specific connections
        self.project_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        
        # Global connections (for system-wide updates)
        self.global_connections: Set[WebSocket] = set()
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, ConnectionInfo] = {}
        
        # Message queue for broadcasting
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Background task for processing messages
        self.broadcast_task: Optional[asyncio.Task] = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the connection manager and background tasks"""
        self.broadcast_task = asyncio.create_task(self._broadcast_worker())
        self.logger.info("Connection Manager started")
    
    async def stop(self):
        """Stop the connection manager and cleanup"""
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for websocket in list(self.connection_info.keys()):
            await self.disconnect(websocket)
        
        self.logger.info("Connection Manager stopped")
    
    async def connect(self, websocket: WebSocket, project_name: Optional[str] = None, user_id: Optional[str] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Create connection info
        conn_info = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            project_name=project_name
        )
        self.connection_info[websocket] = conn_info
        
        # Add to appropriate connection sets
        if project_name:
            self.project_connections[project_name].add(websocket)
            self.logger.info(f"User {user_id} connected to project {project_name}")
        else:
            self.global_connections.add(websocket)
            self.logger.info(f"User {user_id} connected to global updates")
        
        # Send welcome message
        welcome_msg = RealtimeMessage(
            type=MessageType.USER_JOINED,
            project_name=project_name,
            user_id=user_id,
            data={
                "message": "Connected to real-time updates",
                "project_name": project_name,
                "connected_at": conn_info.connected_at.isoformat()
            }
        )
        await self._send_message(websocket, welcome_msg)
        
        # Broadcast user joined notification
        if project_name and user_id:
            join_msg = RealtimeMessage(
                type=MessageType.USER_JOINED,
                project_name=project_name,
                user_id=user_id,
                data={
                    "user_id": user_id,
                    "connected_at": conn_info.connected_at.isoformat()
                }
            )
            await self.broadcast_to_project(project_name, join_msg, exclude_user=user_id)
    
    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        if websocket not in self.connection_info:
            return
        
        conn_info = self.connection_info[websocket]
        project_name = conn_info.project_name
        user_id = conn_info.user_id
        
        # Remove from connection sets
        if project_name and websocket in self.project_connections[project_name]:
            self.project_connections[project_name].remove(websocket)
            if not self.project_connections[project_name]:
                del self.project_connections[project_name]
        
        if websocket in self.global_connections:
            self.global_connections.remove(websocket)
        
        # Remove connection info
        del self.connection_info[websocket]
        
        # Broadcast user left notification
        if project_name and user_id:
            leave_msg = RealtimeMessage(
                type=MessageType.USER_LEFT,
                project_name=project_name,
                user_id=user_id,
                data={
                    "user_id": user_id,
                    "disconnected_at": datetime.now().isoformat()
                }
            )
            await self.broadcast_to_project(project_name, leave_msg)
        
        self.logger.info(f"User {user_id} disconnected from project {project_name}")
    
    async def broadcast_to_project(self, project_name: str, message: RealtimeMessage, exclude_user: Optional[str] = None):
        """Broadcast a message to all connections for a specific project"""
        if project_name not in self.project_connections:
            return
        
        disconnected = set()
        for websocket in self.project_connections[project_name]:
            if websocket in self.connection_info:
                conn_info = self.connection_info[websocket]
                if exclude_user and conn_info.user_id == exclude_user:
                    continue
                
                try:
                    await self._send_message(websocket, message)
                except Exception as e:
                    self.logger.error(f"Failed to send message to {conn_info.user_id}: {e}")
                    disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def broadcast_global(self, message: RealtimeMessage):
        """Broadcast a message to all global connections"""
        disconnected = set()
        for websocket in self.global_connections:
            if websocket in self.connection_info:
                try:
                    await self._send_message(websocket, message)
                except Exception as e:
                    self.logger.error(f"Failed to send global message: {e}")
                    disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def _send_message(self, websocket: WebSocket, message: RealtimeMessage):
        """Send a message to a specific WebSocket connection"""
        try:
            message_dict = {
                "type": message.type.value,
                "project_name": message.project_name,
                "user_id": message.user_id,
                "data": message.data,
                "timestamp": message.timestamp.isoformat(),
                "message_id": message.message_id or f"{message.timestamp.timestamp()}_{id(message)}"
            }
            
            await websocket.send_text(json.dumps(message_dict))
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            raise
    
    async def _broadcast_worker(self):
        """Background worker for processing queued messages"""
        while True:
            try:
                message = await self.message_queue.get()
                
                if message.project_name:
                    await self.broadcast_to_project(message.project_name, message)
                else:
                    await self.broadcast_global(message)
                
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in broadcast worker: {e}")
    
    async def queue_message(self, message: RealtimeMessage):
        """Queue a message for broadcasting"""
        await self.message_queue.put(message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections"""
        project_stats = {}
        for project_name, connections in self.project_connections.items():
            project_stats[project_name] = {
                "connection_count": len(connections),
                "users": [
                    self.connection_info[ws].user_id 
                    for ws in connections 
                    if ws in self.connection_info
                ]
            }
        
        return {
            "total_connections": len(self.connection_info),
            "global_connections": len(self.global_connections),
            "project_connections": project_stats,
            "active_projects": list(self.project_connections.keys())
        }


# Global connection manager instance
connection_manager = ConnectionManager()


# Utility functions for creating common message types
def create_context_updated_message(project_name: str, user_id: str, changes: Dict[str, Any]) -> RealtimeMessage:
    """Create a context updated message"""
    return RealtimeMessage(
        type=MessageType.CONTEXT_UPDATED,
        project_name=project_name,
        user_id=user_id,
        data={
            "changes": changes,
            "updated_at": datetime.now().isoformat()
        }
    )


def create_feature_completed_message(project_name: str, user_id: str, feature: str) -> RealtimeMessage:
    """Create a feature completed message"""
    return RealtimeMessage(
        type=MessageType.FEATURE_COMPLETED,
        project_name=project_name,
        user_id=user_id,
        data={
            "feature": feature,
            "completed_at": datetime.now().isoformat()
        }
    )


def create_issue_resolved_message(project_name: str, user_id: str, issue: str) -> RealtimeMessage:
    """Create an issue resolved message"""
    return RealtimeMessage(
        type=MessageType.ISSUE_RESOLVED,
        project_name=project_name,
        user_id=user_id,
        data={
            "issue": issue,
            "resolved_at": datetime.now().isoformat()
        }
    )


def create_goal_changed_message(project_name: str, user_id: str, old_goal: str, new_goal: str) -> RealtimeMessage:
    """Create a goal changed message"""
    return RealtimeMessage(
        type=MessageType.GOAL_CHANGED,
        project_name=project_name,
        user_id=user_id,
        data={
            "old_goal": old_goal,
            "new_goal": new_goal,
            "changed_at": datetime.now().isoformat()
        }
    )
