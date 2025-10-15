"""
Response formatting utilities for the Frigate Dashboard Middleware.

This module provides utilities for formatting API responses,
constructing URLs, and handling data transformation.
"""

from typing import Any, Dict, List, Optional, Union
from .time import timestamp_to_iso, timestamp_to_readable, get_relative_time_string
from ..config import settings


def format_success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """
    Format a successful API response.
    
    Args:
        data: Response data
        message: Success message
        
    Returns:
        Formatted response dictionary
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": timestamp_to_iso(get_current_timestamp())
    }


def format_error_response(error: str, status_code: int = 400, 
                         details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format an error API response.
    
    Args:
        error: Error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Formatted error response dictionary
    """
    response = {
        "success": False,
        "error": error,
        "status_code": status_code,
        "timestamp": timestamp_to_iso(get_current_timestamp())
    }
    
    if details:
        response["details"] = details
        
    return response


def construct_video_url(recording_id: str) -> str:
    """
    Construct video URL for a recording.
    
    Args:
        recording_id: Recording ID
        
    Returns:
        Full video URL
    """
    return f"{settings.video_api_base_url}/clip/{recording_id}"


def construct_thumbnail_url(recording_id: str) -> str:
    """
    Construct thumbnail URL for a recording.
    
    Args:
        recording_id: Recording ID
        
    Returns:
        Full thumbnail URL
    """
    return f"{settings.video_api_base_url}/thumb/{recording_id}"


def construct_snapshot_url(camera: str, timestamp: Union[float, int], 
                          event_id: str) -> str:
    """
    Construct snapshot URL for an event.
    
    Args:
        camera: Camera name
        timestamp: Event timestamp
        event_id: Event ID
        
    Returns:
        Full snapshot URL
    """
    return f"{settings.video_api_base_url}/snapshot/{camera}/{timestamp}-{event_id}"


def construct_face_url(person_name: str, filename: str) -> str:
    """
    Construct face recognition image URL.
    
    Args:
        person_name: Person's name
        filename: Image filename
        
    Returns:
        Full face image URL
    """
    import urllib.parse
    encoded_name = urllib.parse.quote(person_name)
    return f"{settings.video_api_base_url}/face/{encoded_name}/{filename}"


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
        "zones": violation.get("zones", []),
        "thumbnail_url": violation.get("thumbnail_url"),
        "video_url": violation.get("video_url"),
        "snapshot_url": violation.get("snapshot_url")
    }


def format_employee_stats(employee_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format employee statistics data.
    
    Args:
        employee_data: Raw employee data from database
        
    Returns:
        Formatted employee statistics
    """
    detections = employee_data.get("detections", 0)
    
    # Determine activity level
    if detections >= settings.high_activity_threshold:
        activity_level = "high"
    elif detections >= settings.medium_activity_threshold:
        activity_level = "medium"
    else:
        activity_level = "low"
    
    return {
        "employee_name": employee_data.get("employee_name"),
        "detections": detections,
        "cameras_visited": employee_data.get("cameras_visited", 0),
        "last_seen": employee_data.get("last_seen"),
        "last_seen_iso": timestamp_to_iso(employee_data.get("last_seen")) if employee_data.get("last_seen") else None,
        "last_seen_readable": timestamp_to_readable(employee_data.get("last_seen")) if employee_data.get("last_seen") else None,
        "last_seen_relative": get_relative_time_string(employee_data.get("last_seen")) if employee_data.get("last_seen") else None,
        "activity_level": activity_level,
        "violations_count": employee_data.get("violations_count", 0)
    }


def format_camera_summary(camera_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format camera summary data.
    
    Args:
        camera_data: Raw camera data from database
        
    Returns:
        Formatted camera summary
    """
    return {
        "camera": camera_data.get("camera"),
        "active_people": camera_data.get("active_people", 0),
        "total_detections": camera_data.get("total_detections", 0),
        "phone_violations": camera_data.get("phone_violations", 0),
        "recording_status": camera_data.get("recording_status", "unknown"),
        "last_activity": camera_data.get("last_activity"),
        "last_activity_iso": timestamp_to_iso(camera_data.get("last_activity")) if camera_data.get("last_activity") else None,
        "last_activity_relative": get_relative_time_string(camera_data.get("last_activity")) if camera_data.get("last_activity") else None
    }


def format_camera_activity_data(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format camera activity data.
    
    Args:
        activity_data: Raw activity data from database
        
    Returns:
        Formatted camera activity data
    """
    return {
        "camera": activity_data.get("camera"),
        "timestamp": activity_data.get("timestamp"),
        "timestamp_iso": timestamp_to_iso(activity_data.get("timestamp")) if activity_data.get("timestamp") else None,
        "timestamp_relative": get_relative_time_string(activity_data.get("timestamp")) if activity_data.get("timestamp") else None,
        "event_type": activity_data.get("event_type"),
        "label": activity_data.get("label"),
        "zones": activity_data.get("zones", []),
        "employee_name": activity_data.get("employee_name"),
        "snapshot_url": construct_snapshot_url(
            activity_data.get("camera", ""),
            activity_data.get("timestamp", 0),
            activity_data.get("event_id", "")
        ) if activity_data.get("event_id") else None
    }


def format_hourly_trend_data(trend_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format hourly trend data.
    
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


def format_dashboard_overview(overview_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format dashboard overview data.
    
    Args:
        overview_data: Raw overview data from database
        
    Returns:
        Formatted dashboard overview
    """
    return {
        "total_violations_today": overview_data.get("total_violations_today", 0),
        "top_violators": overview_data.get("top_violators", []),
        "active_cameras": overview_data.get("active_cameras", []),
        "recent_events": overview_data.get("recent_events", []),
        "last_updated": timestamp_to_iso(get_current_timestamp()),
        "last_updated_relative": "just now"
    }


def sanitize_employee_name(name: Optional[str]) -> str:
    """
    Sanitize employee name for safe display.
    
    Args:
        name: Raw employee name
        
    Returns:
        Sanitized employee name
    """
    if not name or name.strip() == "":
        return "Unknown"
    
    # Remove any potentially harmful characters
    sanitized = name.strip()
    if len(sanitized) > 50:  # Limit length
        sanitized = sanitized[:50] + "..."
    
    return sanitized


def format_activity_level(detections: int) -> str:
    """
    Determine activity level based on detection count.
    
    Args:
        detections: Number of detections
        
    Returns:
        Activity level string
    """
    if detections >= settings.high_activity_threshold:
        return "high"
    elif detections >= settings.medium_activity_threshold:
        return "medium"
    else:
        return "low"


def paginate_results(results: List[Any], page: int = 1, 
                    per_page: int = 50) -> Dict[str, Any]:
    """
    Paginate a list of results.
    
    Args:
        results: List of results to paginate
        page: Page number (1-based)
        per_page: Items per page
        
    Returns:
        Paginated results with metadata
    """
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_results = results[start:end]
    
    return {
        "items": paginated_results,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
            "has_next": end < total,
            "has_prev": page > 1
        }
    }


# Import get_current_timestamp at the end to avoid circular imports
from .time import get_current_timestamp
