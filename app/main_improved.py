"""
Main FastAPI application following best practices.

This module sets up the FastAPI application with all routers,
middleware, CORS configuration, and lifespan management following
FastAPI best practices from awesome-cursorrules.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
import time
import json
import yaml

from .config_improved import settings
from .database import db_manager
from .cache import cache_manager
from .routers import violations, employees, cameras, websocket
from .services.background import start_background_tasks, stop_background_tasks
from .utils.response_formatter import create_error_json_response, create_json_response
from .utils.errors import (
    BaseAPIError,
    ValidationError,
    DatabaseError,
    CacheError,
    create_error_response,
    handle_database_error,
    handle_cache_error
)
from .utils.time import timestamp_to_iso

# Configure logging with improved settings
logging.basicConfig(
    level=getattr(logging, settings.logging.level),
    format=settings.logging.format,
    filename=settings.logging.file_path
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with proper error handling.
    
    Handles startup and shutdown events for the FastAPI application,
    including database and cache initialization with comprehensive
    error handling and logging.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}...")
    
    try:
        # Initialize database connection pool with error handling
        await db_manager.initialize()
        logger.info("Database connection pool initialized successfully")
        
        # Initialize Redis cache with error handling
        await cache_manager.initialize()
        logger.info("Redis cache initialized successfully")
        
        # Start background tasks with error handling
        await start_background_tasks()
        logger.info("Background tasks started successfully")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    try:
        # Stop background tasks
        await stop_background_tasks()
        logger.info("Background tasks stopped successfully")
        
        # Close cache connections
        await cache_manager.close()
        logger.info("Cache connections closed successfully")
        
        # Close database connections
        await db_manager.close()
        logger.info("Database connections closed successfully")
        
        logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}", exc_info=True)


# Create FastAPI application with improved configuration
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Middleware service for Frigate surveillance dashboard with real-time phone violation detection",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware with improved configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware with improved configuration
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.security.allowed_hosts
)


# Request timing middleware with improved error handling
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Add processing time to response headers with error handling.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware in chain
        
    Returns:
        Response with timing header
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Error in request processing: {e}", exc_info=True)
        process_time = time.time() - start_time
        error_response = create_error_json_response(
            message="Internal server error during request processing",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"processing_time": process_time}
        )
        error_response.headers["X-Process-Time"] = str(process_time)
        return error_response


# Global exception handlers with improved error handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors with improved formatting.
    
    Args:
        request: FastAPI request object
        exc: Validation error exception
        
    Returns:
        JSONResponse with validation error details
    """
    logger.warning(f"Validation error on {request.url}: {exc}")
    
    return create_error_json_response(
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={
            "validation_errors": exc.errors(),
            "request_url": str(request.url),
            "request_method": request.method
        }
    )


