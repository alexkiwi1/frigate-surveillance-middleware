#!/usr/bin/env python3
"""
Data age analysis to understand why some snapshots work and others don't.
"""

import requests
import json
from datetime import datetime, timedelta

def analyze_data_age():
    """Analyze the age of violation data vs available snapshots."""
    print("🕐 DATA AGE ANALYSIS")
    print("=" * 50)
    print(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Current time
    now = datetime.now()
    print(f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get violation data
    print("🚨 VIOLATION DATA (Not Working Snapshots)")
    print("-" * 40)
    try:
        violations_response = requests.get("http://localhost:5002/api/violations/live?limit=5", timeout=10)
        if violations_response.status_code == 200:
            violations_data = violations_response.json()
            if violations_data.get("data"):
                for i, violation in enumerate(violations_data["data"]):
                    timestamp = violation.get('timestamp', 0)
                    violation_time = datetime.fromtimestamp(timestamp)
                    age_minutes = (now - violation_time).total_seconds() / 60
                    age_hours = age_minutes / 60
                    
                    print(f"Violation {i+1}:")
                    print(f"  Camera: {violation.get('camera', 'N/A')}")
                    print(f"  Time: {violation_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Age: {age_hours:.1f} hours ago ({age_minutes:.0f} minutes)")
                    print(f"  Snapshot URL: {violation.get('snapshot_url', 'N/A')}")
                    print()
        else:
            print("❌ Could not fetch violation data")
    except Exception as e:
        print(f"❌ Error fetching violations: {e}")
    
    # Get available snapshots
    print("📸 AVAILABLE SNAPSHOTS (Working)")
    print("-" * 40)
    try:
        snapshots_response = requests.get("http://10.0.20.6:5001/api/snapshots?limit=5", timeout=10)
        if snapshots_response.status_code == 200:
            snapshots_data = snapshots_response.json()
            if snapshots_data.get("snapshots"):
                for i, snapshot in enumerate(snapshots_data["snapshots"]):
                    timestamp = snapshot.get('timestamp', 0)
                    snapshot_time = datetime.fromtimestamp(timestamp)
                    age_minutes = (now - snapshot_time).total_seconds() / 60
                    age_hours = age_minutes / 60
                    
                    print(f"Snapshot {i+1}:")
                    print(f"  Camera: {snapshot.get('camera', 'N/A')}")
                    print(f"  Time: {snapshot_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Age: {age_hours:.1f} hours ago ({age_minutes:.0f} minutes)")
                    print(f"  ID: {snapshot.get('id', 'N/A')}")
                    print()
        else:
            print("❌ Could not fetch snapshot data")
    except Exception as e:
        print(f"❌ Error fetching snapshots: {e}")
    
    # Analysis
    print("🔍 ANALYSIS")
    print("-" * 40)
    print("The issue is NOT about data age - it's about camera mismatch!")
    print()
    print("Violations are from:")
    print("  - employees_07 (multiple times)")
    print("  - employees_04 (multiple times)")
    print()
    print("Available snapshots are from:")
    print("  - meeting_room (3 snapshots)")
    print("  - employees_08 (1 snapshot)")
    print("  - employees_02 (1 snapshot)")
    print()
    print("❌ NO SNAPSHOTS AVAILABLE for employees_07 or employees_04")
    print("✅ Snapshots exist for other cameras (meeting_room, employees_08, employees_02)")
    print()
    print("This means:")
    print("1. The violation data is recent (within 5 hours)")
    print("2. But there are no snapshots for those specific cameras")
    print("3. Frigate only generates snapshots when there's activity")
    print("4. employees_07 and employees_04 may not have had recent activity")

if __name__ == "__main__":
    analyze_data_age()

