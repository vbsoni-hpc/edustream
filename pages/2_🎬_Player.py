"""
🎬 Player — Video player page with embedded Video.js.

Streams video from Telegram via FastAPI's MTProto proxy.
Tracks watch progress and auto-marks completion.
"""
import re
import streamlit as st
import sys
from pathlib import Path

try:
    import g4f
except ImportError:
    g4f = None


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
from components.messaging_sidebar import render_messaging_sidebar
check_and_show_notifications()
render_messaging_sidebar()

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
is_complete = progress["completed"] if progress else False

# Store the initial start position in session state so it doesn't change on st.rerun
if st.session_state.get("player_video_id") != video_id:
    st.session_state["player_start_pos"] = progress["last_position"] if progress else 0
    st.session_state["player_video_id"] = video_id

last_position = st.session_state["player_start_pos"]


# ── Header ────────────────────────────────────────────────
st.markdown(f"""
<div class="player-header">
    <div class="player-breadcrumb">
        <span>{video.get('segment_icon', '📁')} {video.get('segment_name') or 'Uncategorized'}</span>
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

# ── Ask AI ────────────────────────────────────────────────
if "ai_chat_history" not in st.session_state:
    st.session_state["ai_chat_history"] = {}

@st.fragment
def render_ask_ai_section(video_id, video):
    video_chat_history = st.session_state["ai_chat_history"].setdefault(video_id, [])

    with st.container(height=350):
        if not video_chat_history:
            st.caption("Got a question about this lecture? Ask the AI!")
        else:
            for msg in video_chat_history:
                if msg["role"] == "user":
                    st.markdown(f"**👤 You:** {msg['content']}")
                else:
                    st.markdown(f"**🤖 AI:** {msg['content']}")
                
    with st.form("ask_ai_form", clear_on_submit=True):
        ai_q = st.text_input("Ask something...", placeholder="e.g. Summarize this video's topic", label_visibility="collapsed")
        if st.form_submit_button("Ask 🚀", use_container_width=True):
            if ai_q.strip():
                video_chat_history.append({"role": "user", "content": ai_q.strip()})
                if True:
                    with st.spinner("AI is thinking..."):
                        try:
                            # Build context
                            messages = [{"role": "system", "content": f"You are a helpful AI tutor. The student is currently watching a video lecture titled '{video['title']}'. Help answer their questions and if asked explain it in simple and intuitive manner and always explaining through first principles.(always reply in english)"}]
                            messages.extend(video_chat_history[-5:])
                            
                            from g4f.client import Client
                            client = Client()
                            api_res = client.chat.completions.create(
                                model="gpt-4",
                                messages=messages,
                            )
                            answer = api_res.choices[0].message.content
                            video_chat_history.append({"role": "assistant", "content": answer})
                        except Exception as e:
                            st.error(f"Failed to get response: {e}")
                            video_chat_history.pop() # remove the user message if it failed
                try:
                    st.rerun(scope="fragment")
                except TypeError:
                    st.rerun()

render_ask_ai_section(video_id, video)


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

col_prev, col_next = st.columns([1, 1])

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


