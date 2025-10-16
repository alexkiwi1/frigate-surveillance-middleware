"""
Recent Media endpoints for the Frigate Dashboard Middleware.

This module provides endpoints for recent clips and recordings with working media URLs.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
import requests
from datetime import datetime

from ..dependencies import validate_limit_parameter
from ..utils.response_formatter import create_json_response, create_error_json_response
from ..utils.errors import ExternalServiceError
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recent-media", tags=["Recent Media"])

@router.get("/clips")
async def get_recent_clips(
    limit: int = Depends(validate_limit_parameter),
    camera: Optional[str] = Query(None, description="Filter by camera name")
):
    """
    Get recent clips with working video and thumbnail URLs.
    
    Args:
        limit: Maximum number of clips to return
        camera: Optional camera filter
        
    Returns:
        List of recent clips with working media URLs
    """
    try:
        # Build Frigate API URL
        url = f"{settings.video_api_base_url}/api/clips"
        params = {"limit": limit}
        if camera:
            params["camera"] = camera
            
        # Fetch clips from Frigate
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        clips = data.get('clips', [])
        
        # Process clips to add full URLs and readable timestamps
        processed_clips = []
        for clip in clips:
            processed_clip = {
                "id": clip.get('id'),
                "camera": clip.get('camera'),
                "start_time": clip.get('start_time'),
                "end_time": clip.get('end_time'),
                "duration": clip.get('duration'),
                "severity": clip.get('severity'),
                "objects": clip.get('objects', []),
                "zones": clip.get('zones', []),
                "readable_time": datetime.fromtimestamp(clip.get('start_time', 0)).strftime("%Y-%m-%d %H:%M:%S"),
                "video_url": f"{settings.video_api_base_url}{clip.get('video_url', '')}",
                "thumbnail_url": f"{settings.video_api_base_url}{clip.get('thumbnail_url', '')}"
            }
            processed_clips.append(processed_clip)
        
        return create_json_response(
            data=processed_clips,
            message=f"Retrieved {len(processed_clips)} recent clips with working media URLs"
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching recent clips from Frigate: {e}")
        raise ExternalServiceError(
            message="Failed to fetch recent clips from Frigate",
            service="frigate_api",
            details={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_recent_clips: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/recordings")
async def get_recent_recordings(
    limit: int = Depends(validate_limit_parameter),
    camera: Optional[str] = Query(None, description="Filter by camera name")
):
    """
    Get recent recordings with working video URLs.
    
    Args:
        limit: Maximum number of recordings to return
        camera: Optional camera filter
        
    Returns:
        List of recent recordings with working video URLs
    """
    try:
        # Build Frigate API URL
        url = f"{settings.video_api_base_url}/api/recordings"
        params = {"limit": limit}
        if camera:
            params["camera"] = camera
            
        # Fetch recordings from Frigate
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        recordings = data.get('recordings', [])
        
        # Process recordings to add full URLs and readable timestamps
        processed_recordings = []
        for recording in recordings:
            processed_recording = {
                "id": recording.get('id'),
                "camera": recording.get('camera'),
                "start_time": recording.get('start_time'),
                "end_time": recording.get('end_time'),
                "duration": recording.get('duration'),
                "objects": recording.get('objects', 0),
                "motion": recording.get('motion', 0),
                "readable_time": datetime.fromtimestamp(recording.get('start_time', 0)).strftime("%Y-%m-%d %H:%M:%S"),
                "video_url": f"{settings.video_api_base_url}{recording.get('video_url', '')}"
            }
            processed_recordings.append(processed_recording)
        
        return create_json_response(
            data=processed_recordings,
            message=f"Retrieved {len(processed_recordings)} recent recordings with working video URLs"
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching recent recordings from Frigate: {e}")
        raise ExternalServiceError(
            message="Failed to fetch recent recordings from Frigate",
            service="frigate_api",
            details={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_recent_recordings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/test-media")
async def test_media_urls(
    clip_id: Optional[str] = Query(None, description="Test specific clip ID"),
    recording_id: Optional[str] = Query(None, description="Test specific recording ID")
):
    """
    Test media URL accessibility for debugging.
    
    Args:
        clip_id: Optional clip ID to test
        recording_id: Optional recording ID to test
        
    Returns:
        Media URL test results
    """
    results = {
        "clip_tests": [],
        "recording_tests": [],
        "summary": {}
    }
    
    try:
        # Test clip if provided
        if clip_id:
            clip_video_url = f"{settings.video_api_base_url}/clip/{clip_id}"
            clip_thumb_url = f"{settings.video_api_base_url}/thumb/{clip_id}"
            
            # Test video
            try:
                response = requests.head(clip_video_url, timeout=5)
                results["clip_tests"].append({
                    "type": "video",
                    "url": clip_video_url,
                    "status": response.status_code,
                    "accessible": response.status_code == 200,
                    "size": response.headers.get('Content-Length', 'unknown')
                })
            except Exception as e:
                results["clip_tests"].append({
                    "type": "video",
                    "url": clip_video_url,
                    "status": "error",
                    "accessible": False,
                    "error": str(e)
                })
            
            # Test thumbnail
            try:
                response = requests.head(clip_thumb_url, timeout=5)
                results["clip_tests"].append({
                    "type": "thumbnail",
                    "url": clip_thumb_url,
                    "status": response.status_code,
                    "accessible": response.status_code == 200,
                    "size": response.headers.get('Content-Length', 'unknown')
                })
            except Exception as e:
                results["clip_tests"].append({
                    "type": "thumbnail",
                    "url": clip_thumb_url,
                    "status": "error",
                    "accessible": False,
                    "error": str(e)
                })
        
        # Test recording if provided
        if recording_id:
            recording_video_url = f"{settings.video_api_base_url}/video/{recording_id}"
            
            try:
                response = requests.head(recording_video_url, timeout=5)
                results["recording_tests"].append({
                    "type": "video",
                    "url": recording_video_url,
                    "status": response.status_code,
                    "accessible": response.status_code == 200,
                    "size": response.headers.get('Content-Length', 'unknown')
                })
            except Exception as e:
                results["recording_tests"].append({
                    "type": "video",
                    "url": recording_video_url,
                    "status": "error",
                    "accessible": False,
                    "error": str(e)
                })
        
        # Calculate summary
        total_tests = len(results["clip_tests"]) + len(results["recording_tests"])
        accessible_tests = sum(1 for test in results["clip_tests"] + results["recording_tests"] if test.get("accessible", False))
        
        results["summary"] = {
            "total_tests": total_tests,
            "accessible": accessible_tests,
            "success_rate": (accessible_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        return create_json_response(
            data=results,
            message=f"Media URL test completed: {accessible_tests}/{total_tests} accessible"
        )
        
    except Exception as e:
        logger.error(f"Error in test_media_urls: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
