#!/bin/bash

# PostgreSQL Shared Memory Fix Script
# Run this script on the PostgreSQL server (10.0.20.6)

echo "🔧 POSTGRESQL SHARED MEMORY FIX SCRIPT"
echo "======================================"
echo "This script will fix PostgreSQL shared memory issues"
echo "Run this on the PostgreSQL server (10.0.20.6)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo $0"
    exit 1
fi

echo "📋 Step 1: Backup current configuration"
# Find PostgreSQL config file
PG_CONFIG=$(find /etc -name "postgresql.conf" 2>/dev/null | head -1)
if [ -z "$PG_CONFIG" ]; then
    echo "❌ PostgreSQL config file not found. Please specify the path manually."
    exit 1
fi

echo "Found PostgreSQL config: $PG_CONFIG"
cp "$PG_CONFIG" "${PG_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Backup created"

echo ""
echo "📋 Step 2: Update PostgreSQL configuration"
# Create temporary config file with new settings
cat > /tmp/postgresql_fix.conf << 'EOF'
# Shared Memory Settings - Fix for middleware queries
shared_buffers = 256MB
work_mem = 64MB
maintenance_work_mem = 256MB
effective_cache_size = 1GB

# Connection Settings
max_connections = 200

# Memory Management
temp_buffers = 32MB
max_stack_depth = 2MB

# Query Planning (for SSD)
random_page_cost = 1.1
effective_io_concurrency = 200
EOF

echo "✅ Configuration file created: /tmp/postgresql_fix.conf"
echo "📝 Please manually merge these settings into your postgresql.conf:"
echo ""
cat /tmp/postgresql_fix.conf
echo ""

echo "📋 Step 3: Update system shared memory settings"
# Update sysctl.conf
if ! grep -q "kernel.shmmax" /etc/sysctl.conf; then
    cat >> /etc/sysctl.conf << 'EOF'

# PostgreSQL Shared Memory Settings
kernel.shmmax = 1073741824
kernel.shmall = 262144
kernel.shmmni = 4096
EOF
    echo "✅ Added shared memory settings to /etc/sysctl.conf"
else
    echo "⚠️  Shared memory settings already exist in /etc/sysctl.conf"
fi

echo ""
echo "📋 Step 4: Update user limits"
# Update limits.conf
if ! grep -q "postgres soft memlock" /etc/security/limits.conf; then
    cat >> /etc/security/limits.conf << 'EOF'

# PostgreSQL user limits
postgres soft memlock unlimited
postgres hard memlock unlimited
postgres soft stack 8192
postgres hard stack 8192
EOF
    echo "✅ Added PostgreSQL user limits to /etc/security/limits.conf"
else
    echo "⚠️  PostgreSQL user limits already exist in /etc/security/limits.conf"
fi

echo ""
echo "📋 Step 5: Apply system settings"
sysctl -p
echo "✅ Applied system settings"

echo ""
echo "📋 Step 6: Check shared memory"
echo "Current shared memory usage:"
df -h /dev/shm
echo ""
echo "Current shared memory segments:"
ipcs -m

echo ""
echo "📋 Step 7: Instructions for PostgreSQL restart"
echo "⚠️  IMPORTANT: You need to manually:"
echo "1. Edit $PG_CONFIG and add the settings from /tmp/postgresql_fix.conf"
echo "2. Restart PostgreSQL: systemctl restart postgresql"
echo "3. Check status: systemctl status postgresql"
echo ""

echo "📋 Step 8: Test commands (run after restart)"
echo "Test from middleware server:"
echo "curl 'http://localhost:5002/api/violations/hourly-trend?hours=168'"
echo "curl 'http://localhost:5002/api/employees/Unknown/violations?hours=168'"
echo ""

echo "🎯 QUICK FIX (if you want minimal changes):"
echo "Just add these two lines to $PG_CONFIG:"
echo "shared_buffers = 256MB"
echo "work_mem = 32MB"
echo "Then restart PostgreSQL: systemctl restart postgresql"
echo ""

echo "✅ Script completed! Follow the manual steps above to complete the fix."
