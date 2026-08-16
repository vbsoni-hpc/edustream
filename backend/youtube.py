import yt_dlp
import logging
from backend.models import get_or_create_segment, upsert_youtube_video

logger = logging.getLogger(__name__)

def process_youtube_playlist(url: str, icon: str = "▶️", description: str = "", user_id: int = None) -> int:
    """
    Extracts playlist information and videos from a YouTube URL.
    Creates a new segment for the playlist and inserts the videos into the database.
    Returns the new segment_id.
    """
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True, # Skip unavailable videos
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        if not info:
            raise ValueError("Could not extract information from the provided URL.")
            
        # Determine title
        title = info.get('title', 'Imported YouTube Course')
        
        # Create segment
        segment_id = get_or_create_segment(
            name=title, 
            icon=icon, 
            description=description or f"YouTube Playlist: {title}",
            uploaded_by=user_id
        )
        
        entries = info.get('entries', [])
        
        # If it's a single video and not a playlist, `entries` might be empty but `id` exists
        if not entries and info.get('id'):
            entries = [info]

        for entry in entries:
            if not entry:
                continue
            
            video_id = entry.get('id')
            video_title = entry.get('title', 'Unknown Video')
            duration = entry.get('duration', 0)
            
            if video_id:
                upsert_youtube_video(
                    youtube_id=video_id,
                    title=video_title,
                    segment_id=segment_id,
                    duration_sec=duration
                )
                
        return segment_id
