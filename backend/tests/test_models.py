import pytest
import os
import sqlite3
import asyncio
from backend.models import (
    init_db,
    create_user,
    get_user_by_username,
    get_or_create_segment,
    upsert_video,
    get_all_videos,
)
from config import DB_PATH

@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_user_creation():
    user_id = create_user("testuser", "hashedpass", "Test User", "Test Inst")
    assert user_id > 0
    
    user = get_user_by_username("testuser")
    assert user is not None
    assert user["username"] == "testuser"
    assert user["display_name"] == "Test User"
    assert user["institute"] == "Test Inst"
    
def test_video_operations():
    segment_id = get_or_create_segment("Maths", "📐")
    assert segment_id > 0
    
    upsert_video(
        telegram_msg_id=123,
        title="Integration 101",
        segment_id=segment_id,
        duration_sec=300,
        file_size=1024,
        mime_type="video/mp4",
        caption="test"
    )
    
    videos = get_all_videos()
    assert len(videos) == 1
    assert videos[0]["title"] == "Integration 101"
