#!/usr/bin/env python3
"""
Test recent media URLs from the database
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:5002/api"
FRIGATE_BASE = "http://10.0.20.6:5001"

def test_url(url, url_type):
    """Test a single URL and return status"""
    try:
        response = requests.head(url, timeout=5)
        status = response.status_code
        size = response.headers.get('Content-Length', 'unknown')
        return {
            'url': url,
            'type': url_type,
            'status': status,
            'size': size,
            'accessible': status == 200
        }
    except Exception as e:
        return {
            'url': url,
            'type': url_type,
            'status': 'error',
            'size': 'unknown',
            'accessible': False,
            'error': str(e)
        }

def main():
    print("🔍 TESTING RECENT MEDIA URLS")
    print("=" * 40)
    print()
    
    # Get recent recordings from Frigate API directly
    print("📊 Getting recent recordings from Frigate...")
    response = requests.get(f"{FRIGATE_BASE}/api/recordings?limit=5")
    
    if response.status_code != 200:
        print(f"❌ Failed to get recordings: {response.status_code}")
        return
    
    data = response.json()
    recordings = data.get('recordings', [])
    
    if not recordings:
        print("⚠️  No recordings found")
        return
    
    print(f"✅ Found {len(recordings)} recent recordings")
    print()
    
    # Test media URLs for recent recordings
    results = {
        'video': [],
        'thumbnail': [],
        'snapshot': []
    }
    
    for i, recording in enumerate(recordings, 1):
        print(f"Testing recording {i}/{len(recordings)}...")
        print(f"  Camera: {recording['camera']}")
        print(f"  Start: {datetime.fromtimestamp(recording['start_time'])}")
        print(f"  Video URL: {recording['video_url']}")
        
        # Test video URL (use the provided video_url, make it absolute)
        video_url = f"{FRIGATE_BASE}{recording['video_url']}"
        result = test_url(video_url, 'video')
        results['video'].append(result)
        status_icon = "✅" if result['accessible'] else "❌"
        print(f"    {status_icon} Video: {result['status']} ({result['size']} bytes)")
        
        # Extract ID from video_url for other tests
        video_id = video_url.split('/')[-1]
        
        # Test thumbnail URL
        thumbnail_url = f"{FRIGATE_BASE}/thumb/{video_id}"
        result = test_url(thumbnail_url, 'thumbnail')
        results['thumbnail'].append(result)
        status_icon = "✅" if result['accessible'] else "❌"
        print(f"    {status_icon} Thumbnail: {result['status']} ({result['size']} bytes)")
        
        # Test snapshot URL (using start_time as timestamp)
        snapshot_url = f"{FRIGATE_BASE}/snapshot/{recording['camera']}/{recording['start_time']}-{video_id}"
        result = test_url(snapshot_url, 'snapshot')
        results['snapshot'].append(result)
        status_icon = "✅" if result['accessible'] else "❌"
        print(f"    {status_icon} Snapshot: {result['status']} ({result['size']} bytes)")
        
        print()
    
    # Summary
    print("=" * 40)
    print("📊 SUMMARY")
    print("=" * 40)
    
    for media_type, tests in results.items():
        if tests:
            accessible = sum(1 for t in tests if t['accessible'])
            total = len(tests)
            percentage = (accessible / total * 100) if total > 0 else 0
            print(f"{media_type.upper()}:")
            print(f"  Total: {total}")
            print(f"  Accessible: {accessible} ({percentage:.1f}%)")
            print(f"  Failed: {total - accessible}")
            print()
    
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()
