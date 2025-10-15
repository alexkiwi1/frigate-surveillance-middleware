"""
Error handling utilities for the Frigate Dashboard Middleware.

This module provides custom error types, error factories, and consistent
error handling patterns following FastAPI best practices.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BaseAPIError(Exception):
    """Base class for all API errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseAPIError):
    """Error for validation failures."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundError(BaseAPIError):
    """Error for resource not found."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier}
        )


class DatabaseError(BaseAPIError):
    """Error for database operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Database error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class CacheError(BaseAPIError):
    """Error for cache operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Cache error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ExternalServiceError(BaseAPIError):
    """Error for external service failures."""
    
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"External service '{service}' error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service, **(details or {})}
        )


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str


def create_error_response(
    error: BaseAPIError,
    timestamp: str
) -> ErrorResponse:
    """Create a standardized error response."""
    logger.error(f"API Error: {error.message}", extra={
        "status_code": error.status_code,
        "details": error.details
    })
    
    return ErrorResponse(
        error=error.__class__.__name__,
        message=error.message,
        details=error.details,
        timestamp=timestamp
    )


def create_http_exception(error: BaseAPIError) -> HTTPException:
    """Convert custom error to HTTPException."""
    return HTTPException(
        status_code=error.status_code,
        detail=create_error_response(error, "").dict()
    )


def handle_database_error(error: Exception, operation: str) -> DatabaseError:
    """Handle database errors with proper logging."""
    logger.error(f"Database error during {operation}: {str(error)}", exc_info=True)
    return DatabaseError(
        message=f"Failed to {operation}",
        details={"original_error": str(error)}
    )


def handle_cache_error(error: Exception, operation: str) -> CacheError:
    """Handle cache errors with proper logging."""
    logger.error(f"Cache error during {operation}: {str(error)}", exc_info=True)
    return CacheError(
        message=f"Failed to {operation}",
        details={"original_error": str(error)}
    )


def validate_required_fields(data: Dict[str, Any], required_fields: list[str]) -> None:
    """Validate that required fields are present in data."""
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )


def validate_positive_integer(value: Any, field_name: str) -> int:
    """Validate that a value is a positive integer."""
    try:
        int_value = int(value)
        if int_value <= 0:
            raise ValidationError(
                message=f"{field_name} must be a positive integer",
                details={"field": field_name, "value": value}
            )
        return int_value
    except (ValueError, TypeError):
        raise ValidationError(
            message=f"{field_name} must be a valid integer",
            details={"field": field_name, "value": value}
        )


def validate_string_length(value: str, field_name: str, min_length: int = 1, max_length: Optional[int] = None) -> str:
    """Validate string length constraints."""
    if not isinstance(value, str):
        raise ValidationError(
            message=f"{field_name} must be a string",
            details={"field": field_name, "value": value}
        )
    
    if len(value) < min_length:
        raise ValidationError(
            message=f"{field_name} must be at least {min_length} characters long",
            details={"field": field_name, "value": value, "min_length": min_length}
        )
    
    if max_length and len(value) > max_length:
        raise ValidationError(
            message=f"{field_name} must be no more than {max_length} characters long",
            details={"field": field_name, "value": value, "max_length": max_length}
        )
    
    return value


def validate_camera_name(camera_name: str, valid_cameras: list[str]) -> str:
    """Validate camera name against list of valid cameras."""
    if camera_name not in valid_cameras:
        raise NotFoundError(
            resource="Camera",
            identifier=camera_name
        )
    return camera_name


def validate_employee_name(employee_name: str) -> str:
    """Validate employee name format and constraints."""
    return validate_string_length(
        value=employee_name,
        field_name="employee_name",
        min_length=2,
        max_length=100
    )


def validate_hours_range(hours: int) -> int:
    """Validate hours parameter is within acceptable range."""
    if hours < 1:
        raise ValidationError(
            message="Hours must be greater than 0",
            details={"field": "hours", "value": hours, "min_value": 1}
        )
    
    if hours > 168:  # 1 week
        raise ValidationError(
            message="Hours cannot exceed 168 (1 week)",
            details={"field": "hours", "value": hours, "max_value": 168}
        )
    
    return hours


def validate_limit_range(limit: int) -> int:
    """Validate limit parameter is within acceptable range."""
    if limit < 1:
        raise ValidationError(
            message="Limit must be greater than 0",
            details={"field": "limit", "value": limit, "min_value": 1}
        )
    
    if limit > 1000:
        raise ValidationError(
            message="Limit cannot exceed 1000",
            details={"field": "limit", "value": limit, "max_value": 1000}
        )
    
    return limit
