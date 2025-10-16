"""
Zone-related API endpoints for Frigate Dashboard Middleware.

This module provides zone occupancy and activity analytics APIs including:
- Real-time zone occupancy
- Activity heatmaps
- Zone statistics
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

router = APIRouter(prefix="/api/zones", tags=["zones"])


# Pydantic models for request/response
class ZoneOccupancy(BaseModel):
    """Zone occupancy response model."""
    zone: str = Field(..., description="Zone name")
    employee: Optional[str] = Field(None, description="Current occupant")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp (ISO)")
    duration: Optional[str] = Field(None, description="Duration in zone")
    status: str = Field(..., description="Status: occupied, vacant")
    camera: Optional[str] = Field(None, description="Camera name")


class HourlyActivity(BaseModel):
    """Hourly activity data model."""
    hour: int = Field(..., description="Hour (0-23)")
    detections: int = Field(..., description="Number of detections")
    unique_employees: int = Field(..., description="Number of unique employees")
    activity_level: str = Field(..., description="Activity level: high, medium, low")


class ZoneActivity(BaseModel):
    """Zone activity data model."""
    zone: str = Field(..., description="Zone name")
    hourly_activity: List[HourlyActivity] = Field(..., description="Hourly activity data")
    total_detections: int = Field(..., description="Total detections")
    activity_level: str = Field(..., description="Overall activity level")


# Helper functions
def calculate_activity_level(detections_per_hour: int) -> str:
    """Calculate activity level based on detections per hour."""
    if detections_per_hour > 100:
        return "high"
    elif detections_per_hour >= 30:
        return "medium"
    else:
        return "low"


def calculate_duration_in_zone(start_timestamp: float, end_timestamp: float) -> str:
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

@router.get("/occupancy", response_model=Dict[str, Any])
async def get_zone_occupancy(
    minutes_threshold: int = Query(5, description="Minutes threshold for recent activity"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get real-time zone occupancy status.
    
    Returns current occupants for each zone based on recent detections.
    Shows employee, last seen time, duration in zone, and status.
    """
    try:
        # Check cache first
        cache_key = f"zone_occupancy:{minutes_threshold}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Zone occupancy (last {minutes_threshold} minutes)"
            )
        
        # Calculate threshold timestamp
        threshold_timestamp = datetime.now().timestamp() - (minutes_threshold * 60)
        
        # Query latest detections per zone
        query = """
        WITH latest_detections AS (
            SELECT 
                data->'zones' as zones,
                data->>'label' as employee_name,
                timestamp,
                camera,
                ROW_NUMBER() OVER (
                    PARTITION BY jsonb_array_elements_text(data->'zones') 
                    ORDER BY timestamp DESC
                ) as rn
            FROM timeline
            WHERE data->'zones' IS NOT NULL
            AND data->>'label' IS NOT NULL
            AND data->>'label' != 'cell phone'
            AND timestamp >= $1
        )
        SELECT 
            zone,
            employee_name,
            timestamp,
            camera
        FROM latest_detections,
        LATERAL jsonb_array_elements_text(zones) as zone
        WHERE rn = 1
        ORDER BY zone
        """
        
        results = await db.fetch_all(query, threshold_timestamp)
        
        # Process results into zone occupancy data
        zone_occupancy = {}
        
        for result in results:
            zone = result['zone']
            employee = result['employee_name']
            timestamp = result['timestamp']
            camera = result['camera']
            
            if zone not in zone_occupancy:
                zone_occupancy[zone] = {
                    "zone": zone,
                    "employee": employee,
                    "last_seen": timestamp_to_iso(timestamp),
                    "duration": "Unknown",  # Would need more complex query to calculate
                    "status": "occupied",
                    "camera": camera
                }
        
        # Get all zones and mark unoccupied ones
        all_zones_query = """
        SELECT DISTINCT jsonb_array_elements_text(data->'zones') as zone
        FROM timeline
        WHERE data->'zones' IS NOT NULL
        ORDER BY zone
        """
        
        all_zones = await db.fetch_all(all_zones_query)
        
        for zone_result in all_zones:
            zone = zone_result['zone']
            if zone not in zone_occupancy:
                zone_occupancy[zone] = {
                    "zone": zone,
                    "employee": None,
                    "last_seen": None,
                    "duration": None,
                    "status": "vacant",
                    "camera": None
                }
        
        # Convert to list and sort
        occupancy_list = list(zone_occupancy.values())
        occupancy_list.sort(key=lambda x: x['zone'])
        
        # Cache for 1 minute
        await cache.set(cache_key, {"zones": occupancy_list}, 60)
        
        return format_success_response(
            data={"zones": occupancy_list},
            message=f"Zone occupancy (last {minutes_threshold} minutes)"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting zone occupancy: {str(e)}",
            status_code=500
        )


