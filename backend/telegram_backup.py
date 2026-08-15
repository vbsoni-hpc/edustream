"""
Telegram-based backup & restore for the EdTech platform.

Saves all metadata (course structure, users, progress, notices, messages)
as a JSON file to Telegram Saved Messages. On startup, fetches the latest
backup and restores the database.

Auto-save is debounced (60 seconds) to avoid Telegram rate limits.
"""
import json
import time
import asyncio
import logging
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

BACKUP_CAPTION = "#EDUSTREAM_BACKUP"
DEBOUNCE_SECONDS = 60

# ── Debounce timer state ─────────────────────────────────
_debounce_timer: Optional[threading.Timer] = None
_debounce_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════
#  Export: DB → JSON → Telegram Saved Messages
# ═══════════════════════════════════════════════════════════

def _build_backup_data() -> dict:
    """Read current DB state and serialize to a dict."""
    from backend.models import (
        get_all_segments,
        get_all_modules,
        get_all_videos,
        get_all_users_admin,
        get_all_notices,
    )
    import sqlite3
    from config import DB_PATH

    segments = get_all_segments()
    modules = get_all_modules()
    videos = get_all_videos()
    users = get_all_users_admin()
    notices = get_all_notices()

    # Fetch all progress records directly
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    progress_rows = conn.execute("""
        SELECT p.*, u.username, v.telegram_msg_id
        FROM progress p
        JOIN users u ON p.user_id = u.id
        JOIN videos v ON p.video_id = v.id
    """).fetchall()
    progress = [dict(r) for r in progress_rows]

    # Fetch all messages directly
    message_rows = conn.execute("""
        SELECT m.*, 
               s.username as sender_username,
               r.username as recipient_username
        FROM messages m
        LEFT JOIN users s ON m.sender_id = s.id
        LEFT JOIN users r ON m.recipient_id = r.id
    """).fetchall()
    messages = [dict(r) for r in message_rows]
    conn.close()

    # Build video assignments: telegram_msg_id → {module_name, segment_name}
    video_assignments = {}
    for v in videos:
        if v.get("module_name"):
            video_assignments[str(v["telegram_msg_id"])] = {
                "module_name": v["module_name"],
                "segment_name": v.get("segment_name"),
            }

    return {
        "version": 2,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "segments": [
            {
                "name": s["name"],
                "icon": s["icon"],
                "sort_order": s["sort_order"],
            }
            for s in segments
        ],
        "modules": [
            {
                "name": m["name"],
                "icon": m["icon"],
                "sort_order": m["sort_order"],
                "segment_name": m.get("segment_name"),
            }
            for m in modules
        ],
        "video_assignments": video_assignments,
        "videos": [
            {
                "telegram_msg_id": v["telegram_msg_id"],
                "title": v["title"],
                "segment_name": v.get("segment_name"),
                "module_name": v.get("module_name"),
                "duration_sec": v.get("duration_sec", 0),
                "file_size": v.get("file_size", 0),
                "mime_type": v.get("mime_type", "video/mp4"),
                "caption": v.get("caption", ""),
            }
            for v in videos
        ],
        "users": [
            {
                "username": u["username"],
                "display_name": u["display_name"],
                "created_at": u.get("created_at", 0),
            }
            for u in users
        ],
        "user_passwords": _export_user_passwords(),
        "progress": [
            {
                "username": p["username"],
                "telegram_msg_id": p["telegram_msg_id"],
                "completed": p["completed"],
                "watch_seconds": p["watch_seconds"],
                "last_position": p["last_position"],
                "last_watched_at": p.get("last_watched_at", 0),
            }
            for p in progress
        ],
        "notices": [
            {
                "content": n["content"],
                "created_at": n.get("created_at", 0),
            }
            for n in notices
        ],
        "messages": [
            {
                "sender_username": m.get("sender_username", ""),
                "recipient_username": m.get("recipient_username", ""),
                "recipient_id": m.get("recipient_id", 0),
                "content": m["content"],
                "is_read": m["is_read"],
                "created_at": m.get("created_at", 0),
            }
            for m in messages
        ],
    }


