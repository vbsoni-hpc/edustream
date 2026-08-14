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
    created_at      REAL    NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS segments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    UNIQUE NOT NULL,
    icon       TEXT    NOT NULL DEFAULT '📁',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS videos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_msg_id INTEGER UNIQUE NOT NULL,
    title           TEXT    NOT NULL DEFAULT 'Untitled',
    segment_id      INTEGER REFERENCES segments(id),
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
"""


def init_db():
    """Create tables if they don't exist (sync, for startup)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()


async def async_init_db():
    """Create tables if they don't exist (async, for FastAPI startup)."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.executescript(_SCHEMA)
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


# ── Videos ────────────────────────────────────────────────

def get_all_videos() -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT v.*, s.name as segment_name, s.icon as segment_icon
            FROM videos v
            LEFT JOIN segments s ON v.segment_id = s.id
            ORDER BY s.sort_order, v.telegram_msg_id
        """).fetchall()
        return [dict(r) for r in rows]


def get_videos_by_segment(segment_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT v.*, s.name as segment_name, s.icon as segment_icon
            FROM videos v
            LEFT JOIN segments s ON v.segment_id = s.id
            WHERE v.segment_id = ?
            ORDER BY v.telegram_msg_id
        """, (segment_id,)).fetchall()
        return [dict(r) for r in rows]


def get_video_by_id(video_id: int) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("""
            SELECT v.*, s.name as segment_name, s.icon as segment_icon
            FROM videos v
            LEFT JOIN segments s ON v.segment_id = s.id
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
