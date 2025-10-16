"""
Violation endpoints following FastAPI best practices.

This module provides REST API endpoints for retrieving phone violations,
hourly trends, and related violation data with proper error handling,
guard clauses, and functional programming principles.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..database import DatabaseManager
from ..cache import CacheManager
from ..dependencies_improved import (
    DatabaseDep, 
    CacheDep, 
    CameraDep, 
    LimitDep, 
    HoursDep
)
from ..models import (
    LiveViolationsResponse, 
    HourlyTrendResponse,
    ViolationData,
    HourlyTrendData
)
from ..utils.response_formatter import (
    create_json_response,
    create_error_json_response,
    format_violation_data,
    format_hourly_trend_data,
    handle_api_error
)
from ..utils.errors import (
    NotFoundError,
    DatabaseError,
    CacheError,
    ValidationError,
    handle_database_error,
    handle_cache_error
)
from ..services.queries import ViolationQueries
from ..config import CacheKeys, settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/violations", tags=["violations"])


@router.get(
    "/live",
    response_model=LiveViolationsResponse,
    summary="Get recent phone violations",
    description="Retrieve recent phone violations with employee identification and media URLs"
)
async def get_live_violations(
    camera: Optional[str] = CameraDep,
    limit: int = LimitDep,
    hours: int = HoursDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get recent phone violations with employee identification.
    
    This endpoint returns recent phone violations from the last hour (or specified hours),
    with employee names identified through face recognition, and includes thumbnail,
    video, and snapshot URLs for each violation.
    
    Args:
        camera: Optional camera filter
        limit: Maximum number of violations to return (1-1000)
        hours: Number of hours to look back (1-168)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSONResponse with violation data
        
    Raises:
        HTTPException: If validation fails or service errors occur
    """
    # Guard clauses for early validation
    if not db.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    if not cache.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable"
        )
    
    # Check cache first
    cache_key = CacheKeys.live_violations(camera, limit, hours)
    try:
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for live violations: {cache_key}")
            return create_json_response(
                data=cached_data,
                message="Live violations retrieved from cache"
            )
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
        # Continue without cache
    
    # Fetch data from database
    try:
        violations_data = await ViolationQueries.get_live_violations(
            db=db,
            camera=camera,
            hours=hours,
            limit=limit
        )
        
        # Format violation data
        formatted_violations = [
            format_violation_data(violation) 
            for violation in violations_data
        ]
        
        # Cache the results
        try:
            await cache.set(
                cache_key, 
                formatted_violations, 
                settings.cache_ttl_live_violations
            )
            logger.debug(f"Cached live violations: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
            # Continue without caching
        
        return create_json_response(
            data=formatted_violations,
            message=f"Retrieved {len(formatted_violations)} live violations"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving live violations: {e}")
        return handle_api_error(e, "retrieve live violations")


@router.get(
    "/hourly-trend",
    response_model=HourlyTrendResponse,
    summary="Get hourly violation trends",
    description="Retrieve hourly violation trends with camera and employee breakdowns"
)
async def get_hourly_trend(
    hours: int = HoursDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get hourly violation trends with camera and employee breakdowns.
    
    This endpoint returns hourly violation counts for the specified time period,
    with breakdowns by camera and employee for each hour.
    
    Args:
        hours: Number of hours to analyze (1-168)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSONResponse with hourly trend data
        
    Raises:
        HTTPException: If validation fails or service errors occur
    """
    # Guard clauses
    if not db.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    # Check cache first
    cache_key = CacheKeys.hourly_trend(hours)
    try:
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for hourly trend: {cache_key}")
            return create_json_response(
                data=cached_data,
                message="Hourly trend retrieved from cache"
            )
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
    
    # Fetch data from database
    try:
        trend_data = await ViolationQueries.get_hourly_trend(
            db=db,
            hours=hours
        )
        
        # Format trend data
        formatted_trend = format_hourly_trend_data(trend_data)
        
        # Cache the results
        try:
            await cache.set(
                cache_key, 
                formatted_trend, 
                settings.cache_ttl_hourly_trend
            )
            logger.debug(f"Cached hourly trend: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
        
        return create_json_response(
            data=formatted_trend,
            message=f"Retrieved hourly trend for {hours} hours"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving hourly trend: {e}")
        return handle_api_error(e, "retrieve hourly trend")


@router.get(
    "/stats",
    summary="Get violation statistics",
    description="Retrieve comprehensive violation statistics including camera and employee breakdowns"
)
async def get_violation_stats(
    hours: int = HoursDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get comprehensive violation statistics.
    
    This endpoint returns detailed violation statistics including total counts,
    camera breakdowns, employee violations, and peak hours analysis.
    
    Args:
        hours: Number of hours to analyze (1-168)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSONResponse with violation statistics
        
    Raises:
        HTTPException: If validation fails or service errors occur
    """
    # Guard clauses
    if not db.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    # Check cache first
    cache_key = CacheKeys.violation_stats(hours)
    try:
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for violation stats: {cache_key}")
            return create_json_response(
                data=cached_data,
                message="Violation statistics retrieved from cache"
            )
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
    
    # Fetch data from database
    try:
        stats_data = await ViolationQueries.get_violation_stats(
            db=db,
            hours=hours
        )
        
        # Cache the results
        try:
            await cache.set(
                cache_key, 
                stats_data, 
                settings.cache_ttl_violation_stats
            )
            logger.debug(f"Cached violation stats: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
        
        return create_json_response(
            data=stats_data,
            message=f"Retrieved violation statistics for {hours} hours"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving violation stats: {e}")
        return handle_api_error(e, "retrieve violation statistics")


@router.get(
    "/cache",
    summary="Get violations cache information",
    description="Retrieve information about violations cache status and statistics"
)
async def get_violations_cache_info(
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get violations cache information.
    
    This endpoint returns information about the violations cache including
    status, statistics, and configuration.
    
    Args:
        cache: Cache manager dependency
        
    Returns:
        JSONResponse with cache information
        
    Raises:
        HTTPException: If cache service is unavailable
    """
    # Guard clause
    if not cache.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable"
        )
    
    try:
        cache_info = {
            "status": "connected",
            "keys_pattern": "violations:*",
            "ttl_settings": {
                "live_violations": settings.cache_ttl_live_violations,
                "hourly_trend": settings.cache_ttl_hourly_trend,
                "violation_stats": settings.cache_ttl_violation_stats
            }
        }
        
        return create_json_response(
            data=cache_info,
            message="Violations cache information retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving cache info: {e}")
        return handle_api_error(e, "retrieve cache information")


@router.delete(
    "/cache",
    summary="Clear violations cache",
    description="Clear all violations-related cache entries"
)
async def clear_violations_cache(
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Clear violations cache.
    
    This endpoint clears all violations-related cache entries.
    
    Args:
        cache: Cache manager dependency
        
    Returns:
        JSONResponse with operation result
        
    Raises:
        HTTPException: If cache service is unavailable
    """
    # Guard clause
    if not cache.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable"
        )
    
    try:
        # Clear all violations cache keys
        await cache.delete_pattern("violations:*")
        
        return create_json_response(
            data={"cleared_keys": "violations:*"},
            message="Violations cache cleared successfully"
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return handle_api_error(e, "clear violations cache")




