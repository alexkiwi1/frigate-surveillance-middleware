# Frigate Surveillance Dashboard Middleware - API Documentation

## Overview

The Frigate Surveillance Dashboard Middleware provides a comprehensive REST API and WebSocket interface for monitoring phone violations, employee activity, and camera status in a surveillance system. This document provides detailed information about all available endpoints, request/response formats, and usage examples.

## Base URL

```
http://localhost:5002
```

## Authentication

Currently, no authentication is required. All endpoints are publicly accessible within the internal network.

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00+05:00"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "status_code": 500,
  "details": { ... }
}
```

## Endpoints

### 1. Violations

#### GET /api/violations/live
Get recent phone violations with employee identification.

**Query Parameters:**
- `camera` (optional): Filter by specific camera
- `hours` (optional): Hours to look back (1-168, default 24)
- `limit` (optional): Maximum results (1-1000, default 50)

**Response:**
```json
{
  "success": true,
  "data": {
    "violations": [
      {
        "id": "0sy0od",
        "timestamp": 1705312200.182961,
        "camera": "employees_01",
        "employee_name": "John Doe",
        "confidence": 0.95,
        "zones": ["desk_05"],
        "snapshot_url": "http://10.0.20.6:5001/snapshot/employees_01/1705312200-0sy0od",
        "video_url": "http://10.0.20.6:5001/video/0sy0od",
        "timestamp_iso": "2024-01-15T10:30:00+05:00",
        "timestamp_relative": "2 minutes ago"
      }
    ],
    "count": 1,
    "time_period_hours": 24
  }
}
```

#### GET /api/violations/hourly-trend
Get hourly trend of phone violations.

**Query Parameters:**
- `hours` (optional): Hours to analyze (1-168, default 24)

**Response:**
```json
{
  "success": true,
  "data": {
    "trend": [
      {
        "hour": "2024-01-15T09:00:00+05:00",
        "violations": 3,
        "employees": ["John Doe", "Jane Smith"]
      }
    ],
    "total_violations": 15,
    "unique_employees": 5
  }
}
```

#### GET /api/violations/stats
Get violation statistics.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_violations_24h": 15,
    "unique_employees": 5,
    "most_active_camera": "employees_01",
    "violations_by_camera": {
      "employees_01": 8,
      "employees_02": 4,
      "employees_03": 3
    }
  }
}
```

### 2. Employees

#### GET /api/employees/stats
Get comprehensive employee statistics.

**Query Parameters:**
- `hours` (optional): Hours to analyze (1-168, default 24)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "employee_name": "John Doe",
      "total_detections": 45,
      "cameras_visited": 3,
      "last_seen": 1705312200.182961,
      "phone_violations": 5,
      "activity_level": "high",
      "last_seen_iso": "2024-01-15T10:30:00+05:00",
      "last_seen_relative": "2 minutes ago"
    }
  ]
}
```

#### GET /api/employees/{employee_name}/violations
Get violation history for a specific employee.

**Path Parameters:**
- `employee_name`: Name of the employee

**Query Parameters:**
- `start_time` (optional): Start timestamp filter
- `end_time` (optional): End timestamp filter
- `limit` (optional): Maximum results (1-1000, default 50)

**Response:**
```json
{
  "success": true,
  "data": {
    "violations": [
      {
        "id": "0sy0od",
        "timestamp": 1705312200.182961,
        "camera": "employees_01",
        "employee_name": "John Doe",
        "confidence": 0.95,
        "zones": ["desk_05"],
        "snapshot_url": "http://10.0.20.6:5001/snapshot/employees_01/1705312200-0sy0od",
        "video_url": "http://10.0.20.6:5001/video/0sy0od"
      }
    ],
    "employee_name": "John Doe",
    "time_range": {
      "start_time": 1705225800,
      "end_time": 1705312200
    },
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 5,
      "pages": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

#### GET /api/employees/{employee_name}/activity
Get activity summary for a specific employee.

**Path Parameters:**
- `employee_name`: Name of the employee

**Query Parameters:**
- `hours` (optional): Hours to analyze (1-168, default 24)

**Response:**
```json
{
  "success": true,
  "data": {
    "employee_name": "John Doe",
    "time_period_hours": 24,
    "total_detections": 45,
    "cameras_visited": 3,
    "violation_summary": {
      "total_violations": 5,
      "violation_cameras": 2,
      "last_violation": 1705312200.182961
    },
    "camera_visits": [
      {
        "camera": "employees_01",
        "visits": 25,
        "first_seen": 1705225800,
        "last_seen": 1705312200,
        "duration": 86400
      }
    ],
    "recent_detections": [...],
    "hourly_pattern": [
      {
        "hour": 9,
        "detections": 5
      }
    ],
    "activity_level": "high"
  }
}
```

#### GET /api/employees/search
Search for employees by name.

**Query Parameters:**
- `query`: Search query (minimum 2 characters)
- `limit` (optional): Maximum results (1-50, default 10)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "employee_name": "John Doe",
      "detection_count": 45,
      "last_seen": 1705312200.182961,
      "last_seen_relative": "recent"
    }
  ]
}
```

### 3. Cameras

#### GET /api/cameras/summary
Get live summaries for all cameras.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "camera": "employees_01",
      "active_people": 2,
      "total_detections": 15,
      "phone_violations": 3,
      "recording_status": "active",
      "last_activity": 1705312200.182961,
      "last_activity_iso": "2024-01-15T10:30:00+05:00",
      "last_activity_relative": "2 minutes ago"
    }
  ]
}
```