def _export_user_passwords() -> dict:
    """Export username → password_hash mapping (needed for login to work after restore)."""
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT username, password_hash FROM users").fetchall()
    conn.close()
    return {r["username"]: r["password_hash"] for r in rows}


async def export_to_telegram():
    """Export current DB state to Telegram Saved Messages as a JSON file."""
    from backend.telegram_client import get_client

    try:
        data = _build_backup_data()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        client = await get_client()

        # Write to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="edustream_backup_",
            delete=False, encoding="utf-8"
        ) as f:
            f.write(json_str)
            temp_path = f.name

        # Delete previous backup messages to keep Saved Messages clean
        await _delete_old_backups(client)

        # Upload new backup
        await client.send_file(
            "me",  # Saved Messages
            temp_path,
            caption=BACKUP_CAPTION,
            force_document=True,
        )

        # Clean up temp file
        try:
            Path(temp_path).unlink()
        except Exception:
            pass

        logger.info(f"Backup exported to Telegram Saved Messages ({len(json_str)} bytes)")

    except Exception as e:
        logger.error(f"Failed to export backup to Telegram: {e}")


async def _delete_old_backups(client):
    """Delete previous EDUSTREAM_BACKUP messages from Saved Messages."""
    try:
        old_ids = []
        async for msg in client.iter_messages("me", limit=50):
            caption = msg.text or msg.message or ""
            if BACKUP_CAPTION in caption:
                old_ids.append(msg.id)
        if old_ids:
            await client.delete_messages("me", old_ids)
            logger.info(f"Deleted {len(old_ids)} old backup messages")
    except Exception as e:
        logger.warning(f"Failed to delete old backups: {e}")


# ═══════════════════════════════════════════════════════════
#  Restore: Telegram Saved Messages → JSON → DB
# ═══════════════════════════════════════════════════════════

async def restore_from_telegram() -> bool:
    """
    Find the latest EDUSTREAM_BACKUP in Saved Messages, download it,
    and restore all data into the database.
    
    Returns True if a backup was found and restored.
    """
    from backend.telegram_client import get_client

    try:
        client = await get_client()

        # Find the latest backup message
        backup_msg = None
        async for msg in client.iter_messages("me", limit=100):
            caption = msg.text or msg.message or ""
            if BACKUP_CAPTION in caption:
                backup_msg = msg
                break

        if not backup_msg:
            logger.info("No backup found in Telegram Saved Messages")
            return False

        if not backup_msg.file:
            logger.warning("Backup message found but has no file attachment")
            return False

        # Download the JSON file
        data_bytes = await client.download_media(backup_msg, bytes)
        if not data_bytes:
            logger.warning("Failed to download backup file")
            return False

        data = json.loads(data_bytes.decode("utf-8"))
        logger.info(f"Backup found (exported at {data.get('exported_at', '?')})")

        # Restore data
        _restore_data(data)
        return True

    except Exception as e:
        logger.error(f"Failed to restore from Telegram: {e}")
        return False


