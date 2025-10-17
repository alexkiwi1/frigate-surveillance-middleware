#!/usr/bin/env python3
"""
Corrected Daily API Testing from October 1, 2025 to Today
Tests only the ACTUAL available APIs and media accessibility
"""

import requests
import json
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any

# Configuration
BASE_URL = "http://10.0.20.7:5002"
FRIGATE_URL = "http://10.0.20.6:5001"

def test_media_accessibility(url: str, timeout: int = 5) -> Dict[str, Any]:
    """Test if a media URL is accessible and return details"""
    try:
        response = requests.head(url, timeout=timeout)
        return {
            "accessible": response.status_code == 200,
            "status_code": response.status_code,
            "content_type": response.headers.get('content-type', 'unknown'),
            "content_length": response.headers.get('content-length', 'unknown'),
            "error": None
        }
    except Exception as e:
        return {
            "accessible": False,
            "status_code": None,
            "content_type": None,
            "content_length": None,
            "error": str(e)
        }

def test_endpoint(method: str, endpoint: str, description: str, params: Dict = None, timeout: int = 10) -> Dict[str, Any]:
    """Test an API endpoint and return results"""
    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.request(method, url, params=params, timeout=timeout)
        
        result = {
            "endpoint": endpoint,
            "description": description,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response_time": response.elapsed.total_seconds(),
            "data": None,
            "media_urls": [],
            "media_results": []
        }
        
        if response.status_code == 200:
            try:
                data = response.json()
                result["data"] = data
                
                # Extract media URLs from response
                media_urls = []
                if isinstance(data, dict):
                    # Check for common media URL fields
                    for key in ['video_url', 'thumbnail_url', 'snapshot_url', 'media_url']:
                        if key in data and data[key]:
                            media_urls.append(data[key])
                    
                    # Check for arrays of items with media URLs
                    for key in ['violations', 'clips', 'recordings', 'events', 'data']:
                        if key in data and isinstance(data[key], list):
                            for item in data[key]:
                                if isinstance(item, dict):
                                    for media_key in ['video_url', 'thumbnail_url', 'snapshot_url', 'media_url']:
                                        if media_key in item and item[media_key]:
                                            media_urls.append(item[media_key])
                
                result["media_urls"] = media_urls
                
                # Test media accessibility
                for media_url in media_urls:
                    media_result = test_media_accessibility(media_url)
                    result["media_results"].append({
                        "url": media_url,
                        "result": media_result
                    })
                    
            except json.JSONDecodeError:
                result["data"] = response.text[:200]  # First 200 chars if not JSON
        
        return result
        
    except Exception as e:
        return {
            "endpoint": endpoint,
            "description": description,
            "status_code": None,
            "success": False,
            "response_time": None,
            "data": None,
            "media_urls": [],
            "media_results": [],
            "error": str(e)
        }

def get_daily_timestamp(date: datetime) -> int:
    """Convert date to Unix timestamp for API calls"""
    return int(date.timestamp())

def test_daily_apis(target_date: datetime) -> Dict[str, Any]:
    """Test all APIs for a specific date"""
    print(f"\n📅 Testing APIs for {target_date.strftime('%Y-%m-%d')}")
    print("=" * 50)
    
    timestamp = get_daily_timestamp(target_date)
    date_str = target_date.strftime('%Y-%m-%d')
    
    # Define ONLY the ACTUAL available API endpoints
    api_tests = [
        # Core Violation APIs (these exist)
        ("GET", "/api/violations/live", "Live Violations", {"limit": 5}),
        ("GET", "/api/violations/hourly-trend", "Hourly Trend (24h)", {"hours": 24}),
        ("GET", "/api/violations/hourly-trend", "Hourly Trend (48h)", {"hours": 48}),
        
        # Recent Media APIs (these exist)
        ("GET", "/api/recent-media/clips", "Recent Clips", {"limit": 5}),
        ("GET", "/api/recent-media/recordings", "Recent Recordings", {"limit": 5}),
        
        # Employee APIs (these exist but need valid employee names)
        ("GET", f"/api/employees/John%20Doe/current-status", "Employee Current Status", {}),
        ("GET", f"/api/employees/John%20Doe/work-hours", "Employee Work Hours", {"date": date_str}),
        ("GET", f"/api/employees/John%20Doe/breaks", "Employee Breaks", {"date": date_str}),
        ("GET", f"/api/employees/John%20Doe/timeline", "Employee Timeline", {"date": date_str}),
        ("GET", f"/api/employees/John%20Doe/movements", "Employee Movements", {"date": date_str}),
        
        # Zone APIs (these exist)
        ("GET", "/api/zones/occupancy", "Zone Occupancy", {}),
        ("GET", "/api/zones/activity-heatmap", "Zone Activity Heatmap", {"date": date_str}),
        ("GET", "/api/zones/stats", "Zone Statistics", {}),
        
        # Attendance APIs (these exist)
        ("GET", "/api/attendance/daily", "Daily Attendance", {"date": date_str}),
        ("GET", "/api/attendance/stats", "Attendance Statistics", {}),
        
        # Dashboard APIs (these exist)
        ("GET", "/api/dashboard/summary", "Dashboard Summary", {}),
        
        # Violation Duration API (test with a sample violation ID)
        ("GET", "/api/violations/1234567890/duration", "Violation Duration", {}),
    ]
    
    results = {
        "date": date_str,
        "timestamp": timestamp,
        "apis_tested": len(api_tests),
        "apis_successful": 0,
        "apis_failed": 0,
        "media_tested": 0,
        "media_accessible": 0,
        "media_failed": 0,
        "api_results": [],
        "summary": {}
    }
    
    for method, endpoint, description, params in api_tests:
        print(f"Testing {description}...")
        result = test_endpoint(method, endpoint, description, params, timeout=15)
        results["api_results"].append(result)
        
        if result["success"]:
            results["apis_successful"] += 1
            print(f"  ✅ {description} - {result['response_time']:.2f}s")
        else:
            results["apis_failed"] += 1
            error_msg = result.get('data', {}).get('error', 'Unknown error') if result.get('data') else f"Status: {result.get('status_code', 'Error')}"
            print(f"  ❌ {description} - {error_msg}")
        
        # Count media tests
        for media_result in result["media_results"]:
            results["media_tested"] += 1
            if media_result["result"]["accessible"]:
                results["media_accessible"] += 1
            else:
                results["media_failed"] += 1
    
    # Calculate success rates
    results["api_success_rate"] = (results["apis_successful"] / results["apis_tested"]) * 100 if results["apis_tested"] > 0 else 0
    results["media_success_rate"] = (results["media_accessible"] / results["media_tested"]) * 100 if results["media_tested"] > 0 else 0
    
    # Create summary
    results["summary"] = {
        "apis": f"{results['apis_successful']}/{results['apis_tested']} ({results['api_success_rate']:.1f}%)",
        "media": f"{results['media_accessible']}/{results['media_tested']} ({results['media_success_rate']:.1f}%)",
        "overall_status": "✅ EXCELLENT" if results['api_success_rate'] >= 90 else "⚠️ NEEDS ATTENTION" if results['api_success_rate'] >= 70 else "❌ CRITICAL ISSUES"
    }
    
    print(f"\n📊 Daily Summary for {date_str}:")
    print(f"  APIs: {results['summary']['apis']}")
    print(f"  Media: {results['summary']['media']}")
    print(f"  Status: {results['summary']['overall_status']}")
    
    return results

