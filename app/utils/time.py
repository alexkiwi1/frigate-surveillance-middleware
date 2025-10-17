"""
Time utilities for handling Unix timestamps and timezone conversions.

This module provides utilities for converting between Unix timestamps
and human-readable formats, with proper timezone handling.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import pytz


def get_current_timestamp() -> float:
    """Get current Unix timestamp as float."""
    return time.time()


def get_timestamp_ago(hours: int) -> float:
    """Get Unix timestamp from N hours ago."""
    return get_current_timestamp() - (hours * 3600)


def get_today_start_timestamp() -> float:
    """Get Unix timestamp for start of today (00:00:00)."""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start.timestamp()


def timestamp_to_datetime(timestamp: Union[float, int, None], 
                         timezone_name: str = "Asia/Karachi") -> Optional[datetime]:
    """
    Convert Unix timestamp to datetime with timezone.
    
    Args:
        timestamp: Unix timestamp (float or int) or None
        timezone_name: Target timezone (default: Asia/Karachi)
        
    Returns:
        datetime object in specified timezone or None
    """
    if timestamp is None:
        return None
    
    # Convert Decimal to float if needed
    if hasattr(timestamp, 'as_tuple'):  # Decimal type
        timestamp = float(timestamp)
    
    tz = pytz.timezone(timezone_name)
    dt = datetime.fromtimestamp(timestamp, tz=tz)
    return dt


def datetime_to_timestamp(dt: datetime) -> float:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: datetime object
        
    Returns:
        Unix timestamp as float
    """
    return dt.timestamp()


def timestamp_to_iso(timestamp: Union[float, int, None], 
                    timezone_name: str = "Asia/Karachi") -> Optional[str]:
    """
    Convert Unix timestamp to ISO format string.
    
    Args:
        timestamp: Unix timestamp or None
        timezone_name: Target timezone
        
    Returns:
        ISO format string or None
    """
    dt = timestamp_to_datetime(timestamp, timezone_name)
    return dt.isoformat() if dt is not None else None


def timestamp_to_readable(timestamp: Union[float, int, None], 
                         timezone_name: str = "Asia/Karachi",
                         format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
    """
    Convert Unix timestamp to readable string format.
    
    Args:
        timestamp: Unix timestamp or None
        timezone_name: Target timezone
        format_str: strftime format string
        
    Returns:
        Formatted string or None
    """
    dt = timestamp_to_datetime(timestamp, timezone_name)
    return dt.strftime(format_str) if dt is not None else None


def get_hour_buckets(hours: int = 24) -> list[tuple[float, float]]:
    """
    Get list of hour bucket tuples (start, end) for the last N hours.
    
    Args:
        hours: Number of hours to go back
        
    Returns:
        List of (start_timestamp, end_timestamp) tuples
    """
    buckets = []
    now = get_current_timestamp()
    
    for i in range(hours):
        end_time = now - (i * 3600)
        start_time = end_time - 3600
        buckets.append((start_time, end_time))
    
    return buckets


def is_within_time_window(timestamp: Union[float, int], 
                         window_start: Union[float, int],
                         window_duration: int) -> bool:
    """
    Check if timestamp is within a time window.
    
    Args:
        timestamp: Timestamp to check
        window_start: Start of time window
        window_duration: Duration of window in seconds
        
    Returns:
        True if timestamp is within window
    """
    window_end = window_start + window_duration
    return window_start <= timestamp <= window_end


def get_time_range_string(start_time: Union[float, int], 
                         end_time: Union[float, int],
                         timezone_name: str = "Asia/Karachi") -> str:
    """
    Get human-readable time range string.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        timezone_name: Timezone for display
        
    Returns:
        Formatted time range string
    """
    start_str = timestamp_to_readable(start_time, timezone_name, "%H:%M")
    end_str = timestamp_to_readable(end_time, timezone_name, "%H:%M")
    return f"{start_str} - {end_str}"


def get_relative_time_string(timestamp: Union[float, int, None]) -> Optional[str]:
    """
    Get relative time string (e.g., "2 hours ago", "5 minutes ago").
    
    Args:
        timestamp: Unix timestamp or None
        
    Returns:
        Relative time string or None
    """
    if timestamp is None:
        return None
    
    now = get_current_timestamp()
    diff = now - timestamp
    
    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(diff / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def calculate_time_duration(start_time: Union[float, int, None] = None, 
                          end_time: Union[float, int, None] = None,
                          duration_seconds: Union[int, None] = None) -> str:
    """
    Calculate duration and return formatted string.
    
    Args:
        start_time: Start timestamp (if calculating from two timestamps)
        end_time: End timestamp (if calculating from two timestamps)
        duration_seconds: Duration in seconds (if providing directly)
        
    Returns:
        Formatted duration string (e.g., "2:30:45", "1:15", "0:05")
    """
    if duration_seconds is not None:
        total_seconds = int(duration_seconds)
    elif start_time is not None and end_time is not None:
        total_seconds = int(end_time - start_time)
    else:
        return "0:00"
    
    if total_seconds < 0:
        return "0:00"
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


# Time constants for easy reference
SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400
SECONDS_IN_WEEK = 604800



