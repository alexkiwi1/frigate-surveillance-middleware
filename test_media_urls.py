#!/usr/bin/env python3
"""
Comprehensive Media URL Testing Script
Tests all media URLs from violations to verify accessibility
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
    print("🔍 COMPREHENSIVE MEDIA URL ACCESSIBILITY TEST")
    print("=" * 60)
    print()
    
    # Get violations with media URLs
    print("📊 Fetching violations...")
    response = requests.get(f"{API_BASE}/violations/live?limit=10")
    
    if response.status_code != 200:
        print(f"❌ Failed to get violations: {response.status_code}")
        return
    
    data = response.json()
    violations = data.get('data', [])
    
    if not violations:
        print("⚠️  No violations found in the system")
        return
    
    print(f"✅ Found {len(violations)} violations to test")
    print()
    
    # Test media URLs
    results = {
        'video': [],
        'thumbnail': [],
        'snapshot': []
    }
    
    for i, violation in enumerate(violations, 1):
        print(f"Testing violation {i}/{len(violations)}...")
        print(f"  ID: {violation['id']}")
        print(f"  Camera: {violation['camera']}")
        print(f"  Time: {datetime.fromtimestamp(violation['timestamp'])}")
        
        # Test video URL
        if violation.get('video_url'):
            result = test_url(violation['video_url'], 'video')
            results['video'].append(result)
            status_icon = "✅" if result['accessible'] else "❌"
            print(f"    {status_icon} Video: {result['status']} ({result['size']} bytes)")
        
        # Test thumbnail URL
        if violation.get('thumbnail_url'):
            result = test_url(violation['thumbnail_url'], 'thumbnail')
            results['thumbnail'].append(result)
            status_icon = "✅" if result['accessible'] else "❌"
            print(f"    {status_icon} Thumbnail: {result['status']} ({result['size']} bytes)")
        
        # Test snapshot URL
        if violation.get('snapshot_url'):
            result = test_url(violation['snapshot_url'], 'snapshot')
            results['snapshot'].append(result)
            status_icon = "✅" if result['accessible'] else "❌"
            print(f"    {status_icon} Snapshot: {result['status']} ({result['size']} bytes)")
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
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
    
    # Test Frigate API directly
    print("=" * 60)
    print("🔍 TESTING FRIGATE API DIRECTLY")
    print("=" * 60)
    
    endpoints = [
        "/",
        "/api/stats",
        "/api/config",
    ]
    
    for endpoint in endpoints:
        url = f"{FRIGATE_BASE}{endpoint}"
        result = test_url(url, 'frigate_api')
        status_icon = "✅" if result['accessible'] else "❌"
        print(f"{status_icon} {endpoint}: {result['status']}")
    
    print()
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()






