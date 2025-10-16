#!/usr/bin/env python3
"""
Comprehensive Multi-Day API & Media Test Suite
Tests all APIs and media across different time periods to ensure 100% functionality
"""

import requests
import json
from datetime import datetime, timedelta
import time
import sys

API_BASE = "http://localhost:5002/api"
FRIGATE_BASE = "http://10.0.20.6:5001"

class TestResults:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_details = []
        self.start_time = time.time()
    
    def add_test(self, test_name, success, details=""):
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        self.test_details.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
    
    def get_summary(self):
        duration = time.time() - self.start_time
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        return {
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "success_rate": success_rate,
            "duration": duration
        }

def test_url(url, timeout=5):
    """Test a single URL and return status"""
    try:
        response = requests.head(url, timeout=timeout)
        return {
            'status': response.status_code,
            'size': response.headers.get('Content-Length', 'unknown'),
            'accessible': response.status_code == 200
        }
    except Exception as e:
        return {
            'status': 'error',
            'size': 'unknown',
            'accessible': False,
            'error': str(e)
        }

def test_api_endpoint(url, expected_status=200, params=None, method='GET'):
    """Test an API endpoint"""
    try:
        if method == 'POST':
            response = requests.post(url, params=params, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, params=params, timeout=10)
        else:
            response = requests.get(url, params=params, timeout=10)
        return {
            'status': response.status_code,
            'success': response.status_code == expected_status,
            'response_time': response.elapsed.total_seconds()
        }
    except Exception as e:
        return {
            'status': 'error',
            'success': False,
            'error': str(e)
        }

