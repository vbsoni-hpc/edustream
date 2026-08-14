"""
🎬 Player — Video player page with embedded Video.js.

Streams video from Telegram via FastAPI's MTProto proxy.
Tracks watch progress and auto-marks completion.
"""
import re
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import API_BASE_URL
from backend.models import (
    init_db,
    get_video_by_id,
    get_video_progress,
    get_videos_by_segment,
    mark_video_complete,
    get_group_messages,
    send_message,
)
from components.video_player import render_video_player

init_db()

st.set_page_config(page_title="Player — EduStream", page_icon="🎬", layout="wide")

# ── Check auth ────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in first.")
    st.page_link("Dashboard.py", label="Go to Login", icon="🔑")
    st.stop()

from components.notifications import check_and_show_notifications
check_and_show_notifications()

user_id = st.session_state["user_id"]
jwt_token = st.session_state.get("jwt_token", "")

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer { visibility: hidden; }

    .player-header {
        margin-bottom: 16px;
    }
    .player-title {
        font-size: 24px;
        font-weight: 700;
        color: #FAFAFA;
        margin-bottom: 4px;
    }
    .player-breadcrumb {
        font-size: 13px;
        color: #9CA3AF;
    }
    .player-breadcrumb span {
        color: #a78bfa;
        font-weight: 600;
    }

    .nav-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.12);
        border-radius: 12px;
        padding: 14px 18px;
        transition: all 0.3s ease;
    }
    .nav-card:hover {
        border-color: rgba(108, 99, 255, 0.3);
    }
    .nav-label {
        font-size: 11px;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .nav-title {
        font-size: 14px;
        font-weight: 600;
        color: #FAFAFA;
    }

    .progress-section {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.12);
        border-radius: 14px;
        padding: 20px;
        margin-top: 16px;
    }
    .progress-outer {
        width: 100%;
        height: 6px;
        background: rgba(255,255,255,0.06);
        border-radius: 3px;
        overflow: hidden;
    }
    .progress-inner {
        height: 100%;
        border-radius: 3px;
        background: linear-gradient(90deg, #6C63FF, #a78bfa);
    }

    /* Chat styling */
    .msg-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.15);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .msg-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    .msg-sender {
        font-weight: 600;
        color: #a78bfa;
        font-size: 13px;
    }
    .msg-time {
        font-size: 11px;
        color: #9CA3AF;
    }
    .msg-content {
        color: #FAFAFA;
        font-size: 13px;
        line-height: 1.4;
        white-space: pre-wrap;
    }
    .chat-bubble-me {
        background: rgba(108, 99, 255, 0.2);
        border-right: 3px solid #6C63FF;
        margin-left: 10%;
        border-radius: 12px 0 12px 12px;
    }
    .chat-bubble-other {
        background: rgba(26, 29, 41, 0.8);
        border-left: 3px solid #a78bfa;
        margin-right: 10%;
        border-radius: 0 12px 12px 12px;
    }
</style>
""", unsafe_allow_html=True)


# ── Get current video ─────────────────────────────────────
video_id = st.session_state.get("current_video_id")

if not video_id:
    st.info("No video selected. Go to **📚 Courses** and pick a video to watch.")
    st.page_link("pages/1_📚_Courses.py", label="Browse Courses", icon="📚")
    st.stop()

video = get_video_by_id(video_id)
if not video:
    st.error("Video not found.")
    st.stop()

progress = get_video_progress(user_id, video_id)
last_position = progress["last_position"] if progress else 0
is_complete = progress["completed"] if progress else False


# ── Header ────────────────────────────────────────────────
st.markdown(f"""
<div class="player-header">
    <div class="player-breadcrumb">
        <span>{video.get('segment_icon', '📁')} {video.get('segment_name', 'General')}</span>
    </div>
    <div class="player-title">{video['title']}</div>
