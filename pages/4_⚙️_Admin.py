"""
⚙️ Admin — Telegram sync and segment management.

Allows syncing the Telegram channel, editing segments, and reassigning videos.
"""
import streamlit as st
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import API_BASE_URL, DEFAULT_SEGMENT_ICONS
from backend.models import (
    init_db,
    get_all_segments,
    get_all_videos,
    get_or_create_segment,
    update_segment,
    upsert_video,
)

init_db()

st.set_page_config(page_title="Admin — EduStream", page_icon="⚙️", layout="wide")

# ── Check auth ────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in first.")
    st.page_link("app.py", label="Go to Login", icon="🔑")
    st.stop()

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


st.markdown("# ⚙️ Admin Panel")
st.markdown("Manage Telegram sync and course segments.")
st.markdown("---")


# ═══════════════════════════════════════════════════════════
#  Telegram Sync
# ═══════════════════════════════════════════════════════════

st.markdown("### 📡 Telegram Channel Sync")
st.markdown("Pull latest videos from your Telegram channel into the course catalog.")

col_sync, col_status = st.columns([1, 2])

with col_sync:
    if st.button("🔄 Sync Now", use_container_width=True, type="primary"):
        with st.spinner("Syncing from Telegram... This may take a moment."):
            try:
                resp = requests.post(f"{API_BASE_URL}/api/sync", timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"✅ Synced **{data.get('synced', 0)}** videos from Telegram!")
                    st.rerun()
                else:
                    st.error(f"Sync failed: {resp.text}")
            except requests.ConnectionError:
                st.error(
                    "⚠️ Cannot connect to the FastAPI backend. "
                    "Make sure you've started both servers with `python start.py`"
                )
            except Exception as e:
                st.error(f"Sync error: {e}")

with col_status:
    all_videos = get_all_videos()
    all_segments = get_all_segments()
    st.info(f"📊 **{len(all_videos)}** videos synced across **{len(all_segments)}** segments")

st.markdown("---")


# ═══════════════════════════════════════════════════════════
#  Manage Segments
# ═══════════════════════════════════════════════════════════

st.markdown("### 📁 Manage Segments")

segments = get_all_segments()

if not segments:
    st.info("No segments yet. Sync your Telegram channel first, or add one manually below.")
else:
    for seg in segments:
        with st.expander(f"{seg['icon']} {seg['name']} (ID: {seg['id']})"):
            col1, col2, col3 = st.columns(3)
            with col1:
                new_name = st.text_input("Name", value=seg["name"], key=f"seg_name_{seg['id']}")
            with col2:
                new_icon = st.text_input("Icon", value=seg["icon"], key=f"seg_icon_{seg['id']}")
            with col3:
                new_order = st.number_input("Sort Order", value=seg["sort_order"], key=f"seg_order_{seg['id']}")

            if st.button("💾 Save", key=f"seg_save_{seg['id']}"):
                update_segment(seg["id"], name=new_name, icon=new_icon, sort_order=int(new_order))
                st.success(f"Updated segment: {new_icon} {new_name}")
                st.rerun()

# ── Add new segment ──
st.markdown("#### ➕ Add New Segment")
col_new1, col_new2 = st.columns(2)
with col_new1:
    new_seg_name = st.text_input("Segment Name", key="new_seg_name", placeholder="e.g. Physics")
with col_new2:
    new_seg_icon = st.text_input("Icon (emoji)", key="new_seg_icon", value="📁", placeholder="📁")

if st.button("➕ Add Segment"):
    if new_seg_name:
        seg_id = get_or_create_segment(new_seg_name, new_seg_icon or "📁")
        st.success(f"Created segment: {new_seg_icon} {new_seg_name} (ID: {seg_id})")
        st.rerun()
    else:
        st.warning("Please enter a segment name.")

st.markdown("---")


# ═══════════════════════════════════════════════════════════
#  Video Catalog
# ═══════════════════════════════════════════════════════════

st.markdown("### 🎬 Video Catalog")

videos = get_all_videos()
if not videos:
    st.info("No videos synced yet.")
else:
    # Show as a table
    st.markdown(f"**{len(videos)}** videos in the catalog:")

    for v in videos:
        seg_display = f"{v.get('segment_icon', '📁')} {v.get('segment_name', 'Unassigned')}"
        dur_min = v["duration_sec"] / 60 if v["duration_sec"] else 0
        size_mb = v["file_size"] / (1024 * 1024) if v["file_size"] else 0

        with st.expander(f"#{v['telegram_msg_id']} — {v['title']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Segment:** {seg_display}")
                st.markdown(f"**Duration:** {dur_min:.1f} min")
                st.markdown(f"**Size:** {size_mb:.1f} MB")
            with col2:
                st.markdown(f"**MIME:** {v['mime_type']}")
                st.markdown(f"**Telegram Msg ID:** {v['telegram_msg_id']}")
                if v.get("caption"):
                    st.markdown(f"**Caption:** {v['caption'][:200]}")

            # Reassign segment
            seg_options = {f"{s['icon']} {s['name']}": s["id"] for s in segments}
            if seg_options:
                current_seg = f"{v.get('segment_icon', '📁')} {v.get('segment_name', 'General')}"
                new_seg = st.selectbox(
                    "Reassign to segment",
                    list(seg_options.keys()),
                    index=list(seg_options.keys()).index(current_seg) if current_seg in seg_options else 0,
                    key=f"reassign_{v['id']}",
                )
                if st.button("Move", key=f"move_{v['id']}"):
                    upsert_video(
                        telegram_msg_id=v["telegram_msg_id"],
                        title=v["title"],
                        segment_id=seg_options[new_seg],
                        duration_sec=v["duration_sec"],
                        file_size=v["file_size"],
                        mime_type=v["mime_type"],
                        caption=v.get("caption", ""),
                    )
                    st.success(f"Moved '{v['title']}' to {new_seg}")
                    st.rerun()
