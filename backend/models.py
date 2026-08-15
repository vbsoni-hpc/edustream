"""
Database schema and CRUD helpers for the EdTech platform.

Uses standard sqlite3 for Streamlit reads and aiosqlite for FastAPI async writes.
"""
import sqlite3
import time
from pathlib import Path
from typing import Optional

import aiosqlite

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH


# ═══════════════════════════════════════════════════════════
#  Schema Initialisation
# ═══════════════════════════════════════════════════════════

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    UNIQUE NOT NULL,
    password_hash   TEXT    NOT NULL,
    display_name    TEXT    NOT NULL DEFAULT '',
    created_at      REAL    NOT NULL DEFAULT (strftime('%s','now')),
    last_active     REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS segments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    UNIQUE NOT NULL,
    icon       TEXT    NOT NULL DEFAULT '📁',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS modules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    segment_id INTEGER NOT NULL REFERENCES segments(id),
    icon       TEXT    NOT NULL DEFAULT '📂',
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(name, segment_id)
);

CREATE TABLE IF NOT EXISTS videos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_msg_id INTEGER UNIQUE NOT NULL,
    title           TEXT    NOT NULL DEFAULT 'Untitled',
    segment_id      INTEGER REFERENCES segments(id),
    module_id       INTEGER REFERENCES modules(id),
    duration_sec    REAL    NOT NULL DEFAULT 0,
    file_size       INTEGER NOT NULL DEFAULT 0,
    mime_type       TEXT    NOT NULL DEFAULT 'video/mp4',
    caption         TEXT    NOT NULL DEFAULT '',
    synced_at       REAL    NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    video_id        INTEGER NOT NULL REFERENCES videos(id),
    completed       INTEGER NOT NULL DEFAULT 0,
    watch_seconds   REAL    NOT NULL DEFAULT 0,
    last_position   REAL    NOT NULL DEFAULT 0,
    last_watched_at REAL    NOT NULL DEFAULT (strftime('%s','now')),
    UNIQUE(user_id, video_id)
);
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id    INTEGER NOT NULL REFERENCES users(id),
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    content      TEXT    NOT NULL,
    is_read      INTEGER NOT NULL DEFAULT 0,
    created_at   REAL    NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS notices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    content      TEXT    NOT NULL,
    created_at   REAL    NOT NULL DEFAULT (strftime('%s','now'))
);
"""

# Migration: add module_id to existing videos table if missing
_MIGRATIONS = [
    "ALTER TABLE videos ADD COLUMN module_id INTEGER REFERENCES modules(id)",
    "ALTER TABLE users ADD COLUMN last_active REAL NOT NULL DEFAULT 0",
    "CREATE TABLE IF NOT EXISTS notices (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, created_at REAL NOT NULL DEFAULT (strftime('%s','now')))"
]


def init_db():
    """Create tables if they don't exist (sync, for startup)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(_SCHEMA)
    # Run safe migrations
    for migration in _MIGRATIONS:
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    conn.close()


async def async_init_db():
    """Create tables if they don't exist (async, for FastAPI startup)."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.executescript(_SCHEMA)
        for migration in _MIGRATIONS:
            try:
                await db.execute(migration)
            except Exception:
                pass
        await db.commit()


# ═══════════════════════════════════════════════════════════
#  Synchronous helpers  (for Streamlit reads)
# ═══════════════════════════════════════════════════════════

def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


# ── Users ─────────────────────────────────────────────────

def get_user_by_username(username: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_user(username: str, password_hash: str, display_name: str = "") -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
            (username, password_hash, display_name or username),
        )
        c.commit()
        return cur.lastrowid


def get_all_users() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT id, username, display_name FROM users ORDER BY display_name").fetchall()
        return [dict(r) for r in rows]

# ── Messages ──────────────────────────────────────────────

def send_message(sender_id: int, recipient_id: int, content: str):
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (sender_id, recipient_id, content) VALUES (?, ?, ?)",
            (sender_id, recipient_id, content)
        )
        c.commit()

def get_messages_for_user(user_id: int) -> list[dict]:
    """Get all received messages with sender details."""
    with _conn() as c:
        rows = c.execute("""
            SELECT m.*, u.username as sender_username, u.display_name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.recipient_id = ?
            ORDER BY m.created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]

