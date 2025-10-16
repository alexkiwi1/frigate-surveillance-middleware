"""
Attendance-related API endpoints for Frigate Dashboard Middleware.

This module provides daily attendance tracking and analytics APIs including:
- Daily attendance summary
- Employee attendance status
- Attendance statistics
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

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


# Pydantic models for request/response
class EmployeeAttendance(BaseModel):
    """Employee attendance model."""
    employee_name: str = Field(..., description="Employee name")
    arrival: Optional[str] = Field(None, description="Arrival time (ISO)")
    departure: Optional[str] = Field(None, description="Departure time (ISO)")
    status: str = Field(..., description="Current status: active, on_break, left")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp (ISO)")
    violations_count: int = Field(default=0, description="Number of phone violations")
    current_zone: Optional[str] = Field(None, description="Current zone/desk")


class DailyAttendanceSummary(BaseModel):
    """Daily attendance summary model."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    total_present: int = Field(..., description="Total employees present")
    currently_active: int = Field(..., description="Currently active employees")
    on_break: int = Field(..., description="Employees on break")
    left_early: int = Field(..., description="Employees who left early")
    total_violations: int = Field(..., description="Total phone violations")
    attendance_rate: float = Field(..., description="Attendance rate percentage")
    employees: List[EmployeeAttendance] = Field(..., description="Employee attendance details")


# Helper functions
def determine_attendance_status(last_seen_timestamp: float) -> str:
    """Determine attendance status based on last seen timestamp."""
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


def calculate_attendance_rate(present_employees: int, total_expected: int = 50) -> float:
    """Calculate attendance rate percentage."""
    if total_expected == 0:
        return 0.0
    return round((present_employees / total_expected) * 100, 2)


# API Endpoints

