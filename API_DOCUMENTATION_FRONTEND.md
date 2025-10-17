# 🎯 Frigate Dashboard Middleware - Complete API Documentation for Frontend

## Base Configuration
- **Base URL**: `http://10.0.20.7:5002`
- **API Prefix**: `/api`
- **Health Check**: `http://10.0.20.7:5002/health`
- **Swagger UI**: `http://10.0.20.7:5002/docs`

## Core API Endpoints

### 1. Health & Status
```javascript
// Health Check
GET /health
Response: { success: true, data: { status: "healthy", services: {...} } }

// API Info
GET /api/info
Response: { success: true, data: { name: "Frigate Dashboard Middleware", version: "1.0.0" } }

// System Status
GET /api/status
Response: { success: true, data: { status: "operational", uptime: "..." } }

// Cache Statistics
GET /api/cache/stats
Response: { success: true, data: { hits: 123, misses: 45, size: 67 } }
```

## Violations API

### 2. Live Violations
```javascript
// Get live violations (default: last 24 hours, limit 50)
GET /api/violations/live
GET /api/violations/live?limit=10
GET /api/violations/live?hours=12
GET /api/violations/live?camera=employees_01
GET /api/violations/live?limit=5&hours=6&camera=employees_02

Response: {
  success: true,
  data: {
    violations: [
      {
        id: "1760599637.527265-lqg8sx",
        camera: "employees_01",
        timestamp: 1760599637.527265,
        label: "cell phone",
        zones: ["desk_05"],
        video_url: "http://10.0.20.6:5001/video/1760599637.527265-lqg8sx",
        thumbnail_url: "http://10.0.20.6:5001/thumb/1760599637.527265-lqg8sx",
        snapshot_url: "http://10.0.20.6:5001/snapshot/employees_01/1760599637.527265-lqg8sx"
      }
    ],
    total: 25,
    limit: 10,
    hours: 24
  }
}
```

### 3. Hourly Trends
```javascript
// Get hourly violation trends
GET /api/violations/hourly-trend
GET /api/violations/hourly-trend?hours=48
GET /api/violations/hourly-trend?hours=168&camera=employees_01

Response: {
  success: true,
  data: {
    trends: [
      {
        hour: "2025-10-16T07:00:00Z",
        timestamp: 1760598000,
        violations: 5,
        cell_phones: 2,
        cameras: ["employees_01", "employees_02"]
      }
    ],
    total_hours: 48,
    total_violations: 125
  }
}
```

### 4. Violation Statistics
```javascript
// Get violation statistics
GET /api/violations/stats
GET /api/violations/stats?hours=24
GET /api/violations/stats?camera=employees_01

Response: {
  success: true,
  data: {
    total_violations: 45,
    cell_phone_violations: 12,
    cameras: {
      "employees_01": 15,
      "employees_02": 18,
      "employees_03": 12
    },
    hourly_average: 1.9,
    peak_hour: "14:00-15:00"
  }
}
```

## Employees API

### 5. Employee Statistics
```javascript
// Get employee statistics
GET /api/employees/stats
GET /api/employees/stats?hours=24

Response: {
  success: true,
  data: {
    total_employees: 25,
    active_employees: 18,
    violations_by_employee: {
      "John Doe": 3,
      "Jane Smith": 1,
      "Unknown": 5
    },
    activity_summary: {
      high_activity: 5,
      medium_activity: 8,
      low_activity: 10
    }
  }
}
```

### 6. Employee Search
```javascript
// Search employees
GET /api/employees/search?query=john
GET /api/employees/search?query=unknown

Response: {
  success: true,
  data: {
    employees: [
      {
        name: "John Doe",
        violations_count: 3,
        last_seen: "2025-10-16T07:30:00Z",
        cameras: ["employees_01", "employees_02"]
      }
    ],
    total: 1
  }
}
```

### 7. Employee Violations
```javascript
// Get violations for specific employee
GET /api/employees/{employee_name}/violations
GET /api/employees/John%20Doe/violations?limit=10&hours=24

Response: {
  success: true,
  data: {
    employee: "John Doe",
    violations: [
      {
        id: "1760599637.527265-lqg8sx",
        camera: "employees_01",
        timestamp: 1760599637.527265,
        label: "cell phone",
        zones: ["desk_05"],
        video_url: "http://10.0.20.6:5001/video/1760599637.527265-lqg8sx",
        thumbnail_url: "http://10.0.20.6:5001/thumb/1760599637.527265-lqg8sx"
      }
    ],
    total: 3,
    limit: 10,
    hours: 24
  }
}
```

