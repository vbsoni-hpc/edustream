"""
GitHub-based backup & restore for the EdTech platform.

Saves all metadata (course structure, users, progress, notices, messages)
as a JSON file to a private GitHub repository. On startup, fetches the latest
backup and restores the database.

Auto-save is debounced (60 seconds) to avoid rate limits (disabled in models.py).
"""
import json
import time
import asyncio
import logging
import threading
import base64
import requests
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 60

GITHUB_TOKEN = os.getenv("GITHUB_BACKUP_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_BACKUP_REPO")
GITHUB_PATH = os.getenv("GITHUB_BACKUP_PATH", "backup.json")

# ── Debounce timer state ─────────────────────────────────
_debounce_timer: Optional[threading.Timer] = None
_debounce_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════
#  Export: DB → JSON → GitHub
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

    # Fetch access control mapping
    usa = conn.execute("""
        SELECT u.username, s.name as segment_name
        FROM user_segment_access a
        JOIN users u ON a.user_id = u.id
        JOIN segments s ON a.segment_id = s.id
    """).fetchall()
    user_segment_access = [{"username": r["username"], "segment_name": r["segment_name"]} for r in usa]
    
    uma = conn.execute("""
        SELECT u.username, m.name as module_name, s.name as segment_name
        FROM user_module_access a
        JOIN users u ON a.user_id = u.id
        JOIN modules m ON a.module_id = m.id
        LEFT JOIN segments s ON m.segment_id = s.id
    """).fetchall()
    user_module_access = [{"username": r["username"], "module_name": r["module_name"], "segment_name": r["segment_name"]} for r in uma]

    uva = conn.execute("""
        SELECT u.username, v.telegram_msg_id
        FROM user_video_access a
        JOIN users u ON a.user_id = u.id
        JOIN videos v ON a.video_id = v.id
    """).fetchall()
    user_video_access = [{"username": r["username"], "telegram_msg_id": r["telegram_msg_id"]} for r in uva]
    
    # Calculate Leaderboard
    leaderboard_rows = conn.execute("""
        SELECT 
            u.username,
            u.display_name,
            COALESCE(SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END), 0) as total_completed,
            COALESCE(SUM(p.watch_seconds), 0) as total_watch_seconds
        FROM users u
        LEFT JOIN progress p ON p.user_id = u.id
        GROUP BY u.id
        ORDER BY total_completed DESC, total_watch_seconds DESC
    """).fetchall()
    leaderboard = [dict(r) for r in leaderboard_rows]

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
                "description": s.get("description", ""),
                "is_restricted": s.get("is_restricted", 0),
            }
            for s in segments
        ],
        "modules": [
            {
                "id": m["id"],
                "name": m["name"],
                "icon": m["icon"],
                "sort_order": m["sort_order"],
                "segment_name": m.get("segment_name"),
                "is_restricted": m.get("is_restricted", 0),
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
                "youtube_id": v.get("youtube_id", ""),
                "is_restricted": v.get("is_restricted", 0),
            }
            for v in videos
        ],
        "users": [
            {
                "id": u["id"],
                "username": u["username"],
                "display_name": u["display_name"],
                "created_at": u.get("created_at", 0),
                "password_hash": _export_user_passwords().get(u["username"], ""),
                "is_admin": u.get("is_admin", 0),
            }
            for u in users
        ],
        "user_passwords": _export_user_passwords(),
        "user_segment_access": user_segment_access,
        "user_module_access": user_module_access,
        "user_video_access": user_video_access,
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
        "leaderboard": [
            {
                "username": l["username"],
                "display_name": l["display_name"],
                "total_completed": l["total_completed"],
                "total_watch_seconds": l["total_watch_seconds"],
            }
            for l in leaderboard
        ]
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


