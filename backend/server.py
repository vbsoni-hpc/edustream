"""
FastAPI backend server for the EdTech platform.

Endpoints:
- /api/auth/register, /api/auth/login   → User authentication
- /api/stream/{msg_id}                   → MTProto video streaming with Range support
- /api/progress/{video_id}              → Update watch progress
- /api/complete/{video_id}              → Mark video as completed
- /api/sync                             → Trigger Telegram channel sync
- /api/videos                           → List all videos
"""
import logging
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import FASTAPI_PORT, DEFAULT_SEGMENT_ICONS
from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token,
)
from backend.models import (
    async_init_db,
    get_user_by_username,
    create_user,
    get_or_create_segment,
    upsert_video,
    get_all_videos,
    async_upsert_progress,
    async_mark_complete,
    async_get_video_by_msg_id,
)
from backend.telegram_client import (
    get_client,
    disconnect,
    sync_channel,
    stream_video_chunks,
    get_file_size,
    get_message_media,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  App lifecycle
# ═══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    await async_init_db()
    logger.info("Database initialised")
    yield
    await disconnect()
    logger.info("Telegram client disconnected")


app = FastAPI(title="EdTech API", lifespan=lifespan)

# Allow Streamlit (different port) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
#  Auth dependency
# ═══════════════════════════════════════════════════════════

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract user from Bearer token."""
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Invalid Authorization header format")
    
    user = verify_access_token(parts[1])
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user


# ═══════════════════════════════════════════════════════════
#  Auth endpoints
# ═══════════════════════════════════════════════════════════

class AuthRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


@app.post("/api/auth/register")
async def register(req: AuthRequest):
    existing = get_user_by_username(req.username)
    if existing:
        raise HTTPException(400, "Username already taken")
    
    hashed = hash_password(req.password)
    user_id = create_user(req.username, hashed, req.display_name)
    token = create_access_token(user_id, req.username)
    return {"token": token, "user_id": user_id, "username": req.username}


@app.post("/api/auth/login")
async def login(req: AuthRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    
    token = create_access_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"]}


# ═══════════════════════════════════════════════════════════
#  Video streaming (MTProto → HTTP Range)
# ═══════════════════════════════════════════════════════════

def _parse_range(range_header: Optional[str], file_size: int) -> tuple[int, int]:
    """Parse HTTP Range header → (start, end) byte offsets."""
    if not range_header:
        return 0, file_size - 1
    
    match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not match:
        return 0, file_size - 1
    
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else file_size - 1
    end = min(end, file_size - 1)
    return start, end


@app.get("/api/stream/{msg_id}")
async def stream_video(msg_id: int, request: Request):
    """
    Stream video from Telegram with HTTP Range request support.
    Uses DB-stored file_size to avoid an extra Telegram API call.
    """
    # FAST PATH: get file_size from our database (no Telegram API call needed)
    file_size = 0
    video_record = await async_get_video_by_msg_id(msg_id)
    if video_record and video_record.get("file_size"):
        file_size = video_record["file_size"]
    
    # Fallback: only hit Telegram API if DB doesn't have the size
    if file_size == 0:
        try:
            file_size = await get_file_size(msg_id)
        except Exception as e:
            logger.error(f"Failed to get file size for msg {msg_id}: {e}")
            raise HTTPException(404, f"Video not found: {e}")
    
    if file_size == 0:
        raise HTTPException(404, "Video not found or has zero size")

    range_header = request.headers.get("range")
    start, end = _parse_range(range_header, file_size)
    content_length = end - start + 1

    # Cap chunk to avoid huge single responses (max 2MB per range response)
    max_chunk = 2 * 1024 * 1024
    if content_length > max_chunk and range_header:
        end = start + max_chunk - 1
        content_length = max_chunk

    async def generate():
        sent = 0
        try:
            async for chunk in stream_video_chunks(
                msg_id, offset=start, limit=content_length
            ):
                sent += len(chunk)
                yield chunk
        except Exception as e:
            logger.error(f"Streaming error for msg {msg_id} (sent {sent}/{content_length} bytes): {e}")
            # If we haven't sent anything yet, we can't do much —
            # the error will propagate. If we've sent partial data,
            # the client will get a truncated response and may retry.
            if sent == 0:
                # Yield empty to close the stream cleanly
                return

    # Determine status code
    status = 206 if range_header else 200

    headers = {
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Cache-Control": "public, max-age=3600",  # Browser can cache chunks for 1 hour
    }

    return StreamingResponse(
        generate(),
        status_code=status,
        headers=headers,
        media_type="video/mp4",
    )


# ═══════════════════════════════════════════════════════════
#  Progress tracking
# ═══════════════════════════════════════════════════════════

class ProgressUpdate(BaseModel):
    watch_seconds: float = 0
    last_position: float = 0


@app.post("/api/progress/{video_id}")
async def update_progress(
    video_id: int,
    data: ProgressUpdate,
    user: dict = Depends(get_current_user),
):
    await async_upsert_progress(
        user_id=user["user_id"],
        video_id=video_id,
        watch_seconds=data.watch_seconds,
        last_position=data.last_position,
    )
    return {"status": "ok"}


@app.post("/api/complete/{video_id}")
async def complete_video(
    video_id: int,
    user: dict = Depends(get_current_user),
):
    await async_mark_complete(user["user_id"], video_id)
    return {"status": "completed"}


# ═══════════════════════════════════════════════════════════
#  Sync & video listing
# ═══════════════════════════════════════════════════════════

@app.post("/api/sync")
async def trigger_sync():
    """Sync videos from Telegram channel into the database."""
    try:
        videos = await sync_channel()
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(500, f"Sync failed: {e}")
    
    synced_count = 0
    for v in videos:
        segment_name = v.get("segment") or "General"
        icon = DEFAULT_SEGMENT_ICONS.get(segment_name, "📁")
        segment_id = get_or_create_segment(segment_name, icon)
        upsert_video(
            telegram_msg_id=v["telegram_msg_id"],
            title=v["title"],
            segment_id=segment_id,
            duration_sec=v["duration_sec"],
            file_size=v["file_size"],
            mime_type=v["mime_type"],
            caption=v["caption"],
        )
        synced_count += 1
    
    return {"status": "ok", "synced": synced_count}


@app.get("/api/videos")
async def list_videos():
    videos = get_all_videos()
    return {"videos": videos}


# ═══════════════════════════════════════════════════════════
#  Run server
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host="127.0.0.1",
        port=FASTAPI_PORT,
        reload=True,
        log_level="info",
    )
