#!/usr/bin/env python3
"""
Test script to identify current issues with the Frigate Dashboard Middleware.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
MIDDLEWARE_BASE = "http://localhost:5002"
FRIGATE_BASE = "http://10.0.20.6:5001"
API_BASE = f"{MIDDLEWARE_BASE}/api"

def test_url(url, description):
    """Test a URL and return results."""
    try:
        response = requests.get(url, timeout=5)
        return {
            "url": url,
            "description": description,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "content_length": response.headers.get('Content-Length', 'N/A'),
            "content_type": response.headers.get('Content-Type', 'N/A')
        }
    except Exception as e:
        return {
            "url": url,
            "description": description,
            "status_code": "ERROR",
            "success": False,
            "error": str(e)
        }

def run_comprehensive_test():
    """Run comprehensive test to identify current issues."""
    print("🔍 COMPREHENSIVE ISSUE ANALYSIS")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Test Frigate API endpoints
    print("🎥 TESTING FRIGATE API ENDPOINTS")
    print("-" * 40)
    
    frigate_tests = [
        (f"{FRIGATE_BASE}/api/config", "Frigate Config"),
        (f"{FRIGATE_BASE}/api/cameras", "Frigate Cameras"),
        (f"{FRIGATE_BASE}/api/snapshots?limit=3", "Frigate Snapshots"),
        (f"{FRIGATE_BASE}/api/clips?limit=3", "Frigate Clips"),
        (f"{FRIGATE_BASE}/api/recordings?limit=3", "Frigate Recordings"),
    ]
    
    for url, desc in frigate_tests:
        result = test_url(url, desc)
        status = "✅" if result["success"] else "❌"
        print(f"{status} {desc}: {result['status_code']}")
        if result["success"] and "content_length" in result:
            print(f"    Size: {result['content_length']} bytes")
            print(f"    Type: {result['content_type']}")
        elif "error" in result:
            print(f"    Error: {result['error']}")
        print()
    
    # 2. Test Middleware API endpoints
    print("🔧 TESTING MIDDLEWARE API ENDPOINTS")
    print("-" * 40)
    
    middleware_tests = [
        (f"{API_BASE}/violations/live?limit=3", "Live Violations"),
        (f"{API_BASE}/recent-media/clips?limit=3", "Recent Clips"),
        (f"{API_BASE}/recent-media/recordings?limit=3", "Recent Recordings"),
        (f"{API_BASE}/dashboard/summary", "Dashboard Summary"),
        (f"{API_BASE}/zones/occupancy", "Zone Occupancy"),
    ]
    
    for url, desc in middleware_tests:
        result = test_url(url, desc)
        status = "✅" if result["success"] else "❌"
        print(f"{status} {desc}: {result['status_code']}")
        if result["success"] and "content_length" in result:
            print(f"    Size: {result['content_length']} bytes")
            print(f"    Type: {result['content_type']}")
        elif "error" in result:
            print(f"    Error: {result['error']}")
        print()
    
    # 3. Test specific media URLs
    print("🎬 TESTING SPECIFIC MEDIA URLS")
    print("-" * 40)
    
    # Get a violation with media URLs
    try:
        violations_response = requests.get(f"{API_BASE}/violations/live?limit=1", timeout=10)
        if violations_response.status_code == 200:
            violations_data = violations_response.json()
            if violations_data.get("data") and len(violations_data["data"]) > 0:
                violation = violations_data["data"][0]
                print(f"Testing violation: {violation.get('id', 'N/A')}")
                print(f"Camera: {violation.get('camera', 'N/A')}")
                print()
                
                # Test each media URL
                media_tests = [
                    (violation.get('video_url'), "Video URL"),
                    (violation.get('thumbnail_url'), "Thumbnail URL"),
                    (violation.get('snapshot_url'), "Snapshot URL"),
                ]
                
                for url, desc in media_tests:
                    if url:
                        result = test_url(url, desc)
                        status = "✅" if result["success"] else "❌"
                        print(f"{status} {desc}: {result['status_code']}")
                        if result["success"]:
                            print(f"    Size: {result['content_length']} bytes")
                            print(f"    Type: {result['content_type']}")
                        else:
                            print(f"    URL: {url}")
                    else:
                        print(f"❌ {desc}: No URL provided")
                    print()
        else:
            print("❌ Could not fetch violations data")
    except Exception as e:
        print(f"❌ Error fetching violations: {e}")
    
    # 4. Test Frigate snapshots directly
    print("📸 TESTING FRIGATE SNAPSHOTS DIRECTLY")
    print("-" * 40)
    
    try:
        snapshots_response = requests.get(f"{FRIGATE_BASE}/api/snapshots?limit=3", timeout=10)
        if snapshots_response.status_code == 200:
            snapshots_data = snapshots_response.json()
            if snapshots_data.get("snapshots"):
                print(f"Found {len(snapshots_data['snapshots'])} snapshots from Frigate")
                for i, snapshot in enumerate(snapshots_data["snapshots"][:3]):
                    print(f"\nSnapshot {i+1}:")
                    print(f"  Camera: {snapshot.get('camera', 'N/A')}")
                    print(f"  ID: {snapshot.get('id', 'N/A')}")
                    print(f"  Filename: {snapshot.get('filename', 'N/A')}")
                    
                    # Test the snapshot URL
                    snapshot_url = f"{FRIGATE_BASE}{snapshot.get('snapshot_url', '')}"
                    result = test_url(snapshot_url, f"Snapshot {i+1}")
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} Snapshot URL: {result['status_code']}")
                    if result["success"]:
                        print(f"    Size: {result['content_length']} bytes")
                        print(f"    Type: {result['content_type']}")
                    else:
                        print(f"    URL: {snapshot_url}")
            else:
                print("❌ No snapshots found in Frigate response")
        else:
            print(f"❌ Frigate snapshots API failed: {snapshots_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Frigate snapshots: {e}")
    
    # 5. Test recent clips and recordings
    print("\n🎥 TESTING RECENT MEDIA")
    print("-" * 40)
    
    try:
        clips_response = requests.get(f"{API_BASE}/recent-media/clips?limit=2", timeout=10)
        if clips_response.status_code == 200:
            clips_data = clips_response.json()
            if clips_data.get("data"):
                print(f"Found {len(clips_data['data'])} recent clips")
                for i, clip in enumerate(clips_data["data"][:2]):
                    print(f"\nClip {i+1}:")
                    print(f"  ID: {clip.get('id', 'N/A')}")
                    
                    # Test video URL
                    video_url = clip.get('video_url')
                    if video_url:
                        result = test_url(video_url, f"Clip {i+1} Video")
                        status = "✅" if result["success"] else "❌"
                        print(f"  {status} Video: {result['status_code']}")
                        if result["success"]:
                            print(f"    Size: {result['content_length']} bytes")
                            print(f"    Type: {result['content_type']}")
                    
                    # Test thumbnail URL
                    thumbnail_url = clip.get('thumbnail_url')
                    if thumbnail_url:
                        result = test_url(thumbnail_url, f"Clip {i+1} Thumbnail")
                        status = "✅" if result["success"] else "❌"
                        print(f"  {status} Thumbnail: {result['status_code']}")
                        if result["success"]:
                            print(f"    Size: {result['content_length']} bytes")
                            print(f"    Type: {result['content_type']}")
            else:
                print("❌ No recent clips found")
        else:
            print(f"❌ Recent clips API failed: {clips_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing recent clips: {e}")
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

if __name__ == "__main__":
    run_comprehensive_test()
