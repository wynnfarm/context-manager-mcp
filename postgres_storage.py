#!/usr/bin/env python3
"""
PostgreSQL storage adapter for Context Manager

This module provides PostgreSQL storage for context data, enabling
scalability across multiple context_manager instances.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)

class PostgreSQLStorage:
    """PostgreSQL storage for context data with enhanced caching and connection pooling."""
    
    def __init__(self, database_url: str = None):
        # Add caching for auto-refresh optimization
        self._cache = {}
        self._cache_ttl = 30  # 30 seconds cache for auto-refresh
        self._last_cache_cleanup = datetime.now()
        """
        Initialize PostgreSQL storage.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Create connection pool with enhanced settings for auto-refresh
        self.pool = SimpleConnectionPool(
            minconn=5,
            maxconn=50,  # Increased for auto-refresh load
            dsn=self.database_url
        )
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test database connection."""
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            logger.info("✅ PostgreSQL connection successful")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise
    
    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        now = datetime.now()
        if (now - self._last_cache_cleanup).seconds > 60:  # Cleanup every minute
            expired_keys = []
            for key, (data, timestamp) in self._cache.items():
                if (now - timestamp).seconds > self._cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            self._last_cache_cleanup = now
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _get_cache_key(self, method: str, *args) -> str:
        """Generate cache key for method calls."""
        return f"{method}:{':'.join(str(arg) for arg in args)}"
    
    def _get_from_cache(self, cache_key: str):
        """Get data from cache if valid."""
        self._cleanup_cache()
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, cache_key: str, data):
        """Set data in cache."""
        self._cache[cache_key] = (data, datetime.now())
    
    def _invalidate_project_cache(self, project_name: str):
        """Invalidate cache entries for a specific project."""
        keys_to_remove = []
        for key in self._cache.keys():
            if f"load_project:{project_name}" in key or "list_projects" in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
        
        if keys_to_remove:
            logger.debug(f"🗑️ Invalidated {len(keys_to_remove)} cache entries for project '{project_name}'")
    
    def save_project(self, project_name: str, data: Dict[str, Any]) -> bool:
        """Save project data to PostgreSQL."""
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    # Prepare data for PostgreSQL
                    sql_data = {
                        'name': project_name,
                        'current_goal': data.get('current_goal', ''),
                        'completed_features': json.dumps(data.get('completed_features', [])),
                        'current_issues': json.dumps(data.get('current_issues', [])),
                        'next_steps': json.dumps(data.get('next_steps', [])),
                        'current_state': json.dumps(data.get('current_state', {})),
                        'key_files': json.dumps(data.get('key_files', [])),
                        'context_anchors': json.dumps(data.get('context_anchors', [])),
                        'conversation_history': json.dumps(data.get('conversation_history', []))
                    }
                    
                    # Use UPSERT (INSERT ... ON CONFLICT)
                    cursor.execute("""
                        INSERT INTO projects 
                        (name, current_goal, completed_features, current_issues, next_steps, 
                         current_state, key_files, context_anchors, conversation_history)
                        VALUES (%(name)s, %(current_goal)s, %(completed_features)s, %(current_issues)s, 
                                %(next_steps)s, %(current_state)s, %(key_files)s, %(context_anchors)s, 
                                %(conversation_history)s)
                        ON CONFLICT (name) DO UPDATE SET
                            current_goal = EXCLUDED.current_goal,
                            completed_features = EXCLUDED.completed_features,
                            current_issues = EXCLUDED.current_issues,
                            next_steps = EXCLUDED.next_steps,
                            current_state = EXCLUDED.current_state,
                            key_files = EXCLUDED.key_files,
                            context_anchors = EXCLUDED.context_anchors,
                            conversation_history = EXCLUDED.conversation_history,
                            updated_at = CURRENT_TIMESTAMP
                    """, sql_data)
                    
                    conn.commit()
                    
                    # Invalidate related cache entries
                    self._invalidate_project_cache(project_name)
                    
                    logger.info(f"✅ Saved project '{project_name}' to PostgreSQL")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to save project '{project_name}': {e}")
            return False
    
    def load_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Load project data from PostgreSQL with caching."""
        # Check cache first
        cache_key = self._get_cache_key("load_project", project_name)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"📋 Using cached data for project '{project_name}'")
            return cached_data
        
        try:
            with self.pool.getconn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM projects WHERE name = %s", (project_name,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        # Convert row to dict and parse JSON fields
                        data = dict(row)
                        # Handle JSONB fields - they might already be parsed or need parsing
                        for field in ['completed_features', 'current_issues', 'next_steps', 'current_state', 'key_files', 'context_anchors', 'conversation_history']:
                            if isinstance(data[field], str):
                                data[field] = json.loads(data[field])
                            elif data[field] is None:
                                data[field] = [] if field in ['completed_features', 'current_issues', 'next_steps', 'key_files', 'context_anchors', 'conversation_history'] else {}
                        
                        # Cache the result
                        self._set_cache(cache_key, data)
                        
                        logger.info(f"✅ Loaded project '{project_name}' from PostgreSQL")
                        return data
                    else:
                        logger.warning(f"⚠️ Project '{project_name}' not found in PostgreSQL")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Failed to load project '{project_name}': {e}")
            return None
    
    def list_projects(self) -> List[str]:
        """List all projects in PostgreSQL with caching."""
        # Check cache first
        cache_key = self._get_cache_key("list_projects")
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"📋 Using cached project list")
            return cached_data
        
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT name FROM projects ORDER BY updated_at DESC")
                    projects = [row[0] for row in cursor.fetchall()]
                    
                    # Cache the result
                    self._set_cache(cache_key, projects)
                    
                    logger.info(f"✅ Found {len(projects)} projects in PostgreSQL")
                    return projects
                    
        except Exception as e:
            logger.error(f"❌ Failed to list projects: {e}")
            return []
    
    def delete_project(self, project_name: str) -> bool:
        """Delete project from PostgreSQL."""
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM projects WHERE name = %s", (project_name,))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        logger.info(f"✅ Deleted project '{project_name}' from PostgreSQL")
                        return True
                    else:
                        logger.warning(f"⚠️ Project '{project_name}' not found for deletion")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to delete project '{project_name}': {e}")
            return False
    
    def get_project_stats(self) -> Dict[str, Any]:
        """Get statistics about projects."""
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_projects,
                            COUNT(CASE WHEN updated_at > NOW() - INTERVAL '24 hours' THEN 1 END) as active_24h,
                            COUNT(CASE WHEN updated_at > NOW() - INTERVAL '7 days' THEN 1 END) as active_7d,
                            MAX(updated_at) as last_updated
                        FROM projects
                    """)
                    row = cursor.fetchone()
                    
                    return {
                        'total_projects': row[0],
                        'active_24h': row[1],
                        'active_7d': row[2],
                        'last_updated': row[3].isoformat() if row[3] else None
                    }
                    
        except Exception as e:
            logger.error(f"❌ Failed to get project stats: {e}")
            return {}
    
    def close(self):
        """Close the connection pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("✅ PostgreSQL connection pool closed")
