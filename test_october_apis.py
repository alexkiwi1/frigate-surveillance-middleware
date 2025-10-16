#!/usr/bin/env python3
"""
Comprehensive test script for Frigate Dashboard APIs from October 1, 2025 to today.

Tests all APIs with historical data and verifies media URL accessibility.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Configuration
MIDDLEWARE_BASE = "http://localhost:5002"
API_BASE = f"{MIDDLEWARE_BASE}/api"

def check_url_accessibility(url: str, description: str = "URL") -> Dict[str, Any]:
    """Check if a URL is accessible and return status details."""
    try:
        response = requests.get(url, timeout=5, stream=True)
        status = "✅ WORKING" if response.status_code == 200 else f"❌ FAILED ({response.status_code})"
        size = response.headers.get('Content-Length', 'N/A')
        content_type = response.headers.get('Content-Type', 'N/A')
        response.close()
        return {
            "status": status,
            "size": size,
            "content_type": content_type,
            "accessible": response.status_code == 200
        }
    except requests.exceptions.Timeout:
        return {"status": "❌ FAILED (Timeout)", "size": "N/A", "content_type": "N/A", "accessible": False}
    except requests.exceptions.RequestException as e:
        return {"status": f"❌ FAILED ({e})", "size": "N/A", "content_type": "N/A", "accessible": False}

def test_endpoint(method: str, endpoint: str, description: str, expected_status: int = 200, 
                 params: Optional[Dict] = None, data: Optional[Dict] = None, timeout: int = 15) -> Dict[str, Any]:
    """Test an API endpoint and return results."""
    url = f"{API_BASE}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            response = requests.request(method, url, params=params, json=data, timeout=timeout)
        
        success = response.status_code == expected_status
        result = {
            "endpoint": endpoint,
            "description": description,
            "status_code": response.status_code,
            "expected_status": expected_status,
            "success": success,
            "response_time": response.elapsed.total_seconds(),
            "data": None,
            "media_urls": [],
            "media_tests": []
        }
        
        if success:
            try:
                json_data = response.json()
                result["data"] = json_data
                
                # Extract and test media URLs
                media_urls = extract_media_urls(json_data)
                result["media_urls"] = media_urls
                
                for media_url in media_urls:
                    media_test = check_url_accessibility(media_url["url"], media_url["type"])
                    result["media_tests"].append({
                        "url": media_url["url"],
                        "type": media_url["type"],
                        "test_result": media_test
                    })
                    
            except json.JSONDecodeError:
                result["error"] = "Invalid JSON response"
        else:
            result["error"] = f"Expected {expected_status}, got {response.status_code}"
            
        return result
        
    except requests.exceptions.Timeout:
        return {
            "endpoint": endpoint,
            "description": description,
            "success": False,
            "error": f"Request timeout (>{timeout}s)",
            "status_code": None,
            "expected_status": expected_status,
            "response_time": timeout,
            "media_urls": [],
            "media_tests": []
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "description": description,
            "success": False,
            "error": str(e),
            "status_code": None,
            "expected_status": expected_status,
            "response_time": 0,
            "media_urls": [],
            "media_tests": []
        }

def extract_media_urls(data: Any, prefix: str = "") -> List[Dict[str, str]]:
    """Recursively extract media URLs from API response data."""
    media_urls = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ['video_url', 'thumbnail_url', 'snapshot_url', 'image_url']:
                if isinstance(value, str) and value.startswith('http'):
                    media_urls.append({
                        "url": value,
                        "type": key.replace('_url', ''),
                        "path": f"{prefix}.{key}" if prefix else key
                    })
            else:
                media_urls.extend(extract_media_urls(value, f"{prefix}.{key}" if prefix else key))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            media_urls.extend(extract_media_urls(item, f"{prefix}[{i}]" if prefix else f"[{i}]"))
    
    return media_urls

def print_test_result(result: Dict[str, Any]):
    """Print formatted test result."""
    status_icon = "✅" if result["success"] else "❌"
    print(f"{status_icon} {result['description']}")
    print(f"   Endpoint: {result['endpoint']}")
    print(f"   Status: {result.get('status_code', 'N/A')} (expected: {result.get('expected_status', 'N/A')})")
    print(f"   Response Time: {result.get('response_time', 0):.2f}s")
    
    if result.get("error"):
        print(f"   Error: {result['error']}")
    
    if result["media_urls"]:
        print(f"   Media URLs Found: {len(result['media_urls'])}")
        for media_url in result["media_urls"]:
            print(f"     - {media_url['type']}: {media_url['url']}")
    
    if result["media_tests"]:
        print(f"   Media Accessibility Tests:")
        for media_test in result["media_tests"]:
            test_result = media_test["test_result"]
            print(f"     - {media_test['type']}: {test_result['status']}")
            if test_result["accessible"]:
                print(f"       Size: {test_result['size']} bytes")
                print(f"       Type: {test_result['content_type']}")
    
    print()

def get_employee_names() -> List[str]:
    """Get list of employee names from violations API."""
    try:
        response = requests.get(f"{API_BASE}/violations/live?limit=10", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                employees = set()
                for violation in data["data"]:
                    if violation.get("employee_name") and violation["employee_name"] != "Unknown":
                        employees.add(violation["employee_name"])
                return list(employees)
    except Exception as e:
        print(f"Error getting employee names: {e}")
    
    return ["John Doe", "Jane Smith", "Mike Johnson"]  # Fallback names

def get_violation_ids() -> List[str]:
    """Get list of violation IDs for testing."""
    try:
        response = requests.get(f"{API_BASE}/violations/live?limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                return [v.get("id") for v in data["data"] if v.get("id")]
    except Exception as e:
        print(f"Error getting violation IDs: {e}")
    
    return ["1760634610.968158-zy09rd"]  # Fallback ID

def run_october_tests():
    """Run comprehensive tests for all APIs from October 1, 2025 to today."""
    print("🧪 COMPREHENSIVE API TESTING - OCTOBER 1, 2025 TO TODAY")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing against: {API_BASE}")
    print()
    
    # Get test data
    employee_names = get_employee_names()
    violation_ids = get_violation_ids()
    
    print(f"Using {len(employee_names)} employees for testing: {employee_names[:3]}...")
    print(f"Using {len(violation_ids)} violation IDs for testing: {violation_ids[:3]}...")
    print()
    
    # Test results storage
    all_results = []
    
    # Test dates
    october_1 = "2025-10-01"
    october_15 = "2025-10-15"
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Employee APIs
    print("👤 EMPLOYEE APIs")
    print("=" * 50)
    
    for employee in employee_names[:2]:  # Test first 2 employees
        # Current status
        result = test_endpoint("GET", f"/employees/{employee}/current-status", 
                              f"Employee current status for {employee}")
        all_results.append(result)
        print_test_result(result)
        
        # Work hours for different dates
        for date in [october_1, october_15, today]:
            result = test_endpoint("GET", f"/employees/{employee}/work-hours", 
                                  f"Employee work hours for {employee} on {date}", 
                                  params={"date": date})
            all_results.append(result)
            print_test_result(result)
        
        # Breaks for different dates
        for date in [october_1, october_15, today]:
            result = test_endpoint("GET", f"/employees/{employee}/breaks", 
                                  f"Employee breaks for {employee} on {date}", 
                                  params={"date": date})
            all_results.append(result)
            print_test_result(result)
        
        # Timeline for different dates
        for date in [october_1, october_15, today]:
            result = test_endpoint("GET", f"/employees/{employee}/timeline", 
                                  f"Employee timeline for {employee} on {date}", 
                                  params={"date": date})
            all_results.append(result)
            print_test_result(result)
        
        # Movements for different dates
        for date in [october_1, october_15, today]:
            result = test_endpoint("GET", f"/employees/{employee}/movements", 
                                  f"Employee movements for {employee} on {date}", 
                                  params={"date": date})
            all_results.append(result)
            print_test_result(result)
    
    # 2. Zone APIs
    print("🏢 ZONE APIs")
    print("=" * 50)
    
    # Zone occupancy with different thresholds
    for threshold in [5, 10, 30]:
        result = test_endpoint("GET", "/zones/occupancy", 
                              f"Zone occupancy ({threshold} min threshold)", 
                              params={"minutes_threshold": threshold})
        all_results.append(result)
        print_test_result(result)
    
    # Zone activity heatmap for different dates
    for date in [october_1, october_15, today]:
        result = test_endpoint("GET", "/zones/activity-heatmap", 
                              f"Zone activity heatmap for {date}", 
                              params={"date": date})
        all_results.append(result)
        print_test_result(result)
    
    # Zone statistics for different dates
    for date in [october_1, october_15, today]:
        result = test_endpoint("GET", "/zones/stats", 
                              f"Zone statistics for {date}", 
                              params={"date": date})
        all_results.append(result)
        print_test_result(result)
    
    # 3. Attendance APIs
    print("📊 ATTENDANCE APIs")
    print("=" * 50)
    
    # Daily attendance for different dates
    for date in [october_1, october_15, today]:
        result = test_endpoint("GET", "/attendance/daily", 
                              f"Daily attendance for {date}", 
                              params={"date": date})
        all_results.append(result)
        print_test_result(result)
    
    # Attendance statistics for different date ranges
    date_ranges = [
        (october_1, today),
        (october_15, today),
        (f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}", today)
    ]
    
    for start_date, end_date in date_ranges:
        result = test_endpoint("GET", "/attendance/stats", 
                              f"Attendance statistics from {start_date} to {end_date}", 
                              params={"start_date": start_date, "end_date": end_date})
        all_results.append(result)
        print_test_result(result)
    
    # 4. Dashboard APIs
    print("📈 DASHBOARD APIs")
    print("=" * 50)
    
    # Dashboard summary for different dates
    for date in [october_1, october_15, today]:
        result = test_endpoint("GET", "/dashboard/summary", 
                              f"Dashboard summary for {date}", 
                              params={"date": date})
        all_results.append(result)
        print_test_result(result)
    
    # 5. Violation APIs
    print("🚨 VIOLATION APIs")
    print("=" * 50)
    
    # Live violations
    result = test_endpoint("GET", "/violations/live", 
                          "Live violations", 
                          params={"limit": 10})
    all_results.append(result)
    print_test_result(result)
    
    # Hourly trends for different periods
    for hours in [24, 48, 168]:  # 1 day, 2 days, 1 week
        result = test_endpoint("GET", "/violations/hourly-trend", 
                              f"Hourly trend for {hours} hours", 
                              params={"hours": hours}, timeout=30)
        all_results.append(result)
        print_test_result(result)
    
    # Violation duration for each violation ID
    for violation_id in violation_ids:
        result = test_endpoint("GET", f"/violations/{violation_id}/duration", 
                              f"Violation duration for {violation_id}")
        all_results.append(result)
        print_test_result(result)
    
    # 6. Recent Media APIs
    print("🎬 RECENT MEDIA APIs")
    print("=" * 50)
    
    # Recent clips
    result = test_endpoint("GET", "/recent-media/clips", 
                          "Recent clips", 
                          params={"limit": 5})
    all_results.append(result)
    print_test_result(result)
    
    # Recent recordings
    result = test_endpoint("GET", "/recent-media/recordings", 
                          "Recent recordings", 
                          params={"limit": 5})
    all_results.append(result)
    print_test_result(result)
    
    # Summary
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(all_results)
    successful_tests = sum(1 for r in all_results if r["success"])
    failed_tests = total_tests - successful_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    # Media URL summary
    total_media_urls = sum(len(r["media_urls"]) for r in all_results)
    accessible_media = sum(1 for r in all_results for mt in r["media_tests"] if mt["test_result"]["accessible"])
    failed_media = total_media_urls - accessible_media
    
    print(f"\nMedia URLs:")
    print(f"Total Found: {total_media_urls}")
    print(f"Accessible: {accessible_media} ✅")
    print(f"Failed: {failed_media} ❌")
    if total_media_urls > 0:
        print(f"Media Success Rate: {(accessible_media/total_media_urls)*100:.1f}%")
    
    # Failed tests details
    if failed_tests > 0:
        print(f"\n❌ FAILED TESTS:")
        for result in all_results:
            if not result["success"]:
                print(f"  - {result['description']}: {result.get('error', 'Unknown error')}")
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    run_october_tests()
