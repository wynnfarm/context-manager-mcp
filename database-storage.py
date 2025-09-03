#!/usr/bin/env python3
"""
Database-backed storage for Context Manager

This module provides database storage for context data, enabling
scalability across multiple context_manager instances.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import sqlite3
import redis
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseStorage:
    """Database-backed storage for context data."""
    
    def __init__(self, storage_type: str = "sqlite", db_path: str = None, redis_url: str = None):
        """
        Initialize database storage.
        
        Args:
            storage_type: "sqlite" or "redis"
            db_path: Path to SQLite database
            redis_url: Redis connection URL
        """
        self.storage_type = storage_type
        
        if storage_type == "sqlite":
            self.db_path = db_path or "/app/contexts/context_manager.db"
            self._init_sqlite()
        elif storage_type == "redis":
            self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
            self._init_redis()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
    
    def _init_sqlite(self):
        """Initialize SQLite database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    current_goal TEXT,
                    completed_features TEXT,
                    current_issues TEXT,
                    next_steps TEXT,
                    current_state TEXT,
                    key_files TEXT,
                    context_anchors TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def _init_redis(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(self.redis_url)
        # Test connection
        self.redis_client.ping()
    
    def save_project(self, project_name: str, data: Dict[str, Any]) -> bool:
        """Save project data to database."""
        try:
            if self.storage_type == "sqlite":
                return self._save_sqlite(project_name, data)
            elif self.storage_type == "redis":
                return self._save_redis(project_name, data)
        except Exception as e:
            logger.error(f"Failed to save project {project_name}: {e}")
            return False
    
    def load_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Load project data from database."""
        try:
            if self.storage_type == "sqlite":
                return self._load_sqlite(project_name)
            elif self.storage_type == "redis":
                return self._load_redis(project_name)
        except Exception as e:
            logger.error(f"Failed to load project {project_name}: {e}")
            return None
    
    def list_projects(self) -> List[str]:
        """List all projects in database."""
        try:
            if self.storage_type == "sqlite":
                return self._list_sqlite()
            elif self.storage_type == "redis":
                return self._list_redis()
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []
    
    def delete_project(self, project_name: str) -> bool:
        """Delete project from database."""
        try:
            if self.storage_type == "sqlite":
                return self._delete_sqlite(project_name)
            elif self.storage_type == "redis":
                return self._delete_redis(project_name)
        except Exception as e:
            logger.error(f"Failed to delete project {project_name}: {e}")
            return False
    
    def _save_sqlite(self, project_name: str, data: Dict[str, Any]) -> bool:
        """Save to SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            # Convert data to JSON strings
            json_data = {
                'name': project_name,
                'current_goal': data.get('current_goal', ''),
                'completed_features': json.dumps(data.get('completed_features', [])),
                'current_issues': json.dumps(data.get('current_issues', [])),
                'next_steps': json.dumps(data.get('next_steps', [])),
                'current_state': json.dumps(data.get('current_state', {})),
                'key_files': json.dumps(data.get('key_files', [])),
                'context_anchors': json.dumps(data.get('context_anchors', [])),
                'last_updated': datetime.now().isoformat()
            }
            
            conn.execute("""
                INSERT OR REPLACE INTO projects 
                (name, current_goal, completed_features, current_issues, next_steps, 
                 current_state, key_files, context_anchors, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                json_data['name'], json_data['current_goal'], json_data['completed_features'],
                json_data['current_issues'], json_data['next_steps'], json_data['current_state'],
                json_data['key_files'], json_data['context_anchors'], json_data['last_updated']
            ))
            conn.commit()
            return True
    
    def _load_sqlite(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Load from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM projects WHERE name = ?", (project_name,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    'project_name': row[1],
                    'current_goal': row[2],
                    'completed_features': json.loads(row[3]),
                    'current_issues': json.loads(row[4]),
                    'next_steps': json.loads(row[5]),
                    'current_state': json.loads(row[6]),
                    'key_files': json.loads(row[7]),
                    'context_anchors': json.loads(row[8]),
                    'last_updated': row[9]
                }
            return None
    
    def _list_sqlite(self) -> List[str]:
        """List projects from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM projects")
            return [row[0] for row in cursor.fetchall()]
    
    def _delete_sqlite(self, project_name: str) -> bool:
        """Delete from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM projects WHERE name = ?", (project_name,))
            conn.commit()
            return True
    
    def _save_redis(self, project_name: str, data: Dict[str, Any]) -> bool:
        """Save to Redis database."""
        key = f"context:project:{project_name}"
        self.redis_client.set(key, json.dumps(data))
        return True
    
    def _load_redis(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Load from Redis database."""
        key = f"context:project:{project_name}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def _list_redis(self) -> List[str]:
        """List projects from Redis database."""
        keys = self.redis_client.keys("context:project:*")
        return [key.decode().replace("context:project:", "") for key in keys]
    
    def _delete_redis(self, project_name: str) -> bool:
        """Delete from Redis database."""
        key = f"context:project:{project_name}"
        self.redis_client.delete(key)
        return True