def main():
    print("🚀 COMPREHENSIVE MULTI-DAY API & MEDIA TEST SUITE")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()
    
    results = TestResults()
    
    # Test 1: All Core API Endpoints
    print("📊 TEST 1: CORE API ENDPOINTS")
    print("-" * 40)
    
    core_endpoints = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/api/info", "API information"),
        ("/api/status", "System status"),
        ("/api/cache/stats", "Cache statistics")
    ]
    
    for endpoint, description in core_endpoints:
        result = test_api_endpoint(f"{API_BASE.replace('/api', '')}{endpoint}")
        results.add_test(f"GET {endpoint}", result['success'], 
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
    
    print()
    
    # Test 2: Violations API with Different Time Periods
    print("📊 TEST 2: VIOLATIONS API - MULTI-DAY TESTING")
    print("-" * 40)
    
    time_periods = [
        (1, "Last 1 hour"),
        (6, "Last 6 hours"),
        (12, "Last 12 hours"),
        (24, "Last 24 hours"),
        (48, "Last 48 hours"),
        (72, "Last 72 hours")
    ]
    
    for hours, description in time_periods:
        # Test live violations
        result = test_api_endpoint(f"{API_BASE}/violations/live", params={"hours": hours})
        results.add_test(f"Live violations ({description})", result['success'],
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
        
        # Test hourly trend
        result = test_api_endpoint(f"{API_BASE}/violations/hourly-trend", params={"hours": hours})
        results.add_test(f"Hourly trend ({description})", result['success'],
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
    
    # Test violations with different limits
    for limit in [1, 5, 10, 25, 50, 100]:
        result = test_api_endpoint(f"{API_BASE}/violations/live", params={"limit": limit})
        results.add_test(f"Live violations (limit={limit})", result['success'],
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
    
    print()
    
    # Test 3: Employees API
    print("📊 TEST 3: EMPLOYEES API")
    print("-" * 40)
    
    employee_endpoints = [
        ("/employees/stats", "Employee statistics"),
        ("/employees/search?query=test", "Employee search"),
        ("/employees/Unknown/violations", "Employee violations"),
        ("/employees/Unknown/activity", "Employee activity")
    ]
    
    for endpoint, description in employee_endpoints:
        result = test_api_endpoint(f"{API_BASE}{endpoint}")
        results.add_test(f"GET {endpoint}", result['success'],
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
    
    print()
    
    # Test 4: Cameras API
    print("📊 TEST 4: CAMERAS API")
    print("-" * 40)
    
    camera_endpoints = [
        ("/cameras/list", "List all cameras"),
        ("/cameras/summary", "Camera summary"),
        ("/cameras/employees_01/summary", "Single camera summary"),
        ("/cameras/employees_01/activity", "Camera activity"),
        ("/cameras/employees_01/violations", "Camera violations"),
        ("/cameras/employees_01/status", "Camera status")
    ]
    
    for endpoint, description in camera_endpoints:
        result = test_api_endpoint(f"{API_BASE}{endpoint}")
        results.add_test(f"GET {endpoint}", result['success'],
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
    
    print()
    
    # Test 5: Recent Media API
    print("📊 TEST 5: RECENT MEDIA API")
    print("-" * 40)
    
    media_endpoints = [
        ("/recent-media/clips?limit=5", "Recent clips"),
        ("/recent-media/recordings?limit=5", "Recent recordings"),
        ("/recent-media/test-media?clip_id=1760587749.98418-z4k0d1", "Media URL testing")
    ]
    
    for endpoint, description in media_endpoints:
        result = test_api_endpoint(f"{API_BASE}{endpoint}")
        results.add_test(f"GET {endpoint}", result['success'],
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
    
    print()
    
    # Test 6: WebSocket & Admin API
    print("📊 TEST 6: WEBSOCKET & ADMIN API")
    print("-" * 40)
    
    admin_endpoints = [
        ("/ws/status", "WebSocket status", "GET"),
        ("/admin/restart-task/violation_polling", "Restart task", "POST"),
        ("/violations/cache", "Clear violations cache", "DELETE"),
        ("/employees/cache", "Clear employees cache", "DELETE"),
        ("/cameras/cache", "Clear cameras cache", "DELETE")
    ]
    
    for endpoint, description, method in admin_endpoints:
        if endpoint.startswith("/ws/"):
            result = test_api_endpoint(f"{API_BASE.replace('/api', '')}{endpoint}", method=method)
        elif endpoint.startswith("/admin/"):
            result = test_api_endpoint(f"{API_BASE}{endpoint}", method=method)
        else:
            result = test_api_endpoint(f"{API_BASE}{endpoint}", method=method)
        results.add_test(f"{method} {endpoint}", result['success'],
                        f"Status: {result['status']}, Time: {result.get('response_time', 0):.3f}s")
    
    print()
    
    # Test 7: Media URL Accessibility - Recent Data
    print("📊 TEST 7: MEDIA URL ACCESSIBILITY - RECENT DATA")
    print("-" * 40)
    
    # Get recent clips and test their media URLs
    try:
        response = requests.get(f"{FRIGATE_BASE}/api/clips?limit=5", timeout=10)
        if response.status_code == 200:
            clips = response.json().get('clips', [])
            results.add_test("Fetch recent clips from Frigate", True, f"Found {len(clips)} clips")
            
            for i, clip in enumerate(clips[:3], 1):  # Test first 3 clips
                clip_id = clip.get('id')
                if clip_id:
                    # Test video URL
                    video_url = f"{FRIGATE_BASE}{clip.get('video_url', '')}"
                    video_result = test_url(video_url)
                    results.add_test(f"Clip {i} Video URL", video_result['accessible'],
                                   f"Status: {video_result['status']}, Size: {video_result['size']}")
                    
                    # Test thumbnail URL
                    thumb_url = f"{FRIGATE_BASE}{clip.get('thumbnail_url', '')}"
                    thumb_result = test_url(thumb_url)
                    results.add_test(f"Clip {i} Thumbnail URL", thumb_result['accessible'],
                                   f"Status: {thumb_result['status']}, Size: {thumb_result['size']}")
        else:
            results.add_test("Fetch recent clips from Frigate", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_test("Fetch recent clips from Frigate", False, f"Error: {str(e)}")
    
    # Get recent recordings and test their video URLs
    try:
        response = requests.get(f"{FRIGATE_BASE}/api/recordings?limit=5", timeout=10)
        if response.status_code == 200:
            recordings = response.json().get('recordings', [])
            results.add_test("Fetch recent recordings from Frigate", True, f"Found {len(recordings)} recordings")
            
            for i, recording in enumerate(recordings[:3], 1):  # Test first 3 recordings
                video_url = f"{FRIGATE_BASE}{recording.get('video_url', '')}"
                video_result = test_url(video_url)
                results.add_test(f"Recording {i} Video URL", video_result['accessible'],
                               f"Status: {video_result['status']}, Size: {video_result['size']}")
        else:
            results.add_test("Fetch recent recordings from Frigate", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_test("Fetch recent recordings from Frigate", False, f"Error: {str(e)}")
    
    print()
    
    # Test 8: Performance Testing
    print("📊 TEST 8: PERFORMANCE TESTING")
    print("-" * 40)
    
    performance_endpoints = [
        f"{API_BASE}/violations/live?limit=10",
        f"{API_BASE}/cameras/summary",
        f"{API_BASE}/employees/stats"
    ]
    
    for endpoint in performance_endpoints:
        times = []
        for i in range(5):
            result = test_api_endpoint(endpoint)
            if result['success']:
                times.append(result.get('response_time', 0))
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            results.add_test(f"Performance: {endpoint.split('/')[-1]}", True,
                           f"Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")
        else:
            results.add_test(f"Performance: {endpoint.split('/')[-1]}", False, "All requests failed")
    
    print()
    
    # Test 9: Error Handling
    print("📊 TEST 9: ERROR HANDLING")
    print("-" * 40)
    
    error_tests = [
        (f"{API_BASE}/violations/live?limit=999999", "Large limit parameter"),
        (f"{API_BASE}/violations/live?hours=999999", "Large hours parameter"),
        (f"{API_BASE}/cameras/nonexistent/summary", "Non-existent camera"),
        (f"{API_BASE}/employees/nonexistent/violations", "Non-existent employee")
    ]
    
    for endpoint, description in error_tests:
        result = test_api_endpoint(endpoint)
        # For error handling, we expect either 200 (with empty results) or 404/400 (proper error)
        success = result['status'] in [200, 404, 400, 422]
        results.add_test(f"Error handling: {description}", success,
                        f"Status: {result['status']} (expected: 200/404/400/422)")
    
    print()
    
    # Final Summary
    summary = results.get_summary()
    print("=" * 60)
    print("📋 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Duration: {summary['duration']:.2f} seconds")
    print()
    
    if summary['success_rate'] == 100.0:
        print("🎉 ALL TESTS PASSED - 100% SUCCESS RATE!")
        print("✅ The Frigate Dashboard Middleware is fully functional!")
    elif summary['success_rate'] >= 95.0:
        print("✅ EXCELLENT - Near perfect success rate!")
    elif summary['success_rate'] >= 90.0:
        print("⚠️  GOOD - Most tests passed, minor issues detected")
    else:
        print("❌ ISSUES DETECTED - Some tests failed")
    
    print()
    print("🏁 Comprehensive test completed!")
    
    return summary['success_rate'] == 100.0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
