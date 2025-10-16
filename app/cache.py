"""
Redis cache utilities for the Frigate Dashboard Middleware.

This module handles Redis connections, caching operations,
and provides utilities for cache management and invalidation.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from .config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis cache operations and provides caching utilities."""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.pool: Optional[ConnectionPool] = None
    
    async def initialize(self) -> None:
        """Initialize the Redis connection pool."""
        try:
            # Create connection pool
            self.pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create Redis client
            self.redis = Redis(connection_pool=self.pool)
            
            # Test the connection
            await self.redis.ping()
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def close(self) -> None:
        """Close the Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.redis:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            if ttl:
                await self.redis.setex(key, ttl, serialized_value)
            else:
                await self.redis.set(key, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            result = await self.redis.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Error setting expiration for cache key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> int:
        """
        Get time to live for a key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if not self.redis:
            return -2
        
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for cache key {key}: {e}")
            return -2
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Redis pattern (e.g., "violations:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value or None if error
        """
        if not self.redis:
            return None
        
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing cache key {key}: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.redis:
                return False
            
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def get_info(self) -> Dict[str, Any]:
        """
        Get Redis server information.
        
        Returns:
            Dictionary with Redis info
        """
        if not self.redis:
            return {}
        
        try:
            info = await self.redis.info()
            return {
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses")
            }
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {}


# Global cache manager instance
cache_manager = CacheManager()


# Cache decorator
def cached(ttl: int, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {cache_key}")
            
            return result
        
        return wrapper
    return decorator


# Cache utilities
class CacheUtils:
    """Utility functions for cache operations."""
    
    @staticmethod
    async def get_or_set(key: str, func, ttl: int, *args, **kwargs) -> Any:
        """
        Get value from cache or set it using a function.
        
        Args:
            key: Cache key
            func: Function to call if cache miss
            ttl: Time to live in seconds
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached_value = await cache_manager.get(key)
        if cached_value is not None:
            return cached_value
        
        # Execute function and cache result
        result = await func(*args, **kwargs)
        await cache_manager.set(key, result, ttl)
        
        return result
    
    @staticmethod
    async def invalidate_pattern(pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: Redis pattern
            
        Returns:
            Number of keys invalidated
        """
        return await cache_manager.clear_pattern(pattern)
    
    @staticmethod
    async def warm_cache(key: str, func, ttl: int, *args, **kwargs) -> Any:
        """
        Warm the cache with a value.
        
        Args:
            key: Cache key
            func: Function to call
            ttl: Time to live in seconds
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Cached value
        """
        result = await func(*args, **kwargs)
        await cache_manager.set(key, result, ttl)
        return result
    
    @staticmethod
    async def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        redis_info = await cache_manager.get_info()
        
        # Get cache key counts by pattern
        patterns = [
            "violations:*",
            "employees:*", 
            "cameras:*",
            "dashboard:*"
        ]
        
        key_counts = {}
        for pattern in patterns:
            keys = await cache_manager.redis.keys(pattern) if cache_manager.redis else []
            key_counts[pattern] = len(keys)
        
        return {
            "redis_info": redis_info,
            "key_counts": key_counts,
            "total_keys": sum(key_counts.values())
        }


# Cache dependency for FastAPI
async def get_cache() -> CacheManager:
    """FastAPI dependency to get cache manager."""
    return cache_manager




