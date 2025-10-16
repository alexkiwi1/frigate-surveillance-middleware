"""
Camera endpoints for the Frigate Dashboard Middleware.

This module provides REST API endpoints for retrieving camera summaries,
activity feeds, and related camera data with caching.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import DatabaseManager
from ..cache import CacheManager
from ..dependencies import DatabaseDep, CacheDep, CameraDep, LimitDep, HoursDep
from ..models import (
    CameraSummaryResponse,
    CameraActivityResponse,
    CameraSummary,
    CameraActivityData
)
from ..utils.response_formatter import create_json_response, create_error_json_response
from ..services.queries import CameraQueries
from ..utils.formatting import format_camera_summary, format_camera_activity_data, paginate_results
from ..config import CacheKeys, settings
from ..utils.errors import ValidationError, NotFoundError, DatabaseError, CacheError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get(
    "/summary",
    response_model=CameraSummaryResponse,
    summary="Get live camera summaries",
    description="Retrieve live summaries for all cameras including active people, detections, and recording status"
)
async def get_camera_summary(
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> dict:
    """
    Get live summaries for all cameras.
    
    This endpoint returns live summaries for all cameras including:
    - Number of active people detected
    - Total detections in current hour
    - Phone violations in current hour
    - Recording status
    - Last activity timestamp
    
    Args:
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with camera summaries
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        # Generate cache key
        cache_key = "cameras:summary:all"
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for camera summary: {cache_key}")
            return create_json_response(data=cached_data, message="Camera summaries retrieved from cache")
        
        # Query database for all cameras
        logger.info("Fetching camera summaries for all cameras")
        camera_summaries = []
        
        for camera in CAMERAS:
            try:
                summary_data = await CameraQueries.get_camera_summary(db=db, camera=camera)
                if summary_data:
                    formatted_summary = format_camera_summary(summary_data)
                    camera_summaries.append(formatted_summary)
            except Exception as e:
                logger.warning(f"Failed to get summary for camera {camera}: {e}")
                # Add empty summary for failed camera
                camera_summaries.append({
                    "camera": camera,
                    "active_people": 0,
                    "total_detections": 0,
                    "phone_violations": 0,
                    "recording_status": "error",
                    "last_activity": None,
                    "last_activity_iso": None,
                    "last_activity_relative": None
                })
        
        # Cache the results
        await cache.set(cache_key, camera_summaries, settings.cache_ttl_camera_summary)
        logger.debug(f"Cached camera summaries: {cache_key}")
        
        return create_json_response(data=camera_summaries, message="Camera summaries retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error retrieving camera summaries: {e}")
        return JSONResponse(
            content=create_error_json_response(message="Failed to retrieve camera summaries", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/{camera_name}/summary",
    response_model=CameraSummaryResponse,
    summary="Get camera summary",
    description="Retrieve live summary for a specific camera"
)
async def get_single_camera_summary(
    camera_name: str,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> dict:
    """
    Get live summary for a specific camera.
    
    This endpoint returns a live summary for the specified camera including:
    - Number of active people detected
    - Total detections in current hour
    - Phone violations in current hour
    - Recording status
    - Last activity timestamp
    
    Args:
        camera_name: Name of the camera
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with camera summary
        
    Raises:
        HTTPException: If database query fails or camera not found
    """
    try:
        # Generate cache key
        cache_key = CacheKeys.camera_summary(camera_name)
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for camera summary: {cache_key}")
            return create_json_response(data=[cached_data], message="Camera summary retrieved from cache")
        
        # Query database
        logger.info(f"Fetching summary for camera: {camera_name}")
        summary_data = await CameraQueries.get_camera_summary(
            db=db,
            camera=camera_name
        )
        
        if not summary_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera {camera_name} not found or no data available"
            )
        
        # Format the data
        formatted_summary = format_camera_summary(summary_data)
        
        # Cache the results
        await cache.set(cache_key, formatted_summary, settings.cache_ttl_camera_summary)
        logger.debug(f"Cached camera summary: {cache_key}")
        
        return create_json_response(data=[formatted_summary], message=f"Camera summary for {camera_name} retrieved successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving summary for camera {camera_name}: {e}")
        return JSONResponse(
            content=create_error_json_response(message=f"Failed to retrieve summary for camera {camera_name}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/{camera_name}/activity",
    response_model=CameraActivityResponse,
    summary="Get camera activity",
    description="Retrieve detailed activity feed for a specific camera"
)
async def get_camera_activity(
    camera_name: str,
    hours: int = HoursDep,
    limit: int = LimitDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> dict:
    """
    Get detailed activity feed for a specific camera.
    
    This endpoint returns detailed activity data for the specified camera including:
    - Recent detections and events
    - Employee identifications
    - Zone information
    - Confidence scores
    - Snapshot URLs
    
    Args:
        camera_name: Name of the camera
        hours: Hours to look back (1-168, default 24)
        limit: Maximum number of results (1-1000)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with camera activity data
        
    Raises:
        HTTPException: If database query fails or camera not found
    """
    try:
        # Generate cache key
        cache_key = CacheKeys.camera_activity(camera_name, hours)
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for camera activity: {cache_key}")
            return create_json_response(data=cached_data, message="Camera activity retrieved from cache")
        
        # Query database
        logger.info(f"Fetching activity for camera {camera_name}: hours={hours}, limit={limit}")
        raw_activity = await CameraQueries.get_camera_activity(
            db=db,
            camera=camera_name,
            hours=hours,
            limit=limit
        )
        
        # Format the data
        formatted_activity = [format_camera_activity_data(activity) for activity in raw_activity]
        
        # Add pagination info if needed
        pagination_info = None
        if len(formatted_activity) >= limit:
            # Get total count for pagination
            count_query = """
            SELECT COUNT(*) as total
            FROM timeline
            WHERE camera = $1
            AND timestamp > (EXTRACT(EPOCH FROM NOW()) - $2)
            AND data->>'label' IN ('person', 'cell phone', 'face')
            """
            count_result = await db.fetch_one(count_query, camera_name, hours * 3600)
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
            "activities": formatted_activity,
            "camera": camera_name,
            "time_period_hours": hours,
            "pagination": pagination_info
        }
        
        # Cache the results
        await cache.set(cache_key, response_data, settings.cache_ttl_camera_activity)
        logger.debug(f"Cached camera activity: {cache_key}")
        
        return create_json_response(data=response_data, message=f"Activity for camera {camera_name} retrieved successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving activity for camera {camera_name}: {e}")
        return JSONResponse(
            content=create_error_json_response(message=f"Failed to retrieve activity for camera {camera_name}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/{camera_name}/violations",
    summary="Get camera violations",
    description="Get phone violations for a specific camera"
)
async def get_camera_violations(
    camera_name: str,
    hours: int = HoursDep,
    limit: int = LimitDep,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> dict:
    """
    Get phone violations for a specific camera.
    
    This endpoint returns phone violations detected by the specified camera
    with employee identification and media URLs.
    
    Args:
        camera_name: Name of the camera
        hours: Hours to look back (1-168, default 24)
        limit: Maximum number of results (1-1000)
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with camera violations
    """
    try:
        # Generate cache key
        cache_key = f"cameras:{camera_name}:violations:{hours}:{limit}"
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for camera violations: {cache_key}")
            return create_json_response(data=cached_data, message="Camera violations retrieved from cache")
        
        # Query database for violations
        logger.info(f"Fetching violations for camera {camera_name}: hours={hours}, limit={limit}")
        
        from ..services.queries import ViolationQueries
        raw_violations = await ViolationQueries.get_live_violations(
            db=db,
            camera=camera_name,
            hours=hours,
            limit=limit
        )
        
        # Format the data
        from ..utils.formatting import format_violation_data
        formatted_violations = [format_violation_data(violation) for violation in raw_violations]
        
        # Prepare response data
        response_data = {
            "violations": formatted_violations,
            "camera": camera_name,
            "time_period_hours": hours,
            "total_violations": len(formatted_violations)
        }
        
        # Cache the results
        await cache.set(cache_key, response_data, settings.cache_ttl_camera_activity)
        logger.debug(f"Cached camera violations: {cache_key}")
        
        return create_json_response(data=response_data, message=f"Violations for camera {camera_name} retrieved successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving violations for camera {camera_name}: {e}")
        return JSONResponse(
            content=create_error_json_response(message=f"Failed to retrieve violations for camera {camera_name}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/{camera_name}/status",
    summary="Get camera status",
    description="Get detailed status information for a specific camera"
)
async def get_camera_status(
    camera_name: str,
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> dict:
    """
    Get detailed status information for a specific camera.
    
    This endpoint returns comprehensive status information including:
    - Recording status and health
    - Recent activity metrics
    - Connection status
    - Performance metrics
    
    Args:
        camera_name: Name of the camera
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with camera status
    """
    try:
        # Generate cache key
        cache_key = f"cameras:{camera_name}:status"
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for camera status: {cache_key}")
            return create_json_response(data=cached_data, message="Camera status retrieved from cache")
        
        # Query database for status information
        logger.info(f"Fetching status for camera: {camera_name}")
        
        # Get recording status
        recording_query = """
        SELECT 
            COUNT(*) as recording_count,
            MAX(start_time) as last_recording,
            MIN(start_time) as first_recording
        FROM recordings
        WHERE camera = $1
        AND start_time > (EXTRACT(EPOCH FROM NOW()) - 86400)
        """
        recording_data = await db.fetch_one(recording_query, camera_name)
        
        # Get recent activity
        activity_query = """
        SELECT 
            COUNT(*) as total_events,
            COUNT(*) FILTER (WHERE data->>'label' = 'person') as person_events,
            COUNT(*) FILTER (WHERE data->>'label' = 'cell phone') as phone_events,
            COUNT(*) FILTER (WHERE data->>'label' = 'face') as face_events,
            MAX(timestamp) as last_event
        FROM timeline
        WHERE camera = $1
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - 3600)
        """
        activity_data = await db.fetch_one(activity_query, camera_name)
        
        # Get zone information
        zone_query = """
        SELECT 
            data->'zones' as zones
        FROM timeline
        WHERE camera = $1
        AND data->'zones' IS NOT NULL
        AND timestamp > (EXTRACT(EPOCH FROM NOW()) - 3600)
        LIMIT 1
        """
        zone_data = await db.fetch_one(zone_query, camera_name)
        
        # Compile status information
        status_info = {
            "camera": camera_name,
            "recording": {
                "status": "active" if recording_data and recording_data.get('recording_count', 0) > 0 else "inactive",
                "count_24h": recording_data.get('recording_count', 0) if recording_data else 0,
                "last_recording": recording_data.get('last_recording') if recording_data else None,
                "first_recording": recording_data.get('first_recording') if recording_data else None
            },
            "activity": {
                "total_events_1h": activity_data.get('total_events', 0) if activity_data else 0,
                "person_events_1h": activity_data.get('person_events', 0) if activity_data else 0,
                "phone_events_1h": activity_data.get('phone_events', 0) if activity_data else 0,
                "face_events_1h": activity_data.get('face_events', 0) if activity_data else 0,
                "last_event": activity_data.get('last_event') if activity_data else None
            },
            "zones": zone_data.get('zones', []) if zone_data else [],
            "health": {
                "status": "healthy" if activity_data and activity_data.get('total_events', 0) > 0 else "inactive",
                "last_activity_ago": None  # Will be calculated by frontend
            }
        }
        
        # Cache the results
        await cache.set(cache_key, status_info, 60)  # 1 minute cache
        logger.debug(f"Cached camera status: {cache_key}")
        
        return create_json_response(data=status_info, message=f"Status for camera {camera_name} retrieved successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving status for camera {camera_name}: {e}")
        return JSONResponse(
            content=create_error_json_response(message=f"Failed to retrieve status for camera {camera_name}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/list",
    summary="List all cameras",
    description="Get list of all available cameras with basic information"
)
async def list_cameras(
    db: DatabaseManager = DatabaseDep,
    cache: CacheManager = CacheDep
) -> dict:
    """
    Get list of all available cameras.
    
    This endpoint returns a list of all cameras with basic information
    including their current status and last activity.
    
    Args:
        db: Database manager dependency
        cache: Cache manager dependency
        
    Returns:
        JSON response with camera list
    """
    try:
        # Generate cache key
        cache_key = "cameras:list"
        
        # Try to get from cache first
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for camera list: {cache_key}")
            return create_json_response(data=cached_data, message="Camera list retrieved from cache")
        
        # Query database for camera information
        logger.info("Fetching camera list")
        
        # Simple query to get all unique cameras from database
        query = """
            SELECT DISTINCT camera 
            FROM timeline 
            ORDER BY camera
        """
        
        result = await db.fetch_all(query)
        cameras = [row['camera'] for row in result]
        
        camera_list = []
        for camera in cameras:
            # Get basic info for each camera
            info_query = """
            SELECT 
                COUNT(*) as total_events,
                MAX(timestamp) as last_activity,
                COUNT(*) FILTER (WHERE data->>'label' = 'person') as person_count,
                COUNT(*) FILTER (WHERE data->>'label' = 'cell phone') as phone_count
            FROM timeline
            WHERE camera = $1
            AND timestamp > (EXTRACT(EPOCH FROM NOW()) - 86400)
            """
            camera_info = await db.fetch_one(info_query, camera)
            
            camera_data = {
                "name": camera,
                "total_events_24h": camera_info.get('total_events', 0) if camera_info else 0,
                "person_events_24h": camera_info.get('person_count', 0) if camera_info else 0,
                "phone_events_24h": camera_info.get('phone_count', 0) if camera_info else 0,
                "last_activity": camera_info.get('last_activity') if camera_info else None,
                "status": "active" if camera_info and camera_info.get('total_events', 0) > 0 else "inactive"
            }
            camera_list.append(camera_data)
        
        # Sort by activity
        camera_list.sort(key=lambda x: x['total_events_24h'], reverse=True)
        
        # Cache the results
        await cache.set(cache_key, camera_list, 300)  # 5 minute cache
        logger.debug(f"Cached camera list: {cache_key}")
        
        return JSONResponse(
            content=create_json_response(data=camera_list, message=f"Retrieved {len(camera_list)} cameras"),
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error retrieving camera list: {e}")
        return JSONResponse(
            content=create_error_json_response(message="Failed to retrieve camera list", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete(
    "/cache",
    summary="Clear camera cache",
    description="Clear all cached camera data"
)
async def clear_camera_cache(
    cache: CacheManager = CacheDep
) -> dict:
    """
    Clear all cached camera data.
    
    This endpoint clears all cached camera-related data, forcing fresh
    queries on the next request.
    
    Args:
        cache: Cache manager dependency
        
    Returns:
        JSON response confirming cache clearing
    """
    try:
        # Clear camera-related cache keys
        patterns = [
            "cameras:summary:*",
            "cameras:*:summary",
            "cameras:*:activity:*",
            "cameras:*:violations:*",
            "cameras:*:status",
            "cameras:list"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await cache.clear_pattern(pattern)
            total_cleared += cleared
        
        logger.info(f"Cleared {total_cleared} camera cache entries")
        
        return create_json_response(data=
                {"cleared_keys": total_cleared}, message=f"Cleared {total_cleared} camera cache entries"
            )
        
    except Exception as e:
        logger.error(f"Error clearing camera cache: {e}")
        return JSONResponse(
            content=create_error_json_response(message="Failed to clear camera cache", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"error": str(e)}
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
