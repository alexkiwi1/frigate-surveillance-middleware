"""
FastAPI dependencies for the Frigate Dashboard Middleware.

This module provides dependency injection functions for database,
cache, and other services used throughout the API endpoints.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .database import DatabaseManager, get_database
from .cache import CacheManager, get_cache
from .config import settings

logger = logging.getLogger(__name__)

# Security scheme (optional - can be enabled for authentication)
security = HTTPBearer(auto_error=False)


async def get_database_manager() -> DatabaseManager:
    """
    Dependency to get database manager.
    
    Returns:
        DatabaseManager instance
        
    Raises:
        HTTPException: If database is not available
    """
    db = await get_database()
    
    if not await db.health_check():
        logger.error("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    return db


async def get_cache_manager() -> CacheManager:
    """
    Dependency to get cache manager.
    
    Returns:
        CacheManager instance
        
    Raises:
        HTTPException: If cache is not available
    """
    cache = await get_cache()
    
    if not await cache.health_check():
        logger.warning("Cache health check failed - continuing without cache")
        # Don't raise exception for cache failures, just log warning
        # The application can continue without cache
    
    return cache


async def validate_camera_name(camera: Optional[str] = None) -> Optional[str]:
    """
    Validate camera name against known cameras.
    
    Args:
        camera: Camera name to validate
        
    Returns:
        Validated camera name or None
        
    Raises:
        HTTPException: If camera name is invalid
    """
    if camera is None:
        return None
    
    if camera not in settings.CAMERAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid camera name: {camera}. Valid cameras: {', '.join(settings.CAMERAS)}"
        )
    
    return camera


async def validate_limit(limit: int = 50) -> int:
    """
    Validate and sanitize limit parameter.
    
    Args:
        limit: Limit value to validate
        
    Returns:
        Validated limit value
        
    Raises:
        HTTPException: If limit is invalid
    """
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be greater than 0"
        )
    
    if limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit cannot exceed 1000"
        )
    
    return limit


async def validate_hours(hours: int = 24) -> int:
    """
    Validate and sanitize hours parameter.
    
    Args:
        hours: Hours value to validate
        
    Returns:
        Validated hours value
        
    Raises:
        HTTPException: If hours is invalid
    """
    if hours < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hours must be greater than 0"
        )
    
    if hours > 168:  # 1 week
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hours cannot exceed 168 (1 week)"
        )
    
    return hours


async def validate_timestamp_range(
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> tuple[Optional[float], Optional[float]]:
    """
    Validate timestamp range parameters.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        Tuple of validated timestamps
        
    Raises:
        HTTPException: If timestamps are invalid
    """
    if start_time is not None and start_time < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be a positive timestamp"
        )
    
    if end_time is not None and end_time < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be a positive timestamp"
        )
    
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    return start_time, end_time


async def get_optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Optional authentication dependency.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Token if provided, None otherwise
    """
    if credentials is None:
        return None
    
    # In a real implementation, you would validate the token here
    # For now, we just return the token as-is
    return credentials.credentials


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Required authentication dependency.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Validated token
        
    Raises:
        HTTPException: If authentication is required but not provided
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # In a real implementation, you would validate the token here
    # For now, we just return the token as-is
    return credentials.credentials


# Common dependency combinations
DatabaseDep = Depends(get_database_manager)
CacheDep = Depends(get_cache_manager)
CameraDep = Depends(validate_camera_name)
LimitDep = Depends(validate_limit)
HoursDep = Depends(validate_hours)
AuthDep = Depends(get_optional_auth)
RequiredAuthDep = Depends(require_auth)