def get_unread_messages(user_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT m.*, u.display_name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.recipient_id = ? AND m.is_read = 0
            ORDER BY m.created_at ASC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]

def get_group_messages(limit: int = 50) -> list[dict]:
    """Get all global group chat messages (where recipient_id = 0)"""
    with _conn() as c:
        rows = c.execute("""
            SELECT m.*, u.username as sender_username, u.display_name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.recipient_id = 0
            ORDER BY m.created_at ASC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_max_group_message_id() -> int:
    with _conn() as c:
        row = c.execute("SELECT MAX(id) as max_id FROM messages WHERE recipient_id = 0").fetchone()
        return row["max_id"] or 0

def get_new_group_messages_since(last_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT m.*, u.display_name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.recipient_id = 0 AND m.id > ?
            ORDER BY m.created_at ASC
        """, (last_id,)).fetchall()
        return [dict(r) for r in rows]

def mark_messages_read(message_ids: list[int]):
    if not message_ids:
        return
    with _conn() as c:
        placeholders = ",".join("?" for _ in message_ids)
        c.execute(f"UPDATE messages SET is_read = 1 WHERE id IN ({placeholders})", message_ids)
        c.commit()

# ── Notices ───────────────────────────────────────────────

def add_notice(content: str):
    with _conn() as c:
        c.execute("INSERT INTO notices (content) VALUES (?)", (content,))
        c.commit()

def get_latest_notices(limit: int = 3) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM notices ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_all_notices() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM notices ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def delete_notice(notice_id: int):
    with _conn() as c:
        c.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
        c.commit()


# ── Segments ──────────────────────────────────────────────

def get_all_segments() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM segments ORDER BY sort_order, name").fetchall()
        return [dict(r) for r in rows]


def get_or_create_segment(name: str, icon: str = "📁") -> int:
    with _conn() as c:
        row = c.execute("SELECT id FROM segments WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = c.execute(
            "INSERT INTO segments (name, icon) VALUES (?, ?)", (name, icon)
        )
        c.commit()
        return cur.lastrowid


def update_segment(segment_id: int, name: str = None, icon: str = None, sort_order: int = None):
    with _conn() as c:
        if name is not None:
            c.execute("UPDATE segments SET name = ? WHERE id = ?", (name, segment_id))
        if icon is not None:
            c.execute("UPDATE segments SET icon = ? WHERE id = ?", (icon, segment_id))
        if sort_order is not None:
            c.execute("UPDATE segments SET sort_order = ? WHERE id = ?", (sort_order, segment_id))
        c.commit()


# ── Modules ──────────────────────────────────────────────

def get_all_modules() -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT m.*, s.name as segment_name, s.icon as segment_icon
            FROM modules m
            LEFT JOIN segments s ON m.segment_id = s.id
            ORDER BY m.segment_id, m.sort_order, m.name
        """).fetchall()
        return [dict(r) for r in rows]


def get_modules_by_segment(segment_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT * FROM modules
            WHERE segment_id = ?
            ORDER BY sort_order, name
        """, (segment_id,)).fetchall()
        return [dict(r) for r in rows]


def get_or_create_module(name: str, segment_id: int, icon: str = "📂") -> int:
    with _conn() as c:
        row = c.execute(
            "SELECT id FROM modules WHERE name = ? AND segment_id = ?",
            (name, segment_id)
        ).fetchone()
        if row:
            return row["id"]
        cur = c.execute(
            "INSERT INTO modules (name, segment_id, icon) VALUES (?, ?, ?)",
            (name, segment_id, icon)
        )
        c.commit()
        return cur.lastrowid


