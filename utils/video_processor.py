# utils/video_processor.py
"""
Video processing utilities for working with installation videos from Google Cloud Storage.
"""
import os
import tempfile
import urllib.parse
from google.cloud import storage

class VideoProcessor:
    """Process and serve video files for the chatbot."""
    
    def __init__(self, storage_client=None):
        """Initialize the video processor."""
        self.storage_client = storage_client
        self.use_cloud = storage_client is not None
        self.local_video_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                           'data', 'videos')
        
        # Create videos directory if it doesn't exist
        os.makedirs(self.local_video_dir, exist_ok=True)
    
    def get_gcs_signed_url(self, gcs_uri, expiration=3600):
        """
        Generate a signed URL for a GCS object.
        
        Args:
            gcs_uri (str): GCS URI (gs://bucket/path/to/object)
            expiration (int): URL expiration time in seconds
            
        Returns:
            str: Signed URL
        """
        if not self.use_cloud:
            return None
            
        try:
            # Parse the GCS URI
            parsed_url = urllib.parse.urlparse(gcs_uri)
            if parsed_url.scheme != 'gs':
                raise ValueError(f"Invalid GCS URI scheme: {parsed_url.scheme}")
            
            bucket_name = parsed_url.netloc
            blob_path = parsed_url.path.lstrip('/')
            
            # Create a signed URL
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            return url
        
        except Exception as e:
            print(f"Error generating signed URL: {e}")
            return None
    
    def prepare_segments_from_kb(self, knowledge_base, installation_method="Drill and Tap"):
        """Extract video segments defined in the knowledge base."""
        # Find the installation method in the knowledge base
        method = None
        for machine in knowledge_base.get("machines", []):
            for method_data in machine.get("installation_methods", []):
                if method_data.get("name") == installation_method:
                    method = method_data
                    break
            if method:
                break
        
        if not method:
            print(f"Installation method '{installation_method}' not found in knowledge base")
            return {}
        
        # Get videos from the installation method
        videos = method.get("videos", [])
        if not videos:
            print(f"No videos found for installation method '{installation_method}'")
            return {}
        
        # For now, just use the first video
        video = videos[0]
        video_uri = video.get("uri")
        segments = video.get("segments", [])
        
        if not video_uri or not segments:
            print(f"Invalid video data for installation method '{installation_method}'")
            return {}
        
        # Create signed URL for the full video
        full_video_url = video_uri
        if video_uri.startswith("gs://") and self.use_cloud:
            signed_url = self.get_gcs_signed_url(video_uri)
            if signed_url:
                full_video_url = signed_url
        
        # Prepare segments
        segment_map = {}
        
        # Add the full video
        segment_map["full"] = {
            "title": video.get("title", "Full Installation Video"),
            "description": "Complete installation process from start to finish",
            "video_path": full_video_url,
            "is_full_video": True
        }
        
        # For cloud storage, we can't easily extract segments 
        # If implementing segment extraction is critical, we would need to:
        # 1. Download the video locally (or to memory)
        # 2. Use ffmpeg to extract segments
        # 3. Upload segments to a web-accessible location
        
        # For now, we'll just provide timestamps to skip to in the full video
        for segment in segments:
            start_time = segment.get("start")
            end_time = segment.get("end")
            title = segment.get("title")
            description = segment.get("description")
            step_reference = segment.get("step_reference")
            
            if not all([start_time, end_time, title]):
                continue
                
            segment_info = {
                "title": title,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "video_path": f"{full_video_url}#t={self._time_to_seconds(start_time)},{self._time_to_seconds(end_time)}",
                "full_video_url": full_video_url,
                "timestamp_start": self._time_to_seconds(start_time)
            }
            
            if step_reference:
                segment_map[step_reference] = segment_info
        
        return segment_map
    
    def _time_to_seconds(self, time_str):
        """Convert time string to seconds."""
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError(f"Invalid time format: {time_str}")