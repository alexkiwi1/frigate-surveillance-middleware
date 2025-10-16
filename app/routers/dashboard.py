"""
Dashboard summary API endpoints for Frigate Dashboard Middleware.

This module provides comprehensive dashboard analytics and summary statistics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.database import DatabaseManager, get_database
from app.cache import CacheManager, get_cache
from app.config import settings
from app.utils.response_formatter import format_success_response, format_error_response
from app.utils.time import timestamp_to_iso

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
):
    """Get comprehensive dashboard summary statistics."""
    try:
        # Parse date or use today
        target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now().date()
        start_ts = datetime.combine(target_date, datetime.min.time()).timestamp()
        end_ts = datetime.combine(target_date, datetime.max.time()).timestamp()
        
        # Check cache
        cache_key = f"dashboard_summary:{date or 'today'}"
        cached = await cache.get(cache_key)
        if cached:
            return format_success_response(data=cached, message="Dashboard summary")
        
        # Active employees (last 5 min)
        now = datetime.now().timestamp()
        active_query = """
        SELECT COUNT(DISTINCT data->>'label') as count
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND timestamp > $1
        """
        active_result = await db.fetch_one(active_query, now - 300)
        active_employees = active_result['count'] if active_result else 0
        
        # On break (5min-3hrs ago)
        break_query = """
        SELECT COUNT(DISTINCT data->>'label') as count
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND timestamp > $1
        AND timestamp <= $2
        """
        break_result = await db.fetch_one(break_query, now - 10800, now - 300)
        on_break = break_result['count'] if break_result else 0
        
        # Total present today
        present_query = """
        SELECT COUNT(DISTINCT data->>'label') as count
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND timestamp >= $1
        AND timestamp <= $2
        """
        present_result = await db.fetch_one(present_query, start_ts, end_ts)
        total_present = present_result['count'] if present_result else 0
        
        # Phone violations today/this hour
        violations_today_query = """
        SELECT COUNT(*) as count
        FROM timeline
        WHERE data->>'label' = 'cell phone'
        AND timestamp >= $1
        AND timestamp <= $2
        """
        violations_today_result = await db.fetch_one(violations_today_query, start_ts, end_ts)
        violations_today = violations_today_result['count'] if violations_today_result else 0
        
        violations_hour_result = await db.fetch_one(violations_today_query, now - 3600, now)
        violations_hour = violations_hour_result['count'] if violations_hour_result else 0
        
        # Average work hours
        work_hours_query = """
        SELECT 
            data->>'label' as employee,
            (MAX(timestamp) - MIN(timestamp)) / 3600 as hours
        FROM timeline
        WHERE data->>'label' IS NOT NULL
        AND data->>'label' != 'cell phone'
        AND timestamp >= $1
        AND timestamp <= $2
        GROUP BY data->>'label'
        """
        work_hours_results = await db.fetch_all(work_hours_query, start_ts, end_ts)
        avg_work_hours = sum(r['hours'] for r in work_hours_results) / len(work_hours_results) if work_hours_results else 0
        
        # Busiest zone
        busiest_zone_query = """
        SELECT 
            jsonb_array_elements_text(data->'zones') as zone,
            COUNT(*) as detections
        FROM timeline
        WHERE data->'zones' IS NOT NULL
        AND timestamp >= $1
        AND timestamp <= $2
        GROUP BY zone
        ORDER BY detections DESC
        LIMIT 1
        """
        busiest_result = await db.fetch_one(busiest_zone_query, start_ts, end_ts)
        busiest_zone = busiest_result['zone'] if busiest_result else None
        
        # Top violators
        top_violators_query = """
        SELECT 
            t1.data->>'label' as employee,
            COUNT(*) as violation_count
        FROM timeline t1
        WHERE t1.data->>'label' = 'cell phone'
        AND t1.timestamp >= $1
        AND t1.timestamp <= $2
        GROUP BY employee
        ORDER BY violation_count DESC
        LIMIT 5
        """
        top_violators = await db.fetch_all(top_violators_query, start_ts, end_ts)
        
        summary = {
            "active_employees": active_employees,
            "on_break": on_break,
            "total_present": total_present,
            "violations_today": violations_today,
            "violations_this_hour": violations_hour,
            "avg_work_hours": round(avg_work_hours, 2),
            "busiest_zone": busiest_zone,
            "top_violators": [{"employee": v['employee'], "violations": v['violation_count']} for v in top_violators]
        }
        
        await cache.set(cache_key, summary, 300)
        return format_success_response(data=summary, message="Dashboard summary")
        
    except Exception as e:
        return format_error_response(message=f"Error: {str(e)}", status_code=500)

