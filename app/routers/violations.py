"""
Violation endpoints for the Frigate Dashboard Middleware.

This module provides REST API endpoints for retrieving phone violations,
hourly trends, and related violation data with caching.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..database import DatabaseManager
from ..cache import CacheManager, CacheUtils
from ..dependencies import DatabaseDep, CacheDep, CameraDep, LimitDep, HoursDep, get_database_manager, get_cache_manager
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
from ..utils.time import timestamp_to_iso
from ..config import settings
from ..utils.errors import (
    ValidationError,
    NotFoundError,
    DatabaseError,
    CacheError
)
from ..services.queries import ViolationQueries
from ..config import CacheKeys, settings
from ..utils.errors import ValidationError, NotFoundError, DatabaseError, CacheError

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
        camera: Optional camera name filter
        limit: Maximum number of results (1-1000)
        hours: Hours to look back (1-168)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with violation data
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        # Generate cache key
        cache_key = CacheKeys.live_violations(camera, limit)
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for live violations: {cache_key}")
            return create_json_response(
                data=cached_data,
                message="Live violations retrieved from cache"
            )
        
        # Query database
        logger.info(f"Fetching live violations: camera={camera}, limit={limit}, hours={hours}")
        raw_violations = await ViolationQueries.get_live_violations(
            db=db,
            camera=camera,
            hours=hours,
            limit=limit
        )
        
        # Format the data
        formatted_violations = [format_violation_data(violation) for violation in raw_violations]
        
        # Cache the results
        await cache.set(cache_key, formatted_violations, settings.cache_ttl_live_violations)
        logger.debug(f"Cached live violations: {cache_key}")
        
        return create_json_response(data=formatted_violations, message="Live violations retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error retrieving live violations: {e}")
        return create_error_json_response(
            "Failed to retrieve live violations",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": str(e)}
        )


@router.get(
    "/hourly-trend",
    response_model=HourlyTrendResponse,
    summary="Get hourly violation trends",
    description="Retrieve hourly violation trends with camera and employee breakdown"
)
async def get_hourly_trend(
    hours: int = HoursDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get hourly violation trends with camera and employee breakdown.
    
    This endpoint returns aggregated violation data by hour, showing:
    - Number of violations per hour
    - Which cameras had violations
    - Which employees had violations
    
    Args:
        hours: Hours to analyze (1-168, default 24)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with hourly trend data
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        # Generate cache key
        cache_key = CacheKeys.hourly_trend(hours)
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for hourly trend: {cache_key}")
            return create_json_response(data=cached_data, message="Hourly trend retrieved from cache")
        
        # Query database
        logger.info(f"Fetching hourly trend: hours={hours}")
        raw_trend_data = await ViolationQueries.get_hourly_trend(
            db=db,
            hours=hours
        )
        
        # Format the data
        formatted_trend = format_hourly_trend_data(raw_trend_data)
        
        # Cache the results
        await cache.set(cache_key, formatted_trend, settings.cache_ttl_hourly_trend)
        logger.debug(f"Cached hourly trend: {cache_key}")
        
        return create_json_response(data=formatted_trend, message="Hourly trend retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error retrieving hourly trend: {e}")
        return create_error_json_response(
            "Failed to retrieve hourly trend",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": str(e)}
        )


@router.get(
    "/stats",
    summary="Get violation statistics",
    description="Get summary statistics for violations"
)
async def get_violation_stats(
    hours: int = HoursDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Get summary statistics for violations.
    
    This endpoint returns aggregated statistics including:
    - Total violations in time period
    - Violations by camera
    - Violations by employee
    - Peak violation hours
    
    Args:
        hours: Hours to analyze (1-168, default 24)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with violation statistics
    """
    try:
        # Generate cache key
        cache_key = f"violations:stats:{hours}"
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for violation stats: {cache_key}")
            return create_json_response(data=cached_data, message="Violation stats retrieved from cache")
        
        # Query database for statistics
        logger.info(f"Fetching violation stats: hours={hours}")
        
        # Get total violations
        total_query = """
        SELECT COUNT(*) as total_violations
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - $1)
        """
        total_result = await db.fetch_one(total_query, hours * 3600)
        total_violations = total_result['total_violations'] if total_result else 0
        
        # Get violations by camera
        camera_query = """
        SELECT 
            camera,
            COUNT(*) as violations
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - $1)
        GROUP BY camera
        ORDER BY violations DESC
        """
        camera_stats = await db.fetch_all(camera_query, hours * 3600)
        
        # Get violations by employee
        employee_query = """
        WITH employee_violations AS (
            SELECT 
                COALESCE(nf.employee_name, 'Unknown') as employee_name,
                COUNT(*) as violations
            FROM timeline p
            LEFT JOIN (
                SELECT DISTINCT ON (p.timestamp, p.camera)
                    p.timestamp, 
                    p.camera,
                    f.data->>'sub_label' as employee_name
                FROM timeline p
                LEFT JOIN timeline f ON 
                    f.camera = p.camera 
                    AND f.source = 'face'
                    AND ABS(f.timestamp - p.timestamp) < 3
                WHERE p.data->>'label' = 'cell phone'
                AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - $1)
                ORDER BY p.timestamp, p.camera, ABS(f.timestamp - p.timestamp)
            ) nf USING (timestamp, camera)
            WHERE p.data->>'label' = 'cell phone'
            AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - $2)
            GROUP BY nf.employee_name
        )
        SELECT * FROM employee_violations
        ORDER BY violations DESC
        LIMIT 10
        """
        employee_stats = await db.fetch_all(employee_query, hours * 3600, hours * 3600)
        
        # Get peak hours
        peak_hours_query = """
        SELECT 
            EXTRACT(HOUR FROM to_timestamp(timestamp)) as hour,
            COUNT(*) as violations
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - $1)
        GROUP BY EXTRACT(HOUR FROM to_timestamp(timestamp))
        ORDER BY violations DESC
        LIMIT 5
        """
        peak_hours = await db.fetch_all(peak_hours_query, hours * 3600)
        
        # Convert Decimal types to float for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif hasattr(obj, 'as_tuple'):  # Decimal type
                return float(obj)
            else:
                return obj
        
        # Compile statistics
        stats = {
            "total_violations": int(total_violations),
            "time_period_hours": hours,
            "violations_by_camera": convert_decimals(camera_stats),
            "violations_by_employee": convert_decimals(employee_stats),
            "peak_hours": convert_decimals(peak_hours),
            "summary": {
                "most_active_camera": camera_stats[0]['camera'] if camera_stats else None,
                "most_violating_employee": employee_stats[0]['employee_name'] if employee_stats else None,
                "peak_hour": int(peak_hours[0]['hour']) if peak_hours else None
            }
        }
        
        # Cache the results
        await cache.set(cache_key, stats, settings.cache_ttl_hourly_trend)
        logger.debug(f"Cached violation stats: {cache_key}")
        
        return create_json_response(data=stats, message="Violation statistics retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error retrieving violation stats: {e}")
        return create_error_json_response(
            "Failed to retrieve violation statistics",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": str(e)}
        )