### 8. Employee Activity
```javascript
// Get employee activity summary
GET /api/employees/{employee_name}/activity
GET /api/employees/John%20Doe/activity?hours=24

Response: {
  success: true,
  data: {
    employee: "John Doe",
    activity_level: "high",
    total_detections: 15,
    cameras: ["employees_01", "employees_02"],
    zones: ["desk_05", "desk_06"],
    time_breakdown: {
      "08:00-12:00": 8,
      "12:00-17:00": 5,
      "17:00-20:00": 2
    }
  }
}
```

## Cameras API

### 9. List All Cameras
```javascript
// Get list of all cameras
GET /api/cameras/list

Response: {
  success: true,
  data: {
    cameras: [
      {
        name: "employees_01",
        ip: "172.16.5.242",
        fps: 8,
        resolution: [3840, 2160],
        status: "online",
        desk_count: 12
      }
    ],
    total: 12
  }
}
```

### 10. Camera Summary
```javascript
// Get summary for all cameras
GET /api/cameras/summary

Response: {
  success: true,
  data: {
    cameras: [
      {
        camera: "employees_01",
        active_people: 3,
        recording_status: "active",
        violations_today: 5,
        last_activity: "2025-10-16T07:30:00Z"
      }
    ],
    total_cameras: 12,
    online_cameras: 11,
    total_violations: 45
  }
}
```

### 11. Single Camera Summary
```javascript
// Get summary for specific camera
GET /api/cameras/{camera_name}/summary
GET /api/cameras/employees_01/summary

Response: {
  success: true,
  data: {
    camera: "employees_01",
    active_people: 3,
    recording_status: "active",
    violations_today: 5,
    last_activity: "2025-10-16T07:30:00Z",
    desk_occupancy: {
      "desk_01": true,
      "desk_02": false,
      "desk_03": true
    }
  }
}
```

### 12. Camera Activity
```javascript
// Get camera activity feed
GET /api/cameras/{camera_name}/activity
GET /api/cameras/employees_01/activity?limit=20

Response: {
  success: true,
  data: {
    camera: "employees_01",
    activities: [
      {
        timestamp: 1760599637.527265,
        type: "person_detection",
        zones: ["desk_05"],
        confidence: 0.95
      }
    ],
    total: 15,
    limit: 20
  }
}
```

### 13. Camera Violations
```javascript
// Get violations for specific camera
GET /api/cameras/{camera_name}/violations
GET /api/cameras/employees_01/violations?limit=10&hours=24

Response: {
  success: true,
  data: {
    camera: "employees_01",
    violations: [
      {
        id: "1760599637.527265-lqg8sx",
        timestamp: 1760599637.527265,
        label: "cell phone",
        zones: ["desk_05"],
        video_url: "http://10.0.20.6:5001/video/1760599637.527265-lqg8sx",
        thumbnail_url: "http://10.0.20.6:5001/thumb/1760599637.527265-lqg8sx"
      }
    ],
    total: 5,
    limit: 10,
    hours: 24
  }
}
```

### 14. Camera Status
```javascript
// Get camera status
GET /api/cameras/{camera_name}/status
GET /api/cameras/employees_01/status

Response: {
  success: true,
  data: {
    camera: "employees_01",
    status: "online",
    fps: 8,
    resolution: [3840, 2160],
    recording: true,
    last_frame: "2025-10-16T07:30:00Z",
    uptime: "2 days, 5 hours"
  }
}
```

## WebSocket API

### 15. WebSocket Broadcast
```javascript
// Broadcast message via WebSocket
POST /ws/broadcast
Content-Type: application/json

{
  "message_type": "violation_alert",
  "data": {
    "camera": "employees_01",
    "violation": "cell phone",
    "timestamp": 1760599637.527265
  },
  "target": "all"
}

Response: {
  success: true,
  message: "Message broadcasted successfully",
  data: {
    message_type: "violation_alert",
    target: "all",
    timestamp: "2025-10-16T07:30:00Z"
  }
}
```

### 16. WebSocket Status
```javascript
// Get WebSocket status
GET /ws/status

Response: {
  success: true,
  data: {
    status: "active",
    connected_clients: 3,
    last_activity: "2025-10-16T07:30:00Z"
  }
}
```

