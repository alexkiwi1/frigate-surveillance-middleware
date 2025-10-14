"""
Main FastAPI application for the Frigate Dashboard Middleware.

This module sets up the FastAPI application with all routers,
middleware, CORS configuration, and lifespan management.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
import time
import json
import yaml

from .config import settings
from .database import db_manager
from .cache import cache_manager
from .routers import violations, employees, cameras, websocket
from .services.background import start_background_tasks, stop_background_tasks
from .utils.formatting import format_error_response
from .utils.time import timestamp_to_iso

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application,
    including database and cache initialization.
    """
    # Startup
    logger.info("Starting Frigate Dashboard Middleware...")
    
    try:
        # Initialize database connection pool
        await db_manager.initialize()
        logger.info("Database connection pool initialized")
        
        # Initialize Redis cache
        await cache_manager.initialize()
        logger.info("Redis cache initialized")
        
        # Start background tasks
        await start_background_tasks()
        logger.info("Background tasks started")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Frigate Dashboard Middleware...")
    
    try:
        # Close database connections
        await db_manager.close()
        logger.info("Database connections closed")
        
        # Close Redis connections
        await cache_manager.close()
        logger.info("Redis connections closed")
        
        # Stop background tasks
        await stop_background_tasks()
        logger.info("Background tasks stopped")
        
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Middleware service for Frigate surveillance dashboard with real-time violation monitoring",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response(
            "Request validation failed",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"validation_errors": exc.errors()}
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            "Internal server error",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": str(exc)} if settings.debug else None
        )
    )


# Include routers
app.include_router(violations.router)
app.include_router(employees.router)
app.include_router(cameras.router)
app.include_router(websocket.router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Frigate Dashboard Middleware API",
        "docs_url": "/docs",
        "health_url": "/health",
        "timestamp": timestamp_to_iso(time.time())
    }


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    try:
        # Check database health
        db_healthy = await db_manager.health_check()
        
        # Check Redis health
        redis_healthy = await cache_manager.health_check()
        
        # Determine overall health
        overall_healthy = db_healthy and redis_healthy
        status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if overall_healthy else "unhealthy",
                "database": "healthy" if db_healthy else "unhealthy",
                "redis": "healthy" if redis_healthy else "unhealthy",
                "timestamp": timestamp_to_iso(time.time())
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": timestamp_to_iso(time.time())
            }
        )


# API info endpoint
@app.get("/api/info", tags=["info"])
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Middleware service for Frigate surveillance dashboard",
        "endpoints": [
            "/api/violations/live",
            "/api/violations/hourly-trend",
            "/api/employees/stats",
            "/api/employees/{employee_name}/violations",
            "/api/cameras/summary",
            "/api/cameras/{camera_name}/activity",
            "/api/dashboard/overview",
            "/ws/violations"
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
        "timestamp": timestamp_to_iso(time.time())
    }


# Cache statistics endpoint
@app.get("/api/cache/stats", tags=["cache"])
async def cache_stats():
    """Get cache statistics."""
    try:
        from .cache import CacheUtils
        stats = await CacheUtils.get_cache_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": timestamp_to_iso(time.time())
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=format_error_response(
                "Failed to retrieve cache statistics",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"error": str(e)}
            )
        )


# System status endpoint
@app.get("/api/status", tags=["admin"])
async def system_status():
    """Get system status including background tasks."""
    from .services.background import get_background_status
    from .utils.time import get_current_timestamp
    
    try:
        # Get background task status
        bg_status = await get_background_status()
        
        # Get database and cache health
        db_health = await db_manager.health_check()
        cache_health = await cache_manager.health_check()
        
        return {
            "status": "healthy" if db_health and cache_health else "degraded",
            "timestamp": timestamp_to_iso(get_current_timestamp()),
            "database": {
                "status": "healthy" if db_health else "unhealthy",
                "pool_size": db_manager.pool.get_size() if db_manager.pool else 0
            },
            "cache": {
                "status": "healthy" if cache_health else "unhealthy",
                "connected": cache_manager.redis is not None
            },
            "background_tasks": bg_status,
            "uptime": "unknown"  # Could calculate from start time
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": timestamp_to_iso(get_current_timestamp())
        }


