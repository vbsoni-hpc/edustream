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


def _trigger_backup():
    """Trigger a debounced backup to GitHub. Safe to call frequently."""
    try:
        from backend.github_backup import schedule_backup
        schedule_backup()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to schedule auto-backup: {e}")


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
    last_active     REAL    NOT NULL DEFAULT 0,
    is_admin        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS segments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    UNIQUE NOT NULL,
    icon       TEXT    NOT NULL DEFAULT '📁',
    description TEXT   NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_restricted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS modules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    segment_id INTEGER NOT NULL REFERENCES segments(id),
    icon       TEXT    NOT NULL DEFAULT '📂',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_restricted INTEGER NOT NULL DEFAULT 0,
    UNIQUE(name, segment_id)
);

CREATE TABLE IF NOT EXISTS videos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_msg_id INTEGER UNIQUE NOT NULL,
    youtube_id      TEXT    UNIQUE,
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
CREATE TABLE IF NOT EXISTS user_segment_access (
    user_id      INTEGER NOT NULL REFERENCES users(id),
    segment_id   INTEGER NOT NULL REFERENCES segments(id),
    PRIMARY KEY (user_id, segment_id)
);
CREATE TABLE IF NOT EXISTS user_module_access (
    user_id      INTEGER NOT NULL REFERENCES users(id),
    module_id    INTEGER NOT NULL REFERENCES modules(id),
    PRIMARY KEY (user_id, module_id)
);
CREATE TABLE IF NOT EXISTS user_segment_subscriptions (
    user_id      INTEGER NOT NULL REFERENCES users(id),
    segment_id   INTEGER NOT NULL REFERENCES segments(id),
    PRIMARY KEY (user_id, segment_id)
);
"""

# Migration: add module_id to existing videos table if missing
_MIGRATIONS = [
    "ALTER TABLE videos ADD COLUMN module_id INTEGER REFERENCES modules(id)",
    "ALTER TABLE users ADD COLUMN last_active REAL NOT NULL DEFAULT 0",
    "CREATE TABLE IF NOT EXISTS notices (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, created_at REAL NOT NULL DEFAULT (strftime('%s','now')))",
    "ALTER TABLE segments ADD COLUMN description TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE segments ADD COLUMN is_restricted INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE modules ADD COLUMN is_restricted INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE videos ADD COLUMN youtube_id TEXT",
    "CREATE TABLE IF NOT EXISTS user_segment_access (user_id INTEGER NOT NULL REFERENCES users(id), segment_id INTEGER NOT NULL REFERENCES segments(id), PRIMARY KEY (user_id, segment_id))",
    "CREATE TABLE IF NOT EXISTS user_module_access (user_id INTEGER NOT NULL REFERENCES users(id), module_id INTEGER NOT NULL REFERENCES modules(id), PRIMARY KEY (user_id, module_id))",
    "UPDATE users SET is_admin = 1 WHERE username = 'vbsoni'",
    "ALTER TABLE videos ADD COLUMN is_restricted INTEGER NOT NULL DEFAULT 0",
    "CREATE TABLE IF NOT EXISTS user_video_access (user_id INTEGER NOT NULL REFERENCES users(id), video_id INTEGER NOT NULL REFERENCES videos(id), PRIMARY KEY (user_id, video_id))",
    "CREATE TABLE IF NOT EXISTS user_segment_subscriptions (user_id INTEGER NOT NULL REFERENCES users(id), segment_id INTEGER NOT NULL REFERENCES segments(id), PRIMARY KEY (user_id, segment_id))"
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
        _trigger_backup()
        return cur.lastrowid


def get_all_users() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT id, username, display_name FROM users ORDER BY display_name").fetchall()
        return [dict(r) for r in rows]

def get_all_users_admin() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT id, username, display_name, created_at, last_active, is_admin FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]

def update_user_admin(user_id: int, username: str, display_name: str, is_admin: bool = False):
    with _conn() as c:
        c.execute("UPDATE users SET username=?, display_name=?, is_admin=? WHERE id=?", (username, display_name, int(is_admin), user_id))
        c.commit()
        _trigger_backup()

def delete_user_admin(user_id: int):
    with _conn() as c:
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        c.commit()
        _trigger_backup()

# ── Messages ──────────────────────────────────────────────

def send_message(sender_id: int, recipient_id: int, content: str):
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (sender_id, recipient_id, content) VALUES (?, ?, ?)",
            (sender_id, recipient_id, content)
        )
        # Auto-delete messages older than 7 days
        c.execute(
            "DELETE FROM messages WHERE created_at < (strftime('%s', 'now') - (7 * 24 * 60 * 60))"
        )
        c.commit()
        _trigger_backup()

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

def delete_all_messages():
    """Delete all messages (group chat + DMs) from the database."""
    with _conn() as c:
        c.execute("DELETE FROM messages")
        c.commit()
        _trigger_backup()

# ── Notices ───────────────────────────────────────────────

def add_notice(content: str):
    with _conn() as c:
        c.execute("INSERT INTO notices (content) VALUES (?)", (content,))
        c.commit()
        _trigger_backup()

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
        _trigger_backup()


# ── Segments ──────────────────────────────────────────────

def get_all_segments(user_id: int = None) -> list[dict]:
    with _conn() as c:
        if user_id is None:
            rows = c.execute("SELECT * FROM segments ORDER BY sort_order, name").fetchall()
        else:
            user_row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
            is_admin = bool(user_row["is_admin"]) if user_row else False
            if is_admin:
                rows = c.execute("SELECT * FROM segments ORDER BY sort_order, name").fetchall()
            else:
                rows = c.execute("""
                    SELECT * FROM segments 
                    WHERE is_restricted = 0 
                    OR id IN (SELECT segment_id FROM user_segment_access WHERE user_id = ?)
                    ORDER BY sort_order, name
                """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_or_create_segment(name: str, icon: str = "📁", description: str = "") -> int:
    with _conn() as c:
        row = c.execute("SELECT id FROM segments WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = c.execute(
            "INSERT INTO segments (name, icon, description) VALUES (?, ?, ?)", (name, icon, description)
        )
        c.commit()
        _trigger_backup()
        return cur.lastrowid


def update_segment(segment_id: int, name: str = None, icon: str = None, description: str = None, sort_order: int = None, is_restricted: bool = None):
    with _conn() as c:
        if name is not None:
            c.execute("UPDATE segments SET name = ? WHERE id = ?", (name, segment_id))
        if icon is not None:
            c.execute("UPDATE segments SET icon = ? WHERE id = ?", (icon, segment_id))
        if description is not None:
            c.execute("UPDATE segments SET description = ? WHERE id = ?", (description, segment_id))
        if sort_order is not None:
            c.execute("UPDATE segments SET sort_order = ? WHERE id = ?", (sort_order, segment_id))
        if is_restricted is not None:
            c.execute("UPDATE segments SET is_restricted = ? WHERE id = ?", (int(is_restricted), segment_id))
        c.commit()
        _trigger_backup()


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


def get_modules_by_segment(segment_id: int, user_id: int = None) -> list[dict]:
    with _conn() as c:
        if user_id is None:
            rows = c.execute("""
                SELECT * FROM modules
                WHERE segment_id = ?
                ORDER BY sort_order, name
            """, (segment_id,)).fetchall()
        else:
            user_row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
            is_admin = bool(user_row["is_admin"]) if user_row else False
            if is_admin:
                rows = c.execute("""
                    SELECT * FROM modules
                    WHERE segment_id = ?
                    ORDER BY sort_order, name
                """, (segment_id,)).fetchall()
            else:
                rows = c.execute("""
                    SELECT * FROM modules
                    WHERE segment_id = ? AND (is_restricted = 0 OR id IN (SELECT module_id FROM user_module_access WHERE user_id = ?))
                    ORDER BY sort_order, name
                """, (segment_id, user_id)).fetchall()
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
        _trigger_backup()
        return cur.lastrowid


def update_module(module_id: int, name: str = None, icon: str = None, sort_order: int = None, is_restricted: bool = None):
    with _conn() as c:
        if name is not None:
            c.execute("UPDATE modules SET name = ? WHERE id = ?", (name, module_id))
        if icon is not None:
            c.execute("UPDATE modules SET icon = ? WHERE id = ?", (icon, module_id))
        if sort_order is not None:
            c.execute("UPDATE modules SET sort_order = ? WHERE id = ?", (sort_order, module_id))
        if is_restricted is not None:
            c.execute("UPDATE modules SET is_restricted = ? WHERE id = ?", (int(is_restricted), module_id))
        c.commit()
        _trigger_backup()


def delete_module(module_id: int):
    """Delete a module and unassign its videos (set module_id to NULL)."""
    with _conn() as c:
        c.execute("UPDATE videos SET module_id = NULL WHERE module_id = ?", (module_id,))
        c.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        c.commit()
        _trigger_backup()


def move_videos_to_module(video_ids: list[int], module_id: int):
    """Assign a list of videos to a module."""
    with _conn() as c:
        mod_row = c.execute("SELECT segment_id FROM modules WHERE id = ?", (module_id,)).fetchone()
        if not mod_row:
            return
        seg_id = mod_row["segment_id"]
        for vid in video_ids:
            c.execute("UPDATE videos SET module_id = ?, segment_id = ? WHERE id = ?", (module_id, seg_id, vid))
        c.commit()
        _trigger_backup()


def unassign_videos_from_module(video_ids: list[int]):
    """Remove videos from their module (set to NULL)."""
    with _conn() as c:
        for vid in video_ids:
            c.execute("UPDATE videos SET module_id = NULL WHERE id = ?", (vid,))
        c.commit()
        _trigger_backup()


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


def get_videos_by_segment(segment_id: int, user_id: int = None) -> list[dict]:
    with _conn() as c:
        if user_id is None:
            rows = c.execute("""
                SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                       m.name as module_name, m.icon as module_icon
                FROM videos v
                LEFT JOIN segments s ON v.segment_id = s.id
                LEFT JOIN modules m ON v.module_id = m.id
                WHERE v.segment_id = ?
                ORDER BY v.telegram_msg_id
            """, (segment_id,)).fetchall()
        else:
            user_row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
            is_admin = bool(user_row["is_admin"]) if user_row else False
            if is_admin:
                rows = c.execute("""
                    SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                           m.name as module_name, m.icon as module_icon
                    FROM videos v
                    LEFT JOIN segments s ON v.segment_id = s.id
                    LEFT JOIN modules m ON v.module_id = m.id
                    WHERE v.segment_id = ?
                    ORDER BY v.telegram_msg_id
                """, (segment_id,)).fetchall()
            else:
                rows = c.execute("""
                    SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                           m.name as module_name, m.icon as module_icon
                    FROM videos v
                    LEFT JOIN segments s ON v.segment_id = s.id
                    LEFT JOIN modules m ON v.module_id = m.id
                    WHERE v.segment_id = ? AND (v.is_restricted = 0 OR v.id IN (SELECT video_id FROM user_video_access WHERE user_id = ?))
                    ORDER BY v.telegram_msg_id
                """, (segment_id, user_id)).fetchall()
        return [dict(r) for r in rows]


def get_videos_by_module(module_id: int, user_id: int = None) -> list[dict]:
    with _conn() as c:
        if user_id is None:
            rows = c.execute("""
                SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                       m.name as module_name, m.icon as module_icon
                FROM videos v
                LEFT JOIN segments s ON v.segment_id = s.id
                LEFT JOIN modules m ON v.module_id = m.id
                WHERE v.module_id = ?
                ORDER BY v.telegram_msg_id
            """, (module_id,)).fetchall()
        else:
            user_row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
            is_admin = bool(user_row["is_admin"]) if user_row else False
            if is_admin:
                rows = c.execute("""
                    SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                           m.name as module_name, m.icon as module_icon
                    FROM videos v
                    LEFT JOIN segments s ON v.segment_id = s.id
                    LEFT JOIN modules m ON v.module_id = m.id
                    WHERE v.module_id = ?
                    ORDER BY v.telegram_msg_id
                """, (module_id,)).fetchall()
            else:
                rows = c.execute("""
                    SELECT v.*, s.name as segment_name, s.icon as segment_icon,
                           m.name as module_name, m.icon as module_icon
                    FROM videos v
                    LEFT JOIN segments s ON v.segment_id = s.id
                    LEFT JOIN modules m ON v.module_id = m.id
                    WHERE v.module_id = ? AND (v.is_restricted = 0 OR v.id IN (SELECT video_id FROM user_video_access WHERE user_id = ?))
                    ORDER BY v.telegram_msg_id
                """, (module_id, user_id)).fetchall()
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
            # DO NOT overwrite segment_id or module_id for existing videos!
            # The user might have customized them, or they were just restored from backup.
            c.execute("""
                UPDATE videos SET title=?, duration_sec=?, file_size=?,
                       mime_type=?, caption=?, synced_at=?
                WHERE telegram_msg_id=?
            """, (title, duration_sec, file_size, mime_type, caption, time.time(), telegram_msg_id))
            c.commit()
            return row["id"]
        cur = c.execute("""
            INSERT INTO videos (telegram_msg_id, title, segment_id, duration_sec, file_size, mime_type, caption)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (telegram_msg_id, title, segment_id, duration_sec, file_size, mime_type, caption))
        c.commit()
        return cur.lastrowid

