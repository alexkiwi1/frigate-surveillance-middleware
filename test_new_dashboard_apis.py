#!/usr/bin/env python3
"""
Test script for the 4 new dashboard APIs
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://10.0.20.7:5002"

def test_endpoint(method, endpoint, description, params=None, timeout=10):
    """Test an API endpoint"""
    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.request(method, url, params=params, timeout=timeout)
        
        result = {
            "endpoint": endpoint,
            "description": description,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response_time": response.elapsed.total_seconds(),
            "data": None
        }
        
        if response.status_code == 200:
            try:
                result["data"] = response.json()
            except:
                result["data"] = response.text[:200]
        
        return result
        
    except Exception as e:
        return {
            "endpoint": endpoint,
            "description": description,
            "status_code": None,
            "success": False,
            "response_time": None,
            "data": None,
            "error": str(e)
        }

def main():
    """Test all 4 new dashboard APIs"""
    print("🚀 TESTING NEW DASHBOARD APIs")
    print("=============================")
    
    # Test data
    test_date = "2025-10-16"
    employee_name = "John Doe"
    
    # Define API tests
    api_tests = [
        # 1. Bulk Daily Report
        ("GET", "/api/attendance/daily-report", "Bulk Daily Report", {"date": test_date}),
        ("GET", "/api/attendance/daily-report", "Bulk Daily Report (Today)", {}),
        
        # 2. Idle Time
        ("GET", f"/api/employees/{employee_name}/idle-time", "Employee Idle Time", {"date": test_date}),
        ("GET", f"/api/employees/{employee_name}/idle-time", "Employee Idle Time (Today)", {}),
        
        # 3. Timeline Segments
        ("GET", f"/api/employees/{employee_name}/timeline-segments", "Timeline Segments", {"date": test_date}),
        ("GET", f"/api/employees/{employee_name}/timeline-segments", "Timeline Segments (Today)", {}),
        
        # 4. Enhanced Breaks with Snapshots
        ("GET", f"/api/employees/{employee_name}/breaks", "Enhanced Breaks (No Snapshots)", {"date": test_date}),
        ("GET", f"/api/employees/{employee_name}/breaks", "Enhanced Breaks (With Snapshots)", {"date": test_date, "include_snapshots": True}),
    ]
    
    results = []
    successful = 0
    failed = 0
    
    for method, endpoint, description, params in api_tests:
        print(f"\nTesting {description}...")
        result = test_endpoint(method, endpoint, description, params)
        results.append(result)
        
        if result["success"]:
            successful += 1
            print(f"  ✅ {description} - {result['response_time']:.2f}s")
            
            # Show sample data for successful requests
            if result["data"] and isinstance(result["data"], dict):
                if "data" in result["data"]:
                    data = result["data"]["data"]
                    if isinstance(data, dict):
                        if "employees" in data:
                            print(f"    📊 Found {len(data['employees'])} employees")
                        elif "idle_periods" in data:
                            print(f"    ⏱️ Found {len(data['idle_periods'])} idle periods")
                        elif "segments" in data:
                            print(f"    📈 Found {len(data['segments'])} timeline segments")
                        elif "breaks" in data:
                            print(f"    ☕ Found {len(data['breaks'])} breaks")
                            if data["breaks"] and "snapshot_url" in data["breaks"][0]:
                                print(f"    📸 Snapshots: {'Yes' if data['breaks'][0]['snapshot_url'] else 'No'}")
        else:
            failed += 1
            error_msg = result.get('data', {}).get('error', 'Unknown error') if result.get('data') else f"Status: {result.get('status_code', 'Error')}"
            print(f"  ❌ {description} - {error_msg}")
    
    # Summary
    print(f"\n📊 TEST RESULTS SUMMARY")
    print("=" * 30)
    print(f"Total APIs Tested: {len(api_tests)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(successful/len(api_tests)*100):.1f}%")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    print("-" * 50)
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['description']}")
        if result["success"] and result["data"]:
            data = result["data"].get("data", {})
            if isinstance(data, dict):
                if "total_employees" in data:
                    print(f"    Employees: {data['total_employees']}")
                if "total_idle_seconds" in data:
                    print(f"    Idle Time: {data['total_idle_formatted']}")
                if "total_duration" in data:
                    print(f"    Duration: {data['total_duration']}")
                if "breaks" in data:
                    print(f"    Breaks: {len(data['breaks'])}")
    
    print(f"\n🎉 Testing completed!")

if __name__ == "__main__":
    main()

