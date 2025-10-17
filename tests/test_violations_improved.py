"""
Comprehensive tests for violations endpoints following best practices.

This module provides comprehensive tests for the violations API endpoints
with proper test structure, fixtures, and error handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.models import LiveViolationsResponse, HourlyTrendResponse
from app.utils.errors import ValidationError, NotFoundError, DatabaseError
from app.config_improved import settings


class TestViolationsEndpoints:
    """Test class for violations endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client fixture."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database fixture."""
        mock_db = AsyncMock()
        mock_db.is_connected.return_value = True
        return mock_db
    
    @pytest.fixture
    def mock_cache(self):
        """Create mock cache fixture."""
        mock_cache = AsyncMock()
        mock_cache.is_connected.return_value = True
        mock_cache.get.return_value = None
        return mock_cache
    
    @pytest.fixture
    def sample_violations_data(self):
        """Create sample violations data fixture."""
        return [
            {
                "id": "test_violation_1",
                "timestamp": 1640995200.0,
                "camera": "employees_01",
                "employee_name": "John Doe",
                "confidence": 0.95,
                "zones": ["desk_1"],
                "thumbnail_url": "http://test.com/thumb/test_violation_1",
                "video_url": "http://test.com/clip/test_violation_1",
                "snapshot_url": "http://test.com/snapshot/employees_01/1640995200-test_violation_1"
            }
        ]
    
    @pytest.fixture
    def sample_trend_data(self):
        """Create sample trend data fixture."""
        return [
            {
                "hour": 1640995200.0,
                "violations": 5,
                "cameras": ["employees_01", "employees_02"],
                "employees": ["John Doe", "Jane Smith"]
            }
        ]


class TestLiveViolationsEndpoint(TestViolationsEndpoints):
    """Test live violations endpoint."""
    
    @patch('app.routers.violations_improved.ViolationQueries.get_live_violations')
    async def test_get_live_violations_success(
        self, 
        mock_get_violations,
        client,
        mock_database,
        mock_cache,
        sample_violations_data
    ):
        """Test successful retrieval of live violations."""
        # Arrange
        mock_get_violations.return_value = sample_violations_data
        
        # Act
        response = client.get("/api/violations/live?limit=10&hours=24")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "test_violation_1"
    
    async def test_get_live_violations_with_camera_filter(
        self,
        client,
        mock_database,
        mock_cache,
        sample_violations_data
    ):
        """Test live violations with camera filter."""
        with patch('app.routers.violations_improved.ViolationQueries.get_live_violations') as mock_get:
            mock_get.return_value = sample_violations_data
            
            response = client.get("/api/violations/live?camera=employees_01&limit=10")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
    
    async def test_get_live_violations_invalid_camera(
        self,
        client,
        mock_database,
        mock_cache
    ):
        """Test live violations with invalid camera."""
        response = client.get("/api/violations/live?camera=invalid_camera")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()
    
    async def test_get_live_violations_invalid_limit(
        self,
        client,
        mock_database,
        mock_cache
    ):
        """Test live violations with invalid limit."""
        response = client.get("/api/violations/live?limit=0")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_get_live_violations_invalid_hours(
        self,
        client,
        mock_database,
        mock_cache
    ):
        """Test live violations with invalid hours."""
        response = client.get("/api/violations/live?hours=0")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_get_live_violations_database_error(
        self,
        client,
        mock_database,
        mock_cache
    ):
        """Test live violations with database error."""
        with patch('app.routers.violations_improved.ViolationQueries.get_live_violations') as mock_get:
            mock_get.side_effect = DatabaseError("Database connection failed")
            
            response = client.get("/api/violations/live")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["success"] is False
    
    async def test_get_live_violations_cache_hit(
        self,
        client,
        mock_database,
        mock_cache,
        sample_violations_data
    ):
        """Test live violations with cache hit."""
        # Arrange
        mock_cache.get.return_value = sample_violations_data
        
        # Act
        response = client.get("/api/violations/live")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "cache" in data["message"].lower()


class TestHourlyTrendEndpoint(TestViolationsEndpoints):
    """Test hourly trend endpoint."""
    
    @patch('app.routers.violations_improved.ViolationQueries.get_hourly_trend')
    async def test_get_hourly_trend_success(
        self,
        mock_get_trend,
        client,
        mock_database,
        mock_cache,
        sample_trend_data
    ):
        """Test successful retrieval of hourly trend."""
        # Arrange
        mock_get_trend.return_value = sample_trend_data
        
        # Act
        response = client.get("/api/violations/hourly-trend?hours=48")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) == 1
    
    async def test_get_hourly_trend_invalid_hours(
        self,
        client,
        mock_database,
        mock_cache
    ):
        """Test hourly trend with invalid hours."""
        response = client.get("/api/violations/hourly-trend?hours=0")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_get_hourly_trend_database_error(
        self,
        client,
        mock_database,
        mock_cache
    ):
        """Test hourly trend with database error."""
        with patch('app.routers.violations_improved.ViolationQueries.get_hourly_trend') as mock_get:
            mock_get.side_effect = DatabaseError("Database connection failed")
            
            response = client.get("/api/violations/hourly-trend")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestViolationStatsEndpoint(TestViolationsEndpoints):
    """Test violation stats endpoint."""
    
    @patch('app.routers.violations_improved.ViolationQueries.get_violation_stats')
    async def test_get_violation_stats_success(
        self,
        mock_get_stats,
        client,
        mock_database,
        mock_cache
    ):
        """Test successful retrieval of violation stats."""
        # Arrange
        mock_stats_data = {
            "total_violations": 100,
            "camera_stats": [{"camera": "employees_01", "count": 50}],
            "employee_stats": [{"employee": "John Doe", "count": 25}],
            "peak_hours": [{"hour": 9, "count": 20}]
        }
        mock_get_stats.return_value = mock_stats_data
        
        # Act
        response = client.get("/api/violations/stats?hours=24")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_violations"] == 100