import zlib

def upsert_youtube_video(youtube_id: str, title: str, segment_id: int, duration_sec: float = 0) -> int:
    with _conn() as c:
        row = c.execute("SELECT id FROM videos WHERE youtube_id = ?", (youtube_id,)).fetchone()
        if row:
            c.execute("""
                UPDATE videos SET title=?, duration_sec=?, synced_at=?
                WHERE youtube_id=?
            """, (title, duration_sec, time.time(), youtube_id))
            c.commit()
            return row["id"]
        
        # generate a unique negative integer for telegram_msg_id since it's required and unique
        fake_msg_id = -(zlib.crc32(youtube_id.encode('utf-8')) & 0xffffffff)
        while c.execute("SELECT id FROM videos WHERE telegram_msg_id = ?", (fake_msg_id,)).fetchone():
            fake_msg_id -= 1

        cur = c.execute("""
            INSERT INTO videos (telegram_msg_id, youtube_id, title, segment_id, duration_sec, mime_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (fake_msg_id, youtube_id, title, segment_id, duration_sec, 'video/youtube'))
        c.commit()
        return cur.lastrowid

# ── Access Control ────────────────────────────────────────

def get_user_segment_access(segment_id: int) -> list[int]:
    with _conn() as c:
        rows = c.execute("SELECT user_id FROM user_segment_access WHERE segment_id = ?", (segment_id,)).fetchall()
        return [r["user_id"] for r in rows]

def set_user_segment_access(segment_id: int, user_ids: list[int]):
    with _conn() as c:
        c.execute("DELETE FROM user_segment_access WHERE segment_id = ?", (segment_id,))
        for uid in user_ids:
            c.execute("INSERT INTO user_segment_access (user_id, segment_id) VALUES (?, ?)", (uid, segment_id))
        c.commit()

def get_user_module_access(module_id: int) -> list[int]:
    with _conn() as c:
        rows = c.execute("SELECT user_id FROM user_module_access WHERE module_id = ?", (module_id,)).fetchall()
        return [r["user_id"] for r in rows]

def set_user_module_access(module_id: int, user_ids: list[int]):
    with _conn() as c:
        c.execute("DELETE FROM user_module_access WHERE module_id = ?", (module_id,))
        for uid in user_ids:
            c.execute("INSERT INTO user_module_access (user_id, module_id) VALUES (?, ?)", (uid, module_id))
        c.commit()

def get_user_video_access(video_id: int) -> list[int]:
    with _conn() as c:
        rows = c.execute("SELECT user_id FROM user_video_access WHERE video_id = ?", (video_id,)).fetchall()
        return [r["user_id"] for r in rows]

def set_user_video_access(video_id: int, user_ids: list[int]):
    with _conn() as c:
        c.execute("DELETE FROM user_video_access WHERE video_id = ?", (video_id,))
        for uid in user_ids:
            c.execute("INSERT INTO user_video_access (user_id, video_id) VALUES (?, ?)", (uid, video_id))
        c.commit()

def update_video_restricted(video_id: int, is_restricted: bool):
    with _conn() as c:
        c.execute("UPDATE videos SET is_restricted = ? WHERE id = ?", (int(is_restricted), video_id))
        c.commit()
        _trigger_backup()

def is_user_admin(user_id: int) -> bool:
    with _conn() as c:
        row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        return bool(row["is_admin"]) if row else False

def get_user_subscriptions(user_id: int) -> list[int]:
    with _conn() as c:
        rows = c.execute("SELECT segment_id FROM user_segment_subscriptions WHERE user_id = ?", (user_id,)).fetchall()
        return [r["segment_id"] for r in rows]

def subscribe_to_segment(user_id: int, segment_id: int):
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO user_segment_subscriptions (user_id, segment_id) VALUES (?, ?)", (user_id, segment_id))
        c.commit()
        _trigger_backup()

def unsubscribe_from_segment(user_id: int, segment_id: int):
    with _conn() as c:
        c.execute("DELETE FROM user_segment_subscriptions WHERE user_id = ? AND segment_id = ?", (user_id, segment_id))
        c.commit()
        _trigger_backup()



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
        _trigger_backup()


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
        _trigger_backup()


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
        user_row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
        
        if is_admin:
            query = """
                SELECT 
                    s.id, s.name, s.icon, s.description, s.is_restricted,
                    COUNT(v.id) as total_videos,
                    COALESCE(SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END), 0) as completed_videos,
                    COALESCE(SUM(p.watch_seconds), 0) as watch_seconds
                FROM segments s
                LEFT JOIN videos v ON v.segment_id = s.id
                LEFT JOIN progress p ON p.video_id = v.id AND p.user_id = ?
                GROUP BY s.id
                ORDER BY s.sort_order, s.name
            """
            params = (user_id,)
        else:
            query = """
                SELECT 
                    s.id, s.name, s.icon, s.description, s.is_restricted,
                    COUNT(v.id) as total_videos,
                    COALESCE(SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END), 0) as completed_videos,
                    COALESCE(SUM(p.watch_seconds), 0) as watch_seconds
                FROM segments s
                LEFT JOIN videos v ON v.segment_id = s.id
                LEFT JOIN progress p ON p.video_id = v.id AND p.user_id = ?
                WHERE s.is_restricted = 0 OR s.id IN (SELECT segment_id FROM user_segment_access WHERE user_id = ?)
                GROUP BY s.id
                ORDER BY s.sort_order, s.name
            """
            params = (user_id, user_id)
            
        rows = c.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_last_viewed_segment_stats(user_id: int) -> Optional[dict]:
    """Returns the stats of the last watched segment."""
    with _conn() as c:
        row = c.execute("""
            SELECT v.segment_id 
            FROM progress p
            JOIN videos v ON p.video_id = v.id
            WHERE p.user_id = ?
            ORDER BY p.last_watched_at DESC
            LIMIT 1
        """, (user_id,)).fetchone()
        
        if not row:
            return None
            
        segment_id = row["segment_id"]
        
        stats = c.execute("""
            SELECT 
                s.id, s.name, s.icon,
                COUNT(v.id) as total_videos,
                COALESCE(SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END), 0) as completed_videos,
                COALESCE(SUM(p.watch_seconds), 0) as watch_seconds
            FROM segments s
            LEFT JOIN videos v ON v.segment_id = s.id
            LEFT JOIN progress p ON p.video_id = v.id AND p.user_id = ?
            WHERE s.id = ?
            GROUP BY s.id
        """, (user_id, segment_id)).fetchone()
        
        return dict(stats) if stats else None


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

def get_segment_leaderboard(segment_id: int, days: int = 7) -> list[dict]:
    """Get leaderboard of watch time for a specific segment over the last N days."""
    with _conn() as c:
        cutoff = time.time() - (days * 86400)
        rows = c.execute("""
            SELECT 
                u.username, u.display_name, 
                COALESCE(SUM(p.watch_seconds), 0) as total_watch_sec
            FROM users u
            JOIN progress p ON u.id = p.user_id
            JOIN videos v ON p.video_id = v.id
            WHERE p.last_watched_at >= ? AND v.segment_id = ?
            GROUP BY u.id
            HAVING total_watch_sec > 0
            ORDER BY total_watch_sec DESC
            LIMIT 10
        """, (cutoff, segment_id)).fetchall()
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
        _trigger_backup()


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
        _trigger_backup()


async def async_get_video_by_msg_id(msg_id: int) -> Optional[dict]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM videos WHERE telegram_msg_id = ?", (msg_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