def _restore_data(data: dict):
    """Insert backup data into the database."""
    import sqlite3
    from config import DB_PATH

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        # 1. Restore users
        user_passwords = data.get("user_passwords", {})
        for user in data.get("users", []):
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?", (user["username"],)
            ).fetchone()
            if not existing:
                password_hash = user_passwords.get(user["username"], "")
                if not password_hash:
                    logger.warning(f"Skipping user {user['username']} — no password hash in backup")
                    continue
                conn.execute(
                    "INSERT INTO users (username, password_hash, display_name, created_at) VALUES (?, ?, ?, ?)",
                    (user["username"], password_hash, user["display_name"], user.get("created_at", time.time())),
                )
        conn.commit()

        # 2. Restore segments
        for seg in data.get("segments", []):
            existing = conn.execute(
                "SELECT id FROM segments WHERE name = ?", (seg["name"],)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE segments SET icon = ?, sort_order = ? WHERE name = ?",
                    (seg["icon"], seg.get("sort_order", 0), seg["name"]),
                )
            else:
                conn.execute(
                    "INSERT INTO segments (name, icon, sort_order) VALUES (?, ?, ?)",
                    (seg["name"], seg["icon"], seg.get("sort_order", 0)),
                )
        conn.commit()

        # 3. Restore modules
        for mod in data.get("modules", []):
            seg_name = mod.get("segment_name")
            seg_id = None
            if seg_name:
                seg_row = conn.execute(
                    "SELECT id FROM segments WHERE name = ?", (seg_name,)
                ).fetchone()
                if not seg_row:
                    conn.execute(
                        "INSERT INTO segments (name, icon) VALUES (?, ?)",
                        (seg_name, "📁"),
                    )
                    conn.commit()
                    seg_row = conn.execute(
                        "SELECT id FROM segments WHERE name = ?", (seg_name,)
                    ).fetchone()
                seg_id = seg_row["id"]

            existing = conn.execute(
                "SELECT id FROM modules WHERE name = ? AND segment_id = ?",
                (mod["name"], seg_id),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE modules SET icon = ?, sort_order = ? WHERE id = ?",
                    (mod["icon"], mod.get("sort_order", 0), existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO modules (name, segment_id, icon, sort_order) VALUES (?, ?, ?, ?)",
                    (mod["name"], seg_id, mod["icon"], mod.get("sort_order", 0)),
                )
        conn.commit()

        # 4. Restore notices
        for notice in data.get("notices", []):
            existing = conn.execute(
                "SELECT id FROM notices WHERE content = ? AND created_at = ?",
                (notice["content"], notice.get("created_at", 0)),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO notices (content, created_at) VALUES (?, ?)",
                    (notice["content"], notice.get("created_at", time.time())),
                )
        conn.commit()

        # 5. Restore videos (with segment and module assignments)
        video_assignments = data.get("video_assignments", {})
        restored_videos = 0
        for vid in data.get("videos", []):
            msg_id = vid["telegram_msg_id"]

            # Find segment
            seg_name = vid.get("segment_name")
            seg_id = None
            if seg_name:
                seg_row = conn.execute(
                    "SELECT id FROM segments WHERE name = ?", (seg_name,)
                ).fetchone()
                seg_id = seg_row["id"] if seg_row else None

            # Find module (from video record or assignments dict)
            mod_name = vid.get("module_name")
            if not mod_name:
                assignment = video_assignments.get(str(msg_id), {})
                mod_name = assignment.get("module_name")

            mod_id = None
            if mod_name and seg_id:
                mod_row = conn.execute(
                    "SELECT m.id FROM modules m WHERE m.name = ? AND m.segment_id = ?",
                    (mod_name, seg_id),
                ).fetchone()
                if mod_row:
                    mod_id = mod_row["id"]
                else:
                    # Try without segment constraint
                    mod_row = conn.execute(
                        "SELECT id FROM modules WHERE name = ?", (mod_name,)
                    ).fetchone()
                    if mod_row:
                        mod_id = mod_row["id"]

            # Upsert video
            existing = conn.execute(
                "SELECT id FROM videos WHERE telegram_msg_id = ?", (msg_id,)
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE videos SET title=?, segment_id=?, module_id=?, duration_sec=?,
                           file_size=?, mime_type=?, caption=?
                    WHERE telegram_msg_id=?
                """, (vid["title"], seg_id, mod_id, vid.get("duration_sec", 0),
                      vid.get("file_size", 0), vid.get("mime_type", "video/mp4"),
                      vid.get("caption", ""), msg_id))
            else:
                conn.execute("""
                    INSERT INTO videos (telegram_msg_id, title, segment_id, module_id,
                                       duration_sec, file_size, mime_type, caption)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (msg_id, vid["title"], seg_id, mod_id,
                      vid.get("duration_sec", 0), vid.get("file_size", 0),
                      vid.get("mime_type", "video/mp4"), vid.get("caption", "")))
            restored_videos += 1
        conn.commit()

        # 6. Restore progress (videos now exist in DB)
        restored_progress = 0
        for p in data.get("progress", []):
            user = conn.execute(
                "SELECT id FROM users WHERE username = ?", (p["username"],)
            ).fetchone()
            if not user:
                continue
            video = conn.execute(
                "SELECT id FROM videos WHERE telegram_msg_id = ?", (p["telegram_msg_id"],)
            ).fetchone()
            if not video:
                continue
            existing = conn.execute(
                "SELECT id FROM progress WHERE user_id = ? AND video_id = ?",
                (user["id"], video["id"]),
            ).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO progress (user_id, video_id, completed, watch_seconds,
                                         last_position, last_watched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user["id"], video["id"],
                    p.get("completed", 0),
                    p.get("watch_seconds", 0),
                    p.get("last_position", 0),
                    p.get("last_watched_at", time.time()),
                ))
                restored_progress += 1
        conn.commit()

        # 7. Restore messages (users already exist at this point)
        _restore_messages(conn, data.get("messages", []))
        conn.commit()

        logger.info(
            f"Restored: {len(data.get('users', []))} users, "
            f"{len(data.get('segments', []))} segments, "
            f"{len(data.get('modules', []))} modules, "
            f"{restored_videos} videos, "
            f"{restored_progress} progress records, "
            f"{len(data.get('notices', []))} notices"
        )

    except Exception as e:
        logger.error(f"Error during restore: {e}")
        raise
    finally:
        conn.close()


