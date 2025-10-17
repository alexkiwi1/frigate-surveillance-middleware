# 🎯 Frontend API Update Guide - Violations API

## 📊 **Updated Violations API Details**

### **Endpoint**
```
GET /api/violations/live
```

### **Query Parameters**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 50 | Maximum number of violations to return |
| `camera` | string | No | null | Filter by specific camera (e.g., "employees_02") |
| `hours` | integer | No | 24 | Hours to look back for violations |

### **Example Requests**
```javascript
// Get all recent violations
fetch('/api/violations/live?limit=10')

// Get violations from specific camera
fetch('/api/violations/live?camera=employees_02&limit=5')

// Get violations from last 2 hours
fetch('/api/violations/live?hours=2&limit=20')
```

## 🎯 **Updated Response Format**

### **Response Structure**
```json
{
  "success": true,
  "message": "Live violations retrieved from cache",
  "data": [
    {
      "id": "1760702820.784903-qllmpw",
      "timestamp": 1760703412.548718,
      "timestamp_iso": "2025-10-17T17:16:52.548718+05:00",
      "timestamp_readable": "2025-10-17 17:16:52",
      "relative_time": "just now",
      "camera": "employees_02",
      "employee_name": "Nimra Fareed",
      "confidence": 0.99,
      "zones": "[\"employee_area\", \"desk_11\", \"desk_10\"]",
      "thumbnail_url": null,
      "video_url": null,
      "snapshot_url": "http://10.0.20.6:5001/snapshot/employees_02/1760702820.784903-qllmpw"
    }
  ],
  "timestamp": "2025-10-17T17:19:24.934015+05:00"
}
```

## 🔄 **Key Changes from Previous Version**

### **✅ What's New**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **`zones`** | string | JSON string of zones where violation occurred | `"[\"employee_area\", \"desk_11\", \"desk_10\"]"` |
| **`employee_name`** | string | Real employee name (desk-based linking) | `"Nimra Fareed"` |
| **`confidence`** | float | Face recognition confidence score | `0.99` |

### **❌ What's Removed/Changed**
| Field | Old Value | New Value | Reason |
|-------|-----------|-----------|---------|
| **`thumbnail_url`** | `http://10.0.20.6:5001/thumb/...` | `null` | Thumbnails don't exist for violations |
| **`video_url`** | `http://10.0.20.6:5001/clip/...` | `null` | Video clips don't exist for violations |
| **`employee_name`** | `"Unknown"` | Real names | Now uses desk-based linking |

## 🎨 **Frontend Implementation Guide**

### **1. Display Employee Information**
```javascript
// Parse zones data
const zones = JSON.parse(violation.zones);
const deskZones = zones.filter(zone => zone.startsWith('desk_'));

// Display employee info
const employeeInfo = {
  name: violation.employee_name,
  confidence: Math.round(violation.confidence * 100) + '%',
  desks: deskZones.join(', ')
};

// Example display
console.log(`${employeeInfo.name} (${employeeInfo.confidence}) at ${employeeInfo.desks}`);
// Output: "Nimra Fareed (99%) at desk_11, desk_10"
```

### **2. Handle Media URLs**
```javascript
// Only use snapshot_url (thumbnails and videos are null)
const mediaUrl = violation.snapshot_url; // This works!
const thumbnailUrl = violation.thumbnail_url; // This is null
const videoUrl = violation.video_url; // This is null

// Display logic
if (mediaUrl) {
  // Show snapshot image
  imgElement.src = mediaUrl;
} else {
  // Show placeholder
  imgElement.src = '/placeholder-violation.png';
}
```

### **3. Zone-Based Filtering**
```javascript
// Filter violations by specific desk
function filterByDesk(violations, targetDesk) {
  return violations.filter(violation => {
    const zones = JSON.parse(violation.zones);
    return zones.some(zone => zone === targetDesk);
  });
}

// Example: Get violations at desk_11
const desk11Violations = filterByDesk(violations, 'desk_11');
```

### **4. Employee-Based Grouping**
```javascript
// Group violations by employee
function groupByEmployee(violations) {
  const grouped = {};
  
  violations.forEach(violation => {
    const employee = violation.employee_name;
    if (!grouped[employee]) {
      grouped[employee] = [];
    }
    grouped[employee].push(violation);
  });
  
  return grouped;
}

// Example usage
const employeeGroups = groupByEmployee(violations);
Object.keys(employeeGroups).forEach(employee => {
  console.log(`${employee}: ${employeeGroups[employee].length} violations`);
});
```