@router.get("/activity-heatmap", response_model=Dict[str, Any])
async def get_zone_activity_heatmap(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    hours: int = Query(24, description="Number of hours to analyze"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get zone activity heatmap data.
    
    Groups timeline entries by zone and hour buckets.
    Calculates activity levels and detection counts.
    """
    try:
        # Parse date or use today
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.now().date()
        
        # Calculate time range
        start_timestamp = datetime.combine(target_date, datetime.min.time()).timestamp()
        end_timestamp = start_timestamp + (hours * 3600)
        
        # Check cache
        cache_key = f"zone_heatmap:{date or 'today'}:{hours}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Zone activity heatmap for {target_date.strftime('%Y-%m-%d')}"
            )
        
        # Query hourly activity per zone
        query = """
        WITH zone_hourly_activity AS (
            SELECT 
                jsonb_array_elements_text(data->'zones') as zone,
                EXTRACT(HOUR FROM to_timestamp(timestamp)) as hour,
                COUNT(*) as detections,
                COUNT(DISTINCT data->>'label') as unique_employees
            FROM timeline
            WHERE data->'zones' IS NOT NULL
            AND data->>'label' IS NOT NULL
            AND data->>'label' != 'cell phone'
            AND timestamp >= $1
            AND timestamp <= $2
            GROUP BY zone, hour
        )
        SELECT 
            zone,
            hour,
            detections,
            unique_employees
        FROM zone_hourly_activity
        ORDER BY zone, hour
        """
        
        results = await db.fetch_all(query, start_timestamp, end_timestamp)
        
        # Process results into zone activity data
        zone_activities = {}
        
        for result in results:
            zone = result['zone']
            hour = int(result['hour'])
            detections = result['detections']
            unique_employees = result['unique_employees']
            
            if zone not in zone_activities:
                zone_activities[zone] = {
                    "zone": zone,
                    "hourly_activity": [],
                    "total_detections": 0,
                    "activity_level": "low"
                }
            
            # Add hourly activity
            activity_level = calculate_activity_level(detections)
            zone_activities[zone]["hourly_activity"].append({
                "hour": hour,
                "detections": detections,
                "unique_employees": unique_employees,
                "activity_level": activity_level
            })
            
            zone_activities[zone]["total_detections"] += detections
        
        # Calculate overall activity levels and fill missing hours
        for zone, data in zone_activities.items():
            # Fill missing hours with zero activity
            existing_hours = {activity["hour"] for activity in data["hourly_activity"]}
            for hour in range(24):
                if hour not in existing_hours:
                    data["hourly_activity"].append({
                        "hour": hour,
                        "detections": 0,
                        "unique_employees": 0,
                        "activity_level": "low"
                    })
            
            # Sort by hour
            data["hourly_activity"].sort(key=lambda x: x["hour"])
            
            # Calculate overall activity level
            avg_detections_per_hour = data["total_detections"] / 24
            data["activity_level"] = calculate_activity_level(avg_detections_per_hour)
        
        # Convert to list and sort
        activity_list = list(zone_activities.values())
        activity_list.sort(key=lambda x: x["zone"])
        
        # Cache for 5 minutes
        await cache.set(cache_key, {"zones": activity_list}, 300)
        
        return format_success_response(
            data={"zones": activity_list},
            message=f"Zone activity heatmap for {target_date.strftime('%Y-%m-%d')}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting zone activity heatmap: {str(e)}",
            status_code=500
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_zone_stats(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get zone statistics and summary data.
    
    Returns:
    - Total zones
    - Most active zone
    - Least active zone
    - Average activity per zone
    - Zone utilization rates
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
        cache_key = f"zone_stats:{date or 'today'}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Zone statistics for {target_date.strftime('%Y-%m-%d')}"
            )
        
        # Query zone statistics
        query = """
        WITH zone_stats AS (
            SELECT 
                jsonb_array_elements_text(data->'zones') as zone,
                COUNT(*) as detections,
                COUNT(DISTINCT data->>'label') as unique_employees,
                MIN(timestamp) as first_detection,
                MAX(timestamp) as last_detection
            FROM timeline
            WHERE data->'zones' IS NOT NULL
            AND data->>'label' IS NOT NULL
            AND data->>'label' != 'cell phone'
            AND timestamp >= $1
            AND timestamp <= $2
            GROUP BY zone
        )
        SELECT 
            zone,
            detections,
            unique_employees,
            first_detection,
            last_detection,
            (last_detection - first_detection) as active_duration
        FROM zone_stats
        ORDER BY detections DESC
        """
        
        results = await db.fetch_all(query, start_timestamp, end_timestamp)
        
        if not results:
            return format_error_response(
                message=f"No zone data found for {target_date.strftime('%Y-%m-%d')}",
                status_code=404
            )
        
        # Calculate statistics
        total_zones = len(results)
        total_detections = sum(r['detections'] for r in results)
        total_employees = sum(r['unique_employees'] for r in results)
        
        # Most and least active zones
        most_active_zone = results[0] if results else None
        least_active_zone = results[-1] if results else None
        
        # Average activity
        avg_detections_per_zone = total_detections / total_zones if total_zones > 0 else 0
        avg_employees_per_zone = total_employees / total_zones if total_zones > 0 else 0
        
        # Zone utilization (zones with activity vs total zones)
        active_zones = len([r for r in results if r['detections'] > 0])
        utilization_rate = (active_zones / total_zones * 100) if total_zones > 0 else 0
        
        # Format response
        stats_data = {
            "summary": {
                "total_zones": total_zones,
                "active_zones": active_zones,
                "utilization_rate": round(utilization_rate, 2),
                "total_detections": total_detections,
                "total_employees": total_employees,
                "avg_detections_per_zone": round(avg_detections_per_zone, 2),
                "avg_employees_per_zone": round(avg_employees_per_zone, 2)
            },
            "most_active_zone": {
                "zone": most_active_zone['zone'],
                "detections": most_active_zone['detections'],
                "unique_employees": most_active_zone['unique_employees'],
                "activity_level": calculate_activity_level(most_active_zone['detections'] / 24)
            } if most_active_zone else None,
            "least_active_zone": {
                "zone": least_active_zone['zone'],
                "detections": least_active_zone['detections'],
                "unique_employees": least_active_zone['unique_employees'],
                "activity_level": calculate_activity_level(least_active_zone['detections'] / 24)
            } if least_active_zone else None,
            "zones": [
                {
                    "zone": r['zone'],
                    "detections": r['detections'],
                    "unique_employees": r['unique_employees'],
                    "first_detection": timestamp_to_iso(r['first_detection']),
                    "last_detection": timestamp_to_iso(r['last_detection']),
                    "active_duration": calculate_duration_in_zone(r['first_detection'], r['last_detection']),
                    "activity_level": calculate_activity_level(r['detections'] / 24)
                }
                for r in results
            ]
        }
        
        # Cache for 10 minutes
        await cache.set(cache_key, stats_data, 600)
        
        return format_success_response(
            data=stats_data,
            message=f"Zone statistics for {target_date.strftime('%Y-%m-%d')}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting zone statistics: {str(e)}",
            status_code=500
        )
