# 🎯 Zone-Based Employee Linking Solution

## 📊 **Problem Statement**

**Current Issue:**
- Phone violations detected on Camera B (can see back/phone)
- Face recognition works on Camera A (can see face)
- Need to link them via shared zones (desk assignments)

**Example Scenario:**
```
Camera A (employees_01): Sees face → "John Doe" at desk_30
Camera B (employees_05): Sees phone violation at desk_30
Result: Link "John Doe" to the phone violation
```

## 🛠️ **Solution: Zone-Based Linking Algorithm**

### **Step 1: Find Violations with Zones**
```sql
-- Get phone violations that have zone data
SELECT 
    p.timestamp,
    p.camera as violation_camera,
    p.source_id as id,
    p.data->'zones' as violation_zones
FROM timeline p
WHERE p.data->>'label' = 'cell phone'
AND p.data->'zones' IS NOT NULL
AND p.data->'zones' != '[]'::jsonb
```

### **Step 2: Find Person Detections with Same Zones**
```sql
-- Find person detections that share zones with violations
SELECT 
    f.timestamp,
    f.camera as person_camera,
    f.data->'zones' as person_zones,
    f.data->'sub_label'->>0 as employee_name,
    (f.data->'sub_label'->>1)::float as confidence
FROM timeline f
WHERE f.data->>'label' = 'person'
AND f.data->'sub_label' IS NOT NULL
AND f.data->'sub_label'->>0 IS NOT NULL
AND f.data->'zones' IS NOT NULL
```

### **Step 3: Zone Intersection Logic**
```python
def find_zone_intersection(violation_zones, person_zones):
    """
    Find if violation and person detection share any zones
    """
    if not violation_zones or not person_zones:
        return False
    
    # Convert to sets for intersection
    violation_set = set(violation_zones)
    person_set = set(person_zones)
    
    # Check for intersection (shared zones)
    intersection = violation_set.intersection(person_set)
    return len(intersection) > 0
```

### **Step 4: Complete Zone-Based Query**
```sql
WITH violation_zones AS (
    -- Get violations with zone data
    SELECT 
        p.timestamp as violation_time,
        p.camera as violation_camera,
        p.source_id as id,
        p.data->'zones' as violation_zones
    FROM timeline p
    WHERE p.data->>'label' = 'cell phone'
    AND p.data->'zones' IS NOT NULL
    AND p.data->'zones' != '[]'::jsonb
    AND p.timestamp > (EXTRACT(EPOCH FROM NOW()) - 3600)  -- Last hour
),
person_detections AS (
    -- Get person detections with face recognition and zones
    SELECT 
        f.timestamp as person_time,
        f.camera as person_camera,
        f.data->'zones' as person_zones,
        f.data->'sub_label'->>0 as employee_name,
        (f.data->'sub_label'->>1)::float as confidence
    FROM timeline f
    WHERE f.data->>'label' = 'person'
    AND f.data->'sub_label' IS NOT NULL
    AND f.data->'sub_label'->>0 IS NOT NULL
    AND f.data->'zones' IS NOT NULL
    AND f.timestamp > (EXTRACT(EPOCH FROM NOW()) - 3600)  -- Last hour
)
SELECT 
    v.violation_time,
    v.violation_camera,
    v.id,
    v.violation_zones,
    p.employee_name,
    p.confidence,
    p.person_camera,
    p.person_zones,
    ABS(p.person_time - v.violation_time) as time_gap
FROM violation_zones v
LEFT JOIN person_detections p ON (
    -- Zone intersection: check if any zones overlap
    v.violation_zones && p.person_zones  -- JSONB overlap operator
    AND ABS(p.person_time - v.violation_time) < 300  -- Within 5 minutes
)
ORDER BY v.violation_time DESC;
```

## 🎯 **Implementation Strategy**

### **Option 1: Hybrid Approach (Recommended)**
1. **First try**: Temporal proximity (current method)
2. **If no match**: Try zone-based linking
3. **Fallback**: "Unknown" employee

### **Option 2: Zone-First Approach**
1. **Primary**: Zone-based linking
2. **Fallback**: Temporal proximity
3. **Last resort**: "Unknown" employee

### **Option 3: Zone-Only Approach**
1. **Only use**: Zone-based linking
2. **No temporal**: Ignore time proximity
3. **Result**: More accurate but fewer matches

## 📊 **Expected Results**

### **Before (Temporal Only)**
```
Violation: Camera B, desk_30, no face recognition
Person: Camera A, desk_30, "John Doe" (5 minutes later)
Result: "Unknown" (different cameras)
```

### **After (Zone-Based)**
```
Violation: Camera B, desk_30, no face recognition
Person: Camera A, desk_30, "John Doe" (5 minutes later)
Result: "John Doe" (shared zone: desk_30)
```

## 🔧 **Configuration Options**

```python
# Zone-based linking settings
ZONE_LINKING_ENABLED = True
ZONE_TIME_WINDOW = 300  # 5 minutes
ZONE_CONFIDENCE_THRESHOLD = 0.8
FALLBACK_TO_TEMPORAL = True
```

## 🎉 **Benefits**

1. **More Accurate**: Links violations to correct employees
2. **Multi-Camera Support**: Works across different cameras
3. **Desk-Based**: Uses your existing zone setup
4. **Flexible**: Can combine with temporal proximity
5. **Scalable**: Works with any number of cameras/zones

## 🚀 **Next Steps**

1. **Implement zone intersection logic**
2. **Update violation query to use zones**
3. **Test with your multi-camera setup**
4. **Fine-tune time windows and confidence thresholds**
5. **Monitor accuracy and adjust as needed**

This solution will solve your multi-camera employee linking problem! 🎯
