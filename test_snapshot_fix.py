#!/usr/bin/env python3
"""
Test script to verify snapshot URL fixes are working correctly.
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

def run_snapshot_test():
    """Test snapshot functionality comprehensively."""
    print("🔧 SNAPSHOT FIX VERIFICATION")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Test available Frigate snapshots
    print("📸 TESTING AVAILABLE FRIGATE SNAPSHOTS")
    print("-" * 40)
    
    try:
        snapshots_response = requests.get(f"{FRIGATE_BASE}/api/snapshots?limit=5", timeout=10)
        if snapshots_response.status_code == 200:
            snapshots_data = snapshots_response.json()
            if snapshots_data.get("snapshots"):
                print(f"Found {len(snapshots_data['snapshots'])} snapshots from Frigate")
                
                working_snapshots = 0
                for i, snapshot in enumerate(snapshots_data["snapshots"]):
                    snapshot_url = f"{FRIGATE_BASE}{snapshot.get('snapshot_url', '')}"
                    result = test_url(snapshot_url, f"Snapshot {i+1}")
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {snapshot.get('camera', 'N/A')} - {result['status_code']}")
                    if result["success"]:
                        working_snapshots += 1
                        print(f"    Size: {result['content_length']} bytes")
                        print(f"    Type: {result['content_type']}")
                
                print(f"\n📊 Frigate Snapshots: {working_snapshots}/{len(snapshots_data['snapshots'])} working")
            else:
                print("❌ No snapshots found in Frigate response")
        else:
            print(f"❌ Frigate snapshots API failed: {snapshots_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Frigate snapshots: {e}")
    
    # 2. Test middleware violation snapshots
    print(f"\n🚨 TESTING MIDDLEWARE VIOLATION SNAPSHOTS")
    print("-" * 40)
    
    try:
        violations_response = requests.get(f"{API_BASE}/violations/live?limit=5", timeout=10)
        if violations_response.status_code == 200:
            violations_data = violations_response.json()
            if violations_data.get("data"):
                print(f"Found {len(violations_data['data'])} violations from middleware")
                
                working_violation_snapshots = 0
                for i, violation in enumerate(violations_data["data"]):
                    snapshot_url = violation.get('snapshot_url')
                    if snapshot_url:
                        result = test_url(snapshot_url, f"Violation {i+1} Snapshot")
                        status = "✅" if result["success"] else "❌"
                        print(f"  {status} {violation.get('camera', 'N/A')} - {result['status_code']}")
                        if result["success"]:
                            working_violation_snapshots += 1
                            print(f"    Size: {result['content_length']} bytes")
                            print(f"    Type: {result['content_type']}")
                        else:
                            print(f"    URL: {snapshot_url}")
                    else:
                        print(f"  ❌ Violation {i+1}: No snapshot URL")
                
                print(f"\n📊 Violation Snapshots: {working_violation_snapshots}/{len(violations_data['data'])} working")
            else:
                print("❌ No violations found in middleware response")
        else:
            print(f"❌ Middleware violations API failed: {violations_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing violation snapshots: {e}")
    
    # 3. Test snapshot URL format
    print(f"\n🔍 TESTING SNAPSHOT URL FORMAT")
    print("-" * 40)
    
    try:
        violations_response = requests.get(f"{API_BASE}/violations/live?limit=3", timeout=10)
        if violations_response.status_code == 200:
            violations_data = violations_response.json()
            if violations_data.get("data"):
                print("Snapshot URL formats:")
                for i, violation in enumerate(violations_data["data"][:3]):
                    snapshot_url = violation.get('snapshot_url', 'N/A')
                    print(f"  Violation {i+1}: {snapshot_url}")
                    
                    # Check if URL follows correct format
                    if snapshot_url and snapshot_url != 'N/A':
                        if '/snapshot/' in snapshot_url and '-' in snapshot_url.split('/')[-1]:
                            print(f"    ✅ Format looks correct")
                        else:
                            print(f"    ❌ Format looks incorrect")
                    else:
                        print(f"    ❌ No snapshot URL")
    except Exception as e:
        print(f"❌ Error checking snapshot formats: {e}")
    
    # 4. Test recent media snapshots
    print(f"\n🎬 TESTING RECENT MEDIA SNAPSHOTS")
    print("-" * 40)
    
    try:
        clips_response = requests.get(f"{API_BASE}/recent-media/clips?limit=3", timeout=10)
        if clips_response.status_code == 200:
            clips_data = clips_response.json()
            if clips_data.get("data"):
                print(f"Found {len(clips_data['data'])} recent clips")
                
                for i, clip in enumerate(clips_data["data"][:3]):
                    print(f"\nClip {i+1}:")
                    print(f"  ID: {clip.get('id', 'N/A')}")
                    
                    # Test video and thumbnail
                    video_url = clip.get('video_url')
                    thumbnail_url = clip.get('thumbnail_url')
                    
                    if video_url:
                        result = test_url(video_url, "Video")
                        status = "✅" if result["success"] else "❌"
                        print(f"  {status} Video: {result['status_code']}")
                    
                    if thumbnail_url:
                        result = test_url(thumbnail_url, "Thumbnail")
                        status = "✅" if result["success"] else "❌"
                        print(f"  {status} Thumbnail: {result['status_code']}")
            else:
                print("❌ No recent clips found")
        else:
            print(f"❌ Recent clips API failed: {clips_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing recent media: {e}")
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

if __name__ == "__main__":
    run_snapshot_test()