class TestCacheEndpoints(TestViolationsEndpoints):
    """Test cache-related endpoints."""
    
    async def test_get_cache_info_success(
        self,
        client,
        mock_cache
    ):
        """Test successful retrieval of cache info."""
        response = client.get("/api/violations/cache")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "status" in data["data"]
    
    async def test_clear_cache_success(
        self,
        client,
        mock_cache
    ):
        """Test successful cache clearing."""
        response = client.delete("/api/violations/cache")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "cleared" in data["message"].lower()


class TestErrorHandling(TestViolationsEndpoints):
    """Test error handling scenarios."""
    
    async def test_database_unavailable(
        self,
        client,
        mock_cache
    ):
        """Test behavior when database is unavailable."""
        with patch('app.routers.violations_improved.DatabaseDep') as mock_db_dep:
            mock_db = AsyncMock()
            mock_db.is_connected.return_value = False
            mock_db_dep.return_value = mock_db
            
            response = client.get("/api/violations/live")
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert "unavailable" in data["error"].lower()
    
    async def test_cache_unavailable(
        self,
        client,
        mock_database
    ):
        """Test behavior when cache is unavailable."""
        with patch('app.routers.violations_improved.CacheDep') as mock_cache_dep:
            mock_cache = AsyncMock()
            mock_cache.is_connected.return_value = False
            mock_cache_dep.return_value = mock_cache
            
            response = client.get("/api/violations/live")
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert "unavailable" in data["error"].lower()


class TestValidation(TestViolationsEndpoints):
    """Test input validation."""
    
    async def test_validate_camera_parameter(self):
        """Test camera parameter validation."""
        from app.dependencies_improved import validate_camera_parameter
        
        # Valid camera
        result = validate_camera_parameter("employees_01")
        assert result == "employees_01"
        
        # None camera
        result = validate_camera_parameter(None)
        assert result is None
    
    async def test_validate_limit_parameter(self):
        """Test limit parameter validation."""
        from app.dependencies_improved import validate_limit_parameter
        
        # Valid limit
        result = validate_limit_parameter(50)
        assert result == 50
        
        # Default limit
        result = validate_limit_parameter()
        assert result == 100
    
    async def test_validate_hours_parameter(self):
        """Test hours parameter validation."""
        from app.dependencies_improved import validate_hours_parameter
        
        # Valid hours
        result = validate_hours_parameter(48)
        assert result == 48
        
        # Default hours
        result = validate_hours_parameter()
        assert result == 24


# Integration tests
class TestIntegration(TestViolationsEndpoints):
    """Integration tests for violations endpoints."""
    
    @pytest.mark.asyncio
    async def test_full_violations_workflow(
        self,
        client,
        mock_database,
        mock_cache,
        sample_violations_data
    ):
        """Test complete violations workflow."""
        with patch('app.routers.violations_improved.ViolationQueries.get_live_violations') as mock_get:
            mock_get.return_value = sample_violations_data
            
            # Test live violations
            response = client.get("/api/violations/live?limit=5&hours=12")
            assert response.status_code == status.HTTP_200_OK
            
            # Test hourly trend
            with patch('app.routers.violations_improved.ViolationQueries.get_hourly_trend') as mock_trend:
                mock_trend.return_value = []
                response = client.get("/api/violations/hourly-trend?hours=12")
                assert response.status_code == status.HTTP_200_OK
            
            # Test violation stats
            with patch('app.routers.violations_improved.ViolationQueries.get_violation_stats') as mock_stats:
                mock_stats.return_value = {"total_violations": 0}
                response = client.get("/api/violations/stats?hours=12")
                assert response.status_code == status.HTTP_200_OK


# Performance tests
class TestPerformance(TestViolationsEndpoints):
    """Performance tests for violations endpoints."""
    
    @pytest.mark.asyncio
    async def test_response_time(
        self,
        client,
        mock_database,
        mock_cache,
        sample_violations_data
    ):
        """Test response time performance."""
        import time
        
        with patch('app.routers.violations_improved.ViolationQueries.get_live_violations') as mock_get:
            mock_get.return_value = sample_violations_data
            
            start_time = time.time()
            response = client.get("/api/violations/live?limit=1")
            end_time = time.time()
            
            response_time = end_time - start_time
            assert response.status_code == status.HTTP_200_OK
            assert response_time < 1.0  # Should respond within 1 second
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self,
        client,
        mock_database,
        mock_cache,
        sample_violations_data
    ):
        """Test concurrent request handling."""
        import asyncio
        
        with patch('app.routers.violations_improved.ViolationQueries.get_live_violations') as mock_get:
            mock_get.return_value = sample_violations_data
            
            async def make_request():
                response = client.get("/api/violations/live?limit=1")
                return response.status_code
            
            # Make 10 concurrent requests
            tasks = [make_request() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            
            # All requests should succeed
            assert all(status_code == status.HTTP_200_OK for status_code in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])





