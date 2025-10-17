#!/usr/bin/env python3
"""
Extended Time Period Testing - Beyond 72 Hours
Tests API functionality for longer time periods to ensure complete coverage
"""

import requests
import json
from datetime import datetime, timedelta
import time

API_BASE = "http://localhost:5002/api"

def test_endpoint(url, description, expected_status=200):
    """Test an endpoint and return results"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)  # Longer timeout for large queries
        response_time = time.time() - start_time
        
        success = response.status_code == expected_status
        status_icon = "✅" if success else "❌"
        
        print(f"{status_icon} {description}")
        print(f"    Status: {response.status_code}, Time: {response_time:.2f}s")
        
        if not success:
            try:
                error_data = response.json()
                if 'error' in error_data:
                    print(f"    Error: {error_data['error']}")
                if 'details' in error_data:
                    print(f"    Details: {error_data['details']}")
            except:
                print(f"    Raw response: {response.text[:200]}...")
        
        return {
            'success': success,
            'status': response.status_code,
            'response_time': response_time,
            'description': description
        }
    except Exception as e:
        print(f"❌ {description}")
        print(f"    Exception: {str(e)}")
        return {
            'success': False,
            'status': 'error',
            'response_time': 0,
            'description': description,
            'error': str(e)
        }

def main():
    print("🚀 EXTENDED TIME PERIOD TESTING - BEYOND 72 HOURS")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Extended time periods to test
    time_periods = [
        (96, "4 days (96 hours)"),
        (120, "5 days (120 hours)"),
        (168, "1 week (168 hours)"),
        (336, "2 weeks (336 hours)"),
        (720, "1 month (720 hours)"),
        (1440, "2 months (1440 hours)"),
        (2160, "3 months (2160 hours)")
    ]
    
    results = []
    
    print("📊 TESTING VIOLATIONS API - EXTENDED PERIODS")
    print("-" * 50)
    
    for hours, description in time_periods:
        print(f"\n🕐 Testing {description}:")
        
        # Test live violations
        url = f"{API_BASE}/violations/live?hours={hours}"
        result = test_endpoint(url, f"Live violations ({description})")
        results.append(result)
        
        # Test hourly trend
        url = f"{API_BASE}/violations/hourly-trend?hours={hours}"
        result = test_endpoint(url, f"Hourly trend ({description})")
        results.append(result)
        
        # Small delay to avoid overwhelming the system
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("📊 TESTING EMPLOYEES API - EXTENDED PERIODS")
    print("-" * 50)
    
    for hours, description in time_periods:
        print(f"\n🕐 Testing {description}:")
        
        # Test employee violations with extended period
        url = f"{API_BASE}/employees/Unknown/violations?hours={hours}"
        result = test_endpoint(url, f"Employee violations ({description})")
        results.append(result)
        
        # Test employee activity with extended period
        url = f"{API_BASE}/employees/Unknown/activity?hours={hours}"
        result = test_endpoint(url, f"Employee activity ({description})")
        results.append(result)
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("📊 TESTING CAMERAS API - EXTENDED PERIODS")
    print("-" * 50)
    
    for hours, description in time_periods:
        print(f"\n🕐 Testing {description}:")
        
        # Test camera activity with extended period
        url = f"{API_BASE}/cameras/employees_01/activity?hours={hours}"
        result = test_endpoint(url, f"Camera activity ({description})")
        results.append(result)
        
        # Test camera violations with extended period
        url = f"{API_BASE}/cameras/employees_01/violations?hours={hours}"
        result = test_endpoint(url, f"Camera violations ({description})")
        results.append(result)
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("📊 TESTING PERFORMANCE WITH LARGE LIMITS")
    print("-" * 50)
    
    # Test with large limits to see if the system can handle big queries
    large_limits = [500, 1000, 2000, 5000]
    
    for limit in large_limits:
        print(f"\n📊 Testing with limit={limit}:")
        
        url = f"{API_BASE}/violations/live?limit={limit}&hours=168"  # 1 week
        result = test_endpoint(url, f"Live violations (limit={limit}, 1 week)")
        results.append(result)
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("📋 EXTENDED TESTING SUMMARY")
    print("=" * 60)
    
    # Calculate summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Group results by time period
    print(f"\n📊 RESULTS BY TIME PERIOD:")
    for hours, description in time_periods:
        period_results = [r for r in results if description in r['description']]
        if period_results:
            period_passed = sum(1 for r in period_results if r['success'])
            period_total = len(period_results)
            period_rate = (period_passed / period_total * 100) if period_total > 0 else 0
            status_icon = "✅" if period_rate == 100 else "⚠️" if period_rate >= 80 else "❌"
            print(f"  {status_icon} {description}: {period_passed}/{period_total} ({period_rate:.1f}%)")
    
    # Show failed tests
    failed_results = [r for r in results if not r['success']]
    if failed_results:
        print(f"\n❌ FAILED TESTS:")
        for result in failed_results:
            print(f"  • {result['description']}")
            if 'error' in result:
                print(f"    Error: {result['error']}")
    
    print(f"\n🏁 Extended testing completed!")
    
    if success_rate >= 95:
        print("🎉 EXCELLENT - System handles extended time periods very well!")
    elif success_rate >= 90:
        print("✅ GOOD - System mostly handles extended time periods well!")
    elif success_rate >= 80:
        print("⚠️  FAIR - Some issues with extended time periods detected!")
    else:
        print("❌ POOR - Significant issues with extended time periods!")
    
    return success_rate >= 90

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)




