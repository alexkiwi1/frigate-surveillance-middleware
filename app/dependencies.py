"""
FastAPI dependencies following best practices.

This module provides dependency injection functions for database connections,
cache operations, and parameter validation following FastAPI best practices.
"""

import logging
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .database import DatabaseManager, get_database, db_manager
from .cache import CacheManager, get_cache, cache_manager
from .config import settings
from .utils.errors import (
    validate_positive_integer,
    validate_hours_range,
    validate_limit_range,
    validate_camera_name,
    validate_employee_name,
    NotFoundError,
    ValidationError
)

logger = logging.getLogger(__name__)

# Security scheme (optional - can be enabled for authentication)
security = HTTPBearer(auto_error=False)


async def get_database_manager() -> DatabaseManager:
    """
    Dependency to get database manager with proper error handling.
    
    Returns:
        DatabaseManager instance
        
    Raises:
        HTTPException: If database is not available
    """
    if not db_manager.pool:
        logger.error("Database manager not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    return db_manager


async def get_cache_manager() -> CacheManager:
    """
    Dependency to get cache manager with proper error handling.
    
    Returns:
        CacheManager instance
        
    Raises:
        HTTPException: If cache is not available
    """
    if not cache_manager.redis:
        logger.error("Cache manager not connected")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable"
        )
    
    return cache_manager


def validate_camera_parameter(camera: Optional[str] = None) -> Optional[str]:
    """
    Validate camera parameter with guard clauses.
    
    Args:
        camera: Camera name to validate
        
    Returns:
        Validated camera name or None
        
    Raises:
        HTTPException: If camera is invalid
    """
    if camera is None:
        return None
    
    try:
        return validate_camera_name(camera, settings.CAMERAS)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera}' not found. Available cameras: {', '.join(settings.CAMERAS)}"
        )


def validate_limit_parameter(limit: int = 100) -> int:
    """
    Validate limit parameter with guard clauses.
    
    Args:
        limit: Limit value to validate
        
    Returns:
        Validated limit value
        
    Raises:
        HTTPException: If limit is invalid
    """
    try:
        return validate_limit_range(limit)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )


def validate_hours_parameter(hours: int = 24) -> int:
    """
    Validate hours parameter with guard clauses.
    
    Args:
        hours: Hours value to validate
        
    Returns:
        Validated hours value
        
    Raises:
        HTTPException: If hours is invalid
    """
    try:
        return validate_hours_range(hours)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )


def validate_employee_name_parameter(employee_name: str) -> str:
    """
    Validate employee name parameter with guard clauses.
    
    Args:
        employee_name: Employee name to validate
        
    Returns:
        Validated employee name
        
    Raises:
        HTTPException: If employee name is invalid
    """
    try:
        return validate_employee_name(employee_name)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )


def validate_query_parameter(query: str) -> str:
    """
    Validate search query parameter with guard clauses.
    
    Args:
        query: Search query to validate
        
    Returns:
        Validated search query
        
    Raises:
        HTTPException: If query is invalid
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query must be at least 2 characters long"
        )
    
    return query.strip()


async def get_optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[HTTPAuthorizationCredentials]:
    """
    Optional authentication dependency.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Credentials if provided, None otherwise
    """
    return credentials


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> HTTPAuthorizationCredentials:
    """
    Required authentication dependency.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Valid credentials
        
    Raises:
        HTTPException: If credentials are not provided
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return credentials


async def validate_timestamp_range(start_time: Optional[float], end_time: Optional[float]) -> tuple[float, float]:
    """
    Validate and normalize timestamp range parameters.
    
    Args:
        start_time: Start timestamp (Unix epoch)
        end_time: End timestamp (Unix epoch)
        
    Returns:
        Tuple of (start_time, end_time) as floats
        
    Raises:
        ValidationError: If timestamps are invalid
    """
    import time
    
    current_time = time.time()
    
    # Set defaults if not provided
    if start_time is None:
        start_time = current_time - (24 * 3600)  # 24 hours ago
    
    if end_time is None:
        end_time = current_time
    
    # Validate timestamps
    if start_time >= end_time:
        raise ValidationError("Start time must be before end time")
    
    if start_time < current_time - (30 * 24 * 3600):  # 30 days ago
        raise ValidationError("Start time cannot be more than 30 days ago")
    
    if end_time > current_time:
        raise ValidationError("End time cannot be in the future")
    
    return float(start_time), float(end_time)


# Dependency aliases for backward compatibility
DatabaseDep = Depends(get_database_manager)
CacheDep = Depends(get_cache_manager)
CameraDep = Depends(validate_camera_parameter)
LimitDep = Depends(validate_limit_parameter)
HoursDep = Depends(validate_hours_parameter)
EmployeeNameDep = Depends(validate_employee_name_parameter)
QueryDep = Depends(validate_query_parameter)
OptionalAuthDep = Depends(get_optional_auth)
RequiredAuthDep = Depends(require_auth)


def create_dependency_factory(dependency_func):
    """
    Create a dependency factory for reusable dependencies.
    
    Args:
        dependency_func: Function to create dependency from
        
    Returns:
        Dependency factory function
    """
    def factory(*args, **kwargs):
        return Depends(lambda: dependency_func(*args, **kwargs))
    
    return factory


def create_validation_dependency(validator_func, error_message: str):
    """
    Create a validation dependency with custom error message.
    
    Args:
        validator_func: Validation function
        error_message: Custom error message
        
    Returns:
        Validation dependency function
    """
    def validation_dependency(value):
        try:
            return validator_func(value)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_message
            )
    
    return Depends(validation_dependency)


# Specialized validation dependencies
validate_positive_int = create_validation_dependency(
    validate_positive_integer,
    "Value must be a positive integer"
)

validate_string_length = create_validation_dependency(
    lambda x: validate_string_length(x, "field", 1, 100),
    "String must be between 1 and 100 characters"
)
