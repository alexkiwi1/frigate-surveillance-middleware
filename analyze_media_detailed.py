#!/usr/bin/env python3
"""
Detailed media analysis script to understand which media URLs are working
and which are failing, with specific breakdown by type and date.
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
            "accessible": response.status_code == 200,
            "status_code": response.status_code
        }
    except requests.exceptions.Timeout:
        return {"status": "❌ FAILED (Timeout)", "size": "N/A", "content_type": "N/A", "accessible": False, "status_code": "TIMEOUT"}
    except requests.exceptions.RequestException as e:
        return {"status": f"❌ FAILED ({e})", "size": "N/A", "content_type": "N/A", "accessible": False, "status_code": "ERROR"}

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

def analyze_media_for_date(date: str) -> Dict[str, Any]:
    """Analyze media URLs for a specific date."""
    print(f"\n📅 ANALYZING MEDIA FOR {date}")
    print("=" * 50)
    
    results = {
        "date": date,
        "media_analysis": {
            "total_urls": 0,
            "working_urls": 0,
            "failed_urls": 0,
            "by_type": {},
            "by_source": {},
            "details": []
        }
    }
    
    # Test different API endpoints that return media
    endpoints_to_test = [
        ("/violations/live?limit=5", "Live Violations"),
        ("/recent-media/clips?limit=5", "Recent Clips"),
        ("/recent-media/recordings?limit=5", "Recent Recordings"),
        ("/dashboard/summary", "Dashboard Summary"),
        ("/zones/occupancy", "Zone Occupancy")
    ]
    
    for endpoint, description in endpoints_to_test:
        try:
            print(f"\n🔍 Testing {description}...")
            response = requests.get(f"{API_BASE}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                media_urls = extract_media_urls(data)
                
                print(f"  Found {len(media_urls)} media URLs")
                
                for media_url in media_urls:
                    url = media_url["url"]
                    media_type = media_url["type"]
                    source = description
                    
                    print(f"    Testing {media_type}: {url}")
                    test_result = check_url_accessibility(url, media_type)
                    
                    # Update counters
                    results["media_analysis"]["total_urls"] += 1
                    if test_result["accessible"]:
                        results["media_analysis"]["working_urls"] += 1
                    else:
                        results["media_analysis"]["failed_urls"] += 1
                    
                    # Update by type
                    if media_type not in results["media_analysis"]["by_type"]:
                        results["media_analysis"]["by_type"][media_type] = {"total": 0, "working": 0, "failed": 0}
                    
                    results["media_analysis"]["by_type"][media_type]["total"] += 1
                    if test_result["accessible"]:
                        results["media_analysis"]["by_type"][media_type]["working"] += 1
                    else:
                        results["media_analysis"]["by_type"][media_type]["failed"] += 1
                    
                    # Update by source
                    if source not in results["media_analysis"]["by_source"]:
                        results["media_analysis"]["by_source"][source] = {"total": 0, "working": 0, "failed": 0}
                    
                    results["media_analysis"]["by_source"][source]["total"] += 1
                    if test_result["accessible"]:
                        results["media_analysis"]["by_source"][source]["working"] += 1
                    else:
                        results["media_analysis"]["by_source"][source]["failed"] += 1
                    
                    # Store details
                    results["media_analysis"]["details"].append({
                        "url": url,
                        "type": media_type,
                        "source": source,
                        "accessible": test_result["accessible"],
                        "status_code": test_result["status_code"],
                        "size": test_result["size"],
                        "content_type": test_result["content_type"]
                    })
                    
                    print(f"      {test_result['status']}")
                    if test_result["accessible"]:
                        print(f"      Size: {test_result['size']} bytes")
                        print(f"      Type: {test_result['content_type']}")
            else:
                print(f"  ❌ API failed with status {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error testing {description}: {e}")
    
    # Calculate success rates
    total = results["media_analysis"]["total_urls"]
    working = results["media_analysis"]["working_urls"]
    failed = results["media_analysis"]["failed_urls"]
    
    if total > 0:
        results["media_analysis"]["success_rate"] = (working / total) * 100
    else:
        results["media_analysis"]["success_rate"] = 0
    
    print(f"\n📊 MEDIA SUMMARY FOR {date}")
    print(f"  Total URLs: {total}")
    print(f"  Working: {working} ✅")
    print(f"  Failed: {failed} ❌")
    print(f"  Success Rate: {results['media_analysis']['success_rate']:.1f}%")
    
    return results

def run_detailed_media_analysis():
    """Run detailed media analysis for recent dates."""
    print("🔍 DETAILED MEDIA ANALYSIS")
    print("=" * 50)
    print(f"Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing against: {API_BASE}")
    
    # Test recent dates
    test_dates = [
        "2025-10-16",  # Today
        "2025-10-15",  # Yesterday
        "2025-10-14",  # 2 days ago
        "2025-10-01",  # October 1st
    ]
    
    all_results = []
    
    for date in test_dates:
        result = analyze_media_for_date(date)
        all_results.append(result)
    
    # Generate comprehensive report
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE MEDIA ANALYSIS REPORT")
    print("=" * 70)
    
    total_urls = sum(r["media_analysis"]["total_urls"] for r in all_results)
    total_working = sum(r["media_analysis"]["working_urls"] for r in all_results)
    total_failed = sum(r["media_analysis"]["failed_urls"] for r in all_results)
    
    print(f"Total Media URLs Tested: {total_urls}")
    print(f"Working URLs: {total_working} ✅")
    print(f"Failed URLs: {total_failed} ❌")
    print(f"Overall Success Rate: {(total_working/total_urls*100):.1f}%")
    
    # Analyze by type
    print(f"\n📊 BREAKDOWN BY MEDIA TYPE:")
    print("-" * 40)
    
    type_totals = {}
    for result in all_results:
        for media_type, stats in result["media_analysis"]["by_type"].items():
            if media_type not in type_totals:
                type_totals[media_type] = {"total": 0, "working": 0, "failed": 0}
            type_totals[media_type]["total"] += stats["total"]
            type_totals[media_type]["working"] += stats["working"]
            type_totals[media_type]["failed"] += stats["failed"]
    
    for media_type, stats in type_totals.items():
        success_rate = (stats["working"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {media_type}: {stats['working']}/{stats['total']} ({success_rate:.1f}%)")
    
    # Analyze by source
    print(f"\n📊 BREAKDOWN BY API SOURCE:")
    print("-" * 40)
    
    source_totals = {}
    for result in all_results:
        for source, stats in result["media_analysis"]["by_source"].items():
            if source not in source_totals:
                source_totals[source] = {"total": 0, "working": 0, "failed": 0}
            source_totals[source]["total"] += stats["total"]
            source_totals[source]["working"] += stats["working"]
            source_totals[source]["failed"] += stats["failed"]
    
    for source, stats in source_totals.items():
        success_rate = (stats["working"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {source}: {stats['working']}/{stats['total']} ({success_rate:.1f}%)")
    
    # Show failed URLs for debugging
    print(f"\n❌ FAILED URLS ANALYSIS:")
    print("-" * 40)
    
    failed_by_status = {}
    for result in all_results:
        for detail in result["media_analysis"]["details"]:
            if not detail["accessible"]:
                status = detail["status_code"]
                if status not in failed_by_status:
                    failed_by_status[status] = []
                failed_by_status[status].append(detail)
    
    for status, urls in failed_by_status.items():
        print(f"  Status {status}: {len(urls)} URLs")
        for url_detail in urls[:3]:  # Show first 3 examples
            print(f"    - {url_detail['type']}: {url_detail['url']}")
        if len(urls) > 3:
            print(f"    ... and {len(urls) - 3} more")
    
    print(f"\n🏁 Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    return all_results

if __name__ == "__main__":
    run_detailed_media_analysis()