def update_module(module_id: int, name: str = None, icon: str = None, sort_order: int = None):
    with _conn() as c:
        if name is not None:
            c.execute("UPDATE modules SET name = ? WHERE id = ?", (name, module_id))
        if icon is not None:
            c.execute("UPDATE modules SET icon = ? WHERE id = ?", (icon, module_id))
        if sort_order is not None:
            c.execute("UPDATE modules SET sort_order = ? WHERE id = ?", (sort_order, module_id))
        c.commit()


def delete_module(module_id: int):
    """Delete a module and unassign its videos (set module_id to NULL)."""
    with _conn() as c:
        c.execute("UPDATE videos SET module_id = NULL WHERE module_id = ?", (module_id,))
        c.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        c.commit()


def move_videos_to_module(video_ids: list[int], module_id: int):
    """Assign a list of videos to a module."""
    with _conn() as c:
        for vid in video_ids:
            c.execute("UPDATE videos SET module_id = ? WHERE id = ?", (module_id, vid))
        c.commit()


def unassign_videos_from_module(video_ids: list[int]):
    """Remove videos from their module (set to NULL)."""
    with _conn() as c:
        for vid in video_ids:
            c.execute("UPDATE videos SET module_id = NULL WHERE id = ?", (vid,))
        c.commit()


# ── Videos ────────────────────────────────────────────────

def get_all_videos() -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                   m.name as module_name, m.icon as module_icon
            FROM videos v
            LEFT JOIN segments s ON v.segment_id = s.id
            LEFT JOIN modules m ON v.module_id = m.id
            ORDER BY s.sort_order, v.telegram_msg_id
        """).fetchall()
        return [dict(r) for r in rows]


def get_videos_by_segment(segment_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                   m.name as module_name, m.icon as module_icon
            FROM videos v
            LEFT JOIN segments s ON v.segment_id = s.id
            LEFT JOIN modules m ON v.module_id = m.id
            WHERE v.segment_id = ?
            ORDER BY v.telegram_msg_id
        """, (segment_id,)).fetchall()
        return [dict(r) for r in rows]


def get_videos_by_module(module_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                   m.name as module_name, m.icon as module_icon
            FROM videos v
            LEFT JOIN segments s ON v.segment_id = s.id
            LEFT JOIN modules m ON v.module_id = m.id
            WHERE v.module_id = ?
            ORDER BY v.telegram_msg_id
        """, (module_id,)).fetchall()
        return [dict(r) for r in rows]


def get_video_by_id(video_id: int) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("""
            SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                   m.name as module_name, m.icon as module_icon
            FROM videos v
            LEFT JOIN segments s ON v.segment_id = s.id
            LEFT JOIN modules m ON v.module_id = m.id
            WHERE v.id = ?
        """, (video_id,)).fetchone()
        return dict(row) if row else None


def upsert_video(telegram_msg_id: int, title: str, segment_id: int,
                 duration_sec: float = 0, file_size: int = 0,
                 mime_type: str = "video/mp4", caption: str = "") -> int:
    with _conn() as c:
        row = c.execute("SELECT id FROM videos WHERE telegram_msg_id = ?", (telegram_msg_id,)).fetchone()
        if row:
            c.execute("""
                UPDATE videos SET title=?, segment_id=?, duration_sec=?, file_size=?,
                       mime_type=?, caption=?, synced_at=?
                WHERE telegram_msg_id=?
            """, (title, segment_id, duration_sec, file_size, mime_type, caption, time.time(), telegram_msg_id))
            c.commit()
            return row["id"]
        cur = c.execute("""
            INSERT INTO videos (telegram_msg_id, title, segment_id, duration_sec, file_size, mime_type, caption)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (telegram_msg_id, title, segment_id, duration_sec, file_size, mime_type, caption))
        c.commit()
        return cur.lastrowid


# ── Progress ──────────────────────────────────────────────

