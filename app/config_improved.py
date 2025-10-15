"""
Configuration management following FastAPI best practices.

This module provides configuration management using Pydantic Settings
with proper validation, type hints, and environment variable handling.
"""

import logging
from typing import List, Optional, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    name: str = Field(default="frigate_db", env="DB_NAME")
    user: str = Field(default="frigate", env="DB_USER")
    password: str = Field(default="frigate_secure_pass_2024", env="DB_PASSWORD")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @validator('pool_size', 'max_overflow')
    def validate_pool_settings(cls, v):
        if v < 1:
            raise ValueError('Pool settings must be positive integers')
        return v


class CacheConfig(BaseSettings):
    """Cache configuration settings."""
    
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class VideoAPIConfig(BaseSettings):
    """Video API configuration settings."""
    
    base_url: str = Field(default="http://10.0.20.6:5001", env="VIDEO_API_BASE_URL")
    timeout: int = Field(default=30, env="VIDEO_API_TIMEOUT")
    retry_attempts: int = Field(default=3, env="VIDEO_API_RETRY_ATTEMPTS")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v.rstrip('/')


class CacheTTLConfig(BaseSettings):
    """Cache TTL configuration settings."""
    
    live_violations: int = Field(default=300, env="CACHE_TTL_LIVE_VIOLATIONS")  # 5 minutes
    hourly_trend: int = Field(default=1800, env="CACHE_TTL_HOURLY_TREND")  # 30 minutes
    violation_stats: int = Field(default=3600, env="CACHE_TTL_VIOLATION_STATS")  # 1 hour
    employee_stats: int = Field(default=1800, env="CACHE_TTL_EMPLOYEE_STATS")  # 30 minutes
    employee_search: int = Field(default=600, env="CACHE_TTL_EMPLOYEE_SEARCH")  # 10 minutes
    camera_summary: int = Field(default=300, env="CACHE_TTL_CAMERA_SUMMARY")  # 5 minutes
    camera_activity: int = Field(default=600, env="CACHE_TTL_CAMERA_ACTIVITY")  # 10 minutes
    
    @validator('*')
    def validate_ttl_values(cls, v):
        if v < 0:
            raise ValueError('TTL values must be non-negative')
        return v


class BackgroundTaskConfig(BaseSettings):
    """Background task configuration settings."""
    
    poll_interval: int = Field(default=30, env="BACKGROUND_POLL_INTERVAL")
    stats_refresh_interval: int = Field(default=300, env="BACKGROUND_STATS_REFRESH_INTERVAL")
    cache_cleanup_interval: int = Field(default=3600, env="BACKGROUND_CACHE_CLEANUP_INTERVAL")
    health_check_interval: int = Field(default=60, env="BACKGROUND_HEALTH_CHECK_INTERVAL")
    
    @validator('*')
    def validate_intervals(cls, v):
        if v < 1:
            raise ValueError('Background task intervals must be positive integers')
        return v


class BusinessLogicConfig(BaseSettings):
    """Business logic configuration settings."""
    
    face_detection_window: int = Field(default=300, env="FACE_DETECTION_WINDOW")  # 5 minutes
    violation_threshold: int = Field(default=5, env="VIOLATION_THRESHOLD")
    activity_level_thresholds: dict = Field(
        default={
            "high": 100,
            "medium": 50,
            "low": 10
        },
        env="ACTIVITY_LEVEL_THRESHOLDS"
    )
    
    @validator('face_detection_window')
    def validate_face_window(cls, v):
        if v < 60:  # At least 1 minute
            raise ValueError('Face detection window must be at least 60 seconds')
        return v


class SecurityConfig(BaseSettings):
    """Security configuration settings."""
    
    cors_origins: List[str] = Field(
        default=["*"],
        env="CORS_ORIGINS"
    )
    allowed_hosts: List[str] = Field(
        default=["*"],
        env="ALLOWED_HOSTS"
    )
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    
    @validator('cors_origins', 'allowed_hosts')
    def validate_origins(cls, v):
        if not v:
            raise ValueError('CORS origins and allowed hosts cannot be empty')
        return v


