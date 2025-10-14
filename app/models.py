"""
Pydantic models for the Frigate Dashboard Middleware.

This module defines all the response models, request models,
and data validation schemas used throughout the API.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


# Enums
class ActivityLevel(str, Enum):
    """Employee activity level enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SeverityLevel(str, Enum):
    """Violation severity level enumeration."""
    ALERT = "alert"
    DETECTION = "detection"
    SIGNIFICANT_MOTION = "significant_motion"


class RecordingStatus(str, Enum):
    """Camera recording status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNKNOWN = "unknown"


# Base Models
class BaseResponse(BaseModel):
    """Base response model with common fields."""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    timestamp: str = Field(..., description="Response timestamp in ISO format")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class PaginationInfo(BaseModel):
    """Pagination information model."""
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


# Violation Models
class ViolationData(BaseModel):
    """Individual violation data model."""
    id: str = Field(..., description="Violation ID")
    timestamp: float = Field(..., description="Unix timestamp of violation")
    timestamp_iso: str = Field(..., description="ISO format timestamp")
    timestamp_readable: str = Field(..., description="Human readable timestamp")
    relative_time: str = Field(..., description="Relative time string (e.g., '2 hours ago')")
    camera: str = Field(..., description="Camera name where violation occurred")
    employee_name: str = Field(..., description="Employee name or 'Unknown'")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    zones: List[str] = Field(default_factory=list, description="Zones where violation occurred")
    thumbnail_url: Optional[str] = Field(None, description="URL to violation thumbnail")
    video_url: Optional[str] = Field(None, description="URL to violation video")
    snapshot_url: Optional[str] = Field(None, description="URL to violation snapshot")


class LiveViolationsResponse(BaseResponse):
    """Response model for live violations endpoint."""
    data: List[ViolationData] = Field(..., description="List of recent violations")


class HourlyTrendData(BaseModel):
    """Hourly trend data model."""
    hour: float = Field(..., description="Hour timestamp")
    hour_readable: str = Field(..., description="Human readable hour (e.g., '14:00')")
    violations: int = Field(..., description="Number of violations in this hour")
    cameras: List[str] = Field(default_factory=list, description="Cameras with violations")
    employees: List[str] = Field(default_factory=list, description="Employees with violations")


class HourlyTrendResponse(BaseResponse):
    """Response model for hourly trend endpoint."""
    data: List[HourlyTrendData] = Field(..., description="Hourly violation trends")


# Employee Models
class EmployeeStats(BaseModel):
    """Employee statistics model."""
    employee_name: str = Field(..., description="Employee name")
    detections: int = Field(..., description="Total detections in time window")
    cameras_visited: int = Field(..., description="Number of cameras visited")
    last_seen: Optional[float] = Field(None, description="Last seen timestamp")
    last_seen_iso: Optional[str] = Field(None, description="Last seen in ISO format")
    last_seen_readable: Optional[str] = Field(None, description="Last seen in readable format")
    last_seen_relative: Optional[str] = Field(None, description="Last seen relative time")
    activity_level: ActivityLevel = Field(..., description="Activity level classification")
    violations_count: int = Field(..., description="Number of phone violations")


class EmployeeStatsResponse(BaseResponse):
    """Response model for employee statistics endpoint."""
    data: List[EmployeeStats] = Field(..., description="List of employee statistics")


class EmployeeViolationsResponse(BaseResponse):
    """Response model for employee violations endpoint."""
    data: List[ViolationData] = Field(..., description="List of violations for specific employee")
    pagination: Optional[PaginationInfo] = Field(None, description="Pagination information")


# Camera Models
class CameraSummary(BaseModel):
    """Camera summary data model."""
    camera: str = Field(..., description="Camera name")
    active_people: int = Field(..., description="Number of active people detected")
    total_detections: int = Field(..., description="Total detections in current hour")
    phone_violations: int = Field(..., description="Phone violations in current hour")
    recording_status: RecordingStatus = Field(..., description="Recording status")
    last_activity: Optional[float] = Field(None, description="Last activity timestamp")
    last_activity_iso: Optional[str] = Field(None, description="Last activity in ISO format")
    last_activity_relative: Optional[str] = Field(None, description="Last activity relative time")


class CameraSummaryResponse(BaseResponse):
    """Response model for camera summary endpoint."""
    data: List[CameraSummary] = Field(..., description="List of camera summaries")


class CameraActivityData(BaseModel):
    """Camera activity data model."""
    timestamp: float = Field(..., description="Activity timestamp")
    timestamp_iso: str = Field(..., description="ISO format timestamp")
    timestamp_readable: str = Field(..., description="Human readable timestamp")
    event_type: str = Field(..., description="Type of event (person, cell phone, etc.)")
    employee_name: Optional[str] = Field(None, description="Employee name if identified")
    zones: List[str] = Field(default_factory=list, description="Zones involved")
    confidence: Optional[float] = Field(None, description="Confidence score")
    snapshot_url: Optional[str] = Field(None, description="URL to event snapshot")


class CameraActivityResponse(BaseResponse):
    """Response model for camera activity endpoint."""
    data: List[CameraActivityData] = Field(..., description="List of camera activities")
    pagination: Optional[PaginationInfo] = Field(None, description="Pagination information")


# Dashboard Models
class TopViolator(BaseModel):
    """Top violator data model."""
    employee_name: str = Field(..., description="Employee name")
    violations_count: int = Field(..., description="Number of violations")
    last_violation: Optional[float] = Field(None, description="Last violation timestamp")
    last_violation_relative: Optional[str] = Field(None, description="Last violation relative time")


class ActiveCamera(BaseModel):
    """Active camera data model."""
    camera: str = Field(..., description="Camera name")
    active_people: int = Field(..., description="Number of active people")
    last_activity: Optional[float] = Field(None, description="Last activity timestamp")
    last_activity_relative: Optional[str] = Field(None, description="Last activity relative time")


class RecentEvent(BaseModel):
    """Recent event data model."""
    timestamp: float = Field(..., description="Event timestamp")
    timestamp_iso: str = Field(..., description="ISO format timestamp")
    timestamp_readable: str = Field(..., description="Human readable timestamp")
    camera: str = Field(..., description="Camera name")
    event_type: str = Field(..., description="Event type")
    employee_name: Optional[str] = Field(None, description="Employee name if identified")
    severity: str = Field(..., description="Event severity")


class DashboardOverview(BaseModel):
    """Dashboard overview data model."""
    total_violations_today: int = Field(..., description="Total violations today")
    top_violators: List[TopViolator] = Field(..., description="Top 5 violators")
    active_cameras: List[ActiveCamera] = Field(..., description="Currently active cameras")
    recent_events: List[RecentEvent] = Field(..., description="Recent events")
    last_updated: str = Field(..., description="Last updated timestamp")
    last_updated_relative: str = Field(..., description="Last updated relative time")


class DashboardOverviewResponse(BaseResponse):
    """Response model for dashboard overview endpoint."""
    data: DashboardOverview = Field(..., description="Dashboard overview data")


# WebSocket Models
class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: str = Field(..., description="Message timestamp")


class ViolationWebSocketMessage(WebSocketMessage):
    """WebSocket message for new violations."""
    type: str = Field(default="new_violation", description="Message type")
    data: ViolationData = Field(..., description="Violation data")


# Request Models
class ViolationFilters(BaseModel):
    """Request filters for violation endpoints."""
    camera: Optional[str] = Field(None, description="Filter by camera name")
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum number of results")
    hours: int = Field(default=24, ge=1, le=168, description="Hours to look back")


class EmployeeViolationFilters(BaseModel):
    """Request filters for employee violation endpoints."""
    start_time: Optional[float] = Field(None, description="Start timestamp filter")
    end_time: Optional[float] = Field(None, description="End timestamp filter")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")


class CameraActivityFilters(BaseModel):
    """Request filters for camera activity endpoints."""
    hours: int = Field(default=24, ge=1, le=168, description="Hours to look back")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")


# Health Check Models
class HealthStatus(BaseModel):
    """Health status model."""
    status: str = Field(..., description="Overall health status")
    database: bool = Field(..., description="Database connection status")
    redis: bool = Field(..., description="Redis connection status")
    timestamp: str = Field(..., description="Health check timestamp")


class HealthResponse(BaseResponse):
    """Response model for health check endpoint."""
    data: HealthStatus = Field(..., description="Health status information")


# Cache Models
class CacheStats(BaseModel):
    """Cache statistics model."""
    redis_info: Dict[str, Any] = Field(..., description="Redis server information")
    key_counts: Dict[str, int] = Field(..., description="Key counts by pattern")
    total_keys: int = Field(..., description="Total number of cached keys")


class CacheStatsResponse(BaseResponse):
    """Response model for cache statistics endpoint."""
    data: CacheStats = Field(..., description="Cache statistics")


# Validation Models
class TimestampRange(BaseModel):
    """Timestamp range validation model."""
    start_time: float = Field(..., description="Start timestamp")
    end_time: float = Field(..., description="End timestamp")
    
    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


# Utility Models
class APIInfo(BaseModel):
    """API information model."""
    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    endpoints: List[str] = Field(..., description="Available endpoints")


class APIInfoResponse(BaseResponse):
    """Response model for API info endpoint."""
    data: APIInfo = Field(..., description="API information")