def get_user_progress(user_id: int) -> list[dict]:
    """Get progress for all videos for a user."""
    with _conn() as c:
        rows = c.execute("""
            SELECT p.*, v.title, v.duration_sec, v.telegram_msg_id,
                   s.name as segment_name, s.icon as segment_icon
            FROM progress p
            JOIN videos v ON p.video_id = v.id
            LEFT JOIN segments s ON v.segment_id = s.id
            WHERE p.user_id = ?
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_video_progress(user_id: int, video_id: int) -> Optional[dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM progress WHERE user_id = ? AND video_id = ?",
            (user_id, video_id)
        ).fetchone()
        return dict(row) if row else None


def upsert_progress(user_id: int, video_id: int, watch_seconds: float = 0,
                    last_position: float = 0, completed: bool = False):
    with _conn() as c:
        row = c.execute(
            "SELECT id, watch_seconds FROM progress WHERE user_id = ? AND video_id = ?",
            (user_id, video_id)
        ).fetchone()
        now = time.time()
        if row:
            # Only update watch_seconds if the new value is higher
            new_watch = max(row["watch_seconds"], watch_seconds)
            c.execute("""
                UPDATE progress
                SET watch_seconds = ?, last_position = ?, completed = COALESCE(?, completed),
                    last_watched_at = ?
                WHERE user_id = ? AND video_id = ?
            """, (new_watch, last_position, int(completed) if completed else None, now, user_id, video_id))
        else:
            c.execute("""
                INSERT INTO progress (user_id, video_id, watch_seconds, last_position, completed, last_watched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, video_id, watch_seconds, last_position, int(completed), now))
        c.commit()


def mark_video_complete(user_id: int, video_id: int):
    with _conn() as c:
        row = c.execute(
            "SELECT id FROM progress WHERE user_id = ? AND video_id = ?",
            (user_id, video_id)
        ).fetchone()
        now = time.time()
        if row:
            c.execute(
                "UPDATE progress SET completed = 1, last_watched_at = ? WHERE id = ?",
                (now, row["id"])
            )
        else:
            c.execute(
                "INSERT INTO progress (user_id, video_id, completed, last_watched_at) VALUES (?, ?, 1, ?)",
                (user_id, video_id, now)
            )
        c.commit()


# ── Dashboard / Stats ────────────────────────────────────

def get_dashboard_stats(user_id: int) -> dict:
    """Aggregate stats for the dashboard."""
    with _conn() as c:
        total_videos = c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        completed = c.execute(
            "SELECT COUNT(*) FROM progress WHERE user_id = ? AND completed = 1",
            (user_id,)
        ).fetchone()[0]
        total_watch_sec = c.execute(
            "SELECT COALESCE(SUM(watch_seconds), 0) FROM progress WHERE user_id = ?",
            (user_id,)
        ).fetchone()[0]

        return {
            "total_videos": total_videos,
            "completed_videos": completed,
            "completion_pct": (completed / total_videos * 100) if total_videos > 0 else 0,
            "total_watch_hours": total_watch_sec / 3600,
            "total_watch_seconds": total_watch_sec,
        }


