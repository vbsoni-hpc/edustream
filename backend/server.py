"""
FastAPI backend server for the EdTech platform.

Endpoints cover:
- Authentication (register, login)
- Video streaming via MTProto
- Progress tracking
- Dashboard / stats
- Courses (segments, modules, videos)
- Subscriptions
- Messaging (group chat, DMs, broadcast)
- Users & online status
- Admin CRUD
- YouTube import
- Analytics
- AI Chat proxy
"""
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Optional, List
import asyncio

from fastapi import FastAPI, Request, HTTPException, Depends, Header, Query
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
    get_user_by_id,
    create_user,
    get_or_create_segment,
    upsert_video,
    get_all_videos,
    async_upsert_progress,
    async_mark_complete,
    async_get_video_by_msg_id,
    # Dashboard / Stats
    get_dashboard_stats,
    get_segment_stats,
    get_last_viewed_segment_stats,
    get_leaderboard,
    get_latest_notices,
    get_all_notices,
    add_notice,
    delete_notice,
    # Segments / Modules / Videos
    get_all_segments,
    get_videos_by_segment,
    get_modules_by_segment,
    get_videos_by_module,
    get_video_by_id,
    get_all_modules,
    update_segment,
    get_or_create_module,
    update_module,
    delete_module,
    move_videos_to_module,
    unassign_videos_from_module,
    get_segment_leaderboard,
    # Progress
    get_user_progress,
    get_video_progress,
    # Subscriptions
    get_user_subscriptions,
    subscribe_to_segment,
    unsubscribe_from_segment,
    # Messages
    get_group_messages,
    send_message,
    get_messages_for_user,
    get_unread_messages,
    mark_messages_read,
    delete_all_messages,
    # Users
    get_all_users,
    get_all_users_admin,
    update_user_admin,
    delete_user_admin,
    ping_user,
    get_online_users,
    get_watching_users,
    is_user_admin,
    # Access control
    get_user_segment_access,
    set_user_segment_access,
    get_user_module_access,
    set_user_module_access,
    get_user_video_access,
    set_user_video_access,
    update_video_restricted,
    recover_missing_youtube_ids,
    # Analytics
    get_daily_watch_activity,
    get_module_stats,
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

async def auto_sync_task():
    """Background task to sync the Telegram channel periodically."""
    while True:
        try:
            logger.info("Starting auto-sync...")
            videos = await sync_channel()
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
            logger.info(f"Auto-sync complete. Synced {synced_count} videos.")
        except Exception as e:
            logger.error(f"Auto-sync failed: {e}")
        
        # Sleep for 1 hour (3600 seconds)
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    await async_init_db()
    logger.info("Database initialised")
    
    # Start auto-sync background task
    sync_task = asyncio.create_task(auto_sync_task())
    
    yield
    
    sync_task.cancel()
    await disconnect()
    logger.info("Telegram client disconnected")


app = FastAPI(title="EdTech API", lifespan=lifespan)

