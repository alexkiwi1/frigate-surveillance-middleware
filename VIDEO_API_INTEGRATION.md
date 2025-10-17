# Video API Integration Documentation

## Overview
This document describes the integration between the Frigate Surveillance Dashboard Middleware and the Frigate Video & Image API.

## Video API Details
- **Host**: 10.0.20.6
- **Port**: 5001
- **Base URL**: http://10.0.20.6:5001
- **Version**: 3.0
- **Service**: Frigate Complete Video & Image API

## Endpoint Mapping

### Violations (Event-Based Clips)
- **Database Table**: `reviewsegment`
- **Video Endpoint**: `/clip/{id}` ✅
- **Thumbnail Endpoint**: `/thumb/{id}` ✅
- **Status**: Thumbnails working (HTTP 200), videos may have storage issues

### Recordings (Continuous Video)
- **Database Table**: `recordings`
- **Video Endpoint**: `/video/{id}` ✅
- **Status**: For continuous recordings only

### Snapshots (Event Images)
- **Database Table**: `timeline`
- **Snapshot Endpoint**: `/snapshot/{camera}/{timestamp}-{id}` ✅
- **Status**: Working correctly

## Current Integration Status

### ✅ Working Endpoints
- **Thumbnails**: HTTP 200, ~10KB WebP files
- **Snapshots**: Working correctly
- **API Discovery**: Video API responding with correct endpoint documentation

### ⚠️ Issues Identified
- **Video Clips**: Returning HTTP 404 (likely Video API storage issue)
- **Video API Container**: Not running on middleware server (external service)

## Middleware Configuration

### Current Settings
```python
VIDEO_API_BASE_URL = "http://10.0.20.6:5001"
```

### URL Construction
```python
# Violations (Event-based clips)
video_url = f"{VIDEO_API_BASE_URL}/clip/{violation_id}"
thumbnail_url = f"{VIDEO_API_BASE_URL}/thumb/{violation_id}"

# Recordings (Continuous video)
video_url = f"{VIDEO_API_BASE_URL}/video/{recording_id}"

# Snapshots
snapshot_url = f"{VIDEO_API_BASE_URL}/snapshot/{camera}/{timestamp}-{event_id}"
```

## API Response Format

### Violation Data
```json
{
  "id": "1760372618.887707-hl4tok",
  "video_url": "http://10.0.20.6:5001/clip/1760372618.887707-hl4tok",
  "thumbnail_url": "http://10.0.20.6:5001/thumb/1760372618.887707-hl4tok",
  "snapshot_url": "http://10.0.20.6:5001/snapshot/employees_05/1760373020.322353-1760372618.887707-hl4tok"
}
```

## Testing Commands

### Test Video API Health
```bash
curl "http://10.0.20.6:5001/"
```

### Test Thumbnail (Should work)
```bash
curl -I "http://10.0.20.6:5001/thumb/1760373044.376324-eu1919"
# Expected: HTTP 200 OK, Content-Type: image/webp
```

### Test Video Clip (May fail due to storage)
```bash
curl -I "http://10.0.20.6:5001/clip/1760373044.376324-eu1919"
# Expected: HTTP 200 OK or HTTP 404 (storage issue)
```

### Test Middleware Integration
```bash
curl "http://10.0.20.7:5002/api/violations/live?limit=1"
# Should return correct URLs with /clip/ and /thumb/ endpoints
```

## Troubleshooting

### Video API Not Responding
1. Check if Video API service is running on 10.0.20.6:5001
2. Verify network connectivity from middleware server
3. Check Video API logs for errors

### Video Files Not Found (404)
1. Check Video API file system: `/mnt/frigate-recordings/`
2. Verify file permissions and disk space
3. Check Video API path translation logic

### Thumbnails Working but Videos Failing
- This indicates correct endpoint configuration
- Issue is likely Video API storage or file system related
- Middleware is correctly configured

## File System Structure (Video API)
```
/mnt/frigate-recordings/
├── recordings/              # Continuous recordings
│   └── YYYY-MM-DD/HH/{camera}/MM.SS.mp4
├── clips/
│   ├── previews/           # Hourly summary videos
│   ├── review/             # Event thumbnails
│   ├── faces/              # Face recognition images
│   ├── {camera}-{timestamp}-{id}.jpg
│   └── {camera}-{timestamp}-{id}-clean.png
```

## Database Schema Reference

### reviewsegment (Violations)
- `id`: Clip ID for `/clip/{id}` endpoint
- `camera`: Camera name
- `start_time`: Unix timestamp
- `severity`: alert|detection|significant_motion
- `thumb_path`: Thumbnail file path
- `data`: JSONB with objects, zones metadata

### recordings (Continuous Video)
- `id`: Recording ID for `/video/{id}` endpoint
- `camera`: Camera name
- `start_time`: Unix timestamp
- `duration`: Video duration in seconds

### timeline (Snapshots)
- `id`: Auto-increment ID
- `timestamp`: Unix timestamp
- `camera`: Camera name
- `source_id`: Event ID for snapshot URL

## Performance Notes
- Thumbnails: ~10KB WebP files, fast loading
- Videos: Variable size, may have streaming issues
- Snapshots: JPEG/PNG images, moderate size
- Caching: Middleware caches API responses for performance

## Security Considerations
- Video API has CORS enabled for all origins
- No authentication required (internal network)
- Read-only file system access
- Database credentials in environment variables

## Future Improvements
1. Add video streaming optimization
2. Implement video thumbnail generation
3. Add video compression options
4. Implement video caching strategy
5. Add video quality selection

---
*Last Updated: 2025-10-14*
*Middleware Version: 1.0.0*
*Video API Version: 3.0*







