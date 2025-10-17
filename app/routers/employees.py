"""
Employee-related API endpoints for Frigate Dashboard Middleware.

This module provides comprehensive employee tracking and analytics APIs including:
- Current status and location
- Work hours and attendance
- Break tracking
- Activity timeline
- Zone movements
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import DatabaseManager, get_database
from app.cache import CacheManager, get_cache
from app.config import settings
from app.utils.response_formatter import format_success_response, format_error_response
from app.utils.time import timestamp_to_iso, calculate_time_duration

router = APIRouter(prefix="/api/employees", tags=["employees"])


# Pydantic models for request/response
class EmployeeCurrentStatus(BaseModel):
    """Employee current status response model."""
    employee_name: str = Field(..., description="Employee name")
    current_zone: Optional[str] = Field(None, description="Current zone/desk")
    camera: Optional[str] = Field(None, description="Camera name")
    status: str = Field(..., description="Status: active, on_break, left")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp (ISO)")
    time_since_detection: Optional[str] = Field(None, description="Time since last detection")
    confidence: Optional[float] = Field(None, description="Detection confidence")


class WorkHours(BaseModel):
    """Employee work hours response model."""
    employee_name: str = Field(..., description="Employee name")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    arrival: Optional[str] = Field(None, description="Arrival time (ISO)")
    departure: Optional[str] = Field(None, description="Departure time (ISO)")
    total_time: Optional[str] = Field(None, description="Total time in office")
    office_time: Optional[str] = Field(None, description="Office time (excluding breaks)")
    break_time: Optional[str] = Field(None, description="Total break time")
    breaks: List[Dict[str, Any]] = Field(default_factory=list, description="Break details")
    violations_count: int = Field(default=0, description="Number of phone violations")
    status: str = Field(..., description="Current status")


class BreakDetail(BaseModel):
    """Break detail model."""
    start_time: str = Field(..., description="Break start time (ISO)")
    end_time: str = Field(..., description="Break end time (ISO)")
    duration: str = Field(..., description="Break duration")
    location: Optional[str] = Field(None, description="Zone during break")
    snapshot_url: Optional[str] = Field(None, description="Snapshot URL if available")


class ActivityEvent(BaseModel):
    """Activity timeline event model."""
    time: str = Field(..., description="Event timestamp (ISO)")
    event_type: str = Field(..., description="Event type")
    zone: Optional[str] = Field(None, description="Zone name")
    camera: Optional[str] = Field(None, description="Camera name")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")


class ZoneMovement(BaseModel):
    """Zone movement model."""
    from_zone: Optional[str] = Field(None, description="Previous zone")
    to_zone: str = Field(..., description="Current zone")
    timestamp: str = Field(..., description="Movement timestamp (ISO)")
    duration: Optional[str] = Field(None, description="Duration in previous zone")


# Helper functions
def determine_employee_status(last_seen_timestamp: float) -> str:
    """Determine employee status based on last seen timestamp."""
    if not last_seen_timestamp:
        return "left"
    
    now = datetime.now().timestamp()
    time_diff = now - last_seen_timestamp
    
    if time_diff < 300:  # < 5 minutes
        return "active"
    elif time_diff < 10800:  # < 3 hours
        return "on_break"
    else:
        return "left"


# Removed local calculate_time_duration function - using imported one from app.utils.time


# API Endpoints

@router.get("/{employee_name}/current-status", response_model=Dict[str, Any])
async def get_employee_current_status(
    employee_name: str,
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get current status and location of an employee.
    
    Returns:
    - Current zone/desk
    - Camera location
    - Status: active (<5 min), on_break (<3 hrs), left (>3 hrs)
    - Last seen timestamp
    - Time since last detection
    """
    try:
        # Check cache first
        cache_key = f"employee_status:{employee_name}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Current status for {employee_name}"
            )
        
        # Query latest detection for employee
        query = """
        SELECT 
            timestamp,
            camera,
            data->>'zones' as zones,
            (data->'sub_label'->>1)::float as confidence
        FROM timeline
        WHERE data->>'label' = 'person'
        AND data->'sub_label'->>0 = $1::text
        ORDER BY timestamp DESC
        LIMIT 1
        """
        
        result = await db.fetch_one(query, employee_name)
        
        if not result:
            return format_error_response(
                message=f"Employee '{employee_name}' not found",
                status_code=404
            )
        
        # Determine status
        last_seen_timestamp = result['timestamp']
        status = determine_employee_status(last_seen_timestamp)
        
        # Get current zone (most recent zone from zones array)
        zones = result.get('zones', [])
        current_zone = zones[0] if zones else None
        
        # Format response
        response_data = EmployeeCurrentStatus(
            employee_name=employee_name,
            current_zone=current_zone,
            camera=result.get('camera'),
            status=status,
            last_seen=timestamp_to_iso(last_seen_timestamp) if last_seen_timestamp else None,
            time_since_detection=f"{int((datetime.now().timestamp() - last_seen_timestamp) / 60)} minutes ago" if last_seen_timestamp else None,
            confidence=float(result.get('confidence', 0)) if result.get('confidence') else None
        )
        
        # Cache for 1 minute
        await cache.set(cache_key, response_data.dict(), 60)
        
        return format_success_response(
            data=response_data.dict(),
            message=f"Current status for {employee_name}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting employee status: {str(e)}",
            status_code=500
        )


