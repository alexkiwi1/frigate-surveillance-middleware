"""
Attendance router for employee arrival/departure tracking.

This module provides endpoints for tracking employee attendance,
including arrival times, departure times, and current status.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from ..dependencies import DatabaseDep, CacheDep, get_database_manager, get_cache_manager
from ..utils.time import timestamp_to_iso, calculate_time_duration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


class EmployeeAttendance(BaseModel):
    """Employee attendance information."""
    employee_name: str = Field(..., description="Employee name")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    arrival_time: Optional[str] = Field(None, description="Arrival time in ISO format")
    departure_time: Optional[str] = Field(None, description="Departure time in ISO format")
    status: str = Field(..., description="Current status: present, left, not_present")
    total_time: Optional[str] = Field(None, description="Total time spent (HH:MM format)")
    last_seen: Optional[str] = Field(None, description="Last detection time")


class AttendanceResponse(BaseModel):
    """Response model for attendance data."""
    success: bool
    message: str
    data: List[EmployeeAttendance]
    timestamp: str


@router.get("/employee-status", response_model=AttendanceResponse)
async def get_employee_attendance_status(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    employee_name: Optional[str] = Query(None, description="Specific employee name"),
    db: DatabaseDep = Depends(get_database_manager),
    cache: CacheDep = Depends(get_cache_manager)
):
    """
    Get employee attendance status for a specific date.
    
    Returns arrival time, departure time, and current status for each employee.
    """
    try:
        # Validate date format
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Calculate time range for the day
        start_timestamp = target_date.timestamp()
        end_timestamp = (target_date + timedelta(days=1)).timestamp()
        
        # Check cache first
        cache_key = f"attendance_status:{date}:{employee_name or 'all'}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.debug(f"Returning cached attendance data for {date}")
            return AttendanceResponse(**cached_data)
        
        # Get all unique employees from timeline
        employees_query = """
        SELECT DISTINCT data->'sub_label'->>0 as employee_name
        FROM timeline 
        WHERE data->>'label' = 'person'
        AND data->'sub_label' IS NOT NULL
        AND data->'sub_label'->>0 IS NOT NULL
        AND data->'sub_label'->>0 != 'Unknown'
        AND timestamp BETWEEN $1 AND $2
        ORDER BY employee_name
        """
        
        if employee_name:
            employees_query += " AND data->'sub_label'->>0 = $3"
            employee_params = [start_timestamp, end_timestamp, employee_name]
        else:
            employee_params = [start_timestamp, end_timestamp]
        
        employees = await db.fetch_all(employees_query, *employee_params)
        
        attendance_data = []
        
        for emp in employees:
            emp_name = emp['employee_name']
            
            # Get first and last detection for this employee on this date
            detection_query = """
            SELECT 
                MIN(timestamp) as first_detection,
                MAX(timestamp) as last_detection,
                COUNT(*) as detection_count
            FROM timeline
            WHERE data->>'label' = 'person'
            AND data->'sub_label'->>0 = $1
            AND timestamp BETWEEN $2 AND $3
            """
            
            detection_result = await db.fetch_one(detection_query, emp_name, start_timestamp, end_timestamp)
            
            if not detection_result or detection_result['detection_count'] == 0:
                # Employee not present
                attendance_data.append(EmployeeAttendance(
                    employee_name=emp_name,
                    date=date,
                    arrival_time=None,
                    departure_time=None,
                    status="not_present",
                    total_time=None,
                    last_seen=None
                ))
                continue
            
            first_detection = detection_result['first_detection']
            last_detection = detection_result['last_detection']
            
            # Check if employee is still present (last detection within last 30 minutes)
            current_time = datetime.now().timestamp()
            is_still_present = (current_time - last_detection) < 1800  # 30 minutes
            
            # Determine status
            if is_still_present:
                status = "present"
                departure_time = None
            else:
                status = "left"
                departure_time = timestamp_to_iso(last_detection)
            
            # Calculate total time
            if status == "present":
                # Still present - calculate time from arrival to now
                total_seconds = current_time - first_detection
            else:
                # Left - calculate time from arrival to departure
                total_seconds = last_detection - first_detection
            
            total_time = calculate_time_duration(duration_seconds=total_seconds)
            
            attendance_data.append(EmployeeAttendance(
                employee_name=emp_name,
                date=date,
                arrival_time=timestamp_to_iso(first_detection),
                departure_time=departure_time,
                status=status,
                total_time=total_time,
                last_seen=timestamp_to_iso(last_detection)
            ))
        
        # Sort by employee name
        attendance_data.sort(key=lambda x: x.employee_name)
        
        response_data = AttendanceResponse(
            success=True,
            message=f"Attendance status for {date}",
            data=attendance_data,
            timestamp=datetime.now().isoformat()
        )
        
        # Cache for 5 minutes
        await cache.set(cache_key, response_data.dict(), ttl=300)
        
        logger.info(f"Retrieved attendance status for {len(attendance_data)} employees on {date}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting attendance status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve attendance status: {str(e)}")


@router.get("/employee/{employee_name}/daily", response_model=AttendanceResponse)
async def get_employee_daily_attendance(
    employee_name: str,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: DatabaseDep = Depends(get_database_manager),
    cache: CacheDep = Depends(get_cache_manager)
):
    """
    Get daily attendance for a specific employee.
    
    Returns detailed arrival/departure information for a single employee.
    """
    try:
        # Validate date format
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Calculate time range for the day
        start_timestamp = target_date.timestamp()
        end_timestamp = (target_date + timedelta(days=1)).timestamp()
        
        # Check cache first
        cache_key = f"employee_daily_attendance:{employee_name}:{date}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.debug(f"Returning cached daily attendance for {employee_name} on {date}")
            return AttendanceResponse(**cached_data)
        
        # Get employee's detection data for the day
        detection_query = """
        SELECT 
            MIN(timestamp) as first_detection,
            MAX(timestamp) as last_detection,
            COUNT(*) as detection_count,
            COUNT(DISTINCT camera) as cameras_used
        FROM timeline
        WHERE data->>'label' = 'person'
        AND data->'sub_label'->>0 = $1
        AND timestamp BETWEEN $2 AND $3
        """
        
        detection_result = await db.fetch_one(detection_query, employee_name, start_timestamp, end_timestamp)
        
        if not detection_result or detection_result['detection_count'] == 0:
            # Employee not present
            attendance_data = [EmployeeAttendance(
                employee_name=employee_name,
                date=date,
                arrival_time=None,
                departure_time=None,
                status="not_present",
                total_time=None,
                last_seen=None
            )]
        else:
            first_detection = detection_result['first_detection']
            last_detection = detection_result['last_detection']
            
            # Check if employee is still present
            current_time = datetime.now().timestamp()
            is_still_present = (current_time - last_detection) < 1800  # 30 minutes
            
            # Determine status
            if is_still_present:
                status = "present"
                departure_time = None
            else:
                status = "left"
                departure_time = timestamp_to_iso(last_detection)
            
            # Calculate total time
            if status == "present":
                total_seconds = current_time - first_detection
            else:
                total_seconds = last_detection - first_detection
            
            total_time = calculate_time_duration(duration_seconds=total_seconds)
            
            attendance_data = [EmployeeAttendance(
                employee_name=employee_name,
                date=date,
                arrival_time=timestamp_to_iso(first_detection),
                departure_time=departure_time,
                status=status,
                total_time=total_time,
                last_seen=timestamp_to_iso(last_detection)
            )]
        
        response_data = AttendanceResponse(
            success=True,
            message=f"Daily attendance for {employee_name} on {date}",
            data=attendance_data,
            timestamp=datetime.now().isoformat()
        )
        
        # Cache for 5 minutes
        await cache.set(cache_key, response_data.dict(), ttl=300)
        
        logger.info(f"Retrieved daily attendance for {employee_name} on {date}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting daily attendance for {employee_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve daily attendance: {str(e)}")


@router.get("/summary", response_model=dict)
async def get_attendance_summary(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: DatabaseDep = Depends(get_database_manager),
    cache: CacheDep = Depends(get_cache_manager)
):
    """
    Get attendance summary for a specific date.
    
    Returns summary statistics including total present, left, and not present employees.
    """
    try:
        # Validate date format
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Calculate time range for the day
        start_timestamp = target_date.timestamp()
        end_timestamp = (target_date + timedelta(days=1)).timestamp()
        
        # Check cache first
        cache_key = f"attendance_summary:{date}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.debug(f"Returning cached attendance summary for {date}")
            return cached_data
        
        # Get summary statistics
        summary_query = """
        WITH employee_detections AS (
            SELECT 
                data->'sub_label'->>0 as employee_name,
                MIN(timestamp) as first_detection,
                MAX(timestamp) as last_detection,
                COUNT(*) as detection_count
            FROM timeline
            WHERE data->>'label' = 'person'
            AND data->'sub_label' IS NOT NULL
            AND data->'sub_label'->>0 IS NOT NULL
            AND data->'sub_label'->>0 != 'Unknown'
            AND timestamp BETWEEN $1 AND $2
            GROUP BY data->'sub_label'->>0
        )
        SELECT 
            COUNT(*) as total_employees,
            COUNT(CASE WHEN detection_count > 0 THEN 1 END) as present_employees,
            COUNT(CASE WHEN detection_count > 0 AND (EXTRACT(EPOCH FROM NOW()) - last_detection) < 1800 THEN 1 END) as currently_active,
            COUNT(CASE WHEN detection_count > 0 AND (EXTRACT(EPOCH FROM NOW()) - last_detection) >= 1800 THEN 1 END) as left_employees
        FROM employee_detections
        """
        
        summary_result = await db.fetch_one(summary_query, start_timestamp, end_timestamp)
        
        # Get total unique employees from all time (for reference)
        total_employees_query = """
        SELECT COUNT(DISTINCT data->'sub_label'->>0) as total_unique_employees
        FROM timeline
        WHERE data->>'label' = 'person'
        AND data->'sub_label' IS NOT NULL
        AND data->'sub_label'->>0 IS NOT NULL
        AND data->'sub_label'->>0 != 'Unknown'
        """
        
        total_employees_result = await db.fetch_one(total_employees_query)
        
        summary_data = {
            "success": True,
            "message": f"Attendance summary for {date}",
            "data": {
                "date": date,
                "total_employees": total_employees_result['total_unique_employees'],
                "present_employees": summary_result['present_employees'],
                "currently_active": summary_result['currently_active'],
                "left_employees": summary_result['left_employees'],
                "not_present": total_employees_result['total_unique_employees'] - summary_result['present_employees'],
                "attendance_rate": round((summary_result['present_employees'] / total_employees_result['total_unique_employees']) * 100, 1) if total_employees_result['total_unique_employees'] > 0 else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Cache for 5 minutes
        await cache.set(cache_key, summary_data, ttl=300)
        
        logger.info(f"Retrieved attendance summary for {date}")
        return summary_data
        
    except Exception as e:
        logger.error(f"Error getting attendance summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve attendance summary: {str(e)}")