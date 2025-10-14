"""
Background tasks for the Frigate Dashboard Middleware.

This module provides background tasks for polling the database,
refreshing aggregated statistics, and managing cache.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..database import DatabaseManager
from ..cache import CacheManager
from ..services.queries import (
    ViolationQueries,
    EmployeeQueries,
    CameraQueries,
    DashboardQueries
)
from ..utils.time import get_current_timestamp, get_timestamp_ago
from ..config import settings, CacheKeys

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks for the application."""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self.db_manager: Optional[DatabaseManager] = None
        self.cache_manager: Optional[CacheManager] = None
    
    async def start(self):
        """Start all background tasks."""
        if self.is_running:
            logger.warning("Background tasks already running")
            return
        
        logger.info("Starting background tasks...")
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.cache_manager = CacheManager()
        
        await self.db_manager.initialize()
        await self.cache_manager.initialize()
        
        self.is_running = True
        
        # Start individual tasks
        self.tasks["violation_polling"] = asyncio.create_task(
            self._violation_polling_task()
        )
        self.tasks["stats_refresh"] = asyncio.create_task(
            self._stats_refresh_task()
        )
        self.tasks["cache_cleanup"] = asyncio.create_task(
            self._cache_cleanup_task()
        )
        self.tasks["health_check"] = asyncio.create_task(
            self._health_check_task()
        )
        
        logger.info("Background tasks started successfully")
    
    async def stop(self):
        """Stop all background tasks."""
        if not self.is_running:
            return
        
        logger.info("Stopping background tasks...")
        
        self.is_running = False
        
        # Cancel all tasks
        for task_name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"Task {task_name} cancelled")
        
        self.tasks.clear()
        
        # Close managers
        if self.db_manager:
            await self.db_manager.close()
        if self.cache_manager:
            await self.cache_manager.close()
        
        logger.info("Background tasks stopped")
    
    async def _violation_polling_task(self):
        """Poll for new violations and update cache."""
        logger.info("Started violation polling task")
        
        while self.is_running:
            try:
                # Get recent violations
                violations = await ViolationQueries.get_live_violations(
                    db=self.db_manager,
                    hours=1,
                    limit=100
                )
                
                # Update violation cache
                cache_key = CacheKeys.live_violations()
                await self.cache_manager.set(
                    cache_key,
                    violations,
                    settings.cache_ttl_live_violations
                )
                
                # Update hourly trend cache
                hourly_trend = await ViolationQueries.get_hourly_trend(
                    db=self.db_manager,
                    hours=24
                )
                trend_cache_key = CacheKeys.hourly_trend()
                await self.cache_manager.set(
                    trend_cache_key,
                    hourly_trend,
                    settings.cache_ttl_hourly_trend
                )
                
                logger.debug(f"Updated violation cache: {len(violations)} violations")
                
            except Exception as e:
                logger.error(f"Error in violation polling task: {e}")
            
            await asyncio.sleep(settings.background_poll_interval)
    
    async def _stats_refresh_task(self):
        """Refresh aggregated statistics."""
        logger.info("Started stats refresh task")
        
        while self.is_running:
            try:
                # Refresh employee stats
                employee_stats = await EmployeeQueries.get_employee_stats(
                    db=self.db_manager,
                    hours=24
                )
                cache_key = CacheKeys.employee_stats()
                await self.cache_manager.set(
                    cache_key,
                    employee_stats,
                    settings.cache_ttl_employee_stats
                )
                
                # Refresh camera summaries
                from ..config import CAMERAS
                camera_summaries = []
                for camera in CAMERAS:
                    try:
                        summary = await CameraQueries.get_camera_summary(
                            db=self.db_manager,
                            camera=camera
                        )
                        if summary:
                            camera_summaries.append(summary)
                    except Exception as e:
                        logger.warning(f"Failed to get camera summary for {camera}: {e}")
                
                # Cache individual camera summaries
                for summary in camera_summaries:
                    camera_cache_key = CacheKeys.camera_summary(summary['camera'])
                    await self.cache_manager.set(
                        camera_cache_key,
                        summary,
                        settings.cache_ttl_camera_summary
                    )
                
                # Cache all camera summaries
                all_cameras_key = "cameras:summary:all"
                await self.cache_manager.set(
                    all_cameras_key,
                    camera_summaries,
                    settings.cache_ttl_camera_summary
                )
                
                # Refresh dashboard overview
                dashboard_overview = await DashboardQueries.get_dashboard_overview(
                    db=self.db_manager
                )
                dashboard_cache_key = CacheKeys.dashboard_overview()
                await self.cache_manager.set(
                    dashboard_cache_key,
                    dashboard_overview,
                    settings.cache_ttl_dashboard_overview
                )
                
                logger.debug("Refreshed aggregated statistics")
                
            except Exception as e:
                logger.error(f"Error in stats refresh task: {e}")
            
            await asyncio.sleep(settings.background_stats_refresh_interval)
    
    async def _cache_cleanup_task(self):
        """Clean up expired cache entries and perform maintenance."""
        logger.info("Started cache cleanup task")
        
        while self.is_running:
            try:
                # Get cache statistics
                cache_info = await self.cache_manager.redis.info("memory")
                cache_size = cache_info.get("used_memory_human", "unknown")
                
                # Clean up old violation data (older than 7 days)
                cutoff_time = get_past_timestamp(days=7)
                
                # This would require implementing a cleanup query
                # For now, just log cache statistics
                logger.debug(f"Cache size: {cache_size}")
                
                # Clean up any orphaned cache keys
                await self._cleanup_orphaned_keys()
                
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
            
            await asyncio.sleep(settings.background_cache_cleanup_interval)
    
    async def _health_check_task(self):
        """Perform health checks on database and cache."""
        logger.info("Started health check task")
        
        while self.is_running:
            try:
                # Check database health
                db_health = await self.db_manager.health_check()
                
                # Check cache health
                cache_health = await self.cache_manager.health_check()
                
                # Log health status
                if not db_health or not cache_health:
                    logger.warning(f"Health check failed - DB: {db_health}, Cache: {cache_health}")
                else:
                    logger.debug("Health check passed")
                
                # Update health status in cache
                health_status = {
                    "database": db_health,
                    "cache": cache_health,
                    "timestamp": get_current_timestamp(),
                    "uptime": "unknown"  # Could calculate from start time
                }
                
                await self.cache_manager.set(
                    "system:health",
                    health_status,
                    60  # 1 minute TTL
                )
                
            except Exception as e:
                logger.error(f"Error in health check task: {e}")
            
            await asyncio.sleep(settings.background_health_check_interval)
    
    async def _cleanup_orphaned_keys(self):
        """Clean up orphaned cache keys."""
        try:
            # Get all cache keys
            keys = await self.cache_manager.redis.keys("*")
            
            # Count keys by pattern
            key_counts = {}
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                if ":" in key_str:
                    pattern = ":".join(key_str.split(":")[:2])
                    key_counts[pattern] = key_counts.get(pattern, 0) + 1
            
            # Log key statistics
            if key_counts:
                logger.debug(f"Cache key distribution: {key_counts}")
            
            # Clean up any keys that are too old or invalid
            # This is a placeholder for more sophisticated cleanup logic
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned keys: {e}")
    
    async def get_task_status(self) -> Dict[str, Any]:
        """Get status of all background tasks."""
        status = {
            "is_running": self.is_running,
            "tasks": {}
        }
        
        for task_name, task in self.tasks.items():
            status["tasks"][task_name] = {
                "running": not task.done(),
                "cancelled": task.cancelled(),
                "exception": str(task.exception()) if task.done() and task.exception() else None
            }
        
        return status
    
    async def restart_task(self, task_name: str):
        """Restart a specific background task."""
        if task_name not in self.tasks:
            raise ValueError(f"Unknown task: {task_name}")
        
        # Cancel existing task
        if not self.tasks[task_name].done():
            self.tasks[task_name].cancel()
            try:
                await self.tasks[task_name]
            except asyncio.CancelledError:
                pass
        
        # Start new task
        if task_name == "violation_polling":
            self.tasks[task_name] = asyncio.create_task(
                self._violation_polling_task()
            )
        elif task_name == "stats_refresh":
            self.tasks[task_name] = asyncio.create_task(
                self._stats_refresh_task()
            )
        elif task_name == "cache_cleanup":
            self.tasks[task_name] = asyncio.create_task(
                self._cache_cleanup_task()
            )
        elif task_name == "health_check":
            self.tasks[task_name] = asyncio.create_task(
                self._health_check_task()
            )
        
        logger.info(f"Restarted task: {task_name}")


# Global background task manager instance
background_manager = BackgroundTaskManager()


async def start_background_tasks():
    """Start all background tasks."""
    await background_manager.start()


async def stop_background_tasks():
    """Stop all background tasks."""
    await background_manager.stop()


async def get_background_status() -> Dict[str, Any]:
    """Get status of background tasks."""
    return await background_manager.get_task_status()


async def restart_background_task(task_name: str):
    """Restart a specific background task."""
    await background_manager.restart_task(task_name)