@router.get("/{employee_name}/work-hours", response_model=Dict[str, Any])
async def get_employee_work_hours(
    employee_name: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get work hours and attendance details for an employee on a specific date.
    
    Calculates:
    - Arrival time (first detection)
    - Departure time (last detection)
    - Total time in office
    - Office time (excluding breaks)
    - Break time and details
    - Violations count
    """
    try:
        # Parse date or use today
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return format_error_response(
                    message="Invalid date format. Use YYYY-MM-DD",
                    status_code=400
                )
        else:
            target_date = datetime.now().date()
        
        # Get start and end timestamps for the day
        start_timestamp = datetime.combine(target_date, datetime.min.time()).timestamp()
        end_timestamp = datetime.combine(target_date, datetime.max.time()).timestamp()
        
        # Check cache
        cache_key = f"work_hours:{employee_name}:{date or 'today'}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Work hours for {employee_name} on {target_date.strftime('%Y-%m-%d')}"
            )
        
        # Get all detections for employee on the date
        query = """
        SELECT 
            timestamp,
            camera,
            data->>'zones' as zones,
            (data->'sub_label'->>1)::float as confidence
        FROM timeline
        WHERE data->>'label' = 'person'
        AND data->'sub_label'->>0 = $1::text
        AND timestamp >= $2
        AND timestamp <= $3
        ORDER BY timestamp ASC
        """
        
        detections = await db.fetch_all(query, employee_name, start_timestamp, end_timestamp)
        
        if not detections:
            return format_error_response(
                message=f"No data found for {employee_name} on {target_date.strftime('%Y-%m-%d')}",
                status_code=404
            )
        
        # Calculate work hours
        arrival_time = detections[0]['timestamp']
        departure_time = detections[-1]['timestamp']
        total_time_seconds = int(departure_time - arrival_time)
        total_time = calculate_time_duration(duration_seconds=total_time_seconds)
        
        # Detect breaks (gaps between detections >5min and <3hrs)
        breaks = []
        break_time_seconds = 0
        
        for i in range(len(detections) - 1):
            current_time = detections[i]['timestamp']
            next_time = detections[i + 1]['timestamp']
            gap = int(next_time - current_time)
            
            # Break if gap is between 5 minutes and 3 hours
            # Also skip breaks that start within 5 minutes of arrival (likely detection noise)
            time_since_arrival = current_time - arrival_time
            if 300 <= gap <= 10800 and time_since_arrival >= 300:  # 5min to 3hrs, and at least 5min after arrival
                break_start = timestamp_to_iso(current_time)
                break_end = timestamp_to_iso(next_time)
                break_duration = calculate_time_duration(duration_seconds=gap)
                
                breaks.append({
                    "start_time": break_start,
                    "end_time": break_end,
                    "duration": break_duration,
                    "duration_seconds": gap,
                    "location": detections[i].get('zones', [None])[0] if detections[i].get('zones') else None
                })
                
                break_time_seconds += gap
        
        # Calculate office time (total time minus breaks)
        office_time_seconds = total_time_seconds - break_time_seconds
        office_time = calculate_time_duration(duration_seconds=office_time_seconds)
        break_time = calculate_time_duration(duration_seconds=break_time_seconds)
        
        # Count violations (cell phone detections)
        violations_query = """
        SELECT COUNT(*) as violation_count
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND data->'zones' ? $1::text
        AND timestamp >= $2
        AND timestamp <= $3
        """
        
        # Get employee's zones for violation counting
        employee_zones = set()
        for detection in detections:
            if detection.get('zones'):
                employee_zones.update(detection['zones'])
        
        violations_count = 0
        for zone in employee_zones:
            result = await db.fetch_one(violations_query, zone, start_timestamp, end_timestamp)
            violations_count += result['violation_count'] if result else 0
        
        # Determine current status
        current_status = determine_employee_status(departure_time)
        
        # Format response
        response_data = WorkHours(
            employee_name=employee_name,
            date=target_date.strftime('%Y-%m-%d'),
            arrival=timestamp_to_iso(arrival_time),
            departure=timestamp_to_iso(departure_time),
            total_time=total_time,
            office_time=office_time,
            break_time=break_time,
            breaks=breaks,
            violations_count=violations_count,
            status=current_status
        )
        
        # Cache for 5 minutes
        await cache.set(cache_key, response_data.dict(), 300)
        
        return format_success_response(
            data=response_data.dict(),
            message=f"Work hours for {employee_name} on {target_date.strftime('%Y-%m-%d')}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting work hours: {str(e)}",
            status_code=500
        )


@router.get("/{employee_name}/breaks", response_model=Dict[str, Any])
async def get_employee_breaks(
    employee_name: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    include_snapshots: bool = Query(False, description="Include snapshot URLs for break periods"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get detailed break information for an employee.
    
    Finds gaps in detections between 5min and 3hrs.
    Returns break details with timestamps, durations, and locations.
    """
    try:
        # Determine date range
        if date:
            start_dt = datetime.strptime(date, "%Y-%m-%d")
            end_dt = start_dt + timedelta(days=1)
        elif start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        else:
            start_dt = datetime.now().date()
            end_dt = start_dt + timedelta(days=1)
        
        start_timestamp = start_dt.timestamp()
        end_timestamp = end_dt.timestamp()
        
        # Check cache
        cache_key = f"breaks:{employee_name}:{date or start_date or 'today'}:{include_snapshots}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Break details for {employee_name}"
            )
        
        # Get all detections for employee in date range
        query = """
        SELECT 
            timestamp,
            camera,
            data->>'zones' as zones,
            data->>'label' as label,
            source_id
        FROM timeline
        WHERE data->>'sub_label' = $1
        AND timestamp >= $2
        AND timestamp <= $3
        ORDER BY timestamp ASC
        """
        
        detections = await db.fetch_all(query, employee_name, start_timestamp, end_timestamp)
        
        if not detections:
            return format_error_response(
                message=f"No data found for {employee_name} in specified date range",
                status_code=404
            )
        
        # Detect breaks
        breaks = []
        
        for i in range(len(detections) - 1):
            current_time = detections[i]['timestamp']
            next_time = detections[i + 1]['timestamp']
            gap = next_time - current_time
            
            if 300 < gap < 10800:  # 5 minutes to 3 hours
                break_start = timestamp_to_iso(current_time)
                break_end = timestamp_to_iso(next_time)
                break_duration = calculate_time_duration(start_time=current_time, end_time=next_time)
                
                # Get zone during break (zone before break)
                break_zone = None
                if detections[i].get('zones'):
                    try:
                        zones = json.loads(detections[i]['zones'])
                        if zones and len(zones) > 0:
                            break_zone = zones[0]
                    except:
                        break_zone = detections[i]['zones']
                
                # Generate media URLs if requested
                snapshot_url = None
                thumbnail_url = None
                video_url = None
                
                if include_snapshots and detections[i].get('camera'):
                    camera = detections[i]['camera']
                    source_id = detections[i].get('source_id', f"{int(current_time)}-{employee_name.replace(' ', '_')[:6]}")
                    
                    # Generate snapshot URL
                    snapshot_url = f"{settings.video_api_base_url}/snapshot/{camera}/{source_id}"
                    
                    # Generate thumbnail URL
                    thumbnail_url = f"{settings.video_api_base_url}/thumb/{source_id}"
                    
                    # Generate video URL (for break period)
                    video_url = f"{settings.video_api_base_url}/clip/{source_id}"
                
                break_data = {
                    "start_time": break_start,
                    "end_time": break_end,
                    "duration": break_duration,
                    "duration_seconds": int(gap),
                    "location": break_zone,
                    "camera": detections[i].get('camera'),
                    "snapshot_url": snapshot_url,
                    "thumbnail_url": thumbnail_url,
                    "video_url": video_url
                }
                
                breaks.append(break_data)
        
        # Cache for 5 minutes
        await cache.set(cache_key, {"breaks": breaks}, 300)
        
        return format_success_response(
            data={"breaks": breaks},
            message=f"Break details for {employee_name}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting break details: {str(e)}",
            status_code=500
        )


