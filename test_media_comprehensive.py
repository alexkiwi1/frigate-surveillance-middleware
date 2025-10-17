#!/usr/bin/env python3
"""Comprehensive media testing script for Frigate Dashboard Middleware."""

import requests
import time
from datetime import datetime

API_BASE = "http://localhost:5002/api"
FRIGATE_BASE = "http://10.0.20.6:5001"

def test_media_url(url, media_type):
    """Test if a media URL is accessible."""
    try:
        start_time = time.time()
        response = requests.head(url, timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            content_length = response.headers.get('content-length', 'Unknown')
            content_type = response.headers.get('content-type', 'Unknown')
            return {
                "status": "✅ WORKING",
                "status_code": response.status_code,
                "response_time": f"{response_time:.3f}s",
                "content_length": content_length,
                "content_type": content_type
            }
        else:
            return {
                "status": "❌ FAILED",
                "status_code": response.status_code,
                "response_time": f"{response_time:.3f}s",
                "content_length": "N/A",
                "content_type": "N/A"
            }
    except Exception as e:
        return {
            "status": "❌ ERROR",
            "status_code": "ERROR",
            "response_time": "N/A",
            "content_length": "N/A",
            "content_type": "N/A",
            "error": str(e)
        }

def test_middleware_media():
    """Test media through middleware API."""
    print("🎬 TESTING MIDDLEWARE MEDIA API")
    print("=" * 50)
    
    # Test recent clips
    print("\n📹 RECENT CLIPS")
    print("-" * 20)
    try:
        response = requests.get(f"{API_BASE}/recent-media/clips?limit=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            clips = data.get('data', [])
            print(f"✅ Found {len(clips)} recent clips")
            
            for i, clip in enumerate(clips[:3], 1):
                print(f"\n  Clip {i}:")
                print(f"    ID: {clip.get('id', 'N/A')}")
                
                # Test video URL
                video_url = clip.get('video_url')
                if video_url:
                    print(f"    Video: {video_url}")
                    result = test_media_url(video_url, "video")
                    print(f"      Status: {result['status']} ({result['status_code']})")
                    if result['status_code'] == 200:
                        print(f"      Size: {result['content_length']} bytes")
                        print(f"      Type: {result['content_type']}")
                
                # Test thumbnail URL
                thumbnail_url = clip.get('thumbnail_url')
                if thumbnail_url:
                    print(f"    Thumbnail: {thumbnail_url}")
                    result = test_media_url(thumbnail_url, "thumbnail")
                    print(f"      Status: {result['status']} ({result['status_code']})")
                    if result['status_code'] == 200:
                        print(f"      Size: {result['content_length']} bytes")
                        print(f"      Type: {result['content_type']}")
        else:
            print(f"❌ Failed to get recent clips: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing recent clips: {e}")
    
    # Test recent recordings
    print("\n🎥 RECENT RECORDINGS")
    print("-" * 20)
    try:
        response = requests.get(f"{API_BASE}/recent-media/recordings?limit=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            recordings = data.get('data', [])
            print(f"✅ Found {len(recordings)} recent recordings")
            
            for i, recording in enumerate(recordings[:3], 1):
                print(f"\n  Recording {i}:")
                print(f"    ID: {recording.get('id', 'N/A')}")
                
                # Test video URL
                video_url = recording.get('video_url')
                if video_url:
                    print(f"    Video: {video_url}")
                    result = test_media_url(video_url, "video")
                    print(f"      Status: {result['status']} ({result['status_code']})")
                    if result['status_code'] == 200:
                        print(f"      Size: {result['content_length']} bytes")
                        print(f"      Type: {result['content_type']}")
        else:
            print(f"❌ Failed to get recent recordings: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing recent recordings: {e}")

def test_frigate_direct():
    """Test Frigate API directly."""
    print("\n🔗 TESTING FRIGATE API DIRECTLY")
    print("=" * 50)
    
    # Test clips
    print("\n📹 FRIGATE CLIPS")
    print("-" * 20)
    try:
        response = requests.get(f"{FRIGATE_BASE}/api/clips?limit=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            clips = data.get('clips', [])
            print(f"✅ Found {len(clips)} clips from Frigate")
            
            for i, clip in enumerate(clips[:3], 1):
                print(f"\n  Clip {i}:")
                print(f"    ID: {clip.get('id', 'N/A')}")
                
                # Test video URL
                video_url = f"{FRIGATE_BASE}{clip.get('video_url', '')}"
                print(f"    Video: {video_url}")
                result = test_media_url(video_url, "video")
                print(f"      Status: {result['status']} ({result['status_code']})")
                
                # Test thumbnail URL
                thumbnail_url = f"{FRIGATE_BASE}{clip.get('thumbnail_url', '')}"
                print(f"    Thumbnail: {thumbnail_url}")
                result = test_media_url(thumbnail_url, "thumbnail")
                print(f"      Status: {result['status']} ({result['status_code']})")
        else:
            print(f"❌ Failed to get clips from Frigate: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Frigate clips: {e}")
    
    # Test recordings
    print("\n🎥 FRIGATE RECORDINGS")
    print("-" * 20)
    try:
        response = requests.get(f"{FRIGATE_BASE}/api/recordings?limit=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            recordings = data.get('recordings', [])
            print(f"✅ Found {len(recordings)} recordings from Frigate")
            
            for i, recording in enumerate(recordings[:3], 1):
                print(f"\n  Recording {i}:")
                print(f"    ID: {recording.get('id', 'N/A')}")
                
                # Test video URL
                video_url = f"{FRIGATE_BASE}{recording.get('video_url', '')}"
                print(f"    Video: {video_url}")
                result = test_media_url(video_url, "video")
                print(f"      Status: {result['status']} ({result['status_code']})")
                if result['status_code'] == 200:
                    print(f"      Size: {result['content_length']} bytes")
                    print(f"      Type: {result['content_type']}")
        else:
            print(f"❌ Failed to get recordings from Frigate: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Frigate recordings: {e}")

def test_violations_media():
    """Test media URLs from violations API."""
    print("\n🚨 TESTING VIOLATIONS MEDIA")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/violations/live?limit=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            violations = data.get('data', [])
            print(f"✅ Found {len(violations)} violations with media URLs")
            
            for i, violation in enumerate(violations[:3], 1):
                print(f"\n  Violation {i}:")
                print(f"    ID: {violation.get('id', 'N/A')}")
                print(f"    Camera: {violation.get('camera', 'N/A')}")
                
                # Test video URL
                video_url = violation.get('video_url')
                if video_url:
                    print(f"    Video: {video_url}")
                    result = test_media_url(video_url, "video")
                    print(f"      Status: {result['status']} ({result['status_code']})")
                
                # Test thumbnail URL
                thumbnail_url = violation.get('thumbnail_url')
                if thumbnail_url:
                    print(f"    Thumbnail: {thumbnail_url}")
                    result = test_media_url(thumbnail_url, "thumbnail")
                    print(f"      Status: {result['status']} ({result['status_code']})")
                
                # Test snapshot URL
                snapshot_url = violation.get('snapshot_url')
                if snapshot_url:
                    print(f"    Snapshot: {snapshot_url}")
                    result = test_media_url(snapshot_url, "snapshot")
                    print(f"      Status: {result['status']} ({result['status_code']})")
        else:
            print(f"❌ Failed to get violations: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing violations media: {e}")

if __name__ == "__main__":
    print("🎬 FRIGATE DASHBOARD MIDDLEWARE - COMPREHENSIVE MEDIA TEST")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test middleware media API
    test_middleware_media()
    
    # Test Frigate API directly
    test_frigate_direct()
    
    # Test violations media
    test_violations_media()
    
    print("\n🏁 MEDIA TEST COMPLETED!")
    print("=" * 70)

