#!/usr/bin/env python3
"""
Comprehensive test script for new Frigate Dashboard APIs.

Tests all new employee, zone, attendance, and dashboard APIs.
Verifies that any media URLs returned are actually accessible.
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
                 params: Optional[Dict] = None, data: Optional[Dict] = None, timeout: int = 10) -> Dict[str, Any]:
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

def run_comprehensive_tests():
    """Run comprehensive tests for all new APIs."""
    print("🧪 COMPREHENSIVE API TESTING - NEW FRIGATE DASHBOARD APIs")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing against: {API_BASE}")
    print()
    
    # Test results storage
    all_results = []
    
    # 1. Employee APIs
    print("👤 EMPLOYEE APIs")
    print("=" * 50)
    
    # Test employee current status (need to get a real employee name first)
    print("Getting employee list for testing...")
    try:
        # Try to get a list of employees from violations or timeline
        violations_response = requests.get(f"{API_BASE}/violations/live?limit=5", timeout=10)
        if violations_response.status_code == 200:
            violations_data = violations_response.json()
            if violations_data.get("data"):
                # Extract employee names from violations
                employee_names = set()
                for violation in violations_data["data"]:
                    if violation.get("employee_name") and violation["employee_name"] != "Unknown":
                        employee_names.add(violation["employee_name"])
                
                if employee_names:
                    test_employee = list(employee_names)[0]
                    print(f"Using employee '{test_employee}' for testing")
                else:
                    test_employee = "John Doe"  # Fallback
                    print(f"No employee names found, using fallback: {test_employee}")
            else:
                test_employee = "John Doe"
                print(f"No violation data, using fallback: {test_employee}")
        else:
            test_employee = "John Doe"
            print(f"Could not get violations, using fallback: {test_employee}")
    except Exception as e:
        test_employee = "John Doe"
        print(f"Error getting employee list: {e}, using fallback: {test_employee}")
    
    # Test employee current status
    result = test_endpoint("GET", f"/employees/{test_employee}/current-status", 
                          f"Employee current status for {test_employee}")
    all_results.append(result)
    print_test_result(result)
    
    # Test employee work hours
    result = test_endpoint("GET", f"/employees/{test_employee}/work-hours", 
                          f"Employee work hours for {test_employee}")
    all_results.append(result)
    print_test_result(result)
    
    # Test employee breaks
    result = test_endpoint("GET", f"/employees/{test_employee}/breaks", 
                          f"Employee breaks for {test_employee}")
    all_results.append(result)
    print_test_result(result)
    
    # Test employee timeline
    result = test_endpoint("GET", f"/employees/{test_employee}/timeline", 
                          f"Employee timeline for {test_employee}")
    all_results.append(result)
    print_test_result(result)
    
    # Test employee movements
    result = test_endpoint("GET", f"/employees/{test_employee}/movements", 
                          f"Employee movements for {test_employee}")
    all_results.append(result)
    print_test_result(result)
    
    # 2. Zone APIs
    print("🏢 ZONE APIs")
    print("=" * 50)
    
    # Test zone occupancy
    result = test_endpoint("GET", "/zones/occupancy", "Zone occupancy (5 min threshold)")
    all_results.append(result)
    print_test_result(result)
    
    # Test zone occupancy with custom threshold
    result = test_endpoint("GET", "/zones/occupancy", "Zone occupancy (10 min threshold)", 
                          params={"minutes_threshold": 10})
    all_results.append(result)
    print_test_result(result)
    
    # Test zone activity heatmap
    result = test_endpoint("GET", "/zones/activity-heatmap", "Zone activity heatmap (today)")
    all_results.append(result)
    print_test_result(result)
    
    # Test zone activity heatmap for yesterday
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    result = test_endpoint("GET", "/zones/activity-heatmap", f"Zone activity heatmap ({yesterday})", 
                          params={"date": yesterday})
    all_results.append(result)
    print_test_result(result)
    
    # Test zone stats
    result = test_endpoint("GET", "/zones/stats", "Zone statistics (today)")
    all_results.append(result)
    print_test_result(result)
    
    # 3. Attendance APIs
    print("📊 ATTENDANCE APIs")
    print("=" * 50)
    
    # Test daily attendance
    result = test_endpoint("GET", "/attendance/daily", "Daily attendance (today)")
    all_results.append(result)
    print_test_result(result)
    
    # Test daily attendance for yesterday
    result = test_endpoint("GET", "/attendance/daily", f"Daily attendance ({yesterday})", 
                          params={"date": yesterday})
    all_results.append(result)
    print_test_result(result)
    
    # Test attendance stats
    result = test_endpoint("GET", "/attendance/stats", "Attendance statistics (last 7 days)")
    all_results.append(result)
    print_test_result(result)
    
    # Test attendance stats for specific date range
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    result = test_endpoint("GET", "/attendance/stats", f"Attendance statistics ({week_ago} to today)", 
                          params={"start_date": week_ago, "end_date": datetime.now().strftime('%Y-%m-%d')})
    all_results.append(result)
    print_test_result(result)
    
    # 4. Dashboard APIs
    print("📈 DASHBOARD APIs")
    print("=" * 50)
    
    # Test dashboard summary
    result = test_endpoint("GET", "/dashboard/summary", "Dashboard summary (today)")
    all_results.append(result)
    print_test_result(result)
    
    # Test dashboard summary for yesterday
    result = test_endpoint("GET", "/dashboard/summary", f"Dashboard summary ({yesterday})", 
                          params={"date": yesterday})
    all_results.append(result)
    print_test_result(result)
    
    # 5. Violation Duration API (if implemented)
    print("🚨 VIOLATION APIs")
    print("=" * 50)
    
    # Test violation duration (need a real violation ID)
    try:
        violations_response = requests.get(f"{API_BASE}/violations/live?limit=1", timeout=10)
        if violations_response.status_code == 200:
            violations_data = violations_response.json()
            if violations_data.get("data") and violations_data["data"]:
                violation_id = violations_data["data"][0].get("id")
                if violation_id:
                    result = test_endpoint("GET", f"/violations/{violation_id}/duration", 
                                          f"Violation duration for {violation_id}")
                    all_results.append(result)
                    print_test_result(result)
                else:
                    print("❌ No violation ID found for duration test")
            else:
                print("❌ No violation data found for duration test")
        else:
            print("❌ Could not fetch violations for duration test")
    except Exception as e:
        print(f"❌ Error getting violation ID: {e}")
    
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
    run_comprehensive_tests()
