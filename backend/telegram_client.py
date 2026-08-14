"""
Telethon MTProto client wrapper for Telegram channel access.

Handles connection management, channel syncing, and video streaming.
"""
import asyncio
import re
import logging
from typing import AsyncIterator, Optional

from telethon import TelegramClient
from telethon.tl.types import (
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    MessageMediaDocument,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_CHANNEL,
    SESSION_NAME,
    DEFAULT_SEGMENT_ICONS,
)

logger = logging.getLogger(__name__)

# ── Singleton client ──────────────────────────────────────
_client: Optional[TelegramClient] = None


async def get_client() -> TelegramClient:
    """Get or create the Telethon client. Connects if not already connected."""
    global _client
    if _client is None:
        _client = TelegramClient(SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    if not _client.is_connected():
        await _client.start()
    return _client


async def disconnect():
    """Gracefully disconnect the client."""
    global _client
    if _client and _client.is_connected():
        await _client.disconnect()
    _client = None


# ── Hashtag parsing ───────────────────────────────────────

_HASHTAG_RE = re.compile(r"#(\w+)")


def extract_segment_from_caption(caption: str) -> str:
    """
    Extract segment name from caption hashtags.
    e.g. '#Math Lecture 1 on derivatives' → 'Math'
    Falls back to 'General' if no hashtag found.
    """
    if not caption:
        return "General"
    match = _HASHTAG_RE.search(caption)
    return match.group(1) if match else "General"


def extract_title_from_caption(caption: str) -> str:
    """
    Clean caption to create a video title.
    Removes hashtags and strips whitespace.
    """
    if not caption:
        return "Untitled"
    title = _HASHTAG_RE.sub("", caption).strip()
    return title if title else "Untitled"


# ── Channel sync ─────────────────────────────────────────

async def sync_channel(channel: str = None) -> list[dict]:
    """
    Iterate over all messages in the channel and return video metadata.
    
    Returns list of dicts:
        {telegram_msg_id, title, segment, duration_sec, file_size, mime_type, caption}
    """
    client = await get_client()
    channel = channel or TELEGRAM_CHANNEL

    if not channel:
        raise ValueError("No Telegram channel configured. Set TELEGRAM_CHANNEL in .env")

    videos = []
    logger.info(f"Syncing channel: {channel}")

    async for message in client.iter_messages(channel):
        if not message.media or not isinstance(message.media, MessageMediaDocument):
            continue

        doc = message.media.document
        if not doc:
            continue

        mime = doc.mime_type or ""
        if not mime.startswith("video/"):
            continue

        # Extract metadata from document attributes
        duration = 0
        filename = ""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeVideo):
                duration = attr.duration or 0
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name or ""

        caption = message.text or ""
        segment = extract_segment_from_caption(caption)
        title = extract_title_from_caption(caption)

        # If title is still empty, use filename
        if title == "Untitled" and filename:
            title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

        videos.append({
            "telegram_msg_id": message.id,
            "title": title,
            "segment": segment,
            "duration_sec": duration,
            "file_size": doc.size or 0,
            "mime_type": mime,
            "caption": caption,
        })

    logger.info(f"Found {len(videos)} videos in channel")
    return videos


# ── Video streaming ───────────────────────────────────────

async def get_message_media(msg_id: int, channel: str = None):
    """Fetch a specific message by ID to get its media for streaming."""
    client = await get_client()
    channel = channel or TELEGRAM_CHANNEL
    message = await client.get_messages(channel, ids=msg_id)
    if message and message.media:
        return message
    return None


async def stream_video_chunks(
    msg_id: int,
    offset: int = 0,
    chunk_size: int = 1024 * 1024,  # 1 MB chunks
    limit: int = 0,
    channel: str = None,
) -> AsyncIterator[bytes]:
    """
    Stream video bytes from Telegram using MTProto iter_download.
    
    Yields chunks starting from `offset`. If `limit` > 0, stops after
    yielding `limit` bytes total.
    """
    client = await get_client()
    message = await get_message_media(msg_id, channel)

    if not message:
        raise ValueError(f"Message {msg_id} not found or has no media")

    sent = 0
    async for chunk in client.iter_download(
        message.media,
        offset=offset,
        chunk_size=chunk_size,
    ):
        if limit > 0:
            remaining = limit - sent
            if remaining <= 0:
                break
            if len(chunk) > remaining:
                yield chunk[:remaining]
                break
            yield chunk
            sent += len(chunk)
        else:
            yield chunk


async def get_file_size(msg_id: int, channel: str = None) -> int:
    """Get the file size of a video message."""
    message = await get_message_media(msg_id, channel)
    if message and message.media and message.media.document:
        return message.media.document.size
    return 0