def _restore_messages(conn, messages: list):
    """Restore messages (group chat and DMs)."""
    for msg in messages:
        sender = conn.execute(
            "SELECT id FROM users WHERE username = ?", (msg.get("sender_username", ""),)
        ).fetchone()
        if not sender:
            continue

        # For group messages (recipient_id=0), keep as-is
        # For DMs, look up recipient by username
        recipient_id = msg.get("recipient_id", 0)
        if recipient_id != 0 and msg.get("recipient_username"):
            recipient = conn.execute(
                "SELECT id FROM users WHERE username = ?", (msg["recipient_username"],)
            ).fetchone()
            if not recipient:
                continue
            recipient_id = recipient["id"]

        # Check for duplicates by content + time
        existing = conn.execute(
            "SELECT id FROM messages WHERE sender_id = ? AND content = ? AND created_at = ?",
            (sender["id"], msg["content"], msg.get("created_at", 0)),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO messages (sender_id, recipient_id, content, is_read, created_at) VALUES (?, ?, ?, ?, ?)",
                (sender["id"], recipient_id, msg["content"], msg.get("is_read", 0), msg.get("created_at", time.time())),
            )



# ═══════════════════════════════════════════════════════════
#  Debounced auto-save
# ═══════════════════════════════════════════════════════════

def schedule_backup():
    """
    Schedule a backup to Telegram, debounced to DEBOUNCE_SECONDS.
    
    If called multiple times within the debounce window, only the
    last call triggers the actual backup. This batches rapid changes
    (e.g. bulk video reassignment) into one upload.
    
    Safe to call from sync code — runs the async export in a background thread.
    """
    global _debounce_timer

    with _debounce_lock:
        if _debounce_timer is not None:
            _debounce_timer.cancel()

        _debounce_timer = threading.Timer(DEBOUNCE_SECONDS, _run_backup)
        _debounce_timer.daemon = True
        _debounce_timer.start()


def _run_backup():
    """Run the async backup in a new event loop (called from timer thread)."""
    global _debounce_timer
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(export_to_telegram())
        loop.close()
    except Exception as e:
        logger.error(f"Background backup failed: {e}")
    finally:
        with _debounce_lock:
            _debounce_timer = None


def force_backup_sync():
    """
    Force an immediate backup (no debounce). Blocks until done.
    Used by admin panel for explicit save.
    """
    global _debounce_timer
    with _debounce_lock:
        if _debounce_timer is not None:
            _debounce_timer.cancel()
            _debounce_timer = None

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(export_to_telegram())
        loop.close()
    except Exception as e:
        logger.error(f"Force backup failed: {e}")
        raise
