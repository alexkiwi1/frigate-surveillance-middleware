#!/usr/bin/env python3
"""
Check PostgreSQL configuration and shared memory status
"""

import psycopg2
import sys

def check_postgresql_config():
    """Check PostgreSQL configuration and shared memory settings"""
    
    print("🔍 POSTGRESQL CONFIGURATION CHECK")
    print("=" * 40)
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host="10.0.20.6",
            port="5433",
            database="frigate_db",
            user="frigate",
            password="frigate_secure_pass_2024"
        )
        
        cursor = conn.cursor()
        
        # Check key configuration settings
        settings_to_check = [
            'shared_buffers',
            'work_mem',
            'maintenance_work_mem',
            'effective_cache_size',
            'max_connections',
            'temp_buffers',
            'max_stack_depth'
        ]
        
        print("📊 Current PostgreSQL Settings:")
        print("-" * 30)
        
        for setting in settings_to_check:
            cursor.execute(f"SHOW {setting};")
            value = cursor.fetchone()[0]
            print(f"{setting:20}: {value}")
        
        print("\n📊 System Information:")
        print("-" * 30)
        
        # Check system info
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL Version: {version}")
        
        cursor.execute("SELECT pg_database_size('frigate_db');")
        db_size = cursor.fetchone()[0]
        print(f"Database Size: {db_size / 1024 / 1024:.1f} MB")
        
        # Check shared memory usage
        cursor.execute("""
            SELECT name, setting, unit, context 
            FROM pg_settings 
            WHERE name LIKE '%shared%' OR name LIKE '%work%' OR name LIKE '%memory%'
            ORDER BY name;
        """)
        
        print("\n📊 Memory-Related Settings:")
        print("-" * 30)
        for row in cursor.fetchall():
            name, setting, unit, context = row
            unit_str = f" {unit}" if unit else ""
            print(f"{name:25}: {setting}{unit_str}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ PostgreSQL connection successful!")
        
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        return False
    
    return True

def main():
    success = check_postgresql_config()
    
    print("\n" + "=" * 40)
    print("📋 RECOMMENDATIONS:")
    print("=" * 40)
    
    print("If you see issues with shared memory, you need to:")
    print("1. Increase shared_buffers (recommended: 256MB)")
    print("2. Increase work_mem (recommended: 64MB)")
    print("3. Increase maintenance_work_mem (recommended: 256MB)")
    print("4. Restart PostgreSQL after changes")
    print("")
    print("Run the fix script: ./fix_postgresql.sh")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)