#### GET /api/cameras/{camera_name}/summary
Get live summary for a specific camera.

**Path Parameters:**
- `camera_name`: Name of the camera

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "camera": "employees_01",
      "active_people": 2,
      "total_detections": 15,
      "phone_violations": 3,
      "recording_status": "active",
      "last_activity": 1705312200.182961,
      "last_activity_iso": "2024-01-15T10:30:00+05:00",
      "last_activity_relative": "2 minutes ago"
    }
  ]
}
```

#### GET /api/cameras/{camera_name}/activity
Get detailed activity feed for a specific camera.

**Path Parameters:**
- `camera_name`: Name of the camera

**Query Parameters:**
- `hours` (optional): Hours to look back (1-168, default 24)
- `limit` (optional): Maximum results (1-1000, default 50)

**Response:**
```json
{
  "success": true,
  "data": {
    "activities": [
      {
        "timestamp": 1705312200.182961,
        "camera": "employees_01",
        "event_type": "person",
        "employee_name": "John Doe",
        "zones": ["desk_05"],
        "confidence": 0.95,
        "snapshot_url": "http://10.0.20.6:5001/snapshot/employees_01/1705312200-0sy0od"
      }
    ],
    "camera": "employees_01",
    "time_period_hours": 24,
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 100,
      "pages": 2,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

#### GET /api/cameras/{camera_name}/violations
Get phone violations for a specific camera.

**Path Parameters:**
- `camera_name`: Name of the camera

**Query Parameters:**
- `hours` (optional): Hours to look back (1-168, default 24)
- `limit` (optional): Maximum results (1-1000, default 50)

**Response:**
```json
{
  "success": true,
  "data": {
    "violations": [...],
    "camera": "employees_01",
    "time_period_hours": 24,
    "total_violations": 5
  }
}
```

#### GET /api/cameras/{camera_name}/status
Get detailed status information for a specific camera.

**Path Parameters:**
- `camera_name`: Name of the camera

**Response:**
```json
{
  "success": true,
  "data": {
    "camera": "employees_01",
    "recording": {
      "status": "active",
      "count_24h": 12,
      "last_recording": 1705312200.182961,
      "first_recording": 1705225800.182961
    },
    "activity": {
      "total_events_1h": 25,
      "person_events_1h": 20,
      "phone_events_1h": 3,
      "face_events_1h": 15,
      "last_event": 1705312200.182961
    },
    "zones": ["desk_01", "desk_02", "desk_03"],
    "health": {
      "status": "healthy",
      "last_activity_ago": null
    }
  }
}
```

#### GET /api/cameras/list
Get list of all available cameras.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "name": "employees_01",
      "total_events_24h": 150,
      "person_events_24h": 120,
      "phone_events_24h": 8,
      "last_activity": 1705312200.182961,
      "status": "active"
    }
  ]
}
```

### 4. WebSocket Endpoints

#### WebSocket /ws/violations
Real-time violation monitoring WebSocket.

**Query Parameters:**
- `camera` (optional): Filter by specific camera
- `hours` (optional): Hours to look back (1-168, default 24)

**Message Types:**

**Client to Server:**
```json
{
  "type": "ping"
}
```

```json
{
  "type": "update_filter",
  "data": {
    "camera": "employees_01",
    "hours": 12
  }
}
```

**Server to Client:**
```json
{
  "type": "initial_data",
  "data": {
    "violations": [...],
    "count": 5,
    "camera_filter": "employees_01",
    "hours": 24,
    "timestamp": 1705312200.182961
  }
}
```

```json
{
  "type": "new_violations",
  "data": {
    "violations": [...],
    "count": 1,
    "timestamp": 1705312200.182961
  }
}
```

```json
{
  "type": "pong",
  "data": {
    "timestamp": 1705312200.182961
  }
}
```

#### WebSocket /ws/dashboard
Dashboard updates WebSocket.

**Query Parameters:**
- `subscribe_to` (optional): Subscribe to: all, violations, cameras, employees (default: all)

**Message Types:**

**Client to Server:**
```json
{
  "type": "ping"
}
```

**Server to Client:**
```json
{
  "type": "dashboard_data",
  "data": {
    "violations": {
      "recent": [...],
      "total_24h": 15,
      "timestamp": 1705312200.182961
    },
    "cameras": {
      "summaries": [...],
      "timestamp": 1705312200.182961
    },
    "employees": {
      "stats": [...],
      "timestamp": 1705312200.182961
    }
  }
}
```

```json
{
  "type": "violation_summary",
  "data": {
    "new_violations_count": 2,
    "timestamp": 1705312200.182961
  }
}
```

### 5. System Endpoints

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "timestamp": "2024-01-15T10:30:00+05:00"
}
```

