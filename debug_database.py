#!/usr/bin/env python3
"""
Debug script to check database directly for recent data
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta

async def check_database():
    """Check database directly for recent data"""
    
    # Database connection
    conn = await asyncpg.connect(
        host="10.0.20.6",
        port=5433,
        user="frigate",
        password="frigate_secure_pass_2024",
        database="frigate_db"
    )
    
    print("🔍 DATABASE DEBUG - CHECKING RECENT DATA")
    print("=" * 50)
    
    # Check current time
    current_time = datetime.now().timestamp()
    print(f"Current time: {datetime.now()}")
    print(f"Current timestamp: {current_time}")
    print()
    
    # Check timeline table for recent data
    print("📊 Checking timeline table for recent data...")
    query = """
    SELECT 
        timestamp,
        camera,
        source,
        data->>'label' as label,
        data->>'id' as id
    FROM timeline 
    WHERE timestamp > (EXTRACT(EPOCH FROM NOW()) - 3600)
    ORDER BY timestamp DESC 
    LIMIT 10
    """
    
    rows = await conn.fetch(query)
    print(f"Found {len(rows)} recent timeline entries:")
    for row in rows:
        readable_time = datetime.fromtimestamp(row['timestamp'])
        print(f"  {readable_time} | {row['camera']} | {row['label']} | {row['id']}")
    
    print()
    
    # Check for cell phone violations specifically
    print("📱 Checking for recent cell phone violations...")
    query = """
    SELECT 
        timestamp,
        camera,
        data->>'id' as id,
        data->'zones' as zones
    FROM timeline 
    WHERE data->>'label' = 'cell phone'
    AND timestamp > (EXTRACT(EPOCH FROM NOW()) - 86400)
    ORDER BY timestamp DESC 
    LIMIT 10
    """
    
    rows = await conn.fetch(query)
    print(f"Found {len(rows)} cell phone violations in last 24h:")
    for row in rows:
        readable_time = datetime.fromtimestamp(row['timestamp'])
        print(f"  {readable_time} | {row['camera']} | {row['id']} | {row['zones']}")
    
    print()
    
    # Check recordings table
    print("🎬 Checking recordings table...")
    query = """
    SELECT 
        id,
        camera,
        start_time,
        end_time,
        duration
    FROM recordings 
    WHERE start_time > (EXTRACT(EPOCH FROM NOW()) - 3600)
    ORDER BY start_time DESC 
    LIMIT 5
    """
    
    rows = await conn.fetch(query)
    print(f"Found {len(rows)} recent recordings:")
    for row in rows:
        start_time = datetime.fromtimestamp(row['start_time'])
        print(f"  {start_time} | {row['camera']} | {row['id']} | {row['duration']}s")
    
    print()
    
    # Check if there's a gap in data
    print("⏰ Checking for data gaps...")
    query = """
    SELECT 
        MAX(timestamp) as latest_timeline,
        MIN(timestamp) as earliest_timeline,
        COUNT(*) as total_entries
    FROM timeline
    """
    
    row = await conn.fetchrow(query)
    if row:
        latest = datetime.fromtimestamp(row['latest_timeline'])
        earliest = datetime.fromtimestamp(row['earliest_timeline'])
        print(f"Timeline data range: {earliest} to {latest}")
        print(f"Total timeline entries: {row['total_entries']}")
        
        # Check if latest data is recent
        time_diff = current_time - row['latest_timeline']
        print(f"Latest data is {time_diff/3600:.1f} hours old")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_database())

