# Frigate Dashboard Middleware

A high-performance FastAPI-based middleware service that aggregates and caches Frigate surveillance data for real-time dashboard applications. This service provides REST APIs and WebSocket endpoints for monitoring phone violations, employee activity, and camera status with intelligent caching and real-time updates.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Middleware     │    │   Frigate NVR   │
│   Dashboard     │◄──►│   Service        │◄──►│   + Database    │
│                 │    │   (FastAPI)      │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Redis Cache    │
                       │   (Performance)  │
                       └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Access to Frigate PostgreSQL database (10.0.20.6:5433)
- Redis server (included in docker-compose)

### 3 Commands to Run

```bash
# 1. Clone and navigate to project
cd /opt/dashboard_middleware

# 2. Start the services
docker-compose up -d

# 3. Check health
curl http://localhost:5002/health
```

That's it! The service will be running on `http://localhost:5002`

## 📋 Features

### Core Functionality
- **Real-time Phone Violation Detection** - Identifies employees using phones with face recognition
- **Employee Activity Monitoring** - Tracks employee movements and activity levels
- **Camera Status Monitoring** - Live camera summaries and activity feeds
- **WebSocket Real-time Updates** - Push notifications for new violations
- **Intelligent Caching** - Redis-based caching with configurable TTL
- **Comprehensive API** - RESTful endpoints with OpenAPI documentation

### Performance Features
- **Async/Await Architecture** - High-performance async operations
- **Connection Pooling** - Optimized database connections
- **Smart Caching** - Reduces database load by 80%+
- **Background Tasks** - Automated cache management and stats refresh
- **Health Monitoring** - Built-in health checks and metrics

## 🔧 Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Key configuration options:

```env
# Database
DB_HOST=10.0.20.6
DB_PORT=5433
DB_NAME=frigate_db
DB_USER=frigate
DB_PASSWORD=frigate_secure_pass_2024

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Video API
VIDEO_API_BASE_URL=http://10.0.20.6:5001

# Cache TTL (seconds)
CACHE_TTL_LIVE_VIOLATIONS=10
CACHE_TTL_HOURLY_TREND=300
CACHE_TTL_EMPLOYEE_STATS=30

# Business Logic
FACE_DETECTION_WINDOW=3
THUMBNAIL_WINDOW=5
HIGH_ACTIVITY_THRESHOLD=20
```

## 📚 API Documentation

### Core Endpoints

| Endpoint | Method | Description | Cache TTL |
|----------|--------|-------------|-----------|
| `/api/violations/live` | GET | Recent phone violations | 10s |
| `/api/violations/hourly-trend` | GET | Hourly violation trends | 5m |
| `/api/employees/stats` | GET | Employee statistics | 30s |
| `/api/employees/{name}/violations` | GET | Employee violation history | 30s |
| `/api/cameras/summary` | GET | Live camera summaries | 15s |
| `/api/cameras/{name}/activity` | GET | Camera activity feed | 1m |
| `/api/dashboard/overview` | GET | Complete dashboard data | 10s |
| `/ws/violations` | WS | Real-time violation updates | - |

### Example API Calls

```bash
# Get recent violations
curl "http://localhost:5002/api/violations/live?camera=employees_01&limit=10"

# Get hourly trends
curl "http://localhost:5002/api/violations/hourly-trend?hours=24"

# Get employee stats
curl "http://localhost:5002/api/employees/stats"

# Get camera summary
curl "http://localhost:5002/api/cameras/summary"

# Health check
curl "http://localhost:5002/health"
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:5002/ws/violations');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'new_violation') {
        console.log('New violation:', data.data);
        // Update UI with new violation
    }
};
```

## 🐳 Docker Deployment

### Development

```bash
# Start with hot reload
docker-compose up

# View logs
docker-compose logs -f dashboard_middleware

# Access Redis Commander (debug mode)
docker-compose --profile debug up
# Then visit http://localhost:8081
```

### Production

```bash
# Build production image
docker-compose -f docker-compose.yml build --target production

# Start production services
docker-compose up -d

# Scale workers
docker-compose up -d --scale dashboard_middleware=3
```

### Health Checks

```bash
# Check service health
curl http://localhost:5002/health

# Check cache stats
curl http://localhost:5002/api/cache/stats

# View service logs
docker-compose logs dashboard_middleware
```

## 🔍 Monitoring & Troubleshooting

### Health Monitoring

The service provides comprehensive health checks:

```bash
# Overall health
curl http://localhost:5002/health

# Response format:
{
  "status": "healthy",
  "database": "healthy", 
  "redis": "healthy",
  "timestamp": "2024-01-15T10:30:00+05:00"
}
```

### Cache Performance

Monitor cache performance:

```bash
# Cache statistics
curl http://localhost:5002/api/cache/stats

# Clear cache if needed
curl -X DELETE http://localhost:5002/api/violations/cache
```

### Common Issues

**Database Connection Failed**
```bash
# Check database connectivity
docker-compose exec dashboard_middleware python -c "
import asyncio
from app.database import db_manager
asyncio.run(db_manager.health_check())
"
```

**Redis Connection Failed**
```bash
# Check Redis
docker-compose exec redis redis-cli ping
```

**High Memory Usage**
```bash
# Check Redis memory
docker-compose exec redis redis-cli info memory

# Clear cache
curl -X DELETE http://localhost:5002/api/violations/cache
```

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_violations.py
```

### Test Data

The service includes sample data insertion scripts for testing:

```bash
# Insert test data
python scripts/insert_test_data.py

# Run integration tests
pytest tests/test_integration.py
```

## 📊 Performance Metrics

### Expected Performance

- **API Response Time**: <100ms for cached requests
- **Cache Hit Rate**: >80% for frequently accessed data
- **Database Load Reduction**: 80%+ through caching
- **Concurrent Connections**: 1000+ WebSocket connections
- **Memory Usage**: <512MB for typical workloads

### Monitoring

```bash
# Check response times
curl -w "@curl-format.txt" http://localhost:5002/api/violations/live

# Monitor cache hit rate
curl http://localhost:5002/api/cache/stats | jq '.data.redis_info.keyspace_hits'
```

## 🔒 Security

### Production Security

1. **Environment Variables**: Never commit `.env` files
2. **Network Security**: Use proper firewall rules
3. **Authentication**: Enable authentication for production
4. **HTTPS**: Use reverse proxy with SSL termination
5. **Rate Limiting**: Configure rate limits for public endpoints

### Security Headers

The service includes security middleware:
- CORS configuration
- Trusted host validation
- Request validation
- Error sanitization

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd dashboard_middleware

# Install dependencies
pip install -r requirements.txt

# Run in development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 5002
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Documentation

- **API Docs**: http://localhost:5002/docs
- **ReDoc**: http://localhost:5002/redoc
- **OpenAPI Spec**: http://localhost:5002/openapi.json

### Getting Help

1. Check the [API Documentation](API_DOCS.md)
2. Review the troubleshooting section above
3. Check service logs: `docker-compose logs dashboard_middleware`
4. Verify database connectivity and Redis status

### Common Commands

```bash
# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Access container shell
docker-compose exec dashboard_middleware bash

# Check service status
docker-compose ps

# Clean up
docker-compose down -v
```

---

**Built with ❤️ for Frigate surveillance monitoring**