# Admin endpoint to restart background tasks
@app.post("/api/admin/restart-task/{task_name}", tags=["admin"])
async def restart_background_task(task_name: str):
    """Restart a specific background task."""
    from .services.background import restart_background_task
    
    try:
        await restart_background_task(task_name)
        return {
            "success": True,
            "message": f"Task {task_name} restarted successfully"
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error restarting task {task_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/docs/download/openapi.json", tags=["docs"])
async def download_openapi_json():
    """
    Download OpenAPI specification in JSON format.
    
    Returns:
        OpenAPI JSON file for download
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
        logger.error(f"Error generating OpenAPI JSON: {e}")
        return JSONResponse(
            content={"error": "Failed to generate OpenAPI JSON"},
            status_code=500
        )


@app.get("/docs/download/openapi.yaml", tags=["docs"])
async def download_openapi_yaml():
    """
    Download OpenAPI specification in YAML format.
    
    Returns:
        OpenAPI YAML file for download
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
        logger.error(f"Error generating OpenAPI YAML: {e}")
        return JSONResponse(
            content={"error": "Failed to generate OpenAPI YAML"},
            status_code=500
        )


@app.get("/docs/download/postman.json", tags=["docs"])
async def download_postman_collection():
    """
    Download Postman collection for API testing.
    
    Returns:
        Postman collection JSON file for download
    """
    try:
        openapi_schema = app.openapi()
        
        # Convert OpenAPI to Postman collection format
        postman_collection = {
            "info": {
                "name": openapi_schema.get("info", {}).get("title", "Frigate Middleware API"),
                "description": openapi_schema.get("info", {}).get("description", ""),
                "version": openapi_schema.get("info", {}).get("version", "1.0.0"),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "variable": [
                {
                    "key": "baseUrl",
                    "value": f"http://{settings.host}:{settings.port}",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # Convert paths to Postman requests
        for path, methods in openapi_schema.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    request_item = {
                        "name": details.get("summary", f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}" + path,
                                "host": ["{{baseUrl}}"],
                                "path": path.strip("/").split("/")
                            },
                            "description": details.get("description", "")
                        },
                        "response": []
                    }
                    
                    # Add parameters if they exist
                    if "parameters" in details:
                        query_params = []
                        for param in details["parameters"]:
                            if param.get("in") == "query":
                                query_params.append({
                                    "key": param.get("name"),
                                    "value": "",
                                    "description": param.get("description", "")
                                })
                        if query_params:
                            request_item["request"]["url"]["query"] = query_params
                    
                    postman_collection["item"].append(request_item)
        
        json_content = json.dumps(postman_collection, indent=2)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=frigate-middleware-postman.json"
            }
        )
    except Exception as e:
        logger.error(f"Error generating Postman collection: {e}")
        return JSONResponse(
            content={"error": "Failed to generate Postman collection"},
            status_code=500
        )


@app.get("/docs/download/insomnia.json", tags=["docs"])
async def download_insomnia_collection():
    """
    Download Insomnia collection for API testing.
    
    Returns:
        Insomnia collection JSON file for download
    """
    try:
        openapi_schema = app.openapi()
        
        # Convert OpenAPI to Insomnia collection format
        insomnia_collection = {
            "_type": "export",
            "__export_format": 4,
            "__export_date": timestamp_to_iso(time.time()),
            "__export_source": "frigate-middleware-api",
            "resources": [
                {
                    "_id": "req_base_url",
                    "_type": "environment",
                    "name": "Base Environment",
                    "data": {
                        "base_url": f"http://{settings.host}:{settings.port}"
                    }
                }
            ]
        }
        
        # Add requests
        request_id = 1
        for path, methods in openapi_schema.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    request_resource = {
                        "_id": f"req_{request_id}",
                        "_type": "request",
                        "name": details.get("summary", f"{method.upper()} {path}"),
                        "description": details.get("description", ""),
                        "url": "{{ _.base_url }}" + path,
                        "method": method.upper(),
                        "body": {},
                        "parameters": [],
                        "headers": [],
                        "authentication": {},
                        "data": {}
                    }
                    
                    # Add query parameters
                    if "parameters" in details:
                        for param in details["parameters"]:
                            if param.get("in") == "query":
                                request_resource["parameters"].append({
                                    "name": param.get("name"),
                                    "value": "",
                                    "description": param.get("description", ""),
                                    "disabled": False
                                })
                    
                    insomnia_collection["resources"].append(request_resource)
                    request_id += 1
        
        json_content = json.dumps(insomnia_collection, indent=2)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=frigate-middleware-insomnia.json"
            }
        )
    except Exception as e:
        logger.error(f"Error generating Insomnia collection: {e}")
        return JSONResponse(
            content={"error": "Failed to generate Insomnia collection"},
            status_code=500
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
