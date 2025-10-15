#!/usr/bin/env python3
"""
Comprehensive API Test Script for Frigate Dashboard Middleware
Tests all endpoints to ensure they're working correctly after performance fixes.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5002"
API_BASE = f"{BASE_URL}/api"

# Test results
results = []
total_tests = 0
passed_tests = 0

def test_endpoint(method, endpoint, description, expected_status=200, params=None, data=None, base_url=None):
    """Test a single endpoint and record results."""
    global total_tests, passed_tests
    
    total_tests += 1
    if base_url:
        url = f"{base_url}{endpoint}"
    else:
        url = f"{API_BASE}{endpoint}"
    
    try:
        start_time = time.time()
        
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.request(method, url, params=params, json=data, timeout=10)
        
        response_time = time.time() - start_time
        status_code = response.status_code
        
        # Check if test passed
        passed = status_code == expected_status
        if passed:
            passed_tests += 1
        
        # Record result
        result = {
            "method": method,
            "endpoint": endpoint,
            "description": description,
            "status_code": status_code,
            "expected_status": expected_status,
            "response_time": f"{response_time:.3f}s",
            "passed": passed,
            "error": None
        }
        
        # Try to get response data for debugging
        try:
            response_data = response.json()
            if "data" in response_data:
                data_count = len(response_data["data"]) if isinstance(response_data["data"], list) else "N/A"
                result["data_count"] = data_count
        except:
            result["response_text"] = response.text[:100] + "..." if len(response.text) > 100 else response.text
        
        results.append(result)
        
        # Print result
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} {method} {endpoint} - {description}")
        print(f"   Status: {status_code} (expected: {expected_status})")
        print(f"   Time: {response_time:.3f}s")
        if not passed:
            print(f"   Error: HTTP {status_code}")
        print()
        
    except requests.exceptions.Timeout:
        result = {
            "method": method,
            "endpoint": endpoint,
            "description": description,
            "status_code": "TIMEOUT",
            "expected_status": expected_status,
            "response_time": "TIMEOUT",
            "passed": False,
            "error": "Request timeout (>10s)"
        }
        results.append(result)
        print(f"❌ {method} {endpoint} - {description}")
        print(f"   Error: Request timeout (>10s)")
        print()
    except Exception as e:
        result = {
            "method": method,
            "endpoint": endpoint,
            "description": description,
            "status_code": "ERROR",
            "expected_status": expected_status,
            "response_time": "ERROR",
            "passed": False,
            "error": str(e)
        }
        results.append(result)
        print(f"❌ {method} {endpoint} - {description}")
        print(f"   Error: {str(e)}")
        print()

def main():
    """Run comprehensive API tests."""
    print("🚀 FRIGATE DASHBOARD MIDDLEWARE - COMPREHENSIVE API TEST")
    print("=" * 60)
    print(f"Testing API at: {API_BASE}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Core API Tests
    print("📊 CORE API ENDPOINTS")
    print("-" * 30)
    test_endpoint("GET", "/", "Root endpoint", base_url=BASE_URL)
    test_endpoint("GET", "/health", "Health check", base_url=BASE_URL)
    test_endpoint("GET", "/api/info", "API information", base_url=BASE_URL)
    test_endpoint("GET", "/api/status", "System status", base_url=BASE_URL)
    test_endpoint("GET", "/api/cache/stats", "Cache statistics", base_url=BASE_URL)
    
    # Violations API Tests
    print("🚨 VIOLATIONS API")
    print("-" * 20)
    test_endpoint("GET", "/violations/live", "Live violations (default)")
    test_endpoint("GET", "/violations/live", "Live violations (limit=1)", params={"limit": 1})
    test_endpoint("GET", "/violations/live", "Live violations (limit=5)", params={"limit": 5})
    test_endpoint("GET", "/violations/live", "Live violations (camera filter)", params={"camera": "employees_01"})
    test_endpoint("GET", "/violations/live", "Live violations (hours=12)", params={"hours": 12})
    test_endpoint("GET", "/violations/hourly-trend", "Hourly trend (default)")
    test_endpoint("GET", "/violations/hourly-trend", "Hourly trend (48 hours)", params={"hours": 48})
    test_endpoint("GET", "/violations/stats", "Violation statistics")
    
    # Employees API Tests
    print("👥 EMPLOYEES API")
    print("-" * 20)
    test_endpoint("GET", "/employees/stats", "Employee statistics")
    test_endpoint("GET", "/employees/search", "Employee search", params={"query": "test"})
    test_endpoint("GET", "/employees/Unknown/violations", "Employee violations")
    test_endpoint("GET", "/employees/Unknown/activity", "Employee activity")
    
    # Cameras API Tests
    print("📹 CAMERAS API")
    print("-" * 20)
    test_endpoint("GET", "/cameras/list", "List all cameras")
    test_endpoint("GET", "/cameras/summary", "Camera summary")
    test_endpoint("GET", "/cameras/employees_01/summary", "Single camera summary")
    test_endpoint("GET", "/cameras/employees_01/activity", "Camera activity")
    test_endpoint("GET", "/cameras/employees_01/violations", "Camera violations")
    test_endpoint("GET", "/cameras/employees_01/status", "Camera status")
    
    # WebSocket Tests (basic connectivity)
    print("🔌 WEBSOCKET API")
    print("-" * 20)
    test_endpoint("GET", "/ws/broadcast", "WebSocket broadcast endpoint", expected_status=426, base_url=BASE_URL)  # 426 = Upgrade Required
    test_endpoint("GET", "/ws/status", "WebSocket status endpoint", expected_status=426, base_url=BASE_URL)  # 426 = Upgrade Required
    
    # Admin API Tests
    print("⚙️ ADMIN API")
    print("-" * 15)
    test_endpoint("POST", "/api/admin/restart-task/violation_polling", "Restart violation polling task", base_url=BASE_URL)
    test_endpoint("GET", "/api/violations/cache", "Violations cache info", base_url=BASE_URL)
    test_endpoint("GET", "/api/employees/cache", "Employees cache info", base_url=BASE_URL)
    test_endpoint("GET", "/api/cameras/cache", "Cameras cache info", base_url=BASE_URL)
    
    # Performance Tests
    print("⚡ PERFORMANCE TESTS")
    print("-" * 25)
    
    # Test violations endpoint performance multiple times
    print("Testing violations endpoint performance (5 iterations):")
    violation_times = []
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{API_BASE}/violations/live?limit=1", timeout=10)
        response_time = time.time() - start_time
        violation_times.append(response_time)
        print(f"  Iteration {i+1}: {response_time:.3f}s (Status: {response.status_code})")
    
    avg_time = sum(violation_times) / len(violation_times)
    max_time = max(violation_times)
    min_time = min(violation_times)
    
    print(f"  Average: {avg_time:.3f}s")
    print(f"  Min: {min_time:.3f}s")
    print(f"  Max: {max_time:.3f}s")
    print()
    
    # Summary
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print()
    
    # Performance summary
    print("⚡ PERFORMANCE SUMMARY")
    print("-" * 25)
    if avg_time < 0.1:
        print(f"✅ EXCELLENT: Average response time {avg_time:.3f}s")
    elif avg_time < 0.5:
        print(f"✅ GOOD: Average response time {avg_time:.3f}s")
    elif avg_time < 1.0:
        print(f"⚠️ ACCEPTABLE: Average response time {avg_time:.3f}s")
    else:
        print(f"❌ SLOW: Average response time {avg_time:.3f}s")
    
    print(f"Response time range: {min_time:.3f}s - {max_time:.3f}s")
    print()
    
    # Failed tests details
    failed_tests = [r for r in results if not r["passed"]]
    if failed_tests:
        print("❌ FAILED TESTS DETAILS")
        print("-" * 30)
        for test in failed_tests:
            print(f"• {test['method']} {test['endpoint']}")
            print(f"  Status: {test['status_code']} (expected: {test['expected_status']})")
            if test.get('error'):
                print(f"  Error: {test['error']}")
            print()
    
    print("🏁 Test completed!")
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