### **5. Confidence-Based Styling**
```javascript
// Apply styling based on confidence
function getConfidenceClass(confidence) {
  if (confidence >= 0.9) return 'high-confidence';
  if (confidence >= 0.7) return 'medium-confidence';
  return 'low-confidence';
}

// CSS classes
const confidenceClass = getConfidenceClass(violation.confidence);
element.className = `violation-item ${confidenceClass}`;
```

## 🎯 **Updated Frontend Components**

### **Violation Card Component**
```jsx
function ViolationCard({ violation }) {
  const zones = JSON.parse(violation.zones);
  const deskZones = zones.filter(zone => zone.startsWith('desk_'));
  const confidencePercent = Math.round(violation.confidence * 100);
  
  return (
    <div className="violation-card">
      <div className="violation-header">
        <h3>{violation.employee_name}</h3>
        <span className={`confidence ${getConfidenceClass(violation.confidence)}`}>
          {confidencePercent}%
        </span>
      </div>
      
      <div className="violation-details">
        <p><strong>Camera:</strong> {violation.camera}</p>
        <p><strong>Desks:</strong> {deskZones.join(', ')}</p>
        <p><strong>Time:</strong> {violation.relative_time}</p>
      </div>
      
      <div className="violation-media">
        {violation.snapshot_url ? (
          <img 
            src={violation.snapshot_url} 
            alt="Violation snapshot"
            className="violation-snapshot"
          />
        ) : (
          <div className="no-media-placeholder">
            No snapshot available
          </div>
        )}
      </div>
    </div>
  );
}
```

### **Employee Filter Component**
```jsx
function EmployeeFilter({ violations, onFilterChange }) {
  const employees = [...new Set(violations.map(v => v.employee_name))];
  
  return (
    <select onChange={(e) => onFilterChange(e.target.value)}>
      <option value="">All Employees</option>
      {employees.map(employee => (
        <option key={employee} value={employee}>
          {employee}
        </option>
      ))}
    </select>
  );
}
```

### **Desk Filter Component**
```jsx
function DeskFilter({ violations, onFilterChange }) {
  const allDesks = new Set();
  violations.forEach(violation => {
    const zones = JSON.parse(violation.zones);
    zones.forEach(zone => {
      if (zone.startsWith('desk_')) {
        allDesks.add(zone);
      }
    });
  });
  
  return (
    <select onChange={(e) => onFilterChange(e.target.value)}>
      <option value="">All Desks</option>
      {Array.from(allDesks).sort().map(desk => (
        <option key={desk} value={desk}>
          {desk.replace('desk_', 'Desk ')}
        </option>
      ))}
    </select>
  );
}
```

## 🎨 **CSS Styling Examples**

```css
/* Confidence-based styling */
.high-confidence {
  background-color: #d4edda;
  border-left: 4px solid #28a745;
}

.medium-confidence {
  background-color: #fff3cd;
  border-left: 4px solid #ffc107;
}

.low-confidence {
  background-color: #f8d7da;
  border-left: 4px solid #dc3545;
}

/* Violation card styling */
.violation-card {
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.violation-snapshot {
  width: 100%;
  max-width: 300px;
  height: auto;
  border-radius: 4px;
}

.no-media-placeholder {
  background-color: #f8f9fa;
  border: 2px dashed #dee2e6;
  padding: 20px;
  text-align: center;
  color: #6c757d;
}
```

## 🚀 **Migration Checklist**

- [ ] Update violation card components to show employee names
- [ ] Remove thumbnail and video URL handling (they're now null)
- [ ] Add zone/desk information display
- [ ] Implement confidence-based styling
- [ ] Add employee and desk filtering options
- [ ] Update error handling for null media URLs
- [ ] Test with real API responses

## 🎯 **Key Benefits for Frontend**

1. **Real Employee Names**: No more "Unknown" employees
2. **Desk Information**: Know exactly which desk the violation occurred at
3. **Confidence Scores**: Show reliability of employee identification
4. **Better Filtering**: Filter by employee or desk
5. **Accurate Media**: Only show snapshots (which actually work)

The API now provides much more accurate and useful data for your frontend! 🎉