def get_segment_stats(user_id: int) -> list[dict]:
    """Per-segment completion and watch time."""
    with _conn() as c:
        rows = c.execute("""
            SELECT 
                s.id, s.name, s.icon,
                COUNT(v.id) as total_videos,
                COALESCE(SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END), 0) as completed_videos,
                COALESCE(SUM(p.watch_seconds), 0) as watch_seconds
            FROM segments s
            LEFT JOIN videos v ON v.segment_id = s.id
            LEFT JOIN progress p ON p.video_id = v.id AND p.user_id = ?
            GROUP BY s.id
            ORDER BY s.sort_order, s.name
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_module_stats(user_id: int) -> list[dict]:
    """Per-module completion and watch time."""
    with _conn() as c:
        rows = c.execute("""
            SELECT 
                m.id, m.name, m.icon, m.segment_id, s.name as segment_name, s.icon as segment_icon,
                COUNT(v.id) as total_videos,
                COALESCE(SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END), 0) as completed_videos,
                COALESCE(SUM(p.watch_seconds), 0) as watch_seconds
            FROM modules m
            JOIN segments s ON m.segment_id = s.id
            LEFT JOIN videos v ON v.module_id = m.id
            LEFT JOIN progress p ON p.video_id = v.id AND p.user_id = ?
            GROUP BY m.id
            ORDER BY s.sort_order, m.sort_order, m.name
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_daily_watch_activity(user_id: int, days: int = 30) -> list[dict]:
    """Daily watch seconds for the last N days."""
    with _conn() as c:
        cutoff = time.time() - days * 86400
        rows = c.execute("""
            SELECT 
                date(last_watched_at, 'unixepoch') as date,
                SUM(watch_seconds) as watch_seconds
            FROM progress
            WHERE user_id = ? AND last_watched_at >= ?
            GROUP BY date(last_watched_at, 'unixepoch')
            ORDER BY date
        """, (user_id, cutoff)).fetchall()
        return [dict(r) for r in rows]


def ping_user(user_id: int):
    """Update the user's last_active timestamp."""
    with _conn() as c:
        c.execute("UPDATE users SET last_active = ? WHERE id = ?", (time.time(), user_id))
        c.commit()

def get_online_users(minutes: int = 5) -> list[dict]:
    """Get users who have been active within the last N minutes."""
    with _conn() as c:
        cutoff = time.time() - (minutes * 60)
        rows = c.execute(
            "SELECT username, display_name FROM users WHERE last_active >= ? ORDER BY last_active DESC",
            (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_leaderboard(days: int = 1) -> list[dict]:
    """Get leaderboard of watch time over the last N days."""
    with _conn() as c:
        cutoff = time.time() - (days * 86400)
        # Note: we use last_watched_at as the time filter.
        rows = c.execute("""
            SELECT 
                u.username, u.display_name, 
                COALESCE(SUM(p.watch_seconds), 0) as total_watch_sec
            FROM users u
            JOIN progress p ON u.id = p.user_id
            WHERE p.last_watched_at >= ?
            GROUP BY u.id
            HAVING total_watch_sec > 0
            ORDER BY total_watch_sec DESC
            LIMIT 10
        """, (cutoff,)).fetchall()
        return [dict(r) for r in rows]


# ── Async helpers (for FastAPI) ───────────────────────────

async def async_upsert_progress(user_id: int, video_id: int,
                                 watch_seconds: float = 0,
                                 last_position: float = 0):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, watch_seconds FROM progress WHERE user_id = ? AND video_id = ?",
            (user_id, video_id)
        )
        row = await cursor.fetchone()
        now = time.time()
        if row:
            new_watch = max(row["watch_seconds"], watch_seconds)
            await db.execute("""
                UPDATE progress SET watch_seconds=?, last_position=?, last_watched_at=?
                WHERE user_id=? AND video_id=?
            """, (new_watch, last_position, now, user_id, video_id))
        else:
            await db.execute("""
                INSERT INTO progress (user_id, video_id, watch_seconds, last_position, last_watched_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, video_id, watch_seconds, last_position, now))
        await db.commit()


async def async_mark_complete(user_id: int, video_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id FROM progress WHERE user_id = ? AND video_id = ?",
            (user_id, video_id)
        )
        row = await cursor.fetchone()
        now = time.time()
        if row:
            await db.execute(
                "UPDATE progress SET completed=1, last_watched_at=? WHERE id=?",
                (now, row["id"])
            )
        else:
            await db.execute(
                "INSERT INTO progress (user_id, video_id, completed, last_watched_at) VALUES (?, ?, 1, ?)",
                (user_id, video_id, now)
            )
        await db.commit()


async def async_get_video_by_msg_id(msg_id: int) -> Optional[dict]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM videos WHERE telegram_msg_id = ?", (msg_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
