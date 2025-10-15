"""
Database connection and query utilities for the Frigate Dashboard Middleware.

This module handles async PostgreSQL connections using asyncpg,
connection pooling, and provides utilities for executing queries.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
import asyncpg
from asyncpg import Pool, Connection
from .config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL connection pool and provides query utilities."""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self._connection_lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=settings.db_pool_size,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,
                command_timeout=60,
                server_settings={
                    'application_name': 'frigate_dashboard_middleware',
                    'timezone': settings.timezone
                }
            )
            logger.info("Database connection pool initialized successfully")
            
            # Test the connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            logger.info("Database connection test successful")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute(self, query: str, *args) -> str:
        """
        Execute a query that doesn't return results.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Status message from the query
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row from the database.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Dictionary representing the row, or None if no results
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Fetch all rows from the database.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            List of dictionaries representing the rows
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetch_many(self, query: str, *args, size: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch many rows from the database with a size limit.
        
        Args:
            query: SQL query string
            *args: Query parameters
            size: Maximum number of rows to fetch
            
        Returns:
            List of dictionaries representing the rows
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows[:size]]
    
    async def transaction(self):
        """
        Get a database transaction context manager.
        
        Returns:
            Transaction context manager
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        return self.pool.acquire()
    
    async def get_connection(self) -> Connection:
        """
        Get a direct database connection.
        
        Returns:
            Database connection
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        return await self.pool.acquire()
    
    async def health_check(self) -> bool:
        """
        Check if the database connection is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Query utilities
class QueryBuilder:
    """Utility class for building common SQL queries."""
    
    @staticmethod
    def build_timeline_query(
        camera: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        source: Optional[str] = None,
        class_type: Optional[str] = None,
        label: Optional[str] = None,
        limit: int = 1000
    ) -> tuple[str, list]:
        """
        Build a timeline query with optional filters.
        
        Args:
            camera: Filter by camera name
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            source: Filter by source type
            class_type: Filter by class type
            label: Filter by label
            limit: Maximum number of results
            
        Returns:
            Tuple of (query_string, parameters)
        """
        query = "SELECT * FROM frigate_timeline WHERE 1=1"
        params = []
        param_count = 0
        
        if camera:
            param_count += 1
            query += f" AND camera = ${param_count}"
            params.append(camera)
        
        if start_time:
            param_count += 1
            query += f" AND timestamp >= ${param_count}"
            params.append(start_time)
        
        if end_time:
            param_count += 1
            query += f" AND timestamp <= ${param_count}"
            params.append(end_time)
        
        if source:
            param_count += 1
            query += f" AND source = ${param_count}"
            params.append(source)
        
        if class_type:
            param_count += 1
            query += f" AND class_type = ${param_count}"
            params.append(class_type)
        
        if label:
            param_count += 1
            query += f" AND data->>'label' = ${param_count}"
            params.append(label)
        
        query += f" ORDER BY timestamp DESC LIMIT ${param_count + 1}"
        params.append(limit)
        
        return query, params
    
    @staticmethod
    def build_violation_query(
        camera: Optional[str] = None,
        hours: int = 1,
        limit: int = 50
    ) -> str:
        """
        Build a complex violation query that joins timeline with face data.
        
        Args:
            camera: Filter by camera name
            hours: Hours to look back
            limit: Maximum number of results
            
        Returns:
            SQL query string
        """
        camera_filter = f"AND p.camera = '{camera}'" if camera else ""
        
        query = f"""
        WITH recent_phones AS (
            SELECT 
                timestamp, 
                camera, 
                source_id, 
                data,
                data->>'label' as label,
                data->'zones' as zones
            FROM frigate_timeline
            WHERE data->>'label' = 'cell phone'
            AND timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours * 3600})
            {camera_filter}
        ),
        nearby_faces AS (
            SELECT DISTINCT ON (rp.timestamp, rp.camera)
                rp.timestamp, 
                rp.camera,
                f.data->>'sub_label' as employee_name,
                f.data->>'score' as confidence
            FROM recent_phones rp
            LEFT JOIN frigate_timeline f ON 
                f.camera = rp.camera 
                AND f.source = 'face'
                AND ABS(f.timestamp - rp.timestamp) < 3
            ORDER BY rp.timestamp, rp.camera, ABS(f.timestamp - rp.timestamp)
        )
        SELECT 
            rp.timestamp,
            rp.camera,
            rp.source_id as id,
            rp.zones,
            COALESCE(nf.employee_name, 'Unknown') as employee_name,
            COALESCE(nf.confidence::float, 0.0) as confidence,
            rs.thumb_path as thumbnail_url,
            CONCAT('{settings.video_api_base_url}/video/', rp.source_id) as video_url,
            CONCAT('{settings.video_api_base_url}/snapshot/', rp.camera, '/', rp.timestamp, '-', rp.source_id) as snapshot_url
        FROM recent_phones rp
        LEFT JOIN nearby_faces nf USING (timestamp, camera)
        LEFT JOIN frigate_reviewsegment rs ON 
            rs.camera = rp.camera 
            AND ABS(rs.start_time - rp.timestamp) < 5
        ORDER BY rp.timestamp DESC
        LIMIT {limit}
        """
        
        return query
    
    @staticmethod
    def build_employee_stats_query(hours: int = 24) -> str:
        """
        Build employee statistics query.
        
        Args:
            hours: Hours to look back for statistics
            
        Returns:
            SQL query string
        """
        query = f"""
        WITH employee_detections AS (
            SELECT 
                data->>'sub_label' as employee_name,
                COUNT(*) as detections,
                COUNT(DISTINCT camera) as cameras_visited,
                MAX(timestamp) as last_seen
            FROM frigate_timeline
            WHERE source = 'face'
            AND timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours * 3600})
            AND data->>'sub_label' IS NOT NULL
            GROUP BY data->>'sub_label'
        ),
        employee_violations AS (
            SELECT 
                COALESCE(nf.employee_name, 'Unknown') as employee_name,
                COUNT(*) as violations_count
            FROM frigate_timeline p
            LEFT JOIN (
                SELECT DISTINCT ON (p.timestamp, p.camera)
                    p.timestamp, 
                    p.camera,
                    f.data->>'sub_label' as employee_name
                FROM frigate_timeline p
                LEFT JOIN frigate_timeline f ON 
                    f.camera = p.camera 
                    AND f.source = 'face'
                    AND ABS(f.timestamp - p.timestamp) < 3
                WHERE p.data->>'label' = 'cell phone'
                AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours * 3600})
                ORDER BY p.timestamp, p.camera, ABS(f.timestamp - p.timestamp)
            ) nf USING (timestamp, camera)
            WHERE p.data->>'label' = 'cell phone'
            AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours * 3600})
            GROUP BY nf.employee_name
        )
        SELECT 
            ed.employee_name,
            ed.detections,
            ed.cameras_visited,
            ed.last_seen,
            COALESCE(ev.violations_count, 0) as violations_count
        FROM employee_detections ed
        LEFT JOIN employee_violations ev ON ed.employee_name = ev.employee_name
        ORDER BY ed.detections DESC
        """
        
        return query


# Database dependency for FastAPI
async def get_database() -> DatabaseManager:
    """FastAPI dependency to get database manager."""
    return db_manager