</div>
""", unsafe_allow_html=True)

if is_complete:
    st.success("✅ You've completed this video!")


# ── Video Player ──────────────────────────────────────────
render_video_player(
    video_msg_id=video["telegram_msg_id"],
    video_id=video["id"],
    jwt_token=jwt_token,
    api_base=API_BASE_URL,
    last_position=last_position,
    title=video["title"],
)


# ── Manual mark complete ──────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_complete, col_spacer = st.columns([1, 3])
with col_complete:
    if not is_complete:
        if st.button("✅ Mark as Complete", use_container_width=True):
            mark_video_complete(user_id, video_id)
            st.balloons()
            st.rerun()
    else:
        st.markdown("✅ **Completed**")


# ── Prev / Next navigation ───────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

# Get sibling videos in the same segment, sorted by lecture number
_NUM_RE = re.compile(r"(\d+)")
def _natural_key(t):
    nums = _NUM_RE.findall(t)
    return tuple(int(n) for n in nums) if nums else (float("inf"),)

segment_videos = get_videos_by_segment(video.get("segment_id")) if video.get("segment_id") else []
segment_videos = sorted(segment_videos, key=lambda v: _natural_key(v["title"]))
current_idx = next((i for i, v in enumerate(segment_videos) if v["id"] == video_id), -1)

col_prev, col_info, col_next = st.columns([1, 2, 1])

with col_prev:
    if current_idx > 0:
        prev_video = segment_videos[current_idx - 1]
        st.markdown(f"""
        <div class="nav-card">
            <div class="nav-label">← Previous</div>
            <div class="nav-title">{prev_video['title']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⬅ Previous", key="prev_btn", use_container_width=True):
            st.session_state["current_video_id"] = prev_video["id"]
            st.rerun()

with col_info:
    # Segment progress
    if segment_videos:
        seg_completed = sum(
            1 for v in segment_videos
            if (p := get_video_progress(user_id, v["id"])) and p["completed"]
        )
        seg_pct = seg_completed / len(segment_videos) * 100
        st.markdown(f"""
        <div class="progress-section">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="font-size:13px; color:#9CA3AF;">
                    {video.get('segment_icon', '📁')} {video.get('segment_name', '')} Progress
                </span>
                <span style="font-size:13px; font-weight:700; color:#a78bfa;">
                    {seg_completed}/{len(segment_videos)} · {seg_pct:.0f}%
                </span>
            </div>
            <div class="progress-outer">
                <div class="progress-inner" style="width:{seg_pct}%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_next:
    if current_idx >= 0 and current_idx < len(segment_videos) - 1:
        next_video = segment_videos[current_idx + 1]
        st.markdown(f"""
        <div class="nav-card">
            <div class="nav-label">Next →</div>
            <div class="nav-title">{next_video['title']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Next ➡", key="next_btn", use_container_width=True):
            st.session_state["current_video_id"] = next_video["id"]
            st.rerun()

# ── Global Chat ───────────────────────────────────────────
st.markdown("---")
st.markdown("### 🌍 Course Discussion")

from datetime import datetime

# Form for new messages
with st.form("player_chat_form", clear_on_submit=True):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        new_group_msg = st.text_input("Message", placeholder="Chat with other students here...", label_visibility="collapsed")
    with col_btn:
        submitted = st.form_submit_button("Send 🚀", use_container_width=True)
        if submitted and new_group_msg.strip():
            send_message(user_id, 0, new_group_msg.strip())
            st.rerun()

# Display group messages (newest at bottom)
group_msgs = get_group_messages(15)  # only show last 15 in player to save space
if not group_msgs:
    st.info("No messages yet. Say hi!")
else:
    for msg in group_msgs:
        is_me = (msg['sender_id'] == user_id)
        msg_time = datetime.fromtimestamp(msg["created_at"]).strftime("%H:%M")
        bubble_class = "chat-bubble-me" if is_me else "chat-bubble-other"
        sender_name = "You" if is_me else msg['sender_name']
        
        st.markdown(f"""
        <div class="msg-card {bubble_class}">
            <div class="msg-header">
                <span class="msg-sender">👤 {sender_name}</span>
                <span class="msg-time">{msg_time}</span>
            </div>
            <div class="msg-content">{msg['content']}</div>
        </div>
        """, unsafe_allow_html=True)
