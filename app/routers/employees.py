"""
Employee endpoints for the Frigate Dashboard Middleware.

This module provides REST API endpoints for retrieving employee statistics,
violation history, and related employee data with caching.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..database import DatabaseManager
from ..cache import CacheManager
from ..dependencies import DatabaseDep, CacheDep, LimitDep, HoursDep, validate_timestamp_range
from ..models import (
    EmployeeStatsResponse,
    EmployeeViolationsResponse,
    EmployeeStats,
    ViolationData
)
from ..utils.formatting import format_success_response, format_error_response
from ..services.queries import EmployeeQueries
from ..utils.formatting import format_employee_stats, format_violation_data, paginate_results
from ..config import CacheKeys, settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get(
    "/stats",
    response_model=EmployeeStatsResponse,
    summary="Get employee statistics",
    description="Retrieve comprehensive employee statistics including activity levels and violation counts"
)
async def get_employee_stats(
    hours: int = HoursDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get comprehensive employee statistics.
    
    This endpoint returns employee statistics including:
    - Total detections per employee
    - Number of cameras visited
    - Last seen timestamp
    - Activity level classification (high/medium/low)
    - Phone violation counts
    
    Args:
        hours: Hours to analyze (1-168, default 24)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with employee statistics
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        # Generate cache key
        cache_key = CacheKeys.employee_stats()
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for employee stats: {cache_key}")
            return JSONResponse(
                content=format_success_response(cached_data, "Employee stats retrieved from cache"),
                status_code=status.HTTP_200_OK
            )
        
        # Query database
        logger.info(f"Fetching employee stats: hours={hours}")
        raw_stats = await EmployeeQueries.get_employee_stats(
            db=db,
            hours=hours
        )
        
        # Format the data
        formatted_stats = [format_employee_stats(stat) for stat in raw_stats]
        
        # Cache the results
        await cache.set(cache_key, formatted_stats, settings.cache_ttl_employee_stats)
        logger.debug(f"Cached employee stats: {cache_key}")
        
        return JSONResponse(
            content=format_success_response(formatted_stats, "Employee statistics retrieved successfully"),
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error retrieving employee stats: {e}")
        return JSONResponse(
            content=format_error_response(
                "Failed to retrieve employee statistics",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/{employee_name}/violations",
    response_model=EmployeeViolationsResponse,
    summary="Get employee violation history",
    description="Retrieve detailed violation history for a specific employee"
)
async def get_employee_violations(
    employee_name: str,
    start_time: Optional[float] = Query(None, description="Start timestamp filter"),
    end_time: Optional[float] = Query(None, description="End timestamp filter"),
    limit: int = LimitDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get detailed violation history for a specific employee.
    
    This endpoint returns all phone violations for a specific employee,
    with optional time filtering and pagination.
    
    Args:
        employee_name: Name of the employee
        start_time: Optional start timestamp filter
        end_time: Optional end timestamp filter
        limit: Maximum number of results (1-1000)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with employee violations
        
    Raises:
        HTTPException: If database query fails or employee not found
    """
    try:
        # Validate timestamp range
        start_time, end_time = await validate_timestamp_range(start_time, end_time)
        
        # Generate cache key
        cache_key = CacheKeys.employee_violations(employee_name, start_time, end_time, limit)
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for employee violations: {cache_key}")
            return JSONResponse(
                content=format_success_response(cached_data, "Employee violations retrieved from cache"),
                status_code=status.HTTP_200_OK
            )
        
        # Query database
        logger.info(f"Fetching violations for employee {employee_name}: start_time={start_time}, end_time={end_time}, limit={limit}")
        raw_violations = await EmployeeQueries.get_employee_violations(
            db=db,
            employee_name=employee_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # Format the data
        formatted_violations = [format_violation_data(violation) for violation in raw_violations]
        
        # Add pagination info if needed
        pagination_info = None
        if len(formatted_violations) >= limit:
            # Get total count for pagination
            count_query = """
            SELECT COUNT(*) as total
            FROM timeline p
            LEFT JOIN timeline f ON 
                f.camera = p.camera 
                AND f.source = 'face'
                AND ABS(f.timestamp - p.timestamp) < 3
            WHERE p.data->>'label' = 'cell phone'
            AND f.data->>'sub_label' = $1
            """
            time_params = [employee_name]
            if start_time and end_time:
                count_query += " AND p.timestamp BETWEEN $2 AND $3"
                time_params.extend([start_time, end_time])
            elif start_time:
                count_query += " AND p.timestamp >= $2"
                time_params.append(start_time)
            elif end_time:
                count_query += " AND p.timestamp <= $2"
                time_params.append(end_time)
            
            count_result = await db.fetch_one(count_query, *time_params)
            total_count = count_result['total'] if count_result else 0
            
            pagination_info = {
                "page": 1,
                "per_page": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit,
                "has_next": total_count > limit,
                "has_prev": False
            }
        
        # Prepare response data
        response_data = {
            "violations": formatted_violations,
            "employee_name": employee_name,
            "time_range": {
                "start_time": start_time,
                "end_time": end_time
            },
            "pagination": pagination_info
        }
        
        # Cache the results
        await cache.set(cache_key, response_data, settings.cache_ttl_employee_violations)
        logger.debug(f"Cached employee violations: {cache_key}")
        
        return JSONResponse(
            content=format_success_response(response_data, f"Violations for {employee_name} retrieved successfully"),
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving violations for employee {employee_name}: {e}")
        return JSONResponse(
            content=format_error_response(
                f"Failed to retrieve violations for employee {employee_name}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/{employee_name}/activity",
    summary="Get employee activity summary",
    description="Get activity summary for a specific employee including recent movements and violations"
)
async def get_employee_activity(
    employee_name: str,
    hours: int = HoursDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get activity summary for a specific employee.
    
    This endpoint returns a comprehensive activity summary including:
    - Recent detections and movements
    - Camera visits and duration
    - Violation patterns
    - Activity timeline
    
    Args:
        employee_name: Name of the employee
        hours: Hours to analyze (1-168, default 24)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with employee activity summary
    """
    try:
        # Generate cache key
        cache_key = f"employees:{employee_name}:activity:{hours}"
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for employee activity: {cache_key}")
            return JSONResponse(
                content=format_success_response(cached_data, "Employee activity retrieved from cache"),
                status_code=status.HTTP_200_OK
            )
        
        # Query database for activity summary
        logger.info(f"Fetching activity for employee {employee_name}: hours={hours}")
        
        # Get recent detections
        detections_query = """
        SELECT 
            timestamp,
            camera,
            data->>'label' as event_type,
            data->'zones' as zones,
            data->>'score' as confidence
        FROM timeline
        WHERE source = 'face'
        AND data->>'sub_label' = $1
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - $2)
        ORDER BY timestamp DESC
        LIMIT 100
        """
        detections = await db.fetch_all(detections_query, employee_name, hours * 3600)
        
        # Get camera visits
        camera_visits_query = """
        SELECT 
            camera,
            COUNT(*) as visits,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen,
            MAX(timestamp) - MIN(timestamp) as duration
        FROM timeline
        WHERE source = 'face'
        AND data->>'sub_label' = $1
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - $2)
        GROUP BY camera
        ORDER BY visits DESC
        """
        camera_visits = await db.fetch_all(camera_visits_query, employee_name, hours * 3600)
        
        # Get violation summary
        violation_summary_query = """
        SELECT 
            COUNT(*) as total_violations,
            COUNT(DISTINCT p.camera) as violation_cameras,
            MAX(p.timestamp) as last_violation
        FROM timeline p
        LEFT JOIN timeline f ON 
            f.camera = p.camera 
            AND f.source = 'face'
            AND ABS(f.timestamp - p.timestamp) < 3
        WHERE p.data->>'label' = 'cell phone'
        AND f.data->>'sub_label' = $1
        AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - $2)
        """
        violation_summary = await db.fetch_one(violation_summary_query, employee_name, hours * 3600)
        
        # Get hourly activity pattern
        hourly_pattern_query = """
        SELECT 
            EXTRACT(HOUR FROM to_timestamp(timestamp)) as hour,
            COUNT(*) as detections
        FROM timeline
        WHERE source = 'face'
        AND data->>'sub_label' = $1
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - $2)
        GROUP BY EXTRACT(HOUR FROM to_timestamp(timestamp))
        ORDER BY hour
        """
        hourly_pattern = await db.fetch_all(hourly_pattern_query, employee_name, hours * 3600)
        
        # Compile activity summary
        activity_summary = {
            "employee_name": employee_name,
            "time_period_hours": hours,
            "total_detections": len(detections),
            "cameras_visited": len(camera_visits),
            "violation_summary": violation_summary or {
                "total_violations": 0,
                "violation_cameras": 0,
                "last_violation": None
            },
            "camera_visits": camera_visits,
            "recent_detections": detections[:20],  # Last 20 detections
            "hourly_pattern": hourly_pattern,
            "activity_level": "high" if len(detections) >= settings.high_activity_threshold else 
                            "medium" if len(detections) >= settings.medium_activity_threshold else "low"
        }
        
        # Cache the results
        await cache.set(cache_key, activity_summary, settings.cache_ttl_employee_stats)
        logger.debug(f"Cached employee activity: {cache_key}")
        
        return JSONResponse(
            content=format_success_response(activity_summary, f"Activity summary for {employee_name} retrieved successfully"),
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error retrieving activity for employee {employee_name}: {e}")
        return JSONResponse(
            content=format_error_response(
                f"Failed to retrieve activity for employee {employee_name}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/search",
    summary="Search employees",
    description="Search for employees by name with fuzzy matching"
)
async def search_employees(
    query: str = Query(..., description="Search query", min_length=2),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Search for employees by name.
    
    This endpoint provides fuzzy search functionality for finding employees
    by name, useful for autocomplete and search features.
    
    Args:
        query: Search query (minimum 2 characters)
        limit: Maximum number of results (1-50)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with matching employees
    """
    try:
        # Generate cache key
        cache_key = f"employees:search:{query}:{limit}"
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for employee search: {cache_key}")
            return JSONResponse(
                content=format_success_response(cached_data, "Employee search results retrieved from cache"),
                status_code=status.HTTP_200_OK
            )
        
        # Query database for employee names
        logger.info(f"Searching employees: query={query}, limit={limit}")
        
        search_query = """
        SELECT DISTINCT
            data->>'sub_label' as employee_name,
            COUNT(*) as detection_count,
            MAX(timestamp) as last_seen
        FROM timeline
        WHERE source = 'face'
        AND data->>'sub_label' IS NOT NULL
        AND LOWER(data->>'sub_label') LIKE LOWER($1)
        GROUP BY data->>'sub_label'
        ORDER BY detection_count DESC, last_seen DESC
        LIMIT $2
        """
        
        search_pattern = f"%{query}%"
        employees = await db.fetch_all(search_query, search_pattern, limit)
        
        # Format the results
        search_results = [
            {
                "employee_name": emp["employee_name"],
                "detection_count": emp["detection_count"],
                "last_seen": emp["last_seen"],
                "last_seen_relative": "recent" if emp["last_seen"] and (time.time() - emp["last_seen"]) < 3600 else "older"
            }
            for emp in employees
        ]
        
        # Cache the results
        await cache.set(cache_key, search_results, 300)  # 5 minute cache
        logger.debug(f"Cached employee search: {cache_key}")
        
        return JSONResponse(
            content=format_success_response(search_results, f"Found {len(search_results)} employees matching '{query}'"),
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error searching employees: {e}")
        return JSONResponse(
            content=format_error_response(
                "Failed to search employees",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete(
    "/cache",
    summary="Clear employee cache",
    description="Clear all cached employee data"
)
async def clear_employee_cache(
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Clear all cached employee data.
    
    This endpoint clears all cached employee-related data, forcing fresh
    queries on the next request.
    
    Args:
        cache: Cache manager dependency
        
    Returns:
        JSON response confirming cache clearing
    """
    try:
        # Clear employee-related cache keys
        patterns = [
            "employees:stats",
            "employees:*:violations:*",
            "employees:*:activity:*",
            "employees:search:*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await cache.clear_pattern(pattern)
            total_cleared += cleared
        
        logger.info(f"Cleared {total_cleared} employee cache entries")
        
        return JSONResponse(
            content=format_success_response(
                {"cleared_keys": total_cleared},
                f"Cleared {total_cleared} employee cache entries"
            ),
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error clearing employee cache: {e}")
        return JSONResponse(
            content=format_error_response(
                "Failed to clear employee cache",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Import time module for relative time calculation
import time
