"""
Employee-related API endpoints for Frigate Dashboard Middleware.

This module provides comprehensive employee tracking and analytics APIs including:
- Current status and location
- Work hours and attendance
- Break tracking
- Activity timeline
- Zone movements
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import DatabaseManager, get_database
from app.cache import CacheManager, get_cache
from app.config import settings
from app.utils.response_formatter import format_success_response, format_error_response
from app.utils.time import timestamp_to_iso

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


def calculate_time_duration(start_timestamp: float, end_timestamp: float) -> str:
    """Calculate duration between two timestamps."""
    if not start_timestamp or not end_timestamp:
        return "0 minutes"
    
    duration_seconds = int(end_timestamp - start_timestamp)
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


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
            data->>'confidence' as confidence
        FROM timeline
        WHERE data->>'label' = $1
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
            data->>'confidence' as confidence
        FROM timeline
        WHERE data->>'label' = $1
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
        total_time = calculate_time_duration(arrival_time, departure_time)
        
        # Detect breaks (gaps between detections >5min and <3hrs)
        breaks = []
        break_time_seconds = 0
        
        for i in range(len(detections) - 1):
            current_time = detections[i]['timestamp']
            next_time = detections[i + 1]['timestamp']
            gap = next_time - current_time
            
            if 300 < gap < 10800:  # 5 minutes to 3 hours
                break_start = timestamp_to_iso(current_time)
                break_end = timestamp_to_iso(next_time)
                break_duration = calculate_time_duration(current_time, next_time)
                
                breaks.append({
                    "start_time": break_start,
                    "end_time": break_end,
                    "duration": break_duration,
                    "location": detections[i].get('zones', [None])[0] if detections[i].get('zones') else None
                })
                
                break_time_seconds += gap
        
        # Calculate office time (total time minus breaks)
        office_time_seconds = (departure_time - arrival_time) - break_time_seconds
        office_time = calculate_time_duration(0, office_time_seconds)
        break_time = calculate_time_duration(0, break_time_seconds)
        
        # Count violations (cell phone detections)
        violations_query = """
        SELECT COUNT(*) as violation_count
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND data->>'zones' ? $1
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
        cache_key = f"breaks:{employee_name}:{date or start_date or 'today'}"
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
            data->>'zones' as zones
        FROM timeline
        WHERE data->>'label' = $1
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
                break_duration = calculate_time_duration(current_time, next_time)
                
                # Get zone during break (zone before break)
                break_zone = None
                if detections[i].get('zones'):
                    break_zone = detections[i]['zones'][0]
                
                # Generate snapshot URL if available
                snapshot_url = None
                if detections[i].get('camera'):
                    snapshot_url = f"{settings.video_api_base_url}/snapshot/{detections[i]['camera']}/{int(current_time)}-{employee_name.replace(' ', '_')}"
                
                breaks.append(BreakDetail(
                    start_time=break_start,
                    end_time=break_end,
                    duration=break_duration,
                    location=break_zone,
                    snapshot_url=snapshot_url
                ).dict())
        
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
                    additional_data["break_duration"] = calculate_time_duration(entry['timestamp'], next_entry['timestamp'])
            
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
                    duration = calculate_time_duration(previous_timestamp, current_timestamp)
                    
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