class LoggingConfig(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    
    @validator('level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class Settings(PydanticBaseSettings):
    """Main application settings following FastAPI best practices."""
    
    # Application metadata
    app_name: str = Field(default="Frigate Dashboard Middleware", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Service configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    video_api: VideoAPIConfig = Field(default_factory=VideoAPIConfig)
    
    # Feature configurations
    cache_ttl: CacheTTLConfig = Field(default_factory=CacheTTLConfig)
    background_tasks: BackgroundTaskConfig = Field(default_factory=BackgroundTaskConfig)
    business_logic: BusinessLogicConfig = Field(default_factory=BusinessLogicConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Camera configuration
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
            "employees_09",
            "meeting_room",
            "reception",
            "camera_237"
        ],
        env="CAMERAS"
    )
    
    # Timezone configuration
    timezone: str = Field(default="Asia/Karachi", env="TIMEZONE")
    
    # WebSocket configuration
    websocket_poll_interval: int = Field(default=5, env="WEBSOCKET_POLL_INTERVAL")
    
    @validator('cameras')
    def validate_cameras(cls, v):
        if not v:
            raise ValueError('Cameras list cannot be empty')
        return v
    
    @validator('timezone')
    def validate_timezone(cls, v):
        try:
            import pytz
            pytz.timezone(v)
        except Exception:
            raise ValueError(f'Invalid timezone: {v}')
        return v
    
    @property
    def CAMERAS(self) -> List[str]:
        """Get cameras list for backward compatibility."""
        return self.cameras
    
    @property
    def db_host(self) -> str:
        """Get database host for backward compatibility."""
        return self.database.host
    
    @property
    def db_port(self) -> int:
        """Get database port for backward compatibility."""
        return self.database.port
    
    @property
    def db_name(self) -> str:
        """Get database name for backward compatibility."""
        return self.database.name
    
    @property
    def db_user(self) -> str:
        """Get database user for backward compatibility."""
        return self.database.user
    
    @property
    def db_password(self) -> str:
        """Get database password for backward compatibility."""
        return self.database.password
    
    @property
    def redis_host(self) -> str:
        """Get Redis host for backward compatibility."""
        return self.cache.host
    
    @property
    def redis_port(self) -> int:
        """Get Redis port for backward compatibility."""
        return self.cache.port
    
    @property
    def video_api_base_url(self) -> str:
        """Get video API base URL for backward compatibility."""
        return self.video_api.base_url
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins for backward compatibility."""
        return self.security.cors_origins
    
    @property
    def face_detection_window(self) -> int:
        """Get face detection window for backward compatibility."""
        return self.business_logic.face_detection_window
    
    @property
    def cache_ttl_live_violations(self) -> int:
        """Get live violations cache TTL for backward compatibility."""
        return self.cache_ttl.live_violations
    
    @property
    def cache_ttl_hourly_trend(self) -> int:
        """Get hourly trend cache TTL for backward compatibility."""
        return self.cache_ttl.hourly_trend
    
    @property
    def cache_ttl_violation_stats(self) -> int:
        """Get violation stats cache TTL for backward compatibility."""
        return self.cache_ttl.violation_stats
    
    @property
    def cache_ttl_employee_stats(self) -> int:
        """Get employee stats cache TTL for backward compatibility."""
        return self.cache_ttl.employee_stats
    
    @property
    def cache_ttl_employee_search(self) -> int:
        """Get employee search cache TTL for backward compatibility."""
        return self.cache_ttl.employee_search
    
    @property
    def cache_ttl_camera_summary(self) -> int:
        """Get camera summary cache TTL for backward compatibility."""
        return self.cache_ttl.camera_summary
    
    @property
    def cache_ttl_camera_activity(self) -> int:
        """Get camera activity cache TTL for backward compatibility."""
        return self.cache_ttl.camera_activity
    
    @property
    def background_poll_interval(self) -> int:
        """Get background poll interval for backward compatibility."""
        return self.background_tasks.poll_interval
    
    @property
    def background_stats_refresh_interval(self) -> int:
        """Get background stats refresh interval for backward compatibility."""
        return self.background_tasks.stats_refresh_interval
    
    @property
    def background_cache_cleanup_interval(self) -> int:
        """Get background cache cleanup interval for backward compatibility."""
        return self.background_tasks.cache_cleanup_interval
    
    @property
    def background_health_check_interval(self) -> int:
        """Get background health check interval for backward compatibility."""
        return self.background_tasks.health_check_interval
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Cache key constants following naming conventions
class CacheKeys:
    """Cache key constants for consistent key management."""
    
    @staticmethod
    def live_violations(camera: Optional[str] = None, limit: int = 100, hours: int = 24) -> str:
        """Generate cache key for live violations."""
        camera_part = f":{camera}" if camera else ""
        return f"violations:live{camera_part}:{limit}:{hours}"
    
    @staticmethod
    def hourly_trend(hours: int = 24) -> str:
        """Generate cache key for hourly trend."""
        return f"violations:hourly_trend:{hours}"
    
    @staticmethod
    def violation_stats(hours: int = 24) -> str:
        """Generate cache key for violation statistics."""
        return f"violations:stats:{hours}"
    
    @staticmethod
    def employee_stats(hours: int = 24) -> str:
        """Generate cache key for employee statistics."""
        return f"employees:stats:{hours}"
    
    @staticmethod
    def employee_search(query: str, limit: int = 50) -> str:
        """Generate cache key for employee search."""
        return f"employees:search:{query}:{limit}"
    
    @staticmethod
    def employee_violations(employee_name: str, limit: int = 100, hours: int = 24) -> str:
        """Generate cache key for employee violations."""
        return f"employees:{employee_name}:violations:{limit}:{hours}"
    
    @staticmethod
    def employee_activity(employee_name: str, hours: int = 24) -> str:
        """Generate cache key for employee activity."""
        return f"employees:{employee_name}:activity:{hours}"
    
    @staticmethod
    def camera_summary() -> str:
        """Generate cache key for camera summary."""
        return "cameras:summary"
    
    @staticmethod
    def camera_activity(camera_name: str, hours: int = 24) -> str:
        """Generate cache key for camera activity."""
        return f"cameras:{camera_name}:activity:{hours}"
    
    @staticmethod
    def camera_violations(camera_name: str, limit: int = 100, hours: int = 24) -> str:
        """Generate cache key for camera violations."""
        return f"cameras:{camera_name}:violations:{limit}:{hours}"
    
    @staticmethod
    def camera_status(camera_name: str) -> str:
        """Generate cache key for camera status."""
        return f"cameras:{camera_name}:status"


# Create global settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.logging.level),
    format=settings.logging.format,
    filename=settings.logging.file_path
)

logger = logging.getLogger(__name__)
logger.info(f"Configuration loaded for {settings.app_name} v{settings.app_version}")
