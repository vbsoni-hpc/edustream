"""
📚 Courses — Browse course segments and videos.

Lists all segments with their videos, shows completion status (✅),
and allows clicking into the video player.
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import (
    init_db,
    get_all_segments,
    get_videos_by_segment,
    get_video_progress,
    get_segment_stats,
)

init_db()

st.set_page_config(page_title="Courses — EduStream", page_icon="📚", layout="wide")

# ── Check auth ────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in first.")
    st.page_link("app.py", label="Go to Login", icon="🔑")
    st.stop()

user_id = st.session_state["user_id"]

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }

    .video-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.1);
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .video-card:hover {
        border-color: rgba(108, 99, 255, 0.4);
        transform: translateX(4px);
        box-shadow: 0 4px 20px rgba(108, 99, 255, 0.1);
    }
    .video-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .video-index {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: rgba(108, 99, 255, 0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 14px;
        color: #a78bfa;
        flex-shrink: 0;
    }
    .video-index.completed {
        background: rgba(52, 211, 153, 0.15);
        color: #34D399;
    }
    .video-title {
        font-size: 15px;
        font-weight: 600;
        color: #FAFAFA;
    }
    .video-meta {
        font-size: 12px;
        color: #6B7280;
        margin-top: 2px;
    }
    .video-right {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .video-duration {
        font-size: 13px;
        color: #9CA3AF;
        font-weight: 500;
    }
    .watch-badge {
        background: rgba(108, 99, 255, 0.15);
        color: #a78bfa;
        font-size: 11px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
    }
    .watch-badge.done {
        background: rgba(52, 211, 153, 0.15);
        color: #34D399;
    }

    .segment-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 6px;
    }
    .segment-header-icon { font-size: 28px; }
    .segment-header-title {
        font-size: 22px;
        font-weight: 700;
        color: #FAFAFA;
    }
    .segment-progress-text {
        font-size: 13px;
        color: #9CA3AF;
        margin-bottom: 16px;
    }
    .progress-outer {
        width: 100%;
        height: 6px;
        background: rgba(255,255,255,0.06);
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 20px;
    }
    .progress-inner {
        height: 100%;
        border-radius: 3px;
        background: linear-gradient(90deg, #6C63FF, #a78bfa);
        transition: width 0.6s ease;
    }
</style>
""", unsafe_allow_html=True)


# ── Page header ───────────────────────────────────────────
st.markdown("# 📚 Courses")
st.markdown("Browse your course segments and track progress.")
st.markdown("---")

# ── Sidebar filter ────────────────────────────────────────
segments = get_all_segments()
if not segments:
    st.info("No courses synced yet. Go to **⚙️ Admin** to sync your Telegram channel.")
    st.stop()

segment_names = ["All Segments"] + [f"{s['icon']} {s['name']}" for s in segments]
with st.sidebar:
    st.markdown("### 🔍 Filter")
    selected = st.selectbox("Segment", segment_names, label_visibility="collapsed")

# Determine which segments to show
if selected == "All Segments":
    segments_to_show = segments
else:
    # Strip icon to find the segment name
    sel_name = selected.split(" ", 1)[1] if " " in selected else selected
    segments_to_show = [s for s in segments if s["name"] == sel_name]


# ── Helper: format duration ──────────────────────────────
def fmt_duration(sec: float) -> str:
    if sec <= 0:
        return "--:--"
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ── Render segments & videos ─────────────────────────────
for seg in segments_to_show:
    videos = get_videos_by_segment(seg["id"])
    if not videos:
        continue

    # Calculate segment progress
    completed_count = 0
    for v in videos:
        prog = get_video_progress(user_id, v["id"])
        if prog and prog["completed"]:
            completed_count += 1
    seg_pct = (completed_count / len(videos) * 100) if videos else 0

    # Segment header
    st.markdown(f"""
    <div class="segment-header">
        <span class="segment-header-icon">{seg['icon']}</span>
        <span class="segment-header-title">{seg['name']}</span>
    </div>
    <div class="segment-progress-text">
        {completed_count}/{len(videos)} completed · {seg_pct:.0f}% done
    </div>
    <div class="progress-outer">
        <div class="progress-inner" style="width:{seg_pct}%;"></div>
    </div>
    """, unsafe_allow_html=True)

    # Video list
    for idx, video in enumerate(videos, 1):
        prog = get_video_progress(user_id, video["id"])
        is_complete = prog and prog["completed"]
        watch_sec = prog["watch_seconds"] if prog else 0

        index_class = "video-index completed" if is_complete else "video-index"
        index_text = "✓" if is_complete else str(idx)
        badge_class = "watch-badge done" if is_complete else "watch-badge"
        badge_text = "✅ Done" if is_complete else f"▶ {fmt_duration(watch_sec)} watched"

        st.markdown(f"""
        <div class="video-card">
            <div class="video-left">
                <div class="{index_class}">{index_text}</div>
                <div>
                    <div class="video-title">{video['title']}</div>
                    <div class="video-meta">Duration: {fmt_duration(video['duration_sec'])}</div>
                </div>
            </div>
            <div class="video-right">
                <span class="{badge_class}">{badge_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Play button — Streamlit native for navigation
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("▶️ Play", key=f"play_{video['id']}", use_container_width=True):
                st.session_state["current_video_id"] = video["id"]
                st.switch_page("pages/2_🎬_Player.py")

    st.markdown("---")