@router.delete(
    "/cache",
    summary="Clear violation cache",
    description="Clear all cached violation data"
)
async def clear_violation_cache(
    cache: CacheManager = CacheDep
) -> JSONResponse:
    """
    Clear all cached violation data.
    
    This endpoint clears all cached violation-related data, forcing fresh
    queries on the next request.
    
    Args:
        cache: Cache manager dependency
        
    Returns:
        JSON response confirming cache clearing
    """
    try:
        # Clear violation-related cache keys
        patterns = [
            "violations:live:*",
            "violations:hourly_trend:*",
            "violations:stats:*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await cache.clear_pattern(pattern)
            total_cleared += cleared
        
        logger.info(f"Cleared {total_cleared} violation cache entries")
        
        return create_json_response(data=
                {"cleared_keys": total_cleared}, message=f"Cleared {total_cleared} violation cache entries"
            )
        
    except Exception as e:
        logger.error(f"Error clearing violation cache: {e}")
        return create_error_json_response(
            "Failed to clear violation cache",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": str(e)}
        )


@router.get("/{violation_id}/duration", response_class=JSONResponse)
async def get_violation_duration(
    violation_id: str,
    db: DatabaseManager = Depends(get_database_manager),
    cache: CacheManager = Depends(get_cache_manager)
) -> JSONResponse:
    """
    Get detailed duration information for a specific violation.
    
    Analyzes consecutive cell phone detections within ±2 minute window
    to calculate actual violation duration and related data.
    
    Args:
        violation_id: The violation ID to analyze
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSONResponse with violation duration details including:
        - Start and end times
        - Duration in seconds
        - Detection count
        - Average confidence
        - Employee name
        - Desk zone
        - Media URLs
    """
    try:
        # Check cache first
        cache_key = f"violation_duration:{violation_id}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return create_json_response(
                data=cached_result,
                message=f"Violation duration for {violation_id}"
            )
        
        # Get violation details from reviewsegment
        violation_query = """
        SELECT 
            camera,
            start_time,
            end_time,
            thumb_path,
            data
        FROM reviewsegment
        WHERE id = $1
        """
        
        violation_result = await db.fetch_one(violation_query, violation_id)
        
        if not violation_result:
            return create_error_json_response(
                f"Violation {violation_id} not found",
                status.HTTP_404_NOT_FOUND
            )
        
        camera = violation_result['camera']
        violation_start = violation_result['start_time']
        violation_end = violation_result['end_time']
        
        # Get all cell phone detections in the same zone within ±2 minute window
        # First, get the zone from the violation data
        zones = violation_result.get('data', {}).get('zones', [])
        if not zones:
            return create_error_json_response(
                f"No zones found for violation {violation_id}",
                status.HTTP_404_NOT_FOUND
            )
        
        zone = zones[0]  # Use first zone
        
        # Query timeline for consecutive cell phone detections
        timeline_query = """
        SELECT 
            timestamp,
            data->>'confidence' as confidence,
            data->>'zones' as zones
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND data->'zones' ? $1
        AND timestamp >= $2
        AND timestamp <= $3
        ORDER BY timestamp ASC
        """
        
        # Expand search window by ±2 minutes
        search_start = violation_start - 120  # 2 minutes before
        search_end = violation_end + 120      # 2 minutes after
        
        detections = await db.fetch_all(timeline_query, zone, search_start, search_end)
        
        if not detections:
            return create_error_json_response(
                f"No cell phone detections found for violation {violation_id}",
                status.HTTP_404_NOT_FOUND
            )
        
        # Find employee name from face detections in same timeframe
        employee_query = """
        SELECT 
            data->>'label' as employee_name,
            data->>'confidence' as confidence
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND data->'zones' ? $1
        AND timestamp >= $2
        AND timestamp <= $3
        ORDER BY ABS(timestamp - $4) ASC
        LIMIT 1
        """
        
        employee_result = await db.fetch_one(
            employee_query, 
            zone, 
            search_start, 
            search_end, 
            violation_start
        )
        
        employee_name = employee_result['employee_name'] if employee_result else "Unknown"
        
        # Calculate duration and statistics
        detection_times = [d['timestamp'] for d in detections]
        actual_start = min(detection_times)
        actual_end = max(detection_times)
        duration_seconds = int(actual_end - actual_start)
        
        # Calculate average confidence
        confidences = [float(d['confidence']) for d in detections if d['confidence']]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Generate media URLs
        video_url = f"{settings.video_api_base_url}/clip/{violation_id}"
        thumbnail_url = f"{settings.video_api_base_url}/thumb/{violation_id}"
        snapshot_url = f"{settings.video_api_base_url}/snapshot/{camera}/{int(violation_start)}-{violation_id}"
        
        # Format response
        duration_data = {
            "violation_id": violation_id,
            "start_time": timestamp_to_iso(actual_start),
            "end_time": timestamp_to_iso(actual_end),
            "duration_seconds": duration_seconds,
            "duration_formatted": f"{duration_seconds // 60}m {duration_seconds % 60}s",
            "detection_count": len(detections),
            "avg_confidence": round(avg_confidence, 3),
            "employee_name": employee_name,
            "desk_zone": zone,
            "camera": camera,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "snapshot_url": snapshot_url,
            "detection_timeline": [
                {
                    "timestamp": timestamp_to_iso(d['timestamp']),
                    "confidence": float(d['confidence']) if d['confidence'] else 0.0
                }
                for d in detections
            ]
        }
        
        # Cache for 5 minutes
        await cache.set(cache_key, duration_data, 300)
        
        return create_json_response(
            data=duration_data,
            message=f"Violation duration for {violation_id}"
        )
        
    except Exception as e:
        logger.error(f"Error getting violation duration for {violation_id}: {e}")
        return create_error_json_response(
            f"Failed to get violation duration: {str(e)}",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"violation_id": violation_id, "error": str(e)}
        )
