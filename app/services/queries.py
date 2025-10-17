"""
Complex SQL queries for the Frigate Dashboard Middleware.

This module contains all the complex SQL queries used throughout the application,
including violation detection, employee statistics, and camera activity queries.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from ..database import DatabaseManager
from ..config import settings

logger = logging.getLogger(__name__)


class ViolationQueries:
    """Queries related to phone violations and detection."""
    
    @staticmethod
    async def get_live_violations(
        db: DatabaseManager,
        camera: Optional[str] = None,
        hours: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent phone violations with employee identification.
        
        This complex query:
        1. Finds recent phone detections
        2. Joins with nearby face detections to identify employees
        3. Links with review segments for thumbnails
        4. Constructs media URLs
        
        Args:
            db: Database manager
            camera: Optional camera filter
            hours: Hours to look back
            limit: Maximum results
            
        Returns:
            List of violation records with employee names and media URLs
        """
        # Ensure hours is an integer (convert from Decimal if needed)
        hours = int(hours)
        hours_seconds = int(hours * 3600)
        face_window = int(settings.face_detection_window)
        
        camera_filter = f"AND camera = '{camera}'" if camera else ""
        
        # Query with desk-based employee identification + face verification
        query = f"""
        WITH violation_zones AS (
            -- Get phone violations with their zones
            SELECT 
                p.timestamp,
                p.camera,
                p.source_id as id,
                p.data->'zones' as zones
            FROM timeline p
            WHERE p.data->>'label' = 'cell phone'
            AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours_seconds})
            {camera_filter}
        ),
        desk_assignments AS (
            -- Official desk assignments (corrected)
            SELECT * FROM (VALUES
                ('desk_1', 'Safia Imtiaz'),
                ('desk_2', 'Kinza Amin'),
                ('desk_3', 'Aiman Jawaid'),
                ('desk_4', 'Nimra Ghulam Fareed'),
                ('desk_5', 'Summaiya Khan'),
                ('desk_6', 'Arifa Dhari'),
                ('desk_7', 'Khalid Ahmed'),
                ('desk_9', 'Muhammad Arsalan'),
                ('desk_10', 'Saadullah Khoso'),
                ('desk_11', 'Muhammad Taha'),
                ('desk_12', 'Muhammad Awais'),
                ('desk_13', 'Nabeel Bhatti'),
                ('desk_14', 'Abdul Qayoom'),
                ('desk_15', 'Sharjeel Abbas'),
                ('desk_16', 'Saad Bin Salman'),
                ('desk_17', 'Sufiyan Ahmed'),
                ('desk_18', 'Muhammad Qasim'),
                ('desk_19', 'Sameer Panhwar'),
                ('desk_20', 'Bilal Soomro'),
                ('desk_21', 'Saqlain Murtaza'),
                ('desk_22', 'Syed Hussain Ali Kazi'),
                ('desk_23', 'Saad Khan'),
                ('desk_24', 'Kabeer Rajput'),
                ('desk_25', 'Mehmood Memon'),
                ('desk_26', 'Ali Habib'),
                ('desk_27', 'Bhamar Lal'),
                ('desk_28', 'Atban Bin Aslam'),
                ('desk_29', 'Sadique Khowaja'),
                ('desk_30', 'Syed Awwab'),
                ('desk_31', 'Samad Siyal'),
                ('desk_32', 'Wasi Khan'),
                ('desk_33', 'Kashif Raza'),
                ('desk_34', 'Wajahat Imam'),
                ('desk_35', 'Bilal Ahmed'),
                ('desk_36', 'Muhammad Usman'),
                ('desk_37', 'Arsalan Khan'),
                ('desk_38', 'Abdul Kabeer'),
                ('desk_39', 'Gian Chand'),
                ('desk_40', 'Ayan Arain'),
                ('desk_41', 'Zaib Ali Mughal'),
                ('desk_42', 'Abdul Wassay'),
                ('desk_43', 'Aashir Ali'),
                ('desk_44', 'Ali Raza'),
                ('desk_45', 'Muhammad Tabish'),
                ('desk_46', 'Farhan Ali'),
                ('desk_47', 'Tahir Ahmed'),
                ('desk_48', 'Zain Nawaz'),
                ('desk_49', 'Ali Memon'),
                ('desk_50', 'Muhammad Wasif Samoon'),
                ('desk_52', 'Sumair Hussain'),
                ('desk_53', 'Natasha Batool'),
                ('desk_55', 'Preet Nuckrich'),
                ('desk_59', 'Muhammad Uzair'),
                ('desk_62', 'Muhammad Roshan'),
                ('desk_58', 'Konain Mustafa'),
                ('desk_61', 'Hira Memon'),
                ('desk_63', 'Syed Safwan Ali Hashmi'),
                ('desk_64', 'Arbaz'),
                ('desk_65', 'Muhammad Shakir'),
                ('desk_66', 'Muneeb Intern')
            ) AS t(desk_zone, employee_name)
        )
        SELECT 
            v.timestamp,
            v.camera,
            v.id,
            v.zones,
            COALESCE(
                da.employee_name,  -- ONLY desk assignment
                'Unknown'          -- No desk assignment = Unknown
            ) as employee_name,
            COALESCE(
                CASE 
                    WHEN da.employee_name IS NOT NULL THEN 1.0  -- High confidence for desk assignment
                    ELSE 0.0
                END,
                0.0
            ) as confidence,
            NULL as thumbnail_url,
            NULL as video_url,
            CONCAT('{settings.video_api_base_url}/snapshot/', v.camera, '/', v.id) as snapshot_url
        FROM violation_zones v
        LEFT JOIN (
            -- Find desk assignment for violation
            SELECT DISTINCT ON (vz.id)
                vz.id,
                da.employee_name
            FROM violation_zones vz
            CROSS JOIN LATERAL (
                SELECT 
                    jsonb_array_elements_text(vz.zones) as desk_zone
            ) desk_list
            JOIN desk_assignments da ON desk_list.desk_zone = da.desk_zone
            WHERE desk_list.desk_zone LIKE 'desk_%'
        ) da ON da.id = v.id
        -- Face verification removed - using ONLY desk assignments
        ORDER BY v.timestamp DESC
        LIMIT {limit}
        """
        
        try:
            results = await db.fetch_all(query)
            logger.debug(f"Retrieved {len(results)} live violations")
            
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
            
            # Convert all Decimal values in the results
            converted_results = [convert_decimals(result) for result in results]
            return converted_results
        except Exception as e:
            logger.error(f"Error retrieving live violations: {e}")
            raise
    
    @staticmethod
    async def get_hourly_trend(
        db: DatabaseManager,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get hourly violation trends with camera and employee breakdown.
        
        Args:
            db: Database manager
            hours: Hours to analyze
            
        Returns:
            List of hourly trend data
        """
        # Ensure hours is an integer (convert from Decimal if needed)
        hours = int(hours)
        
        # Calculate time values as integers
        hours_seconds = int(hours * 3600)
        face_window = int(settings.face_detection_window)
        
        query = f"""
        WITH hourly_buckets AS (
            SELECT 
                generate_series(
                    EXTRACT(EPOCH FROM NOW()) - {hours_seconds}::integer,
                    EXTRACT(EPOCH FROM NOW())::integer,
                    3600
                ) as hour_start
        ),
        hourly_violations AS (
            SELECT 
                FLOOR(timestamp / 3600) * 3600 as hour,
                camera,
                COALESCE(nf.employee_name, 'Unknown') as employee_name
            FROM timeline p
            LEFT JOIN (
                SELECT DISTINCT ON (p.timestamp, p.camera)
                    p.timestamp, 
                    p.camera,
                    (f.data->'sub_label'->>0) as employee_name
                FROM timeline p
                LEFT JOIN timeline f ON 
                    f.camera = p.camera 
                    AND f.source = 'tracked_object'
                    AND f.data->'sub_label' IS NOT NULL
                    AND f.data->'sub_label'->>0 IS NOT NULL
                    AND ABS(f.timestamp - p.timestamp) < {face_window}
                WHERE p.data->>'label' = 'cell phone'
                AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours_seconds})
                ORDER BY p.timestamp, p.camera, ABS(f.timestamp - p.timestamp)
            ) nf USING (timestamp, camera)
            WHERE p.data->>'label' = 'cell phone'
            AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours_seconds})
        )
        SELECT 
            hb.hour_start as hour,
            COUNT(hv.hour) as violations,
            ARRAY_AGG(DISTINCT hv.camera) FILTER (WHERE hv.camera IS NOT NULL) as cameras,
            ARRAY_AGG(DISTINCT hv.employee_name) FILTER (WHERE hv.employee_name IS NOT NULL) as employees
        FROM hourly_buckets hb
        LEFT JOIN hourly_violations hv ON hb.hour_start = hv.hour
        GROUP BY hb.hour_start
        ORDER BY hb.hour_start DESC
        """
        
        try:
            logger.debug(f"Executing hourly trend query with hours={hours}, hours_seconds={hours_seconds}, face_window={face_window}")
            results = await db.fetch_all(query)
            logger.debug(f"Retrieved hourly trend for {len(results)} hours")
            return results
        except Exception as e:
            logger.error(f"Error retrieving hourly trend: {e}")
            logger.error(f"Query parameters: hours={hours}, hours_seconds={hours_seconds}, face_window={face_window}")
            raise


class EmployeeQueries:
    """Queries related to employee statistics and activity."""
    
    @staticmethod
    async def get_employee_stats(
        db: DatabaseManager,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get comprehensive employee statistics including activity levels.
        
        Args:
            db: Database manager
            hours: Hours to analyze
            
        Returns:
            List of employee statistics
        """
        # Ensure hours is an integer (convert from Decimal if needed)
        hours = int(hours)
        hours_seconds = int(hours * 3600)
        face_window = int(settings.face_detection_window)
        
        query = f"""
        WITH employee_detections AS (
            SELECT 
                (data->'sub_label'->>0) as employee_name,
                COUNT(*) as detections,
                COUNT(DISTINCT camera) as cameras_visited,
                MAX(timestamp) as last_seen
            FROM timeline
            WHERE data->>'label' = 'person'
            AND timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours_seconds})
            AND data->'sub_label' IS NOT NULL
            AND data->'sub_label'->>0 IS NOT NULL
            GROUP BY (data->'sub_label'->>0)
        ),
        employee_violations AS (
            SELECT 
                COALESCE(nf.employee_name, 'Unknown') as employee_name,
                COUNT(*) as violations_count
            FROM timeline p
            LEFT JOIN (
                SELECT DISTINCT ON (p.timestamp, p.camera)
                    p.timestamp, 
                    p.camera,
                    (f.data->'sub_label'->>0) as employee_name
                FROM timeline p
                LEFT JOIN timeline f ON 
                    f.camera = p.camera 
                    AND f.data->>'label' = 'person'
                    AND f.data->'sub_label' IS NOT NULL
                    AND f.data->'sub_label'->>0 IS NOT NULL
                    AND ABS(f.timestamp - p.timestamp) < {face_window}
                WHERE p.data->>'label' = 'cell phone'
                AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours_seconds})
                ORDER BY p.timestamp, p.camera, ABS(f.timestamp - p.timestamp)
            ) nf USING (timestamp, camera)
            WHERE p.data->>'label' = 'cell phone'
            AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours_seconds})
            GROUP BY nf.employee_name
        )
        SELECT 
            ed.employee_name,
            ed.detections,
            ed.cameras_visited,
            ed.last_seen,
            COALESCE(ev.violations_count, 0) as violations_count
        FROM employee_detections ed
        LEFT JOIN employee_violations ev ON ed.employee_name = ev.employee_name
        ORDER BY ed.detections DESC
        """
        
        try:
            results = await db.fetch_all(query)
            logger.debug(f"Retrieved stats for {len(results)} employees")
            return results
        except Exception as e:
            logger.error(f"Error retrieving employee stats: {e}")
            raise
    
    @staticmethod
    async def get_employee_violations(
        db: DatabaseManager,
        employee_name: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get detailed violation history for a specific employee.
        
        Args:
            db: Database manager
            employee_name: Name of the employee
            start_time: Optional start timestamp
            end_time: Optional end timestamp
            limit: Maximum results
            
        Returns:
            List of violations for the employee
        """
        # Get face detection window
        face_window = int(settings.face_detection_window)
        
        time_filter = ""
        if start_time and end_time:
            time_filter = f"AND p.timestamp BETWEEN {start_time} AND {end_time}"
        elif start_time:
            time_filter = f"AND p.timestamp >= {start_time}"
        elif end_time:
            time_filter = f"AND p.timestamp <= {end_time}"
        
        query = f"""
        WITH employee_violations AS (
            SELECT 
                p.timestamp,
                p.camera,
                p.source_id,
                p.data->'zones' as zones,
                (f.data->'sub_label'->>0) as employee_name,
                (f.data->'sub_label'->>1)::float as confidence
            FROM timeline p
            LEFT JOIN timeline f ON 
                f.camera = p.camera 
                AND f.data->>'label' = 'person'
                AND f.data->'sub_label' IS NOT NULL
                AND f.data->'sub_label'->>0 IS NOT NULL
                AND ABS(f.timestamp - p.timestamp) < {face_window}
            WHERE p.data->>'label' = 'cell phone'
            AND f.data->'sub_label'->>0 = '{employee_name}'
            {time_filter}
            ORDER BY p.timestamp, p.camera, ABS(f.timestamp - p.timestamp)
        )
        SELECT DISTINCT ON (ev.timestamp, ev.camera)
            ev.timestamp,
            ev.camera,
            ev.source_id as id,
            ev.zones,
            ev.employee_name,
            COALESCE(ev.confidence, 0.0) as confidence,
            CONCAT('{settings.video_api_base_url}/thumb/', ev.source_id) as thumbnail_url,
            CONCAT('{settings.video_api_base_url}/clip/', ev.source_id) as video_url,
            CONCAT('{settings.video_api_base_url}/snapshot/', ev.camera, '/', ev.source_id) as snapshot_url
        FROM employee_violations ev
        ORDER BY ev.timestamp DESC
        LIMIT {limit}
        """
        
        try:
            results = await db.fetch_all(query)
            logger.debug(f"Retrieved {len(results)} violations for employee {employee_name}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving employee violations: {e}")
            raise


class CameraQueries:
    """Queries related to camera activity and status."""
    
    @staticmethod
    async def get_camera_summary(
        db: DatabaseManager,
        camera: str
    ) -> Dict[str, Any]:
        """
        Get live summary for a specific camera.
        
        Args:
            db: Database manager
            camera: Camera name
            
        Returns:
            Camera summary data
        """
        query = f"""
        WITH current_hour AS (
            SELECT EXTRACT(EPOCH FROM DATE_TRUNC('hour', NOW())) as hour_start
        ),
        camera_stats AS (
            SELECT 
                COUNT(*) FILTER (WHERE data->>'label' = 'person') as active_people,
                COUNT(*) as total_detections,
                COUNT(*) FILTER (WHERE data->>'label' = 'cell phone') as phone_violations,
                MAX(timestamp) as last_activity
            FROM timeline
            WHERE camera = '{camera}'
            AND timestamp > (SELECT hour_start FROM current_hour)
        ),
        recording_status AS (
            SELECT 
                CASE 
                    WHEN COUNT(*) > 0 THEN 'active'
                    ELSE 'inactive'
                END as status
            FROM recordings
            WHERE camera = '{camera}'
            AND start_time > (SELECT hour_start FROM current_hour)
        )
        SELECT 
            '{camera}' as camera,
            COALESCE(cs.active_people, 0) as active_people,
            COALESCE(cs.total_detections, 0) as total_detections,
            COALESCE(cs.phone_violations, 0) as phone_violations,
            COALESCE(rs.status, 'unknown') as recording_status,
            cs.last_activity
        FROM camera_stats cs
        CROSS JOIN recording_status rs
        """
        
        try:
            result = await db.fetch_one(query)
            logger.debug(f"Retrieved camera summary for {camera}")
            return result or {}
        except Exception as e:
            logger.error(f"Error retrieving camera summary: {e}")
            raise
    
    @staticmethod
    async def get_camera_activity(
        db: DatabaseManager,
        camera: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get detailed activity for a specific camera.
        
        Args:
            db: Database manager
            camera: Camera name
            hours: Hours to look back
            limit: Maximum results
            
        Returns:
            List of camera activities
        """
        # Ensure hours is an integer (convert from Decimal if needed)
        hours = int(hours)
        hours_seconds = int(hours * 3600)
        face_window = int(settings.face_detection_window)
        
        query = f"""
        WITH camera_events AS (
            SELECT 
                timestamp,
                data->>'label' as event_type,
                data->>'sub_label' as employee_name,
                data->'zones' as zones,
                data->>'score' as confidence
            FROM timeline
            WHERE camera = '{camera}'
            AND timestamp > (EXTRACT(EPOCH FROM NOW()) - {hours_seconds})
            AND data->>'label' IN ('person', 'cell phone', 'face')
        )
        SELECT 
            timestamp,
            event_type,
            employee_name,
            zones,
            COALESCE(confidence::float, 0.0) as confidence,
            CONCAT('{settings.video_api_base_url}/snapshot/', '{camera}', '/', timestamp, '-', 
                   SUBSTRING(MD5(timestamp::text), 1, 6)) as snapshot_url
        FROM camera_events
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        
        try:
            results = await db.fetch_all(query)
            logger.debug(f"Retrieved {len(results)} activities for camera {camera}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving camera activity: {e}")
            raise


class DashboardQueries:
    """Queries for dashboard overview and aggregated data."""
    
    @staticmethod
    async def get_dashboard_overview(
        db: DatabaseManager
    ) -> Dict[str, Any]:
        """
        Get complete dashboard overview data.
        
        Args:
            db: Database manager
            
        Returns:
            Dashboard overview data
        """
        # Get face detection window
        face_window = int(settings.face_detection_window)
        
        query = f"""
        WITH today_start AS (
            SELECT EXTRACT(EPOCH FROM DATE_TRUNC('day', NOW())) as day_start
        ),
        violations_today AS (
            SELECT COUNT(*) as total_violations
            FROM timeline
            WHERE data->>'label' = 'cell phone'
            AND timestamp > (SELECT day_start FROM today_start)
        ),
        top_violators AS (
            SELECT 
                COALESCE(nf.employee_name, 'Unknown') as employee_name,
                COUNT(*) as violations_count,
                MAX(p.timestamp) as last_violation
            FROM timeline p
            LEFT JOIN (
                SELECT DISTINCT ON (p.timestamp, p.camera)
                    p.timestamp, 
                    p.camera,
                    (f.data->'sub_label'->>0) as employee_name
                FROM timeline p
                LEFT JOIN timeline f ON 
                    f.camera = p.camera 
                    AND f.source = 'tracked_object'
                    AND f.data->'sub_label' IS NOT NULL
                    AND f.data->'sub_label'->>0 IS NOT NULL
                    AND ABS(f.timestamp - p.timestamp) < {face_window}
                WHERE p.data->>'label' = 'cell phone'
                AND p.timestamp > (SELECT day_start FROM today_start)
                ORDER BY p.timestamp, p.camera, ABS(f.timestamp - p.timestamp)
            ) nf USING (timestamp, camera)
            WHERE p.data->>'label' = 'cell phone'
            AND p.timestamp > (SELECT day_start FROM today_start)
            GROUP BY nf.employee_name
            ORDER BY violations_count DESC
            LIMIT 5
        ),
        active_cameras AS (
            SELECT 
                camera,
                COUNT(*) FILTER (WHERE data->>'label' = 'person') as active_people,
                MAX(timestamp) as last_activity
            FROM timeline
            WHERE timestamp > (EXTRACT(EPOCH FROM NOW()) - 3600)
            GROUP BY camera
            HAVING COUNT(*) > 0
            ORDER BY active_people DESC
            LIMIT 10
        ),
        recent_events AS (
            SELECT 
                timestamp,
                camera,
                data->>'label' as event_type,
                data->>'sub_label' as employee_name,
                CASE 
                    WHEN data->>'label' = 'cell phone' THEN 'alert'
                    WHEN data->>'label' = 'person' THEN 'detection'
                    ELSE 'info'
                END as severity
            FROM timeline
            WHERE timestamp > (EXTRACT(EPOCH FROM NOW()) - 3600)
            ORDER BY timestamp DESC
            LIMIT 20
        )
        SELECT 
            (SELECT total_violations FROM violations_today) as total_violations_today,
            (SELECT json_agg(row_to_json(top_violators)) FROM top_violators) as top_violators,
            (SELECT json_agg(row_to_json(active_cameras)) FROM active_cameras) as active_cameras,
            (SELECT json_agg(row_to_json(recent_events)) FROM recent_events) as recent_events
        """
        
        try:
            result = await db.fetch_one(query)
            logger.debug("Retrieved dashboard overview data")
            return result or {}
        except Exception as e:
            logger.error(f"Error retrieving dashboard overview: {e}")
            raise