@app.exception_handler(BaseAPIError)
async def api_error_handler(request: Request, exc: BaseAPIError):
    """
    Handle custom API errors with proper logging.
    
    Args:
        request: FastAPI request object
        exc: Custom API error
        
    Returns:
        JSONResponse with error details
    """
    logger.error(f"API error on {request.url}: {exc.message}", extra={
        "status_code": exc.status_code,
        "details": exc.details
    })
    
    return create_error_json_response(
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle general exceptions with improved error handling.
    
    Args:
        request: FastAPI request object
        exc: General exception
        
    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    
    error_details = {
        "request_url": str(request.url),
        "request_method": request.method,
        "error_type": type(exc).__name__
    }
    
    if settings.debug:
        error_details["error_message"] = str(exc)
        error_details["traceback"] = str(exc.__traceback__)
    
    return create_error_json_response(
        message="Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=error_details
    )


# Include routers with improved error handling
try:
    app.include_router(violations.router)
    app.include_router(employees.router)
    app.include_router(cameras.router)
    app.include_router(websocket.router)
    logger.info("All routers included successfully")
except Exception as e:
    logger.error(f"Failed to include routers: {e}", exc_info=True)
    raise


# Root endpoint with improved response formatting
@app.get("/", tags=["root"])
async def root() -> JSONResponse:
    """
    Root endpoint with comprehensive API information.
    
    Returns:
        JSONResponse with API information and metadata
    """
    try:
        api_info = {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": "Frigate Dashboard Middleware API with real-time surveillance capabilities",
            "docs_url": "/docs",
            "health_url": "/health",
            "features": [
                "Real-time phone violation detection",
                "Employee identification via face recognition",
                "Hourly trend analysis",
                "Camera activity monitoring",
                "WebSocket real-time updates",
                "Redis caching for performance",
                "Comprehensive API documentation"
            ],
            "endpoints": {
                "violations": "/api/violations/*",
                "employees": "/api/employees/*",
                "cameras": "/api/cameras/*",
                "websocket": "/ws/*"
            },
            "timestamp": timestamp_to_iso(time.time())
        }
        
        return create_json_response(
            data=api_info,
            message="API information retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error in root endpoint: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to retrieve API information",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Health check endpoint with improved error handling
@app.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    """
    Comprehensive health check endpoint with detailed status information.
    
    Returns:
        JSONResponse with health status and service details
    """
    try:
        # Check database health with error handling
        try:
            db_healthy = await db_manager.health_check()
            db_status = "healthy" if db_healthy else "unhealthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_healthy = False
            db_status = "error"
        
        # Check Redis health with error handling
        try:
            redis_healthy = await cache_manager.health_check()
            redis_status = "healthy" if redis_healthy else "unhealthy"
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            redis_healthy = False
            redis_status = "error"
        
        # Determine overall health
        overall_healthy = db_healthy and redis_healthy
        status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        health_data = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": timestamp_to_iso(time.time()),
            "services": {
                "database": {
                    "status": db_status,
                    "host": settings.database.host,
                    "port": settings.database.port,
                    "name": settings.database.name
                },
                "cache": {
                    "status": redis_status,
                    "host": settings.cache.host,
                    "port": settings.cache.port,
                    "db": settings.cache.db
                }
            },
            "configuration": {
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "debug_mode": settings.debug,
                "timezone": settings.timezone
            }
        }
        
        return JSONResponse(
            content=create_json_response(
                data=health_data,
                message="Health check completed"
            ).get("data"),
            status_code=status_code
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return create_error_json_response(
            message="Health check failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"error": str(e)}
        )


# API info endpoint with improved formatting
@app.get("/api/info", tags=["info"])
async def api_info() -> JSONResponse:
    """
    Comprehensive API information endpoint.
    
    Returns:
        JSONResponse with detailed API information
    """
    try:
        api_data = {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": "Middleware service for Frigate surveillance dashboard",
            "endpoints": [
                "/api/violations/live",
                "/api/violations/hourly-trend",
                "/api/violations/stats",
                "/api/employees/stats",
                "/api/employees/search",
                "/api/employees/{employee_name}/violations",
                "/api/employees/{employee_name}/activity",
                "/api/cameras/summary",
                "/api/cameras/{camera_name}/activity",
                "/api/cameras/{camera_name}/violations",
                "/api/cameras/{camera_name}/status",
                "/ws/violations",
                "/ws/status"
            ],
            "features": [
                "Real-time phone violation detection",
                "Employee identification via face recognition",
                "Hourly trend analysis",
                "Camera activity monitoring",
                "WebSocket real-time updates",
                "Redis caching for performance",
                "Comprehensive API documentation"
            ],
            "configuration": {
                "cameras": settings.cameras,
                "timezone": settings.timezone,
                "cache_ttl": {
                    "live_violations": settings.cache_ttl.live_violations,
                    "hourly_trend": settings.cache_ttl.hourly_trend,
                    "violation_stats": settings.cache_ttl.violation_stats
                }
            },
            "timestamp": timestamp_to_iso(time.time())
        }
        
        return create_json_response(
            data=api_data,
            message="API information retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving API info: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to retrieve API information",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Cache statistics endpoint with improved error handling
@app.get("/api/cache/stats", tags=["cache"])
async def cache_stats() -> JSONResponse:
    """
    Get comprehensive cache statistics with error handling.
    
    Returns:
        JSONResponse with cache statistics
    """
    try:
        from .cache import CacheUtils
        stats = await CacheUtils.get_cache_stats()
        
        return create_json_response(
            data=stats,
            message="Cache statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to retrieve cache statistics",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error": str(e)}
        )


# System status endpoint with improved error handling
@app.get("/api/status", tags=["admin"])
async def system_status() -> JSONResponse:
    """
    Get comprehensive system status including background tasks.
    
    Returns:
        JSONResponse with system status information
    """
    try:
        from .services.background import get_background_status
        from .utils.time import get_current_timestamp
        
        # Get background task status
        bg_status = await get_background_status()
        
        # Get database and cache health
        db_health = await db_manager.health_check()
        cache_health = await cache_manager.health_check()
        
        status_data = {
            "status": "healthy" if db_health and cache_health else "degraded",
            "timestamp": timestamp_to_iso(get_current_timestamp()),
            "database": {
                "status": "healthy" if db_health else "unhealthy",
                "pool_size": db_manager.pool.get_size() if db_manager.pool else 0,
                "host": settings.database.host,
                "port": settings.database.port
            },
            "cache": {
                "status": "healthy" if cache_health else "unhealthy",
                "connected": cache_manager.redis is not None,
                "host": settings.cache.host,
                "port": settings.cache.port
            },
            "background_tasks": bg_status,
            "configuration": {
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "debug_mode": settings.debug,
                "timezone": settings.timezone
            }
        }
        
        return create_json_response(
            data=status_data,
            message="System status retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to retrieve system status",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error": str(e)}
        )


# Admin endpoint to restart background tasks with improved error handling
@app.post("/api/admin/restart-task/{task_name}", tags=["admin"])
async def restart_background_task(task_name: str) -> JSONResponse:
    """
    Restart a specific background task with validation.
    
    Args:
        task_name: Name of the task to restart
        
    Returns:
        JSONResponse with operation result
    """
    try:
        from .services.background import restart_background_task
        
        # Validate task name
        valid_tasks = ["violation_polling", "stats_refresh", "cache_cleanup", "health_check"]
        if task_name not in valid_tasks:
            return create_error_json_response(
                message=f"Invalid task name. Valid tasks: {', '.join(valid_tasks)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        await restart_background_task(task_name)
        
        return create_json_response(
            data={"task_name": task_name, "status": "restarted"},
            message=f"Task {task_name} restarted successfully"
        )
        
    except ValueError as e:
        return create_error_json_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error restarting task {task_name}: {e}", exc_info=True)
        return create_error_json_response(
            message=f"Failed to restart task {task_name}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error": str(e)}
        )


# Documentation download endpoints with improved error handling
@app.get("/docs/download/openapi.json", tags=["docs"])
async def download_openapi_json() -> Response:
    """
    Download OpenAPI specification in JSON format with error handling.
    
    Returns:
        Response with OpenAPI JSON file
    """
    try:
        openapi_schema = app.openapi()
        json_content = json.dumps(openapi_schema, indent=2)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=frigate-middleware-openapi.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating OpenAPI JSON: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to generate OpenAPI JSON",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get("/docs/download/openapi.yaml", tags=["docs"])
async def download_openapi_yaml() -> Response:
    """
    Download OpenAPI specification in YAML format with error handling.
    
    Returns:
        Response with OpenAPI YAML file
    """
    try:
        openapi_schema = app.openapi()
        yaml_content = yaml.dump(openapi_schema, default_flow_style=False, sort_keys=False)
        
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": "attachment; filename=frigate-middleware-openapi.yaml"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating OpenAPI YAML: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to generate OpenAPI YAML",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Postman collection download endpoint
@app.get("/docs/download/postman.json", tags=["docs"])
async def download_postman_collection() -> Response:
    """
    Download Postman collection for API testing with error handling.
    
    Returns:
        Response with Postman collection JSON file
    """
    try:
        openapi_schema = app.openapi()
        
        # Convert OpenAPI to Postman collection format
        postman_collection = {
            "info": {
                "name": f"{settings.app_name} API Collection",
                "description": "Complete API collection for Frigate Dashboard Middleware",
                "version": settings.app_version,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost:5002",
                    "type": "string"
                }
            ]
        }
        
        # Add endpoints to collection
        for path, methods in openapi_schema.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                    item = {
                        "name": details.get("summary", f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "url": {
                                "raw": "{{base_url}}" + path,
                                "host": ["{{base_url}}"],
                                "path": path.strip("/").split("/")
                            },
                            "description": details.get("description", "")
                        }
                    }
                    postman_collection["item"].append(item)
        
        json_content = json.dumps(postman_collection, indent=2)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=frigate-middleware-postman.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating Postman collection: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to generate Postman collection",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Insomnia collection download endpoint
@app.get("/docs/download/insomnia.json", tags=["docs"])
async def download_insomnia_collection() -> Response:
    """
    Download Insomnia collection for API testing with error handling.
    
    Returns:
        Response with Insomnia collection JSON file
    """
    try:
        openapi_schema = app.openapi()
        
        # Convert OpenAPI to Insomnia collection format
        insomnia_collection = {
            "_type": "export",
            "__export_format": 4,
            "__export_date": timestamp_to_iso(time.time()),
            "__export_source": f"{settings.app_name} v{settings.app_version}",
            "resources": [
                {
                    "_id": "req_000000000000000000000000",
                    "parentId": "fld_000000000000000000000000",
                    "modified": int(time.time() * 1000),
                    "created": int(time.time() * 1000),
                    "url": "{{ _.base_url }}",
                    "name": "Base URL",
                    "description": "Base URL for all API requests",
                    "method": "GET",
                    "body": {},
                    "parameters": [],
                    "headers": [],
                    "authentication": {},
                    "metaSortKey": -1000000000000,
                    "isPrivate": False,
                    "settingStoreCookies": True,
                    "settingSendCookies": True,
                    "settingDisableRenderRequestBody": False,
                    "settingEncodeUrl": True,
                    "settingRebuildPath": True,
                    "settingFollowRedirects": "global",
                    "_type": "request"
                }
            ]
        }
        
        json_content = json.dumps(insomnia_collection, indent=2)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=frigate-middleware-insomnia.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating Insomnia collection: {e}", exc_info=True)
        return create_error_json_response(
            message="Failed to generate Insomnia collection",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Log application startup
logger.info(f"{settings.app_name} v{settings.app_version} initialized successfully")
logger.info(f"Debug mode: {settings.debug}")
logger.info(f"Timezone: {settings.timezone}")
logger.info(f"Database: {settings.database.host}:{settings.database.port}/{settings.database.name}")
logger.info(f"Cache: {settings.cache.host}:{settings.cache.port}")
logger.info(f"Video API: {settings.video_api.base_url}")