async def export_to_github():
    """Export current DB state to GitHub as a JSON file."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.error("GITHUB_BACKUP_TOKEN or GITHUB_BACKUP_REPO not set.")
        raise Exception("GITHUB_BACKUP_TOKEN or GITHUB_BACKUP_REPO not set in .env")

    try:
        data = _build_backup_data()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}"

        # 1. Get the current file's SHA (required to update it)
        sha = None
        get_resp = requests.get(url, headers=headers)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")

        # 2. Upload/Update the file
        payload = {
            "message": f"Backup exported at {datetime.now(timezone.utc).isoformat()}",
            "content": content_b64,
        }
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(url, headers=headers, json=payload)
        if put_resp.status_code in [200, 201]:
            logger.info(f"Backup exported to GitHub ({len(json_str)} bytes)")
        else:
            logger.error(f"Failed to export backup to GitHub: {put_resp.text}")
            raise Exception(f"Failed to export backup to GitHub: {put_resp.text}")

    except Exception as e:
        logger.error(f"Failed to export backup to GitHub: {e}")
        raise


# ═══════════════════════════════════════════════════════════
#  Restore: GitHub → JSON → DB
# ═══════════════════════════════════════════════════════════

async def restore_from_github() -> tuple[bool, str]:
    """
    Fetch the latest backup from GitHub and restore all data into the database.
    
    Returns (success_bool, error_message).
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.info("GitHub credentials not configured, skipping restore.")
        return False, "GitHub credentials not configured"

    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}"

        get_resp = requests.get(url, headers=headers)
        if get_resp.status_code != 200:
            logger.info("No backup found in GitHub repo.")
            return False, "No backup found in GitHub repo"

        content_b64 = get_resp.json().get("content")
        if not content_b64:
            logger.warning("Backup file found but it has no content.")
            return False, "Backup file found but it has no content"

        data_bytes = base64.b64decode(content_b64)
        data = json.loads(data_bytes.decode("utf-8"))
        logger.info(f"Backup found (exported at {data.get('exported_at', '?')})")

        # Restore data
        _restore_data(data)
        return True, "Success"

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"Failed to restore from GitHub: {e}")
        return False, f"Exception: {str(e)}\n{err_msg}"


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
            username = user["username"]
            display_name = user["display_name"]
            created_at = user.get("created_at", time.time())
            password_hash = user.get("password_hash") or user_passwords.get(username, "")
            
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            
            if existing:
                if password_hash:
                    conn.execute("UPDATE users SET password_hash = ?, display_name = ? WHERE id = ?", 
                                 (password_hash, display_name, existing["id"]))
            else:
                if not password_hash:
                    logger.warning(f"Skipping user {username} — no password hash in backup")
                    continue
                if "id" in user:
                    conn.execute(
                        "INSERT INTO users (id, username, password_hash, display_name, created_at, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                        (user["id"], username, password_hash, display_name, created_at, user.get("is_admin", 0)),
                    )
                else:
                    conn.execute(
                        "INSERT INTO users (username, password_hash, display_name, created_at, is_admin) VALUES (?, ?, ?, ?, ?)",
                        (username, password_hash, display_name, created_at, user.get("is_admin", 0)),
                    )
        conn.commit()

        # 2. Restore segments
        for seg in data.get("segments", []):
            existing = conn.execute(
                "SELECT id FROM segments WHERE name = ?", (seg["name"],)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE segments SET icon = ?, sort_order = ?, description = ?, is_restricted = ? WHERE name = ?",
                    (seg["icon"], seg.get("sort_order", 0), seg.get("description", ""), seg.get("is_restricted", 0), seg["name"]),
                )
            else:
                conn.execute(
                    "INSERT INTO segments (name, icon, sort_order, description, is_restricted) VALUES (?, ?, ?, ?, ?)",
                    (seg["name"], seg["icon"], seg.get("sort_order", 0), seg.get("description", ""), seg.get("is_restricted", 0)),
                )
        conn.commit()

        # 3. Restore modules
        for mod in data.get("modules", []):
            seg_name = mod.get("segment_name") or "Uncategorized"
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

            existing = None
            if "id" in mod:
                existing = conn.execute("SELECT id FROM modules WHERE id = ?", (mod["id"],)).fetchone()
            
            if not existing:
                existing = conn.execute(
                    "SELECT id FROM modules WHERE name = ? AND segment_id = ?",
                    (mod["name"], seg_id),
                ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE modules SET name = ?, icon = ?, sort_order = ?, segment_id = ?, is_restricted = ? WHERE id = ?",
                    (mod["name"], mod["icon"], mod.get("sort_order", 0), seg_id, mod.get("is_restricted", 0), existing["id"]),
                )
            else:
                if "id" in mod:
                    conn.execute(
                        "INSERT INTO modules (id, name, segment_id, icon, sort_order, is_restricted) VALUES (?, ?, ?, ?, ?, ?)",
                        (mod["id"], mod["name"], seg_id, mod["icon"], mod.get("sort_order", 0), mod.get("is_restricted", 0)),
                    )
                else:
                    conn.execute(
                        "INSERT INTO modules (name, segment_id, icon, sort_order, is_restricted) VALUES (?, ?, ?, ?, ?)",
                        (mod["name"], seg_id, mod["icon"], mod.get("sort_order", 0), mod.get("is_restricted", 0)),
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
            seg_name = vid.get("segment_name") or "Uncategorized"
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

            # Find module (from video record or assignments dict)
            mod_name = vid.get("module_name")
            if not mod_name:
                assignment = video_assignments.get(str(msg_id), {})
                mod_name = assignment.get("module_name")

            mod_id = None
            if mod_name:
                mod_row = None
                if seg_id:
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
                           file_size=?, mime_type=?, caption=?, youtube_id=?, is_restricted=?
                    WHERE telegram_msg_id=?
                """, (vid["title"], seg_id, mod_id, vid.get("duration_sec", 0),
                      vid.get("file_size", 0), vid.get("mime_type", "video/mp4"),
                      vid.get("caption", ""), vid.get("youtube_id") or None, vid.get("is_restricted", 0), msg_id))
            else:
                conn.execute("""
                    INSERT INTO videos (telegram_msg_id, title, segment_id, module_id,
                                       duration_sec, file_size, mime_type, caption, youtube_id, is_restricted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (msg_id, vid["title"], seg_id, mod_id,
                      vid.get("duration_sec", 0), vid.get("file_size", 0),
                      vid.get("mime_type", "video/mp4"), vid.get("caption", ""),
                      vid.get("youtube_id") or None, vid.get("is_restricted", 0)))
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

        # 8. Restore access control mappings
        conn.execute("DELETE FROM user_segment_access")
        for usa in data.get("user_segment_access", []):
            u_row = conn.execute("SELECT id FROM users WHERE username = ?", (usa["username"],)).fetchone()
            s_row = conn.execute("SELECT id FROM segments WHERE name = ?", (usa["segment_name"],)).fetchone()
            if u_row and s_row:
                conn.execute("INSERT OR IGNORE INTO user_segment_access (user_id, segment_id) VALUES (?, ?)", (u_row["id"], s_row["id"]))
                
        conn.execute("DELETE FROM user_module_access")
        for uma in data.get("user_module_access", []):
            u_row = conn.execute("SELECT id FROM users WHERE username = ?", (uma["username"],)).fetchone()
            s_row = conn.execute("SELECT id FROM segments WHERE name = ?", (uma.get("segment_name") or "Uncategorized",)).fetchone()
            if u_row and s_row:
                m_row = conn.execute("SELECT id FROM modules WHERE name = ? AND segment_id = ?", (uma["module_name"], s_row["id"])).fetchone()
                if m_row:
                    conn.execute("INSERT OR IGNORE INTO user_module_access (user_id, module_id) VALUES (?, ?)", (u_row["id"], m_row["id"]))

        conn.execute("DELETE FROM user_video_access")
        for uva in data.get("user_video_access", []):
            u_row = conn.execute("SELECT id FROM users WHERE username = ?", (uva["username"],)).fetchone()
            v_row = conn.execute("SELECT id FROM videos WHERE telegram_msg_id = ?", (uva["telegram_msg_id"],)).fetchone()
            if u_row and v_row:
                conn.execute("INSERT OR IGNORE INTO user_video_access (user_id, video_id) VALUES (?, ?)", (u_row["id"], v_row["id"]))
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
    Schedule a backup to GitHub, debounced to DEBOUNCE_SECONDS.
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
        loop.run_until_complete(export_to_github())
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
        loop.run_until_complete(export_to_github())
        loop.close()
    except Exception as e:
        logger.error(f"Force backup failed: {e}")
        raise
