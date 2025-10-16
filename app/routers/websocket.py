"""
WebSocket endpoints for the Frigate Dashboard Middleware.

This module provides WebSocket endpoints for real-time violation monitoring
and live updates to connected clients.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.websockets import WebSocketState

from ..database import DatabaseManager
from ..cache import CacheManager
from ..dependencies import DatabaseDep, CacheDep
from ..models import ViolationData, WebSocketMessage
from ..utils.formatting import format_violation_data
from ..services.queries import ViolationQueries
from ..utils.time import get_current_timestamp, get_timestamp_ago
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

# Global connection manager
class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""
    
    def __init__(self):
        # Active connections by client type
        self.violation_connections: Set[WebSocket] = set()
        self.dashboard_connections: Set[WebSocket] = set()
        self.all_connections: Set[WebSocket] = set()
        
        # Background task for polling
        self.polling_task: asyncio.Task = None
        self.is_polling = False
        
    async def connect(self, websocket: WebSocket, client_type: str = "dashboard"):
        """Accept a WebSocket connection and add to appropriate group."""
        await websocket.accept()
        
        if client_type == "violations":
            self.violation_connections.add(websocket)
        else:
            self.dashboard_connections.add(websocket)
        
        self.all_connections.add(websocket)
        
        logger.info(f"WebSocket connected: {client_type} (total: {len(self.all_connections)})")
        
        # Start polling if not already running
        if not self.is_polling and len(self.all_connections) > 0:
            await self.start_polling()
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from all groups."""
        self.violation_connections.discard(websocket)
        self.dashboard_connections.discard(websocket)
        self.all_connections.discard(websocket)
        
        logger.info(f"WebSocket disconnected (total: {len(self.all_connections)})")
        
        # Stop polling if no connections
        if len(self.all_connections) == 0 and self.is_polling:
            asyncio.create_task(self.stop_polling())
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_violations(self, message: dict):
        """Broadcast a message to all violation monitoring connections."""
        if not self.violation_connections:
            return
        
        disconnected = set()
        for connection in self.violation_connections.copy():
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(json.dumps(message))
                else:
                    disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to violation connection: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_dashboard(self, message: dict):
        """Broadcast a message to all dashboard connections."""
        if not self.dashboard_connections:
            return
        
        disconnected = set()
        for connection in self.dashboard_connections.copy():
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(json.dumps(message))
                else:
                    disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to dashboard connection: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connections."""
        await self.broadcast_to_violations(message)
        await self.broadcast_to_dashboard(message)
    
    async def start_polling(self):
        """Start background polling for new violations."""
        if self.is_polling:
            return
        
        self.is_polling = True
        self.polling_task = asyncio.create_task(self._poll_violations())
        logger.info("Started violation polling")
    
    async def stop_polling(self):
        """Stop background polling."""
        if not self.is_polling:
            return
        
        self.is_polling = False
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped violation polling")
    
    async def _poll_violations(self):
        """Background task to poll for new violations."""
        last_check = get_current_timestamp()
        
        while self.is_polling:
            try:
                # Get database and cache managers
                db_manager = DatabaseManager()
                cache_manager = CacheManager()
                
                # Initialize if needed
                if not db_manager.pool:
                    await db_manager.initialize()
                if not cache_manager.redis:
                    await cache_manager.initialize()
                
                # Check for new violations in the last 5 seconds
                current_time = get_current_timestamp()
                violations = await ViolationQueries.get_live_violations(
                    db=db_manager,
                    hours=1,  # Look back 1 hour
                    limit=100
                )
                
                # Filter for violations since last check
                new_violations = [
                    v for v in violations 
                    if v.get('timestamp', 0) > last_check
                ]
                
                if new_violations:
                    logger.info(f"Found {len(new_violations)} new violations")
                    
                    # Format violations
                    formatted_violations = [
                        format_violation_data(violation) 
                        for violation in new_violations
                    ]
                    
                    # Create WebSocket message
                    message = WebSocketMessage(
                        type="new_violations",
                        data={
                            "violations": formatted_violations,
                            "count": len(formatted_violations),
                            "timestamp": current_time
                        }
                    )
                    
                    # Broadcast to violation monitoring connections
                    await self.broadcast_to_violations(message.dict())
                    
                    # Also broadcast summary to dashboard connections
                    summary_message = WebSocketMessage(
                        type="violation_summary",
                        data={
                            "new_violations_count": len(formatted_violations),
                            "timestamp": current_time
                        }
                    )
                    await self.broadcast_to_dashboard(summary_message.dict())
                
                last_check = current_time
                
                # Clean up managers
                await db_manager.close()
                await cache_manager.close()
                
            except Exception as e:
                logger.error(f"Error in violation polling: {e}")
            
            # Wait before next poll
            await asyncio.sleep(settings.websocket_poll_interval)
        
        logger.info("Violation polling stopped")

# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/violations")
async def websocket_violations(
    websocket: WebSocket,
    camera: str = Query(None, description="Filter by specific camera"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """
    WebSocket endpoint for real-time violation monitoring.
    
    This endpoint provides real-time updates for phone violations including:
    - New violations as they occur
    - Employee identification
    - Camera information
    - Media URLs
    
    Args:
        websocket: WebSocket connection
        camera: Optional camera filter
        hours: Hours to look back for initial data
    """
    await manager.connect(websocket, "violations")
    
    try:
        # Send initial data
        db_manager = DatabaseManager()
        cache_manager = CacheManager()
        
        # Initialize managers
        await db_manager.initialize()
        await cache_manager.initialize()
        
        # Get recent violations
        violations = await ViolationQueries.get_live_violations(
            db=db_manager,
            camera=camera,
            hours=hours,
            limit=50
        )
        
        # Format violations
        formatted_violations = [
            format_violation_data(violation) 
            for violation in violations
        ]
        
        # Send initial data
        initial_message = WebSocketMessage(
            type="initial_data",
            data={
                "violations": formatted_violations,
                "count": len(formatted_violations),
                "camera_filter": camera,
                "hours": hours,
                "timestamp": get_current_timestamp()
            }
        )
        
        await manager.send_personal_message(initial_message.dict(), websocket)
        
        # Clean up managers
        await db_manager.close()
        await cache_manager.close()
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages (ping/pong, filters, etc.)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    pong_message = WebSocketMessage(
                        type="pong",
                        data={"timestamp": get_current_timestamp()}
                    )
                    await manager.send_personal_message(pong_message.dict(), websocket)
                
                elif message.get("type") == "update_filter":
                    # Handle filter updates (camera, hours, etc.)
                    new_camera = message.get("data", {}).get("camera")
                    new_hours = message.get("data", {}).get("hours", 24)
                    
                    # Get filtered violations
                    db_manager = DatabaseManager()
                    await db_manager.initialize()
                    
                    filtered_violations = await ViolationQueries.get_live_violations(
                        db=db_manager,
                        camera=new_camera,
                        hours=new_hours,
                        limit=50
                    )
                    
                    formatted_filtered = [
                        format_violation_data(violation) 
                        for violation in filtered_violations
                    ]
                    
                    filter_message = WebSocketMessage(
                        type="filtered_data",
                        data={
                            "violations": formatted_filtered,
                            "count": len(formatted_filtered),
                            "camera_filter": new_camera,
                            "hours": new_hours,
                            "timestamp": get_current_timestamp()
                        }
                    )
                    
                    await manager.send_personal_message(filter_message.dict(), websocket)
                    await db_manager.close()
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON from WebSocket client")
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


@router.websocket("/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    subscribe_to: str = Query("all", description="Subscribe to: all, violations, cameras, employees")
):
    """
    WebSocket endpoint for dashboard updates.
    
    This endpoint provides real-time updates for dashboard components including:
    - Violation summaries
    - Camera status updates
    - Employee activity
    - System health
    
    Args:
        websocket: WebSocket connection
        subscribe_to: What to subscribe to (all, violations, cameras, employees)
    """
    await manager.connect(websocket, "dashboard")
    
    try:
        # Send initial dashboard data
        db_manager = DatabaseManager()
        cache_manager = CacheManager()
        
        # Initialize managers
        await db_manager.initialize()
        await cache_manager.initialize()
        
        # Get initial dashboard data based on subscription
        initial_data = {}
        
        if subscribe_to in ["all", "violations"]:
            # Get recent violations summary
            violations = await ViolationQueries.get_live_violations(
                db=db_manager,
                hours=24,
                limit=10
            )
            initial_data["violations"] = {
                "recent": [format_violation_data(v) for v in violations[:5]],
                "total_24h": len(violations),
                "timestamp": get_current_timestamp()
            }
        
        if subscribe_to in ["all", "cameras"]:
            # Get camera summaries
            from ..services.queries import CameraQueries
            from ..utils.formatting import format_camera_summary
            camera_summaries = []
            for camera in settings.CAMERAS[:5]:  # Top 5 cameras
                try:
                    summary = await CameraQueries.get_camera_summary(db=db_manager, camera=camera)
                    if summary:
                        camera_summaries.append(format_camera_summary(summary))
                except Exception as e:
                    logger.warning(f"Failed to get camera summary for {camera}: {e}")
            
            initial_data["cameras"] = {
                "summaries": camera_summaries,
                "timestamp": get_current_timestamp()
            }
        
        if subscribe_to in ["all", "employees"]:
            # Get employee activity summary
            from ..services.queries import EmployeeQueries
            from ..utils.formatting import format_employee_stats
            
            employee_stats = await EmployeeQueries.get_employee_stats(
                db=db_manager,
                hours=24
            )
            
            initial_data["employees"] = {
                "stats": [format_employee_stats(stat) for stat in employee_stats[:10]],
                "timestamp": get_current_timestamp()
            }
        
        # Send initial data
        initial_message = WebSocketMessage(
            type="dashboard_data",
            data=initial_data
        )
        
        await manager.send_personal_message(initial_message.dict(), websocket)
        
        # Clean up managers
        await db_manager.close()
        await cache_manager.close()
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping/pong
                if message.get("type") == "ping":
                    pong_message = WebSocketMessage(
                        type="pong",
                        data={"timestamp": get_current_timestamp()}
                    )
                    await manager.send_personal_message(pong_message.dict(), websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON from dashboard WebSocket client")
            except Exception as e:
                logger.error(f"Error handling dashboard WebSocket message: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


@router.get(
    "/status",
    summary="Get WebSocket status",
    description="Get current WebSocket connection status and statistics"
)
async def get_websocket_status() -> dict:
    """
    Get current WebSocket connection status.
    
    Returns:
        Dictionary with connection statistics
    """
    return {
        "total_connections": len(manager.all_connections),
        "violation_connections": len(manager.violation_connections),
        "dashboard_connections": len(manager.dashboard_connections),
        "is_polling": manager.is_polling,
        "polling_interval": settings.websocket_poll_interval
    }


@router.post(
    "/broadcast",
    summary="Broadcast message",
    description="Broadcast a message to all connected WebSocket clients"
)
async def broadcast_message(
    message_type: str,
    data: dict,
    target: str = "all"
) -> dict:
    """
    Broadcast a message to WebSocket clients.
    
    Args:
        message_type: Type of message to broadcast
        data: Message data
        target: Target audience (all, violations, dashboard)
        
    Returns:
        Confirmation of broadcast
    """
    try:
        message = WebSocketMessage(
            type=message_type,
            data=data,
            timestamp=str(get_current_timestamp())
        )
        
        if target == "violations":
            await manager.broadcast_to_violations(message.dict())
        elif target == "dashboard":
            await manager.broadcast_to_dashboard(message.dict())
        else:
            await manager.broadcast_to_all(message.dict())
        
        return {
            "success": True,
            "message": f"Broadcasted {message_type} to {target}",
            "connections": len(manager.all_connections)
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        return {
            "success": False,
            "error": str(e)
        }