#### GET /api/status
System status including background tasks.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00+05:00",
  "database": {
    "status": "healthy",
    "pool_size": 10
  },
  "cache": {
    "status": "healthy",
    "connected": true
  },
  "background_tasks": {
    "is_running": true,
    "tasks": {
      "violation_polling": {
        "running": true,
        "cancelled": false,
        "exception": null
      },
      "stats_refresh": {
        "running": true,
        "cancelled": false,
        "exception": null
      }
    }
  }
}
```

#### GET /api/info
API information and features.

**Response:**
```json
{
  "name": "Frigate Dashboard Middleware",
  "version": "1.0.0",
  "description": "Middleware service for Frigate surveillance dashboard",
  "endpoints": [...],
  "features": [...],
  "timestamp": "2024-01-15T10:30:00+05:00"
}
```

#### GET /api/cache/stats
Cache statistics.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_keys": 150,
    "memory_usage": "2.5MB",
    "hit_rate": 0.85,
    "keys_by_pattern": {
      "violations": 50,
      "employees": 30,
      "cameras": 40,
      "dashboard": 30
    }
  }
}
```

#### POST /api/admin/restart-task/{task_name}
Restart a specific background task.

**Path Parameters:**
- `task_name`: Name of the task (violation_polling, stats_refresh, cache_cleanup, health_check)

**Response:**
```json
{
  "success": true,
  "message": "Task violation_polling restarted successfully"
}
```

### 6. Cache Management

#### DELETE /api/violations/cache
Clear violation-related cache.

**Response:**
```json
{
  "success": true,
  "data": {
    "cleared_keys": 15
  },
  "message": "Cleared 15 violation cache entries"
}
```

#### DELETE /api/employees/cache
Clear employee-related cache.

**Response:**
```json
{
  "success": true,
  "data": {
    "cleared_keys": 8
  },
  "message": "Cleared 8 employee cache entries"
}
```

#### DELETE /api/cameras/cache
Clear camera-related cache.

**Response:**
```json
{
  "success": true,
  "data": {
    "cleared_keys": 12
  },
  "message": "Cleared 12 camera cache entries"
}
```

## Error Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

## Rate Limiting

Currently, no rate limiting is implemented. However, the system uses Redis caching to optimize performance and reduce database load.

## WebSocket Connection Management

- WebSocket connections are automatically managed
- Connections are grouped by type (violations, dashboard)
- Background polling starts when the first connection is established
- Polling stops when all connections are closed
- Automatic reconnection is handled by the client

## Data Formats

### Timestamps
- All timestamps are Unix epoch (seconds since 1970-01-01)
- ISO format timestamps include timezone information (Asia/Karachi)
- Relative timestamps show human-readable time differences

### Media URLs
- Snapshot URLs: `http://10.0.20.6:5001/snapshot/{camera}/{timestamp}-{id}`
- Video URLs: `http://10.0.20.6:5001/video/{id}`
- Thumbnail URLs: `http://10.0.20.6:5001/thumb/{id}`

### Employee Names
- Employee names are sanitized and validated
- Names are case-sensitive and must match exactly
- Special characters are handled appropriately

## Examples

### Get Recent Violations
```bash
curl "http://localhost:5002/api/violations/live?hours=24&limit=10"
```

### Get Employee Statistics
```bash
curl "http://localhost:5002/api/employees/stats?hours=48"
```

### Get Camera Activity
```bash
curl "http://localhost:5002/api/cameras/employees_01/activity?hours=12&limit=20"
```

### WebSocket Connection (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:5002/ws/violations?camera=employees_01&hours=24');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

// Send ping
ws.send(JSON.stringify({type: 'ping'}));
```

## Support

For technical support or questions about the API, please refer to the main README.md file or contact the development team.




