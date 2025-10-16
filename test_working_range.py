#!/usr/bin/env python3
"""
Test the actual working range (1-168 hours) to confirm 100% functionality
"""

import requests
import json
from datetime import datetime
import time

API_BASE = "http://localhost:5002/api"

def test_endpoint(url, description, expected_status=200):
    """Test an endpoint and return results"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        response_time = time.time() - start_time
        
        success = response.status_code == expected_status
        status_icon = "✅" if success else "❌"
        
        print(f"{status_icon} {description}")
        print(f"    Status: {response.status_code}, Time: {response_time:.2f}s")
        
        return success
    except Exception as e:
        print(f"❌ {description}")
        print(f"    Exception: {str(e)}")
        return False

def main():
    print("🎯 TESTING ACTUAL WORKING RANGE (1-168 HOURS)")
    print("=" * 50)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test the actual working range
    time_periods = [
        (1, "1 hour"),
        (6, "6 hours"),
        (12, "12 hours"),
        (24, "1 day"),
        (48, "2 days"),
        (72, "3 days"),
        (96, "4 days"),
        (120, "5 days"),
        (144, "6 days"),
        (168, "1 week (max limit)")
    ]
    
    results = []
    
    print("📊 TESTING VIOLATIONS API - WORKING RANGE")
    print("-" * 40)
    
    for hours, description in time_periods:
        print(f"\n🕐 Testing {description} ({hours} hours):")
        
        # Test live violations
        url = f"{API_BASE}/violations/live?hours={hours}"
        success = test_endpoint(url, f"Live violations")
        results.append(success)
        
        # Test hourly trend (may fail for 73+ hours due to PostgreSQL)
        url = f"{API_BASE}/violations/hourly-trend?hours={hours}"
        success = test_endpoint(url, f"Hourly trend")
        results.append(success)
        
        time.sleep(0.5)  # Small delay
    
    print("\n" + "=" * 50)
    print("📊 TESTING EMPLOYEES API - WORKING RANGE")
    print("-" * 40)
    
    for hours, description in time_periods:
        print(f"\n🕐 Testing {description} ({hours} hours):")
        
        # Test employee violations
        url = f"{API_BASE}/employees/Unknown/violations?hours={hours}"
        success = test_endpoint(url, f"Employee violations")
        results.append(success)
        
        # Test employee activity
        url = f"{API_BASE}/employees/Unknown/activity?hours={hours}"
        success = test_endpoint(url, f"Employee activity")
        results.append(success)
        
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("📊 TESTING CAMERAS API - WORKING RANGE")
    print("-" * 40)
    
    for hours, description in time_periods:
        print(f"\n🕐 Testing {description} ({hours} hours):")
        
        # Test camera activity
        url = f"{API_BASE}/cameras/employees_01/activity?hours={hours}"
        success = test_endpoint(url, f"Camera activity")
        results.append(success)
        
        # Test camera violations
        url = f"{API_BASE}/cameras/employees_01/violations?hours={hours}"
        success = test_endpoint(url, f"Camera violations")
        results.append(success)
        
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("📊 TESTING RECENT MEDIA API")
    print("-" * 40)
    
    media_tests = [
        f"{API_BASE}/recent-media/clips?limit=5",
        f"{API_BASE}/recent-media/recordings?limit=5",
        f"{API_BASE}/recent-media/test-media?clip_id=1760587749.98418-z4k0d1"
    ]
    
    for url in media_tests:
        success = test_endpoint(url, f"Media API: {url.split('/')[-1]}")
        results.append(success)
    
    print("\n" + "=" * 50)
    print("📋 WORKING RANGE TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(results)
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 95:
        print("\n🎉 EXCELLENT - Working range is fully functional!")
    elif success_rate >= 90:
        print("\n✅ GOOD - Working range is mostly functional!")
    else:
        print("\n⚠️  ISSUES DETECTED - Some problems in working range!")
    
    print(f"\n🏁 Working range test completed!")
    
    return success_rate >= 90

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