def main():
    """Run comprehensive daily testing from October 1, 2025 to today"""
    print("🚀 CORRECTED DAILY API TESTING")
    print("==============================")
    print(f"Testing from October 1, 2025 to {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Base URL: {BASE_URL}")
    print(f"Frigate URL: {FRIGATE_URL}")
    print("Note: Testing only ACTUAL available endpoints")
    
    # Generate date range
    start_date = datetime(2025, 10, 1)
    end_date = datetime.now()
    
    daily_results = []
    total_apis = 0
    total_apis_success = 0
    total_media = 0
    total_media_success = 0
    
    current_date = start_date
    while current_date <= end_date:
        try:
            daily_result = test_daily_apis(current_date)
            daily_results.append(daily_result)
            
            total_apis += daily_result["apis_tested"]
            total_apis_success += daily_result["apis_successful"]
            total_media += daily_result["media_tested"]
            total_media_success += daily_result["media_accessible"]
            
            # Small delay between days to avoid overwhelming the system
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error testing {current_date.strftime('%Y-%m-%d')}: {e}")
            daily_results.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "error": str(e),
                "apis_tested": 0,
                "apis_successful": 0,
                "media_tested": 0,
                "media_accessible": 0,
                "api_success_rate": 0,
                "media_success_rate": 0
            })
        
        current_date += timedelta(days=1)
    
    # Generate comprehensive report
    print("\n" + "="*80)
    print("📊 CORRECTED DAILY TESTING REPORT")
    print("="*80)
    
    overall_api_success = (total_apis_success / total_apis) * 100 if total_apis > 0 else 0
    overall_media_success = (total_media_success / total_media) * 100 if total_media > 0 else 0
    
    print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"📊 Total APIs Tested: {total_apis}")
    print(f"✅ APIs Successful: {total_apis_success} ({overall_api_success:.1f}%)")
    print(f"❌ APIs Failed: {total_apis - total_apis_success}")
    print(f"📊 Total Media Tested: {total_media}")
    print(f"✅ Media Accessible: {total_media_success} ({overall_media_success:.1f}%)")
    print(f"❌ Media Failed: {total_media - total_media_success}")
    
    print(f"\n🎯 Overall Status: {'✅ EXCELLENT' if overall_api_success >= 90 else '⚠️ NEEDS ATTENTION' if overall_api_success >= 70 else '❌ CRITICAL ISSUES'}")
    
    # Daily breakdown
    print(f"\n📅 DAILY BREAKDOWN:")
    print("-" * 80)
    print(f"{'Date':<12} {'APIs':<10} {'Media':<10} {'API %':<8} {'Media %':<8} {'Status':<15}")
    print("-" * 80)
    
    for result in daily_results:
        if "error" in result:
            print(f"{result['date']:<12} {'ERROR':<10} {'ERROR':<10} {'0.0%':<8} {'0.0%':<8} {'❌ ERROR':<15}")
        else:
            status = "✅" if result['api_success_rate'] >= 90 else "⚠️" if result['api_success_rate'] >= 70 else "❌"
            print(f"{result['date']:<12} {result['apis_successful']}/{result['apis_tested']:<8} {result['media_accessible']}/{result['media_tested']:<8} {result['api_success_rate']:.1f}%{'':<3} {result['media_success_rate']:.1f}%{'':<3} {status:<15}")
    
    # Save detailed results to file
    report_file = f"corrected_daily_testing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "summary": {
                "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "total_apis": total_apis,
                "total_apis_success": total_apis_success,
                "overall_api_success_rate": overall_api_success,
                "total_media": total_media,
                "total_media_success": total_media_success,
                "overall_media_success_rate": overall_media_success
            },
            "daily_results": daily_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")
    print("\n🎉 Corrected daily testing completed!")

if __name__ == "__main__":
    main()