# Allow Next.js (different port) to call us
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


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is an admin."""
    if not is_user_admin(user["user_id"]):
        raise HTTPException(403, "Admin access required")
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
    
    token = create_access_token(user['id'], user["username"])
    return {
        "token": token,
        "user_id": user['id'],
        "username": user["username"],
        "display_name": user["display_name"],
        "is_admin": bool(user.get("is_admin", 0)),
    }


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
            if sent == 0:
                return

    # Determine status code
    status = 206 if range_header else 200

    headers = {
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Cache-Control": "public, max-age=3600",
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


@app.get("/api/progress")
async def get_progress(user: dict = Depends(get_current_user)):
    """Get all progress data for the current user."""
    data = get_user_progress(user["user_id"])
    return {"progress": data}


@app.get("/api/progress/{video_id}")
async def get_single_progress(
    video_id: int,
    user: dict = Depends(get_current_user),
):
    """Get progress for a single video."""
    data = get_video_progress(user["user_id"], video_id)
    return {"progress": data}


# ═══════════════════════════════════════════════════════════
#  Dashboard endpoints
# ═══════════════════════════════════════════════════════════

@app.get("/api/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    stats = get_dashboard_stats(user["user_id"])
    return stats


@app.get("/api/dashboard/last-segment")
async def dashboard_last_segment(user: dict = Depends(get_current_user)):
    data = get_last_viewed_segment_stats(user["user_id"])
    return {"segment": data}


@app.get("/api/segments/stats")
async def segments_stats(user: dict = Depends(get_current_user)):
    data = get_segment_stats(user["user_id"])
    return {"segments": data}


@app.get("/api/leaderboard")
async def leaderboard(days: int = Query(1, ge=1)):
    data = get_leaderboard(days=days)
    return {"leaderboard": data}


@app.get("/api/notices")
async def notices():
    data = get_latest_notices(limit=5)
    return {"notices": data}


# ═══════════════════════════════════════════════════════════
#  Courses / Segments / Modules / Videos
# ═══════════════════════════════════════════════════════════

@app.get("/api/segments")
async def list_segments(user: dict = Depends(get_current_user)):
    data = get_all_segments(user["user_id"])
    return {"segments": data}


@app.get("/api/segments/{segment_id}/videos")
async def segment_videos(segment_id: int, user: dict = Depends(get_current_user)):
    videos = get_videos_by_segment(segment_id, user["user_id"])
    # Attach progress for each video
    for v in videos:
        prog = get_video_progress(user["user_id"], v["id"])
        v["progress"] = prog
    return {"videos": videos}


@app.post("/api/segments/{segment_id}/restrict")
async def toggle_segment_restriction(segment_id: int, user: dict = Depends(get_current_admin)):
    """Toggle the is_restricted status of a segment (admin only)."""
    with sqlite3.connect(str(DB_PATH)) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT is_restricted FROM segments WHERE id = ?", (segment_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Segment not found")
        new_status = 0 if row["is_restricted"] else 1
        c.execute("UPDATE segments SET is_restricted = ? WHERE id = ?", (new_status, segment_id))
        c.commit()
    return {"status": "ok", "is_restricted": bool(new_status)}


@app.get("/api/segments/{segment_id}/modules")
async def segment_modules(segment_id: int, user: dict = Depends(get_current_user)):
    modules = get_modules_by_segment(segment_id, user["user_id"])
    return {"modules": modules}


@app.get("/api/segments/{segment_id}/leaderboard")
async def segment_leaderboard_endpoint(segment_id: int, days: int = Query(7, ge=1)):
    data = get_segment_leaderboard(segment_id, days=days)
    return {"leaderboard": data}


@app.get("/api/modules/{module_id}/videos")
async def module_videos(module_id: int, user: dict = Depends(get_current_user)):
    videos = get_videos_by_module(module_id, user["user_id"])
    for v in videos:
        prog = get_video_progress(user["user_id"], v["id"])
        v["progress"] = prog
    return {"videos": videos}


@app.get("/api/videos/{video_id}")
async def single_video(video_id: int, user: dict = Depends(get_current_user)):
    video = get_video_by_id(video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    video["progress"] = get_video_progress(user["user_id"], video_id)
    return video


@app.get("/api/videos")
async def list_videos():
    videos = get_all_videos()
    return {"videos": videos}


# ═══════════════════════════════════════════════════════════
#  Subscriptions
# ═══════════════════════════════════════════════════════════

@app.get("/api/subscriptions")
async def get_subs(user: dict = Depends(get_current_user)):
    ids = get_user_subscriptions(user["user_id"])
    return {"subscribed_ids": ids}


@app.post("/api/subscriptions/{segment_id}")
async def subscribe(segment_id: int, user: dict = Depends(get_current_user)):
    subscribe_to_segment(user["user_id"], segment_id)
    return {"status": "subscribed"}


@app.delete("/api/subscriptions/{segment_id}")
async def unsubscribe(segment_id: int, user: dict = Depends(get_current_user)):
    unsubscribe_from_segment(user["user_id"], segment_id)
    return {"status": "unsubscribed"}


# ═══════════════════════════════════════════════════════════
#  Messaging
# ═══════════════════════════════════════════════════════════

class MessageRequest(BaseModel):
    content: str
    recipient_id: int = 0  # 0 = group chat


@app.get("/api/messages/group")
async def group_messages(limit: int = Query(50, ge=1)):
    data = get_group_messages(limit=limit)
    return {"messages": data}


BAD_WORDS = ["idiot", "fuck", "shit", "bitch", "asshole", "stupid", "crap", "bastard"]

@app.post("/api/messages/group")
async def send_group_message(req: MessageRequest, user: dict = Depends(get_current_user)):
    content = req.content
    content_lower = content.lower()
    is_bad = any(word in content_lower for word in BAD_WORDS)
    
    if is_bad:
        content = "[Message deleted by AI Moderator]"

    send_message(user["user_id"], 0, content)
    return {"status": "sent"}


@app.get("/api/messages/inbox")
async def inbox(user: dict = Depends(get_current_user)):
    data = get_messages_for_user(user["user_id"])
    return {"messages": data}


@app.get("/api/messages/unread")
async def unread(user: dict = Depends(get_current_user)):
    data = get_unread_messages(user["user_id"])
    return {"messages": data}


@app.post("/api/messages/dm")
async def send_dm(req: MessageRequest, user: dict = Depends(get_current_user)):
    if req.recipient_id == 0:
        raise HTTPException(400, "Must specify a recipient_id for DMs")
    send_message(user["user_id"], req.recipient_id, req.content)
    return {"status": "sent"}


class BroadcastRequest(BaseModel):
    content: str


@app.post("/api/messages/broadcast")
async def broadcast(req: BroadcastRequest, user: dict = Depends(get_current_admin)):
    """Send a message to all users."""
    all_users = get_all_users()
    for u in all_users:
        if u["id"] != user["user_id"]:
            send_message(user["user_id"], u["id"], req.content)
    return {"status": "broadcast_sent", "count": len(all_users) - 1}


class ReadRequest(BaseModel):
    message_ids: List[int]


@app.post("/api/messages/read")
async def mark_read(req: ReadRequest, user: dict = Depends(get_current_user)):
    mark_messages_read(req.message_ids)
    return {"status": "ok"}


@app.delete("/api/messages")
async def clear_messages(user: dict = Depends(get_current_admin)):
    delete_all_messages()
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════
#  Users / Online
# ═══════════════════════════════════════════════════════════

class PingRequest(BaseModel):
    video_id: Optional[int] = None

@app.get("/api/videos/{video_id}/watching")
async def get_watching(video_id: int):
    data = get_watching_users(video_id)
    return {"users": data}

@app.post("/api/users/ping")
async def user_ping(req: PingRequest = None, user: dict = Depends(get_current_user)):
    video_id = req.video_id if req else None
    ping_user(user["user_id"], video_id)
    return {"status": "ok"}


@app.get("/api/users/online")
async def online_users():
    data = get_online_users(minutes=5)
    return {"users": data}


@app.get("/api/users")
async def list_users(user: dict = Depends(get_current_user)):
    """Get all users (for DM recipient list)."""
    data = get_all_users()
    return {"users": data}


@app.get("/api/users/me")
async def current_user_info(user: dict = Depends(get_current_user)):
    full_user = get_user_by_id(user["user_id"])
    if not full_user:
        raise HTTPException(404, "User not found")
    return {
        "id": full_user['user_id'],
        "username": full_user["username"],
        "display_name": full_user["display_name"],
        "is_admin": bool(full_user.get("is_admin", 0)),
        "created_at": full_user.get("created_at"),
    }


# ═══════════════════════════════════════════════════════════
#  Admin endpoints
# ═══════════════════════════════════════════════════════════

# -- Users admin --
@app.get("/api/admin/users")
async def admin_list_users(user: dict = Depends(get_current_admin)):
    data = get_all_users_admin()
    return {"users": data}


class UserUpdate(BaseModel):
    username: str
    display_name: str
    is_admin: bool = False


@app.put("/api/admin/users/{user_id}")
async def admin_update_user(user_id: int, req: UserUpdate, user: dict = Depends(get_current_admin)):
    update_user_admin(user_id, req.username, req.display_name, req.is_admin)
    return {"status": "updated"}


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, user: dict = Depends(get_current_admin)):
    delete_user_admin(user_id)
    return {"status": "deleted"}


# -- Segments admin --
class SegmentUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_restricted: Optional[bool] = None


@app.put("/api/admin/segments/{segment_id}")
async def admin_update_segment(segment_id: int, req: SegmentUpdate, user: dict = Depends(get_current_admin)):
    update_segment(segment_id, name=req.name, icon=req.icon, description=req.description,
                   sort_order=req.sort_order, is_restricted=req.is_restricted)
    return {"status": "updated"}


class SegmentCreate(BaseModel):
    name: str
    icon: str = "📁"
    description: str = ""


@app.post("/api/admin/segments")
async def admin_create_segment(req: SegmentCreate, user: dict = Depends(get_current_admin)):
    seg_id = get_or_create_segment(req.name, req.icon, req.description)
    return {"status": "created", "id": seg_id}


# -- Modules admin --
class ModuleUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_restricted: Optional[bool] = None


@app.put("/api/admin/modules/{module_id}")
async def admin_update_module(module_id: int, req: ModuleUpdate, user: dict = Depends(get_current_admin)):
    update_module(module_id, name=req.name, icon=req.icon, sort_order=req.sort_order,
                  is_restricted=req.is_restricted)
    return {"status": "updated"}


class ModuleCreate(BaseModel):
    name: str
    segment_id: int
    icon: str = "📂"


@app.post("/api/admin/modules")
async def admin_create_module(req: ModuleCreate, user: dict = Depends(get_current_admin)):
    mod_id = get_or_create_module(req.name, req.segment_id, req.icon)
    return {"status": "created", "id": mod_id}


@app.delete("/api/admin/modules/{module_id}")
async def admin_delete_module(module_id: int, user: dict = Depends(get_current_admin)):
    delete_module(module_id)
    return {"status": "deleted"}


# -- Videos admin --
class VideoAssign(BaseModel):
    video_ids: List[int]
    module_id: int


@app.post("/api/admin/videos/assign")
async def admin_assign_videos(req: VideoAssign, user: dict = Depends(get_current_admin)):
    move_videos_to_module(req.video_ids, req.module_id)
    return {"status": "assigned"}


class VideoUnassign(BaseModel):
    video_ids: List[int]


@app.post("/api/admin/videos/unassign")
async def admin_unassign_videos(req: VideoUnassign, user: dict = Depends(get_current_admin)):
    unassign_videos_from_module(req.video_ids)
    return {"status": "unassigned"}


class VideoRestrict(BaseModel):
    is_restricted: bool


@app.put("/api/admin/videos/{video_id}/restricted")
async def admin_restrict_video(video_id: int, req: VideoRestrict, user: dict = Depends(get_current_admin)):
    update_video_restricted(video_id, req.is_restricted)
    return {"status": "updated"}


# -- Notices admin --
class NoticeCreate(BaseModel):
    content: str


@app.post("/api/admin/notices")
async def admin_create_notice(req: NoticeCreate, user: dict = Depends(get_current_admin)):
    add_notice(req.content)
    return {"status": "created"}


@app.get("/api/admin/notices")
async def admin_list_notices(user: dict = Depends(get_current_admin)):
    data = get_all_notices()
    return {"notices": data}


@app.delete("/api/admin/notices/{notice_id}")
async def admin_delete_notice(notice_id: int, user: dict = Depends(get_current_admin)):
    delete_notice(notice_id)
    return {"status": "deleted"}


# -- Access control admin --
@app.get("/api/admin/access/segments/{segment_id}")
async def admin_get_segment_access(segment_id: int, user: dict = Depends(get_current_admin)):
    ids = get_user_segment_access(segment_id)
    return {"user_ids": ids}


class AccessUpdate(BaseModel):
    user_ids: List[int]


@app.put("/api/admin/access/segments/{segment_id}")
async def admin_set_segment_access(segment_id: int, req: AccessUpdate, user: dict = Depends(get_current_admin)):
    set_user_segment_access(segment_id, req.user_ids)
    return {"status": "updated"}


@app.get("/api/admin/access/modules/{module_id}")
async def admin_get_module_access(module_id: int, user: dict = Depends(get_current_admin)):
    ids = get_user_module_access(module_id)
    return {"user_ids": ids}


@app.put("/api/admin/access/modules/{module_id}")
async def admin_set_module_access(module_id: int, req: AccessUpdate, user: dict = Depends(get_current_admin)):
    set_user_module_access(module_id, req.user_ids)
    return {"status": "updated"}


@app.get("/api/admin/access/videos/{video_id}")
async def admin_get_video_access(video_id: int, user: dict = Depends(get_current_admin)):
    ids = get_user_video_access(video_id)
    return {"user_ids": ids}


@app.put("/api/admin/access/videos/{video_id}")
async def admin_set_video_access(video_id: int, req: AccessUpdate, user: dict = Depends(get_current_admin)):
    set_user_video_access(video_id, req.user_ids)
    return {"status": "updated"}


# -- Backup & fix --
@app.post("/api/admin/backup")
async def admin_backup(user: dict = Depends(get_current_admin)):
    from backend.github_backup import force_backup
    try:
        success, msg = await force_backup()
        return {"success": success, "message": msg}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/admin/fix-youtube")
async def admin_fix_youtube(user: dict = Depends(get_current_admin)):
    count = recover_missing_youtube_ids()
    return {"status": "ok", "recovered": count}


# ═══════════════════════════════════════════════════════════
#  YouTube Import
# ═══════════════════════════════════════════════════════════

class YouTubeImportRequest(BaseModel):
    url: str
    icon: str = "▶️"
    description: str = ""


@app.post("/api/import/youtube")
async def import_youtube(req: YouTubeImportRequest, user: dict = Depends(get_current_user)):
    from backend.youtube import process_youtube_playlist
    try:
        seg_id = process_youtube_playlist(req.url, req.icon, req.description, user_id=user["user_id"])
        return {"status": "ok", "segment_id": seg_id}
    except Exception as e:
        raise HTTPException(400, str(e))


# ═══════════════════════════════════════════════════════════
#  Analytics
# ═══════════════════════════════════════════════════════════

@app.get("/api/analytics/daily")
async def get_daily_analytics(days: int = 30, user: dict = Depends(get_current_user)):
    from backend.models import get_daily_watch_activity
    return {"daily": get_daily_watch_activity(user["user_id"], days)}

class TelegramImportRequest(BaseModel):
    channel: str
    name: str = ""
    icon: str = "📱"
    description: str = ""

@app.post("/api/import/telegram")
async def import_telegram(req: TelegramImportRequest, user: dict = Depends(get_current_user)):
    from backend.telegram_client import sync_channel
    from backend.models import get_or_create_segment, upsert_video
    try:
        # channel could be a URL like https://t.me/some_channel, let's extract the username
        channel_name = req.channel
        if 't.me/' in channel_name:
            channel_name = channel_name.split('t.me/')[-1].split('/')[0]
        if not channel_name.startswith('@') and not channel_name.startswith('-100'):
            # It might be a public username without @
            if not channel_name.isdigit():
                channel_name = '@' + channel_name
                
        videos = await sync_channel(channel_name)
        if not videos:
            raise ValueError("No videos found in the specified channel.")
            
        segment_name = req.name or channel_name
        segment_id = get_or_create_segment(
            name=segment_name,
            icon=req.icon,
            description=req.description or f"Telegram Channel: {channel_name}",
            uploaded_by=user['user_id']
        )
        
        for v in videos:
            upsert_video(
                telegram_msg_id=v["telegram_msg_id"],
                title=v["title"],
                segment_id=segment_id,
                duration_sec=v["duration_sec"],
                file_size=v["file_size"],
                mime_type=v["mime_type"],
                caption=v["caption"],
            )
        
        return {"status": "ok", "segment_id": segment_id, "videos_imported": len(videos)}
    except Exception as e:
        logger.error(f"Telegram import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/daily")
async def analytics_daily(days: int = Query(30, ge=1), user: dict = Depends(get_current_user)):
    data = get_daily_watch_activity(user["user_id"], days)
    return {"activity": data}


@app.get("/api/analytics/segments")
async def analytics_segments(user: dict = Depends(get_current_user)):
    data = get_segment_stats(user["user_id"])
    return {"segments": data}


@app.get("/api/analytics/modules")
async def analytics_modules(user: dict = Depends(get_current_user)):
    data = get_module_stats(user["user_id"])
    return {"modules": data}


# ═══════════════════════════════════════════════════════════
#  AI Chat Proxy (g4f)
# ═══════════════════════════════════════════════════════════

class AIChatRequest(BaseModel):
    messages: list  # [{role: "user"/"assistant"/"system", content: str}]
    video_title: str = ""


@app.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest, user: dict = Depends(get_current_user)):
    try:
        import httpx
        
        system_msg = {
            "role": "system",
            "content": f"You are a helpful AI tutor. The student is watching a video lecture titled '{req.video_title}'. Help answer their questions, explain in simple and intuitive manner through first principles. Always reply in English."
        }
        messages = [system_msg] + req.messages[-5:]
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://text.pollinations.ai/openai",
                json={
                    "model": "openai",
                    "messages": messages,
                    "seed": 42
                },
                timeout=30.0
            )
            
            if resp.status_code != 200:
                raise Exception(f"API Error {resp.status_code}: {resp.text}")
                
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            
        return {"response": answer}
    except Exception as e:
        raise HTTPException(500, f"AI chat failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
#  Sync & restore
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


@app.get("/api/force_restore")
async def api_force_restore():
    from backend.github_backup import restore_from_github
    success, msg = await restore_from_github()
    return {"success": success, "msg": msg}


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

# ── Edit and Delete Endpoints ─────────────────────────────────

@app.put("/api/segments/{segment_id}")
async def route_update_segment(segment_id: int, request: Request, user: dict = Depends(get_current_user)):
    if not is_user_admin(user['user_id']):
        raise HTTPException(status_code=403, detail="Admin only")
    data = await request.json()
    from backend.models import update_segment
    update_segment(
        segment_id,
        name=data.get("name"),
        icon=data.get("icon"),
        description=data.get("description"),
        sort_order=data.get("sort_order"),
        is_restricted=data.get("is_restricted")
    )
    return {"success": True}

@app.delete("/api/segments/{segment_id}")
async def route_delete_segment(segment_id: int, user: dict = Depends(get_current_user)):
    if not is_user_admin(user['user_id']):
        raise HTTPException(status_code=403, detail="Admin only")
    from backend.models import delete_segment
    delete_segment(segment_id)
    return {"success": True}

@app.put("/api/modules/{module_id}")
async def route_update_module(module_id: int, request: Request, user: dict = Depends(get_current_user)):
    if not is_user_admin(user['user_id']):
        raise HTTPException(status_code=403, detail="Admin only")
    data = await request.json()
    from backend.models import update_module
    update_module(
        module_id,
        name=data.get("name"),
        icon=data.get("icon"),
        sort_order=data.get("sort_order"),
        is_restricted=data.get("is_restricted")
    )
    return {"success": True}

@app.delete("/api/modules/{module_id}")
async def route_delete_module_ep(module_id: int, user: dict = Depends(get_current_user)):
    if not is_user_admin(user['user_id']):
        raise HTTPException(status_code=403, detail="Admin only")
    from backend.models import delete_module
    delete_module(module_id)
    return {"success": True}

@app.put("/api/videos/{video_id}")
async def route_update_video(video_id: int, request: Request, user: dict = Depends(get_current_user)):
    if not is_user_admin(user['user_id']):
        raise HTTPException(status_code=403, detail="Admin only")
    data = await request.json()
    from backend.models import update_video
    update_video(
        video_id,
        title=data.get("title"),
        segment_id=data.get("segment_id"),
        module_id=data.get("module_id"),
        is_restricted=data.get("is_restricted")
    )
    return {"success": True}

@app.delete("/api/videos/{video_id}")
async def route_delete_video(video_id: int, user: dict = Depends(get_current_user)):
    if not is_user_admin(user['user_id']):
        raise HTTPException(status_code=403, detail="Admin only")
    from backend.models import delete_video
    delete_video(video_id)
    return {"success": True}


@app.head("/")
@app.get("/")
def health_check():
    return {"status": "ok"}
