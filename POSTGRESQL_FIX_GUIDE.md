# PostgreSQL Shared Memory Fix Guide

## 🚨 **PROBLEM IDENTIFIED**

The PostgreSQL server at `10.0.20.6:5433` has **shared memory limitations** that prevent complex queries from working beyond 72 hours.

### **Error Messages:**
```
could not resize shared memory segment "/PostgreSQL.XXXXX" to XXXXX bytes: No space left on device
```

### **Affected Operations:**
- Hourly trend queries beyond 72 hours
- Complex employee violation queries
- Large dataset aggregations

---

## 🔧 **POSTGRESQL CONFIGURATION FIXES**

### **1. Increase Shared Memory Settings**

Edit PostgreSQL configuration file (`postgresql.conf`):

```bash
# Connect to PostgreSQL server
ssh root@10.0.20.6

# Edit PostgreSQL config
nano /etc/postgresql/*/main/postgresql.conf
# or
nano /var/lib/postgresql/data/postgresql.conf
```

**Add/Modify these settings:**

```ini
# Shared Memory Settings
shared_buffers = 256MB                    # Increase from default (128MB)
work_mem = 64MB                          # Increase from default (4MB)
maintenance_work_mem = 256MB             # Increase from default (64MB)
effective_cache_size = 1GB               # Set to 75% of available RAM

# Connection Settings
max_connections = 200                    # Increase if needed
shared_preload_libraries = 'pg_stat_statements'

# Memory Management
temp_buffers = 32MB                      # Increase from default (8MB)
max_stack_depth = 2MB                    # Increase from default (2MB)

# Query Planning
random_page_cost = 1.1                   # For SSD storage
effective_io_concurrency = 200           # For SSD storage
```

### **2. System-Level Shared Memory Settings**

Edit system configuration:

```bash
# Edit system limits
nano /etc/sysctl.conf
```

**Add these lines:**

```bash
# Shared Memory Settings
kernel.shmmax = 1073741824              # 1GB (adjust based on RAM)
kernel.shmall = 262144                  # 1GB / 4KB page size
kernel.shmmni = 4096                    # Maximum number of segments

# Apply changes
sysctl -p
```

### **3. PostgreSQL User Limits**

Edit user limits:

```bash
# Edit limits for postgres user
nano /etc/security/limits.conf
```

**Add these lines:**

```bash
postgres soft memlock unlimited
postgres hard memlock unlimited
postgres soft stack 8192
postgres hard stack 8192
```

### **4. System Memory Settings**

Check and adjust system memory:

```bash
# Check current memory
free -h

# Check shared memory
df -h /dev/shm

# If /dev/shm is too small, remount it
mount -o remount,size=2G /dev/shm
```

---

## 🚀 **IMPLEMENTATION STEPS**

### **Step 1: Backup Current Configuration**
```bash
# On PostgreSQL server (10.0.20.6)
cp /etc/postgresql/*/main/postgresql.conf /etc/postgresql/*/main/postgresql.conf.backup
```

### **Step 2: Apply Configuration Changes**
```bash
# Edit postgresql.conf with the settings above
nano /etc/postgresql/*/main/postgresql.conf

# Edit system settings
nano /etc/sysctl.conf
nano /etc/security/limits.conf
```

### **Step 3: Restart Services**
```bash
# Apply system settings
sysctl -p

# Restart PostgreSQL
systemctl restart postgresql

# Check status
systemctl status postgresql
```

### **Step 4: Verify Settings**
```bash
# Connect to PostgreSQL
psql -U frigate -d frigate_db -h localhost

# Check shared memory settings
SHOW shared_buffers;
SHOW work_mem;
SHOW maintenance_work_mem;
SHOW effective_cache_size;
```

---

## 📊 **RECOMMENDED VALUES BY SYSTEM SIZE**

### **Small System (4GB RAM):**
```ini
shared_buffers = 1GB
work_mem = 32MB
maintenance_work_mem = 128MB
effective_cache_size = 3GB
```

### **Medium System (8GB RAM):**
```ini
shared_buffers = 2GB
work_mem = 64MB
maintenance_work_mem = 256MB
effective_cache_size = 6GB
```

### **Large System (16GB+ RAM):**
```ini
shared_buffers = 4GB
work_mem = 128MB
maintenance_work_mem = 512MB
effective_cache_size = 12GB
```

---

## 🔍 **TESTING AFTER FIX**

### **Test Commands:**
```bash
# Test from middleware server
curl "http://localhost:5002/api/violations/hourly-trend?hours=168"
curl "http://localhost:5002/api/employees/Unknown/violations?hours=168"
```

### **Expected Results:**
- ✅ Hourly trend queries work up to 168 hours
- ✅ Employee violation queries work for extended periods
- ✅ No more "shared memory" errors in logs

---

## ⚠️ **IMPORTANT NOTES**

1. **Restart Required**: PostgreSQL must be restarted after configuration changes
2. **Memory Usage**: Increased settings will use more RAM
3. **Backup First**: Always backup configuration before changes
4. **Monitor Performance**: Watch system performance after changes
5. **Gradual Increase**: Start with smaller values and increase gradually

---

## 🎯 **QUICK FIX (Minimal Changes)**

If you want a quick fix with minimal changes:

```ini
# In postgresql.conf - just increase these two:
shared_buffers = 256MB
work_mem = 32MB
```

Then restart PostgreSQL:
```bash
systemctl restart postgresql
```

This should resolve most shared memory issues for queries up to 168 hours.

---

## 📞 **SUPPORT**

If issues persist after these changes:
1. Check PostgreSQL logs: `/var/log/postgresql/postgresql-*.log`
2. Monitor system memory: `free -h` and `top`
3. Check shared memory: `ipcs -m`
4. Verify configuration: `SHOW ALL;` in PostgreSQL



