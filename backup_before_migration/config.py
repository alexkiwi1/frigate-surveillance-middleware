"""
Configuration settings for the Frigate Dashboard Middleware.

This module handles all configuration including database connections,
Redis settings, and application parameters.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Frigate Dashboard Middleware"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=5002, env="PORT")
    
    # Database Configuration
    db_host: str = Field(default="10.0.20.6", env="DB_HOST")
    db_port: int = Field(default=5433, env="DB_PORT")
    db_name: str = Field(default="frigate_db", env="DB_NAME")
    db_user: str = Field(default="frigate", env="DB_USER")
    db_password: str = Field(default="frigate_secure_pass_2024", env="DB_PASSWORD")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    
    # Video API Configuration
    video_api_base_url: str = Field(default="http://10.0.20.6:5001", env="VIDEO_API_BASE_URL")
    
    # Cache TTL Settings (in seconds)
    cache_ttl_live_violations: int = Field(default=10, env="CACHE_TTL_LIVE_VIOLATIONS")
    cache_ttl_hourly_trend: int = Field(default=300, env="CACHE_TTL_HOURLY_TREND")  # 5 minutes
    cache_ttl_employee_stats: int = Field(default=30, env="CACHE_TTL_EMPLOYEE_STATS")
    cache_ttl_employee_violations: int = Field(default=30, env="CACHE_TTL_EMPLOYEE_VIOLATIONS")
    cache_ttl_camera_summary: int = Field(default=15, env="CACHE_TTL_CAMERA_SUMMARY")
    cache_ttl_camera_activity: int = Field(default=60, env="CACHE_TTL_CAMERA_ACTIVITY")
    cache_ttl_dashboard_overview: int = Field(default=10, env="CACHE_TTL_DASHBOARD_OVERVIEW")
    
    # Background Task Settings
    violation_poll_interval: int = Field(default=3, env="VIOLATION_POLL_INTERVAL")  # seconds
    stats_refresh_interval: int = Field(default=30, env="STATS_REFRESH_INTERVAL")  # seconds
    cache_cleanup_interval: int = Field(default=300, env="CACHE_CLEANUP_INTERVAL")  # 5 minutes
    
    # Background Task Intervals (for background service)
    background_poll_interval: int = Field(default=30, env="BACKGROUND_POLL_INTERVAL")  # seconds
    background_stats_refresh_interval: int = Field(default=300, env="BACKGROUND_STATS_REFRESH_INTERVAL")  # seconds
    background_cache_cleanup_interval: int = Field(default=3600, env="BACKGROUND_CACHE_CLEANUP_INTERVAL")  # seconds
    background_health_check_interval: int = Field(default=60, env="BACKGROUND_HEALTH_CHECK_INTERVAL")  # seconds
    
    # WebSocket Settings
    websocket_poll_interval: int = Field(default=5, env="WEBSOCKET_POLL_INTERVAL")  # seconds
    
    # Business Logic Settings
    phone_violation_window: int = Field(default=3600, env="PHONE_VIOLATION_WINDOW")  # 1 hour
    face_detection_window: int = Field(default=3, env="FACE_DETECTION_WINDOW")  # 3 seconds
    thumbnail_window: int = Field(default=5, env="THUMBNAIL_WINDOW")  # 5 seconds
    employee_activity_window: int = Field(default=86400, env="EMPLOYEE_ACTIVITY_WINDOW")  # 24 hours
    
    # Activity Level Thresholds
    high_activity_threshold: int = Field(default=20, env="HIGH_ACTIVITY_THRESHOLD")
    medium_activity_threshold: int = Field(default=10, env="MEDIUM_ACTIVITY_THRESHOLD")
    
    # Timezone
    timezone: str = Field(default="Asia/Karachi", env="TIMEZONE")
    
    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # Rate Limiting (optional)
    rate_limit_enabled: bool = Field(default=False, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Camera Configuration
    cameras: List[str] = Field(
        default=[
            "admin_office",
            "employees_01", 
            "employees_02",
            "employees_03",
            "employees_04",
            "employees_05",
            "employees_06",
            "employees_07",
            "employees_08",
            "meeting_room",
            "reception",
            "camera_237"
        ],
        env="CAMERAS"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def database_url(self) -> str:
        """Construct database URL for asyncpg."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def CAMERAS(self) -> List[str]:
        """Get cameras list for backward compatibility."""
        return self.cameras


# Global settings instance
settings = Settings()


# Camera list from the requirements
CAMERAS = [
    "admin_office",
    "employees_01", 
    "employees_02",
    "employees_03",
    "employees_04",
    "employees_05",
    "employees_06",
    "employees_07",
    "employees_08",
    "meeting_room",
    "reception",
    "camera_237"
]


# Cache key patterns
class CacheKeys:
    """Centralized cache key patterns."""
    
    @staticmethod
    def live_violations(camera: Optional[str] = None, limit: int = 50) -> str:
        """Cache key for live violations."""
        camera_part = f":{camera}" if camera else ""
        return f"violations:live{camera_part}:{limit}"
    
    @staticmethod
    def hourly_trend(hours: int = 24) -> str:
        """Cache key for hourly trend data."""
        return f"violations:hourly_trend:{hours}"
    
    @staticmethod
    def employee_stats() -> str:
        """Cache key for employee statistics."""
        return "employees:stats"
    
    @staticmethod
    def employee_violations(employee_name: str, start_time: Optional[int] = None, 
                          end_time: Optional[int] = None, limit: int = 100) -> str:
        """Cache key for employee violations."""
        time_part = ""
        if start_time and end_time:
            time_part = f":{start_time}:{end_time}"
        return f"employees:{employee_name}:violations{time_part}:{limit}"
    
    @staticmethod
    def camera_summary(camera: str) -> str:
        """Cache key for camera summary."""
        return f"cameras:{camera}:summary"
    
    @staticmethod
    def camera_activity(camera: str, hours: int = 24) -> str:
        """Cache key for camera activity."""
        return f"cameras:{camera}:activity:{hours}"
    
    @staticmethod
    def dashboard_overview() -> str:
        """Cache key for dashboard overview."""
        return "dashboard:overview"
