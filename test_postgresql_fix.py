#!/usr/bin/env python3
"""
Test PostgreSQL fix results across different time periods
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
    print("🧪 POSTGRESQL FIX TESTING")
    print("=" * 40)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test hourly trend across different time periods
    time_periods = [
        (12, "12 hours"),
        (24, "24 hours"),
        (36, "36 hours"),
        (48, "48 hours"),
        (60, "60 hours"),
        (72, "72 hours"),
        (84, "84 hours"),
        (96, "96 hours"),
        (120, "120 hours"),
        (144, "144 hours"),
        (168, "168 hours (max)")
    ]
    
    results = []
    
    print("📊 TESTING HOURLY TREND - FINDING BREAKING POINT")
    print("-" * 50)
    
    for hours, description in time_periods:
        print(f"\n🕐 Testing {description} ({hours} hours):")
        
        url = f"{API_BASE}/violations/hourly-trend?hours={hours}"
        result = test_endpoint(url, f"Hourly trend")
        results.append(result)
        
        # Small delay to avoid overwhelming
        time.sleep(1)
    
    print("\n" + "=" * 40)
    print("📊 TESTING EMPLOYEE VIOLATIONS")
    print("-" * 30)
    
    # Test employee violations for extended periods
    employee_periods = [72, 96, 120, 144, 168]
    
    for hours in employee_periods:
        print(f"\n🕐 Testing employee violations ({hours} hours):")
        
        url = f"{API_BASE}/employees/Unknown/violations?hours={hours}"
        result = test_endpoint(url, f"Employee violations")
        results.append(result)
        
        time.sleep(1)
    
    print("\n" + "=" * 40)
    print("📋 POSTGRESQL FIX RESULTS")
    print("=" * 40)
    
    # Calculate summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Find the breaking point for hourly trends
    hourly_results = [r for r in results[:len(time_periods)]]
    working_hours = []
    failing_hours = []
    
    for i, result in enumerate(hourly_results):
        hours = time_periods[i][0]
        if result['success']:
            working_hours.append(hours)
        else:
            failing_hours.append(hours)
    
    if working_hours:
        max_working = max(working_hours)
        print(f"\n✅ Working up to: {max_working} hours")
    
    if failing_hours:
        min_failing = min(failing_hours)
        print(f"❌ Failing from: {min_failing} hours")
    
    # Show failed tests
    failed_results = [r for r in results if not r['success']]
    if failed_results:
        print(f"\n❌ FAILED TESTS:")
        for result in failed_results:
            print(f"  • {result['description']}")
            if 'error' in result:
                print(f"    Error: {result['error']}")
    
    print(f"\n🏁 PostgreSQL fix testing completed!")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT - PostgreSQL fix was successful!")
    elif success_rate >= 70:
        print("✅ GOOD - PostgreSQL fix helped significantly!")
    elif success_rate >= 50:
        print("⚠️  PARTIAL - PostgreSQL fix helped but more work needed!")
    else:
        print("❌ LIMITED - PostgreSQL fix had minimal impact!")
    
    return success_rate >= 70

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
