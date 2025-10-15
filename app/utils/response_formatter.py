"""
Response formatting utilities following FastAPI best practices.

This module provides utilities for formatting API responses following the RORO pattern
and consistent error handling patterns.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi import status

from .time import timestamp_to_readable, timestamp_to_iso, get_relative_time_string
from .errors import ErrorResponse, create_error_response, BaseAPIError
from ..config import settings

logger = logging.getLogger(__name__)


def get_current_timestamp() -> float:
    """Get current timestamp as float."""
    return datetime.now().timestamp()


def format_success_response(
    data: Any, 
    message: str = "Success",
    status_code: int = status.HTTP_200_OK
) -> Dict[str, Any]:
    """
    Format a successful API response following RORO pattern.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        
    Returns:
        Formatted response dictionary
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": timestamp_to_iso(get_current_timestamp())
    }


def format_error_response(
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format an error API response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Formatted error response dictionary
    """
    return {
        "success": False,
        "error": message,
        "message": message,
        "details": details or {},
        "timestamp": timestamp_to_iso(get_current_timestamp())
    }


def create_json_response(
    data: Any,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    Create a JSONResponse with proper formatting.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        
    Returns:
        JSONResponse object
    """
    response_data = format_success_response(data, message)
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def create_error_json_response(
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create an error JSONResponse with proper formatting.
    
    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        JSONResponse object
    """
    response_data = format_error_response(message, status_code, details)
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def format_violation_data(violation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format violation data for API response.
    
    Args:
        violation: Raw violation data from database
        
    Returns:
        Formatted violation data
    """
    return {
        "id": violation.get("id"),
        "timestamp": violation.get("timestamp"),
        "timestamp_iso": timestamp_to_iso(violation.get("timestamp")),
        "timestamp_readable": timestamp_to_readable(violation.get("timestamp")),
        "relative_time": get_relative_time_string(violation.get("timestamp")),
        "camera": violation.get("camera"),
        "employee_name": violation.get("employee_name", "Unknown"),
        "confidence": violation.get("confidence", 0.0),
        "zones": violation.get("zones"),
        "thumbnail_url": violation.get("thumbnail_url"),
        "video_url": violation.get("video_url"),
        "snapshot_url": violation.get("snapshot_url")
    }


def format_hourly_trend_data(trend_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format hourly trend data for API response.
    
    Args:
        trend_data: Raw trend data from database
        
    Returns:
        Formatted trend data
    """
    # Convert Decimal types to appropriate types for JSON serialization
    def convert_decimals(obj):
        if isinstance(obj, dict):
            return {k: convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_decimals(item) for item in obj]
        elif hasattr(obj, 'as_tuple'):  # Decimal type
            return float(obj)
        else:
            return obj
    
    formatted = []
    for hour_data in trend_data:
        # Convert all Decimal values in the hour_data
        converted_hour_data = convert_decimals(hour_data)
        
        formatted.append({
            "hour": converted_hour_data.get("hour"),
            "hour_readable": timestamp_to_readable(converted_hour_data.get("hour"), format_str="%H:00"),
            "violations": converted_hour_data.get("violations", 0),
            "cameras": converted_hour_data.get("cameras", []),
            "employees": converted_hour_data.get("employees", [])
        })
    return formatted


def format_employee_data(employee: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format employee data for API response.
    
    Args:
        employee: Raw employee data from database
        
    Returns:
        Formatted employee data
    """
    return {
        "employee_name": employee.get("employee_name"),
        "detections": employee.get("detections", 0),
        "cameras_visited": employee.get("cameras_visited", 0),
        "last_seen": employee.get("last_seen"),
        "last_seen_iso": timestamp_to_iso(employee.get("last_seen")),
        "last_seen_readable": timestamp_to_readable(employee.get("last_seen")),
        "last_seen_relative": get_relative_time_string(employee.get("last_seen")),
        "activity_level": employee.get("activity_level", "low"),
        "violations_count": employee.get("violations_count", 0)
    }


def format_camera_data(camera: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format camera data for API response.
    
    Args:
        camera: Raw camera data from database
        
    Returns:
        Formatted camera data
    """
    return {
        "camera_name": camera.get("camera_name"),
        "violations_count": camera.get("violations_count", 0),
        "last_activity": camera.get("last_activity"),
        "last_activity_iso": timestamp_to_iso(camera.get("last_activity")),
        "last_activity_readable": timestamp_to_readable(camera.get("last_activity")),
        "last_activity_relative": get_relative_time_string(camera.get("last_activity")),
        "status": camera.get("status", "unknown"),
        "is_active": camera.get("is_active", False)
    }


def format_camera_activity_data(activity_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format camera activity data for API response.
    
    Args:
        activity_data: Raw activity data from database
        
    Returns:
        Formatted activity data
    """
    formatted = []
    for activity in activity_data:
        formatted.append({
            "timestamp": activity.get("timestamp"),
            "timestamp_iso": timestamp_to_iso(activity.get("timestamp")),
            "timestamp_readable": timestamp_to_readable(activity.get("timestamp")),
            "relative_time": get_relative_time_string(activity.get("timestamp")),
            "camera": activity.get("camera"),
            "event_type": activity.get("event_type"),
            "employee_name": activity.get("employee_name", "Unknown"),
            "confidence": activity.get("confidence", 0.0),
            "zones": activity.get("zones"),
            "thumbnail_url": activity.get("thumbnail_url"),
            "video_url": activity.get("video_url"),
            "snapshot_url": activity.get("snapshot_url")
        })
    return formatted


def construct_video_url(source_id: str) -> str:
    """
    Construct video URL for a given source ID.
    
    Args:
        source_id: Source ID for the video
        
    Returns:
        Complete video URL
    """
    return f"{settings.video_api_base_url}/clip/{source_id}"


def construct_thumbnail_url(source_id: str) -> str:
    """
    Construct thumbnail URL for a given source ID.
    
    Args:
        source_id: Source ID for the thumbnail
        
    Returns:
        Complete thumbnail URL
    """
    return f"{settings.video_api_base_url}/thumb/{source_id}"


def construct_snapshot_url(camera: str, timestamp: float, source_id: str) -> str:
    """
    Construct snapshot URL for a given camera, timestamp, and source ID.
    
    Args:
        camera: Camera name
        timestamp: Event timestamp
        source_id: Source ID for the snapshot
        
    Returns:
        Complete snapshot URL
    """
    return f"{settings.video_api_base_url}/snapshot/{camera}/{timestamp}-{source_id}"


def validate_and_format_response_data(
    data: Any,
    data_type: str,
    message: str = "Success"
) -> Dict[str, Any]:
    """
    Validate and format response data with proper error handling.
    
    Args:
        data: Response data to validate and format
        data_type: Type of data being formatted
        message: Success message
        
    Returns:
        Formatted response data
        
    Raises:
        ValidationError: If data validation fails
    """
    if data is None:
        raise ValueError(f"No {data_type} data available")
    
    if isinstance(data, list) and len(data) == 0:
        logger.warning(f"Empty {data_type} list returned")
    
    return format_success_response(data, message)


def handle_api_error(error: Exception, operation: str) -> JSONResponse:
    """
    Handle API errors with proper logging and response formatting.
    
    Args:
        error: Exception that occurred
        operation: Operation that failed
        
    Returns:
        JSONResponse with error details
    """
    logger.error(f"Error during {operation}: {str(error)}", exc_info=True)
    
    if isinstance(error, BaseAPIError):
        return create_error_json_response(
            message=error.message,
            status_code=error.status_code,
            details=error.details
        )
    
    return create_error_json_response(
        message=f"Internal server error during {operation}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"operation": operation, "error_type": type(error).__name__}
    )
