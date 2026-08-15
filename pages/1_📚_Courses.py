"""
📚 Courses — Browse course segments and videos.

Lists all segments with their videos, shows completion status (✅),
and allows clicking into the video player.
"""
import re
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import (
    init_db,
    get_all_segments,
    get_videos_by_segment,
    get_modules_by_segment,
    get_video_progress,
    get_segment_stats,
)

init_db()

st.set_page_config(page_title="Courses — EduStream", page_icon="📚", layout="wide")

# ── Check auth ────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in first.")
    st.page_link("Dashboard.py", label="Go to Login", icon="🔑")
    st.stop()

# ── Global Notification Hook ─────────────────────────────
from components.notifications import check_and_show_notifications
from components.messaging_sidebar import render_messaging_sidebar
check_and_show_notifications()
render_messaging_sidebar()

user_id = st.session_state["user_id"]

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer { visibility: hidden; }

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



# ── Sidebar filter ────────────────────────────────────────
segments = get_all_segments(user_id)
if not segments:
    st.info("No courses synced or accessible yet.")
    st.stop()

segment_names = ["All Segments"] + [f"{s['icon']} {s['name']}" for s in segments]
with st.sidebar:
    st.markdown("### 🔍 Filter")
    selected = st.selectbox("Segment", segment_names, label_visibility="collapsed")
    st.markdown("### 🔄 Sort By")
    sort_mode = st.selectbox(
        "Sort",
        ["Lecture Number", "Title (A-Z)", "Title (Z-A)", "Duration (Short→Long)", "Duration (Long→Short)"],
        label_visibility="collapsed",
    )

# Determine which segments to show
if selected == "All Segments":
    segments_to_show = segments
else:
    # Strip icon to find the segment name
    sel_name = selected.split(" ", 1)[1] if " " in selected else selected
    segments_to_show = [s for s in segments if s["name"] == sel_name]


# ── Natural sort helpers ─────────────────────────────────

_NUM_RE = re.compile(r"(\d+)")


def _natural_sort_key(title: str) -> tuple:
    """
    Extract all numbers from a title and return as a tuple for sorting.
    '148.Lecture 01 Vector.mkv' → (148, 1)
    '5.Lecture 10 Integrals.mkv' → (5, 10)
    Handles any naming pattern with embedded numbers.
    """
    nums = _NUM_RE.findall(title)
    return tuple(int(n) for n in nums) if nums else (float("inf"),)


def _sort_videos(videos: list[dict], mode: str) -> list[dict]:
    """Sort video list based on selected mode."""
    if mode == "Lecture Number":
        return sorted(videos, key=lambda v: _natural_sort_key(v["title"]))
    elif mode == "Title (A-Z)":
        return sorted(videos, key=lambda v: v["title"].lower())
    elif mode == "Title (Z-A)":
        return sorted(videos, key=lambda v: v["title"].lower(), reverse=True)
    elif mode == "Duration (Short→Long)":
        return sorted(videos, key=lambda v: v["duration_sec"])
    elif mode == "Duration (Long→Short)":
        return sorted(videos, key=lambda v: v["duration_sec"], reverse=True)
    return videos


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



# ── Helper: render a list of videos ──────────────────────
def render_video_list(video_list, prefix=""):
    """Render a list of video cards with play buttons."""
    for idx, video in enumerate(video_list, 1):
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
            if st.button("▶️ Play", key=f"play_{prefix}{video['id']}", use_container_width=True):
                st.session_state["current_video_id"] = video["id"]
                st.switch_page("pages/2_🎬_Player.py")


# ── Render segments & videos ─────────────────────────────
for seg in segments_to_show:
    videos = get_videos_by_segment(seg["id"])
    videos = _sort_videos(videos, sort_mode)
    if not videos:
        continue

    # Calculate segment progress
    completed_count = 0
    for v in videos:
        prog = get_video_progress(user_id, v["id"])
        if prog and prog["completed"]:
            completed_count += 1
    seg_pct = (completed_count / len(videos) * 100) if videos else 0

    with st.expander(f"{seg['icon']} {seg['name']} — {completed_count}/{len(videos)} completed · {seg_pct:.0f}% done", expanded=False):
        st.markdown(f"""
        <div class="progress-outer">
            <div class="progress-inner" style="width:{seg_pct}%;"></div>
        </div>
        """, unsafe_allow_html=True)

        # Get modules for this segment
        seg_modules = get_modules_by_segment(seg["id"], user_id)

        if seg_modules:
            # Group videos by module
            for mod in seg_modules:
                mod_videos = [v for v in videos if v.get("module_id") == mod["id"]]
                if not mod_videos:
                    continue

                mod_completed = sum(
                    1 for v in mod_videos
                    if (p := get_video_progress(user_id, v["id"])) and p["completed"]
                )
                mod_pct = (mod_completed / len(mod_videos) * 100) if mod_videos else 0

                with st.expander(f"{mod['icon']} {mod['name']}  —  {mod_completed}/{len(mod_videos)} done · {mod_pct:.0f}%", expanded=False):
                    render_video_list(mod_videos, prefix=f"m{mod['id']}_")

            # Show unassigned videos (no module)
            unassigned = [v for v in videos if not v.get("module_id")]
            if unassigned:
                with st.expander(f"📄 Other Lectures  —  {len(unassigned)} videos", expanded=False):
                    render_video_list(unassigned, prefix="unassigned_")
        else:
            # No modules — show all videos flat
            render_video_list(videos)
