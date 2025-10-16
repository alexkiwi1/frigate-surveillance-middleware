#!/usr/bin/env python3
"""
Daily API testing script for Frigate Dashboard from October 1, 2025 to today.

Tests all APIs day by day and verifies media URL accessibility.
Generates detailed report for each day.
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

def test_daily_apis(date: str) -> Dict[str, Any]:
    """Test all APIs for a specific date."""
    print(f"\n📅 TESTING APIS FOR {date}")
    print("=" * 50)
    
    results = {
        "date": date,
        "apis": {},
        "summary": {
            "total_tests": 0,
            "successful": 0,
            "failed": 0,
            "media_urls_found": 0,
            "media_accessible": 0
        }
    }
    
    # 1. Employee APIs
    print("👤 EMPLOYEE APIs")
    print("-" * 20)
    
    # Get employee names from violations
    try:
        violations_response = requests.get(f"{API_BASE}/violations/live?limit=5", timeout=10)
        if violations_response.status_code == 200:
            violations_data = violations_response.json()
            if violations_data.get("data"):
                employees = set()
                for violation in violations_data["data"]:
                    if violation.get("employee_name") and violation["employee_name"] != "Unknown":
                        employees.add(violation["employee_name"])
                employee_names = list(employees)[:2]  # Test first 2 employees
            else:
                employee_names = ["John Doe", "Jane Smith"]
        else:
            employee_names = ["John Doe", "Jane Smith"]
    except:
        employee_names = ["John Doe", "Jane Smith"]
    
    for employee in employee_names:
        # Current status
        result = test_endpoint("GET", f"/employees/{employee}/current-status", 
                              f"Current status for {employee}")
        results["apis"][f"employee_current_status_{employee}"] = result
        print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
        
        # Work hours
        result = test_endpoint("GET", f"/employees/{employee}/work-hours", 
                              f"Work hours for {employee}", params={"date": date})
        results["apis"][f"employee_work_hours_{employee}"] = result
        print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
        
        # Breaks
        result = test_endpoint("GET", f"/employees/{employee}/breaks", 
                              f"Breaks for {employee}", params={"date": date})
        results["apis"][f"employee_breaks_{employee}"] = result
        print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
        
        # Timeline
        result = test_endpoint("GET", f"/employees/{employee}/timeline", 
                              f"Timeline for {employee}", params={"date": date})
        results["apis"][f"employee_timeline_{employee}"] = result
        print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
        
        # Movements
        result = test_endpoint("GET", f"/employees/{employee}/movements", 
                              f"Movements for {employee}", params={"date": date})
        results["apis"][f"employee_movements_{employee}"] = result
        print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # 2. Zone APIs
    print("\n🏢 ZONE APIs")
    print("-" * 20)
    
    # Zone occupancy
    result = test_endpoint("GET", "/zones/occupancy", 
                          "Zone occupancy", params={"minutes_threshold": 5})
    results["apis"]["zone_occupancy"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # Zone activity heatmap
    result = test_endpoint("GET", "/zones/activity-heatmap", 
                          "Zone activity heatmap", params={"date": date})
    results["apis"]["zone_heatmap"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # Zone statistics
    result = test_endpoint("GET", "/zones/stats", 
                          "Zone statistics", params={"date": date})
    results["apis"]["zone_stats"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # 3. Attendance APIs
    print("\n📊 ATTENDANCE APIs")
    print("-" * 20)
    
    # Daily attendance
    result = test_endpoint("GET", "/attendance/daily", 
                          "Daily attendance", params={"date": date})
    results["apis"]["attendance_daily"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # Attendance statistics
    result = test_endpoint("GET", "/attendance/stats", 
                          "Attendance statistics", params={"start_date": date, "end_date": date})
    results["apis"]["attendance_stats"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # 4. Dashboard APIs
    print("\n📈 DASHBOARD APIs")
    print("-" * 20)
    
    # Dashboard summary
    result = test_endpoint("GET", "/dashboard/summary", 
                          "Dashboard summary", params={"date": date})
    results["apis"]["dashboard_summary"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # 5. Violation APIs
    print("\n🚨 VIOLATION APIs")
    print("-" * 20)
    
    # Live violations
    result = test_endpoint("GET", "/violations/live", 
                          "Live violations", params={"limit": 10})
    results["apis"]["violations_live"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # Hourly trend
    result = test_endpoint("GET", "/violations/hourly-trend", 
                          "Hourly trend", params={"hours": 24}, timeout=30)
    results["apis"]["violations_hourly_trend"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # 6. Media APIs
    print("\n🎬 MEDIA APIs")
    print("-" * 20)
    
    # Recent clips
    result = test_endpoint("GET", "/recent-media/clips", 
                          "Recent clips", params={"limit": 5})
    results["apis"]["recent_clips"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # Recent recordings
    result = test_endpoint("GET", "/recent-media/recordings", 
                          "Recent recordings", params={"limit": 5})
    results["apis"]["recent_recordings"] = result
    print(f"  {'✅' if result['success'] else '❌'} {result['description']}")
    
    # Calculate summary
    total_tests = len(results["apis"])
    successful = sum(1 for api in results["apis"].values() if api["success"])
    failed = total_tests - successful
    
    total_media_urls = sum(len(api["media_urls"]) for api in results["apis"].values())
    accessible_media = sum(1 for api in results["apis"].values() 
                          for mt in api["media_tests"] if mt["test_result"]["accessible"])
    
    results["summary"] = {
        "total_tests": total_tests,
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / total_tests * 100) if total_tests > 0 else 0,
        "media_urls_found": total_media_urls,
        "media_accessible": accessible_media,
        "media_success_rate": (accessible_media / total_media_urls * 100) if total_media_urls > 0 else 0
    }
    
    print(f"\n📊 SUMMARY FOR {date}")
    print(f"  APIs: {successful}/{total_tests} working ({results['summary']['success_rate']:.1f}%)")
    print(f"  Media: {accessible_media}/{total_media_urls} accessible ({results['summary']['media_success_rate']:.1f}%)")
    
    return results

def run_daily_tests():
    """Run daily tests from October 1, 2025 to today."""
    print("🧪 DAILY API TESTING - OCTOBER 1, 2025 TO TODAY")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing against: {API_BASE}")
    print()
    
    # Generate date range
    start_date = datetime(2025, 10, 1)
    end_date = datetime.now()
    
    all_results = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        day_results = test_daily_apis(date_str)
        all_results.append(day_results)
        current_date += timedelta(days=1)
    
    # Generate final report
    print("\n" + "=" * 70)
    print("📊 FINAL DAILY REPORT")
    print("=" * 70)
    
    total_days = len(all_results)
    total_apis = sum(r["summary"]["total_tests"] for r in all_results)
    total_successful = sum(r["summary"]["successful"] for r in all_results)
    total_media_urls = sum(r["summary"]["media_urls_found"] for r in all_results)
    total_accessible_media = sum(r["summary"]["media_accessible"] for r in all_results)
    
    print(f"Total Days Tested: {total_days}")
    print(f"Total API Tests: {total_apis}")
    print(f"Successful API Tests: {total_successful} ({(total_successful/total_apis*100):.1f}%)")
    print(f"Total Media URLs Found: {total_media_urls}")
    print(f"Accessible Media URLs: {total_accessible_media} ({(total_accessible_media/total_media_urls*100):.1f}%)")
    
    print(f"\n📅 DAILY BREAKDOWN:")
    print("-" * 50)
    
    for day_result in all_results:
        date = day_result["date"]
        summary = day_result["summary"]
        print(f"{date}: APIs {summary['successful']}/{summary['total_tests']} ({summary['success_rate']:.1f}%) | "
              f"Media {summary['media_accessible']}/{summary['media_urls_found']} ({summary['media_success_rate']:.1f}%)")
    
    # Find best and worst days
    best_day = max(all_results, key=lambda x: x["summary"]["success_rate"])
    worst_day = min(all_results, key=lambda x: x["summary"]["success_rate"])
    
    print(f"\n🏆 BEST DAY: {best_day['date']} - {best_day['summary']['success_rate']:.1f}% API success")
    print(f"❌ WORST DAY: {worst_day['date']} - {worst_day['summary']['success_rate']:.1f}% API success")
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    return all_results

if __name__ == "__main__":
    run_daily_tests()