@router.get("/{employee_name}/timeline", response_model=Dict[str, Any])
async def get_employee_timeline(
    employee_name: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: int = Query(100, description="Maximum number of events to return"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get chronological activity timeline for an employee.
    
    Returns enriched events with:
    - Arrival/departure events
    - Zone changes
    - Break events
    - Violation events
    """
    try:
        # Parse date or use today
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.now().date()
        
        start_timestamp = datetime.combine(target_date, datetime.min.time()).timestamp()
        end_timestamp = datetime.combine(target_date, datetime.max.time()).timestamp()
        
        # Check cache
        cache_key = f"timeline:{employee_name}:{date or 'today'}:{limit}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Activity timeline for {employee_name}"
            )
        
        # Get all timeline entries for employee
        query = """
        SELECT 
            timestamp,
            camera,
            source,
            source_id,
            class_type,
            data->>'zones' as zones,
            data->>'confidence' as confidence,
            data->>'label' as label
        FROM timeline
        WHERE data->>'label' = $1
        AND timestamp >= $2
        AND timestamp <= $3
        ORDER BY timestamp ASC
        LIMIT $4
        """
        
        entries = await db.fetch_all(query, employee_name, start_timestamp, end_timestamp, limit)
        
        if not entries:
            return format_error_response(
                message=f"No activity found for {employee_name} on {target_date.strftime('%Y-%m-%d')}",
                status_code=404
            )
        
        # Process entries into timeline events
        timeline_events = []
        previous_zone = None
        
        for i, entry in enumerate(entries):
            current_zone = entry.get('zones', [None])[0] if entry.get('zones') else None
            event_type = "detection"
            additional_data = {}
            
            # Determine event type
            if i == 0:
                event_type = "arrival"
            elif i == len(entries) - 1:
                event_type = "departure"
            elif current_zone != previous_zone:
                event_type = "zone_change"
                additional_data = {
                    "from_zone": previous_zone,
                    "to_zone": current_zone
                }
            
            # Check for break (gap > 5 minutes)
            if i < len(entries) - 1:
                next_entry = entries[i + 1]
                gap = next_entry['timestamp'] - entry['timestamp']
                if gap > 300:  # 5 minutes
                    additional_data["break_duration"] = calculate_time_duration(start_time=entry['timestamp'], end_time=next_entry['timestamp'])
            
            timeline_events.append(ActivityEvent(
                time=timestamp_to_iso(entry['timestamp']),
                event_type=event_type,
                zone=current_zone,
                camera=entry.get('camera'),
                additional_data=additional_data if additional_data else None
            ).dict())
            
            previous_zone = current_zone
        
        # Cache for 2 minutes
        await cache.set(cache_key, {"timeline": timeline_events}, 120)
        
        return format_success_response(
            data={"timeline": timeline_events},
            message=f"Activity timeline for {employee_name}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting activity timeline: {str(e)}",
            status_code=500
        )


@router.get("/{employee_name}/movements", response_model=Dict[str, Any])
async def get_employee_movements(
    employee_name: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Track zone movements and transitions for an employee.
    
    Returns:
    - Zone transitions throughout the day
    - Duration in each zone
    - Zones visited
    - Total movements count
    """
    try:
        # Parse date or use today
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.now().date()
        
        start_timestamp = datetime.combine(target_date, datetime.min.time()).timestamp()
        end_timestamp = datetime.combine(target_date, datetime.max.time()).timestamp()
        
        # Check cache
        cache_key = f"movements:{employee_name}:{date or 'today'}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Zone movements for {employee_name}"
            )
        
        # Get all detections with zones
        query = """
        SELECT 
            timestamp,
            data->>'zones' as zones
        FROM timeline
        WHERE data->>'label' = $1
        AND timestamp >= $2
        AND timestamp <= $3
        AND data->>'zones' IS NOT NULL
        ORDER BY timestamp ASC
        """
        
        entries = await db.fetch_all(query, employee_name, start_timestamp, end_timestamp)
        
        if not entries:
            return format_error_response(
                message=f"No zone data found for {employee_name} on {target_date.strftime('%Y-%m-%d')}",
                status_code=404
            )
        
        # Process movements
        movements = []
        zones_visited = set()
        previous_zone = None
        previous_timestamp = None
        
        for entry in entries:
            current_zone = entry.get('zones', [None])[0] if entry.get('zones') else None
            current_timestamp = entry['timestamp']
            
            if current_zone:
                zones_visited.add(current_zone)
                
                if previous_zone and previous_zone != current_zone:
                    # Zone change detected
                    duration = calculate_time_duration(start_time=previous_timestamp, end_time=current_timestamp)
                    
                    movements.append(ZoneMovement(
                        from_zone=previous_zone,
                        to_zone=current_zone,
                        timestamp=timestamp_to_iso(current_timestamp),
                        duration=duration
                    ).dict())
                
                previous_zone = current_zone
                previous_timestamp = current_timestamp
        
        # Cache for 5 minutes
        await cache.set(cache_key, {
            "movements": movements,
            "zones_visited": list(zones_visited),
            "total_movements": len(movements)
        }, 300)
        
        return format_success_response(
            data={
                "movements": movements,
                "zones_visited": list(zones_visited),
                "total_movements": len(movements)
            },
            message=f"Zone movements for {employee_name}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting zone movements: {str(e)}",
            status_code=500
        )


# New Pydantic models for idle time and timeline segments
class IdlePeriod(BaseModel):
    """Idle period model."""
    start_time: str = Field(..., description="Start time (HH:MM:SS)")
    end_time: str = Field(..., description="End time (HH:MM:SS)")
    duration_seconds: int = Field(..., description="Duration in seconds")
    duration_formatted: str = Field(..., description="Duration formatted (HH:MM:SS)")
    last_zone: Optional[str] = Field(None, description="Last zone before idle period")


class IdleTimeResponse(BaseModel):
    """Idle time response model."""
    employee: str = Field(..., description="Employee name")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    total_idle_seconds: int = Field(..., description="Total idle time in seconds")
    total_idle_formatted: str = Field(..., description="Total idle time formatted")
    idle_periods: List[IdlePeriod] = Field(..., description="List of idle periods")


class TimelineSegment(BaseModel):
    """Timeline segment model."""
    type: str = Field(..., description="Segment type: work, break, phone, idle")
    start_time: str = Field(..., description="Start time (HH:MM:SS)")
    end_time: str = Field(..., description="End time (HH:MM:SS)")
    duration_seconds: int = Field(..., description="Duration in seconds")
    start_percentage: float = Field(..., description="Start position percentage")
    width_percentage: float = Field(..., description="Width percentage")
    color: str = Field(..., description="Suggested color code")


class TimelineSegmentsResponse(BaseModel):
    """Timeline segments response model."""
    employee: str = Field(..., description="Employee name")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    office_start: str = Field(..., description="Office start time")
    office_end: str = Field(..., description="Office end time")
    total_duration: str = Field(..., description="Total duration")
    segments: List[TimelineSegment] = Field(..., description="Timeline segments")


@router.get("/{employee_name}/idle-time", response_model=Dict[str, Any])
async def get_employee_idle_time(
    employee_name: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    start_date: Optional[str] = Query(None, description="Start date for date range"),
    end_date: Optional[str] = Query(None, description="End date for date range"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
) -> Dict[str, Any]:
    """
    Calculate and return idle time periods for an employee.
    
    Idle time is defined as periods when the employee is at their desk but no activity
    is detected (gaps between 2-5 minutes during office hours).
    """
    try:
        # Parse dates
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        elif date:
            try:
                target_date = datetime.strptime(date, '%Y-%m-%d').date()
                start_dt = target_date
                end_dt = target_date
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = datetime.now().date()
            start_dt = target_date
            end_dt = target_date
        
        # Cache key
        cache_key = f"idle_time:{employee_name}:{start_dt.strftime('%Y-%m-%d')}:{end_dt.strftime('%Y-%m-%d')}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return format_success_response(
                data=cached_data,
                message=f"Idle time for {employee_name}"
            )
        
        # Calculate date range
        start_timestamp = datetime.combine(start_dt, datetime.min.time()).timestamp()
        end_timestamp = datetime.combine(end_dt, datetime.max.time()).timestamp()
        
        # Get all detections for the employee in the date range
        detections_query = """
            SELECT 
                timestamp,
                camera,
                data->>'zones' as zones,
                data->>'label' as label
            FROM timeline 
            WHERE timestamp >= $1 AND timestamp <= $2
            AND data->>'sub_label' = $3
            ORDER BY timestamp
        """
        
        detections = await db.fetch_all(detections_query, start_timestamp, end_timestamp, employee_name)
        
        if not detections:
            return format_success_response(
                data={
                    "employee": employee_name,
                    "date": start_dt.strftime('%Y-%m-%d') if start_dt == end_dt else f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
                    "total_idle_seconds": 0,
                    "total_idle_formatted": "0:00",
                    "idle_periods": []
                },
                message=f"No data found for {employee_name}"
            )
        
        # Calculate idle periods
        idle_periods = []
        total_idle_seconds = 0
        
        for i in range(len(detections) - 1):
            current_time = detections[i]['timestamp']
            next_time = detections[i + 1]['timestamp']
            gap_seconds = int(next_time - current_time)
            
            # Idle if gap is between 2-5 minutes
            if 120 <= gap_seconds < 300:  # 2min to 5min
                start_time = datetime.fromtimestamp(current_time).strftime('%H:%M:%S')
                end_time = datetime.fromtimestamp(next_time).strftime('%H:%M:%S')
                
                # Get last zone before idle period
                last_zone = None
                if detections[i]['zones']:
                    try:
                        zones = json.loads(detections[i]['zones'])
                        if zones and len(zones) > 0:
                            last_zone = zones[0]
                    except:
                        pass
                
                idle_period = IdlePeriod(
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=gap_seconds,
                    duration_formatted=calculate_time_duration(gap_seconds),
                    last_zone=last_zone
                )
                
                idle_periods.append(idle_period.dict())
                total_idle_seconds += gap_seconds
        
        # Format response
        response_data = {
            "employee": employee_name,
            "date": start_dt.strftime('%Y-%m-%d') if start_dt == end_dt else f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
            "total_idle_seconds": total_idle_seconds,
            "total_idle_formatted": calculate_time_duration(total_idle_seconds),
            "idle_periods": idle_periods
        }
        
        # Cache for 5 minutes
        await cache.set(cache_key, response_data, 300)
        
        return format_success_response(
            data=response_data,
            message=f"Idle time analysis for {employee_name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return format_error_response(
            message=f"Error getting idle time: {str(e)}",
            status_code=500
        )


@router.get("/{employee_name}/timeline-segments", response_model=Dict[str, Any])
async def get_employee_timeline_segments(
    employee_name: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
) -> Dict[str, Any]:
    """
    Return pre-calculated timeline visualization segments for UI rendering.
    
    Segments include work, break, phone, and idle periods with percentages
    for timeline visualization.
    """
    try:
        # Parse date
        if date:
            try:
                target_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = datetime.now().date()
        
        # Cache key
        cache_key = f"timeline_segments:{employee_name}:{target_date.strftime('%Y-%m-%d')}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return format_success_response(
                data=cached_data,
                message=f"Timeline segments for {employee_name}"
            )
        
        # Calculate date range
        start_timestamp = datetime.combine(target_date, datetime.min.time()).timestamp()
        end_timestamp = datetime.combine(target_date, datetime.max.time()).timestamp()
        
        # Get all detections for the employee
        detections_query = """
            SELECT 
                timestamp,
                camera,
                data->>'zones' as zones,
                data->>'label' as label
            FROM timeline 
            WHERE timestamp >= $1 AND timestamp <= $2
            AND data->>'sub_label' = $3
            ORDER BY timestamp
        """
        
        detections = await db.fetch_all(detections_query, start_timestamp, end_timestamp, employee_name)
        
        if not detections:
            return format_success_response(
                data={
                    "employee": employee_name,
                    "date": target_date.strftime('%Y-%m-%d'),
                    "office_start": "00:00:00",
                    "office_end": "00:00:00",
                    "total_duration": "0:00",
                    "segments": []
                },
                message=f"No data found for {employee_name}"
            )
        
        # Calculate office hours
        first_detection = detections[0]['timestamp']
        last_detection = detections[-1]['timestamp']
        total_duration_seconds = int(last_detection - first_detection)
        
        office_start = datetime.fromtimestamp(first_detection).strftime('%H:%M:%S')
        office_end = datetime.fromtimestamp(last_detection).strftime('%H:%M:%S')
        
        # Create segments
        segments = []
        current_time = first_detection
        
        # Color mapping for segment types
        color_map = {
            "work": "#10b981",      # Green
            "break": "#fbbf24",     # Yellow
            "phone": "#ef4444",     # Red
            "idle": "#6b7280"       # Gray
        }
        
        for i in range(len(detections) - 1):
            current_detection = detections[i]
            next_detection = detections[i + 1]
            
            current_timestamp = current_detection['timestamp']
            next_timestamp = next_detection['timestamp']
            gap_seconds = int(next_timestamp - current_timestamp)
            
            # Determine segment type based on gap and activity
            if current_detection['label'] == 'cell phone':
                segment_type = "phone"
            elif 300 <= gap_seconds <= 10800:  # 5min to 3hrs - break
                segment_type = "break"
            elif 120 <= gap_seconds < 300:  # 2min to 5min - idle
                segment_type = "idle"
            else:  # Normal activity
                segment_type = "work"
            
            # Calculate segment position and width
            segment_start_percentage = ((current_timestamp - first_detection) / total_duration_seconds) * 100
            segment_width_percentage = (gap_seconds / total_duration_seconds) * 100
            
            segment = TimelineSegment(
                type=segment_type,
                start_time=datetime.fromtimestamp(current_timestamp).strftime('%H:%M:%S'),
                end_time=datetime.fromtimestamp(next_timestamp).strftime('%H:%M:%S'),
                duration_seconds=gap_seconds,
                start_percentage=round(segment_start_percentage, 2),
                width_percentage=round(segment_width_percentage, 2),
                color=color_map[segment_type]
            )
            
            segments.append(segment.dict())
        
        # Format response
        response_data = {
            "employee": employee_name,
            "date": target_date.strftime('%Y-%m-%d'),
            "office_start": office_start,
            "office_end": office_end,
            "total_duration": calculate_time_duration(total_duration_seconds),
            "segments": segments
        }
        
        # Cache for 5 minutes
        await cache.set(cache_key, response_data, 300)
        
        return format_success_response(
            data=response_data,
            message=f"Timeline segments for {employee_name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return format_error_response(
            message=f"Error getting timeline segments: {str(e)}",
            status_code=500
        )