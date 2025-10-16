#!/usr/bin/env python3
"""
🎬 COMPREHENSIVE VIDEO ACCESSIBILITY TEST - OCTOBER 2024
========================================================
Tests video accessibility across every day from October 1st, 2024
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys

# Configuration
FRIGATE_BASE = "http://10.0.20.6:5001"
MIDDLEWARE_BASE = "http://10.0.20.7:5002"
OCTOBER_1ST = datetime(2025, 10, 1)  # October 1st, 2025
TODAY = datetime.now()

def get_timestamp_for_date(date: datetime) -> float:
    """Convert datetime to Unix timestamp"""
    return date.timestamp()

def test_video_url(url: str, timeout: int = 10) -> Tuple[bool, int, int]:
    """Test if a video URL is accessible"""
    try:
        response = requests.head(url, timeout=timeout)
        return True, response.status_code, len(response.content) if response.content else 0
    except requests.exceptions.RequestException as e:
        return False, 0, 0

def test_thumbnail_url(url: str, timeout: int = 10) -> Tuple[bool, int, int]:
    """Test if a thumbnail URL is accessible"""
    try:
        response = requests.head(url, timeout=timeout)
        return True, response.status_code, len(response.content) if response.content else 0
    except requests.exceptions.RequestException as e:
        return False, 0, 0

def get_recordings_for_date(date: datetime, limit: int = 50) -> List[Dict]:
    """Get recordings for a specific date"""
    start_time = get_timestamp_for_date(date)
    end_time = get_timestamp_for_date(date + timedelta(days=1))
    
    try:
        url = f"{FRIGATE_BASE}/api/recordings"
        params = {
            "start_time": int(start_time),
            "end_time": int(end_time),
            "limit": limit
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("recordings", [])
        else:
            print(f"❌ Failed to get recordings for {date.strftime('%Y-%m-%d')}: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting recordings for {date.strftime('%Y-%m-%d')}: {e}")
        return []

def get_clips_for_date(date: datetime, limit: int = 50) -> List[Dict]:
    """Get clips for a specific date"""
    start_time = get_timestamp_for_date(date)
    end_time = get_timestamp_for_date(date + timedelta(days=1))
    
    try:
        url = f"{FRIGATE_BASE}/api/clips"
        params = {
            "start_time": int(start_time),
            "end_time": int(end_time),
            "limit": limit
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("clips", [])
        else:
            print(f"❌ Failed to get clips for {date.strftime('%Y-%m-%d')}: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting clips for {date.strftime('%Y-%m-%d')}: {e}")
        return []

def test_day_videos(date: datetime) -> Dict:
    """Test all videos for a specific day"""
    print(f"📅 Testing {date.strftime('%Y-%m-%d (%A)')}...")
    
    # Get recordings and clips for the day
    recordings = get_recordings_for_date(date, limit=20)
    clips = get_clips_for_date(date, limit=20)
    
    day_results = {
        "date": date.strftime('%Y-%m-%d'),
        "day_name": date.strftime('%A'),
        "recordings": {
            "total": len(recordings),
            "accessible": 0,
            "failed": 0,
            "details": []
        },
        "clips": {
            "total": len(clips),
            "accessible": 0,
            "failed": 0,
            "details": []
        }
    }
    
    # Test recordings
    print(f"  🎥 Testing {len(recordings)} recordings...")
    for recording in recordings:
        video_url = f"{FRIGATE_BASE}{recording.get('video_url', '')}"
        if video_url == FRIGATE_BASE:
            continue
            
        accessible, status, size = test_video_url(video_url)
        result = {
            "id": recording.get('id'),
            "camera": recording.get('camera'),
            "start_time": recording.get('start_time'),
            "url": video_url,
            "accessible": accessible,
            "status": status,
            "size": size
        }
        
        if accessible and status == 200:
            day_results["recordings"]["accessible"] += 1
            print(f"    ✅ Recording {recording.get('id', 'unknown')}: {status} ({size:,} bytes)")
        else:
            day_results["recordings"]["failed"] += 1
            print(f"    ❌ Recording {recording.get('id', 'unknown')}: {status}")
        
        day_results["recordings"]["details"].append(result)
    
    # Test clips
    print(f"  🎬 Testing {len(clips)} clips...")
    for clip in clips:
        video_url = f"{FRIGATE_BASE}{clip.get('video_url', '')}"
        thumbnail_url = f"{FRIGATE_BASE}{clip.get('thumbnail_url', '')}"
        
        if video_url == FRIGATE_BASE:
            continue
            
        # Test video
        video_accessible, video_status, video_size = test_video_url(video_url)
        # Test thumbnail
        thumb_accessible, thumb_status, thumb_size = test_thumbnail_url(thumbnail_url)
        
        result = {
            "id": clip.get('id'),
            "camera": clip.get('camera'),
            "start_time": clip.get('start_time'),
            "video_url": video_url,
            "video_accessible": video_accessible,
            "video_status": video_status,
            "video_size": video_size,
            "thumbnail_url": thumbnail_url,
            "thumbnail_accessible": thumb_accessible,
            "thumbnail_status": thumb_status,
            "thumbnail_size": thumb_size
        }
        
        if video_accessible and video_status == 200:
            day_results["clips"]["accessible"] += 1
            print(f"    ✅ Clip {clip.get('id', 'unknown')}: Video {video_status} ({video_size:,} bytes)")
        else:
            day_results["clips"]["failed"] += 1
            print(f"    ❌ Clip {clip.get('id', 'unknown')}: Video {video_status}")
        
        if thumb_accessible and thumb_status == 200:
            print(f"    ✅ Clip {clip.get('id', 'unknown')}: Thumbnail {thumb_status} ({thumb_size:,} bytes)")
        else:
            print(f"    ❌ Clip {clip.get('id', 'unknown')}: Thumbnail {thumb_status}")
        
        day_results["clips"]["details"].append(result)
    
    return day_results

def generate_report(results: List[Dict]) -> str:
    """Generate a comprehensive report"""
    report = []
    report.append("# 🎬 VIDEO ACCESSIBILITY REPORT - OCTOBER 2025")
    report.append("=" * 60)
    report.append(f"Test Period: October 1, 2025 - {TODAY.strftime('%B %d, %Y')}")
    report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary statistics
    total_days = len(results)
    total_recordings = sum(r["recordings"]["total"] for r in results)
    total_clips = sum(r["clips"]["total"] for r in results)
    accessible_recordings = sum(r["recordings"]["accessible"] for r in results)
    accessible_clips = sum(r["clips"]["accessible"] for r in results)
    
    report.append("## 📊 SUMMARY STATISTICS")
    report.append("-" * 30)
    report.append(f"**Total Days Tested**: {total_days}")
    report.append(f"**Total Recordings**: {total_recordings}")
    report.append(f"**Accessible Recordings**: {accessible_recordings}")
    report.append(f"**Recording Success Rate**: {(accessible_recordings/total_recordings*100):.1f}%" if total_recordings > 0 else "**Recording Success Rate**: N/A")
    report.append("")
    report.append(f"**Total Clips**: {total_clips}")
    report.append(f"**Accessible Clips**: {accessible_clips}")
    report.append(f"**Clip Success Rate**: {(accessible_clips/total_clips*100):.1f}%" if total_clips > 0 else "**Clip Success Rate**: N/A")
    report.append("")
    
    # Daily breakdown
    report.append("## 📅 DAILY BREAKDOWN")
    report.append("-" * 30)
    report.append("| Date | Day | Recordings | Clips | Recording % | Clip % |")
    report.append("|------|-----|------------|-------|-------------|--------|")
    
    for result in results:
        date = result["date"]
        day = result["day_name"]
        rec_total = result["recordings"]["total"]
        rec_accessible = result["recordings"]["accessible"]
        clip_total = result["clips"]["total"]
        clip_accessible = result["clips"]["accessible"]
        
        rec_pct = (rec_accessible/rec_total*100) if rec_total > 0 else 0
        clip_pct = (clip_accessible/clip_total*100) if clip_total > 0 else 0
        
        report.append(f"| {date} | {day} | {rec_accessible}/{rec_total} | {clip_accessible}/{clip_total} | {rec_pct:.1f}% | {clip_pct:.1f}% |")
    
    report.append("")
    
    # Problem days
    problem_days = []
    for result in results:
        rec_pct = (result["recordings"]["accessible"]/result["recordings"]["total"]*100) if result["recordings"]["total"] > 0 else 100
        clip_pct = (result["clips"]["accessible"]/result["clips"]["total"]*100) if result["clips"]["total"] > 0 else 100
        
        if rec_pct < 100 or clip_pct < 100:
            problem_days.append({
                "date": result["date"],
                "day": result["day_name"],
                "rec_pct": rec_pct,
                "clip_pct": clip_pct,
                "rec_failed": result["recordings"]["failed"],
                "clip_failed": result["clips"]["failed"]
            })
    
    if problem_days:
        report.append("## ⚠️ PROBLEM DAYS")
        report.append("-" * 30)
        report.append("| Date | Day | Recording Issues | Clip Issues |")
        report.append("|------|-----|------------------|-------------|")
        
        for day in problem_days:
            report.append(f"| {day['date']} | {day['day']} | {day['rec_failed']} failed ({day['rec_pct']:.1f}%) | {day['clip_failed']} failed ({day['clip_pct']:.1f}%) |")
        
        report.append("")
        
        # Detailed problem analysis
        report.append("## 🔍 DETAILED PROBLEM ANALYSIS")
        report.append("-" * 30)
        
        for day in problem_days:
            report.append(f"### {day['date']} ({day['day']})")
            report.append("")
            
            # Find the result for this day
            day_result = next(r for r in results if r["date"] == day["date"])
            
            # Recording issues
            if day_result["recordings"]["failed"] > 0:
                report.append("**Recording Issues:**")
                for detail in day_result["recordings"]["details"]:
                    if not detail["accessible"]:
                        report.append(f"- ID: {detail['id']}, Camera: {detail['camera']}, Status: {detail['status']}")
                report.append("")
            
            # Clip issues
            if day_result["clips"]["failed"] > 0:
                report.append("**Clip Issues:**")
                for detail in day_result["clips"]["details"]:
                    if not detail["video_accessible"]:
                        report.append(f"- ID: {detail['id']}, Camera: {detail['camera']}, Video Status: {detail['video_status']}")
                    if not detail["thumbnail_accessible"]:
                        report.append(f"- ID: {detail['id']}, Camera: {detail['camera']}, Thumbnail Status: {detail['thumbnail_status']}")
                report.append("")
    
    # Recommendations
    report.append("## 🛠️ RECOMMENDATIONS")
    report.append("-" * 30)
    
    if accessible_recordings < total_recordings:
        report.append("### Recording Issues:")
        report.append("- Check Frigate recording storage configuration")
        report.append("- Verify disk space and permissions")
        report.append("- Check Frigate logs for recording errors")
        report.append("")
    
    if accessible_clips < total_clips:
        report.append("### Clip Issues:")
        report.append("- Check Frigate clip generation configuration")
        report.append("- Verify clip storage directory exists")
        report.append("- Check Frigate logs for clip processing errors")
        report.append("- Consider adjusting clip retention settings")
        report.append("")
    
    report.append("## 🏁 CONCLUSION")
    report.append("-" * 30)
    
    overall_rec_success = (accessible_recordings/total_recordings*100) if total_recordings > 0 else 100
    overall_clip_success = (accessible_clips/total_clips*100) if total_clips > 0 else 100
    
    if overall_rec_success >= 95 and overall_clip_success >= 95:
        report.append("✅ **EXCELLENT**: Video accessibility is very good (>95% success rate)")
    elif overall_rec_success >= 80 and overall_clip_success >= 80:
        report.append("⚠️ **GOOD**: Video accessibility is acceptable (>80% success rate)")
    else:
        report.append("❌ **POOR**: Video accessibility needs immediate attention (<80% success rate)")
    
    report.append("")
    report.append(f"**Overall Recording Success**: {overall_rec_success:.1f}%")
    report.append(f"**Overall Clip Success**: {overall_clip_success:.1f}%")
    
    return "\n".join(report)

def main():
    """Main test function"""
    print("🎬 COMPREHENSIVE VIDEO ACCESSIBILITY TEST - OCTOBER 2025")
    print("=" * 60)
    print(f"Testing videos from October 1, 2025 to {TODAY.strftime('%B %d, %Y')}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    results = []
    current_date = OCTOBER_1ST
    
    while current_date <= TODAY:
        try:
            day_result = test_day_videos(current_date)
            results.append(day_result)
            
            # Small delay to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error testing {current_date.strftime('%Y-%m-%d')}: {e}")
        
        current_date += timedelta(days=1)
    
    print("")
    print("📊 Generating comprehensive report...")
    
    # Generate and save report
    report = generate_report(results)
    
    with open("/opt/dashboard_middleware/VIDEO_ACCESSIBILITY_REPORT_OCTOBER_2025.md", "w") as f:
        f.write(report)
    
    print("✅ Report saved to: VIDEO_ACCESSIBILITY_REPORT_OCTOBER_2025.md")
    print("")
    print("📋 QUICK SUMMARY:")
    
    total_recordings = sum(r["recordings"]["total"] for r in results)
    total_clips = sum(r["clips"]["total"] for r in results)
    accessible_recordings = sum(r["recordings"]["accessible"] for r in results)
    accessible_clips = sum(r["clips"]["accessible"] for r in results)
    
    rec_success = (accessible_recordings/total_recordings*100) if total_recordings > 0 else 100
    clip_success = (accessible_clips/total_clips*100) if total_clips > 0 else 100
    
    print(f"  📅 Days tested: {len(results)}")
    print(f"  🎥 Recordings: {accessible_recordings}/{total_recordings} ({rec_success:.1f}%)")
    print(f"  🎬 Clips: {accessible_clips}/{total_clips} ({clip_success:.1f}%)")
    
    if rec_success >= 95 and clip_success >= 95:
        print("  ✅ EXCELLENT: Video accessibility is very good!")
    elif rec_success >= 80 and clip_success >= 80:
        print("  ⚠️ GOOD: Video accessibility is acceptable")
    else:
        print("  ❌ POOR: Video accessibility needs attention")
    
    print("")
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()