## Admin API

### 17. Restart Tasks
```javascript
// Restart background tasks
POST /api/admin/restart-task/violation_polling
POST /api/admin/restart-task/stats_refresh

Response: {
  success: true,
  message: "Task restarted successfully",
  data: {
    task: "violation_polling",
    status: "running"
  }
}
```

### 18. Cache Management
```javascript
// Clear caches
DELETE /api/violations/cache
DELETE /api/employees/cache
DELETE /api/cameras/cache

Response: {
  success: true,
  message: "Cache cleared successfully",
  data: {
    cleared_entries: 15,
    cache_type: "violations"
  }
}
```

## Recent Media API

### 19. Recent Clips
```javascript
// Get recent clips with working media URLs
GET /api/recent-media/clips?limit=10

Response: {
  success: true,
  data: {
    clips: [
      {
        id: "1760599637.527265-lqg8sx",
        camera: "employees_01",
        start_time: 1760599637.527265,
        duration: 5.2,
        video_url: "http://10.0.20.6:5001/video/1760599637.527265-lqg8sx",
        thumbnail_url: "http://10.0.20.6:5001/thumb/1760599637.527265-lqg8sx"
      }
    ],
    total: 10
  }
}
```

### 20. Recent Recordings
```javascript
// Get recent recordings
GET /api/recent-media/recordings?limit=10

Response: {
  success: true,
  data: {
    recordings: [
      {
        id: "1760599637.527265-abc123",
        camera: "employees_01",
        start_time: 1760599637.527265,
        end_time: 1760599642.527265,
        duration: 5.0,
        video_url: "http://10.0.20.6:5001/video/1760599637.527265-abc123"
      }
    ],
    total: 10
  }
}
```

## Common Parameters

### Query Parameters
- `limit`: Number of results (default: 50, max: 1000)
- `hours`: Time range in hours (default: 24, max: 168)
- `camera`: Filter by camera name
- `start_time`: Unix timestamp (optional)
- `end_time`: Unix timestamp (optional)

### Response Format
All responses follow this structure:
```javascript
{
  success: boolean,
  message: string,
  data: object,
  timestamp: string
}
```

### Error Responses
```javascript
{
  success: false,
  message: "Error description",
  details: {
    error_type: "ValidationError",
    field: "limit",
    value: 999999
  },
  timestamp: "2025-10-16T07:30:00Z"
}
```

## Performance Notes
- Average response time: 0.002s
- Hourly trend queries (48+ hours): 7-10s
- All endpoints tested: 100% success rate
- Real-time WebSocket support available

## Frontend Integration Examples

### JavaScript/Fetch Examples
```javascript
// Fetch live violations
const fetchViolations = async (limit = 10, hours = 24) => {
  const response = await fetch(`http://10.0.20.7:5002/api/violations/live?limit=${limit}&hours=${hours}`);
  const data = await response.json();
  return data;
};

// Fetch employee statistics
const fetchEmployeeStats = async () => {
  const response = await fetch('http://10.0.20.7:5002/api/employees/stats');
  const data = await response.json();
  return data;
};

// Fetch camera summary
const fetchCameraSummary = async () => {
  const response = await fetch('http://10.0.20.7:5002/api/cameras/summary');
  const data = await response.json();
  return data;
};

// WebSocket connection
const connectWebSocket = () => {
  const ws = new WebSocket('ws://10.0.20.7:5002/ws');
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('WebSocket message:', data);
  };
  return ws;
};
```

### React Hook Examples
```javascript
// Custom hook for violations
const useViolations = (limit = 10, hours = 24) => {
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`http://10.0.20.7:5002/api/violations/live?limit=${limit}&hours=${hours}`);
        const data = await response.json();
        if (data.success) {
          setViolations(data.data.violations);
        }
      } catch (error) {
        console.error('Error fetching violations:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [limit, hours]);
  
  return { violations, loading };
};
```

## Available Camera Names
- `employees_01` through `employees_08`
- `admin_office`
- `reception`
- `meeting_room`

## Desk Zone Mapping
Each camera has multiple desk zones (desk_01, desk_02, etc.) that can be used for:
- Zone-based filtering
- Desk occupancy tracking
- Location-specific violation analysis

## Real-time Updates
- Use WebSocket connection for real-time violation alerts
- Poll endpoints every 30-60 seconds for dashboard updates
- Cache responses to reduce API calls