@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_attendance(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get daily attendance summary and employee status.
    
    Returns:
    - Total employees present
    - Currently active employees
    - Employees on break
    - Employees who left early
    - Total violations
    - Attendance rate
    - Individual employee details
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
        cache_key = f"daily_attendance:{date or 'today'}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Daily attendance for {target_date.strftime('%Y-%m-%d')}"
            )
        
        # Get all unique employees detected on the date
        employees_query = """
        SELECT DISTINCT data->>'label' as employee_name
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND timestamp >= $1
        AND timestamp <= $2
        ORDER BY employee_name
        """
        
        employees = await db.fetch_all(employees_query, start_timestamp, end_timestamp)
        
        if not employees:
            return format_error_response(
                message=f"No attendance data found for {target_date.strftime('%Y-%m-%d')}",
                status_code=404
            )
        
        # Get detailed attendance data for each employee
        employee_attendance = []
        total_violations = 0
        
        for employee in employees:
            employee_name = employee['employee_name']
            
            # Get employee's first and last detection
            employee_query = """
            SELECT 
                MIN(timestamp) as first_detection,
                MAX(timestamp) as last_detection,
                data->>'zones' as zones
            FROM timeline
            WHERE data->>'label' = $1
            AND timestamp >= $2
            AND timestamp <= $3
            GROUP BY data->>'zones'
            ORDER BY last_detection DESC
            LIMIT 1
            """
            
            employee_data = await db.fetch_one(employee_query, employee_name, start_timestamp, end_timestamp)
            
            if not employee_data:
                continue
            
            # Get current zone (most recent)
            current_zone = None
            if employee_data.get('zones'):
                zones = employee_data['zones']
                current_zone = zones[0] if zones else None
            
            # Count violations for this employee
            violations_query = """
            SELECT COUNT(*) as violation_count
            FROM timeline
            WHERE data->>'label' = 'cell phone'
            AND data->>'zones' ? $1
            AND timestamp >= $2
            AND timestamp <= $3
            """
            
            violations_count = 0
            if current_zone:
                violation_result = await db.fetch_one(violations_query, current_zone, start_timestamp, end_timestamp)
                violations_count = violation_result['violation_count'] if violation_result else 0
            
            total_violations += violations_count
            
            # Determine status
            last_seen = employee_data['last_detection']
            status = determine_attendance_status(last_seen)
            
            # Create employee attendance record
            employee_attendance.append(EmployeeAttendance(
                employee_name=employee_name,
                arrival=timestamp_to_iso(employee_data['first_detection']),
                departure=timestamp_to_iso(employee_data['last_detection']),
                status=status,
                last_seen=timestamp_to_iso(last_seen),
                violations_count=violations_count,
                current_zone=current_zone
            ).dict())
        
        # Calculate summary statistics
        total_present = len(employee_attendance)
        currently_active = len([e for e in employee_attendance if e['status'] == 'active'])
        on_break = len([e for e in employee_attendance if e['status'] == 'on_break'])
        left_early = len([e for e in employee_attendance if e['status'] == 'left'])
        
        # Calculate attendance rate (assuming 50 employees expected)
        attendance_rate = calculate_attendance_rate(total_present, 50)
        
        # Format response
        summary_data = DailyAttendanceSummary(
            date=target_date.strftime('%Y-%m-%d'),
            total_present=total_present,
            currently_active=currently_active,
            on_break=on_break,
            left_early=left_early,
            total_violations=total_violations,
            attendance_rate=attendance_rate,
            employees=employee_attendance
        )
        
        # Cache for 5 minutes
        await cache.set(cache_key, summary_data.dict(), 300)
        
        return format_success_response(
            data=summary_data.dict(),
            message=f"Daily attendance for {target_date.strftime('%Y-%m-%d')}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting daily attendance: {str(e)}",
            status_code=500
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_attendance_stats(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """
    Get attendance statistics over a date range.
    
    Returns:
    - Average attendance rate
    - Most punctual employees
    - Most frequent violators
    - Attendance trends
    - Zone utilization
    """
    try:
        # Parse date range or use last 7 days
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = datetime.now().date()
            start_dt = end_dt - timedelta(days=7)
        
        start_timestamp = datetime.combine(start_dt, datetime.min.time()).timestamp()
        end_timestamp = datetime.combine(end_dt, datetime.max.time()).timestamp()
        
        # Check cache
        cache_key = f"attendance_stats:{start_date or 'last_7_days'}:{end_date or 'today'}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return format_success_response(
                data=cached_result,
                message=f"Attendance statistics from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
            )
        
        # Get daily attendance counts
        daily_attendance_query = """
        SELECT 
            DATE(to_timestamp(timestamp)) as date,
            COUNT(DISTINCT data->>'label') as daily_count
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND timestamp >= $1
        AND timestamp <= $2
        GROUP BY DATE(to_timestamp(timestamp))
        ORDER BY date
        """
        
        daily_counts = await db.fetch_all(daily_attendance_query, start_timestamp, end_timestamp)
        
        # Get employee attendance frequency
        employee_frequency_query = """
        SELECT 
            data->>'label' as employee_name,
            COUNT(DISTINCT DATE(to_timestamp(timestamp))) as days_present,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND timestamp >= $1
        AND timestamp <= $2
        GROUP BY data->>'label'
        ORDER BY days_present DESC
        """
        
        employee_frequency = await db.fetch_all(employee_frequency_query, start_timestamp, end_timestamp)
        
        # Get violation statistics
        violation_stats_query = """
        SELECT 
            data->>'label' as employee_name,
            COUNT(*) as violation_count
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND timestamp >= $1
        AND timestamp <= $2
        GROUP BY data->>'label'
        ORDER BY violation_count DESC
        LIMIT 10
        """
        
        violation_stats = await db.fetch_all(violation_stats_query, start_timestamp, end_timestamp)
        
        # Calculate statistics
        total_days = len(daily_counts)
        avg_daily_attendance = sum(d['daily_count'] for d in daily_counts) / total_days if total_days > 0 else 0
        
        # Most punctual employees (highest attendance rate)
        most_punctual = employee_frequency[:5] if employee_frequency else []
        
        # Most frequent violators
        top_violators = violation_stats[:5] if violation_stats else []
        
        # Attendance trends
        attendance_trend = []
        for day_data in daily_counts:
            attendance_trend.append({
                "date": day_data['date'].strftime('%Y-%m-%d'),
                "count": day_data['daily_count']
            })
        
        # Format response
        stats_data = {
            "date_range": {
                "start_date": start_dt.strftime('%Y-%m-%d'),
                "end_date": end_dt.strftime('%Y-%m-%d'),
                "total_days": total_days
            },
            "summary": {
                "avg_daily_attendance": round(avg_daily_attendance, 2),
                "total_employees": len(employee_frequency),
                "total_violations": sum(v['violation_count'] for v in violation_stats)
            },
            "most_punctual": [
                {
                    "employee_name": emp['employee_name'],
                    "days_present": emp['days_present'],
                    "attendance_rate": round((emp['days_present'] / total_days) * 100, 2),
                    "first_seen": timestamp_to_iso(emp['first_seen']),
                    "last_seen": timestamp_to_iso(emp['last_seen'])
                }
                for emp in most_punctual
            ],
            "top_violators": [
                {
                    "employee_name": viol['employee_name'],
                    "violation_count": viol['violation_count']
                }
                for viol in top_violators
            ],
            "attendance_trend": attendance_trend
        }
        
        # Cache for 10 minutes
        await cache.set(cache_key, stats_data, 600)
        
        return format_success_response(
            data=stats_data,
            message=f"Attendance statistics from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
        )
        
    except Exception as e:
        return format_error_response(
            message=f"Error getting attendance statistics: {str(e)}",
            status_code=500
        )
