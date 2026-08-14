"""
⚙️ Admin — Telegram sync, segment/module management, and video organization.

Allows syncing the Telegram channel, creating modules within segments,
and bulk-assigning videos to modules via select-and-drop.
"""
import re
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
    get_all_modules,
    get_modules_by_segment,
    get_or_create_segment,
    get_or_create_module,
    get_videos_by_segment,
    update_segment,
    update_module,
    delete_module,
    move_videos_to_module,
    unassign_videos_from_module,
    upsert_video,
    add_notice,
)

init_db()

st.set_page_config(page_title="Admin — EduStream", page_icon="⚙️", layout="wide")

# ── Check auth ────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in first.")
    st.page_link("Dashboard.py", label="Go to Login", icon="🔑")
    st.stop()

if st.session_state.get("username") != "vbsoni":
    st.error("🔒 Access Denied. You must be the administrator (vbsoni) to view this page.")
    st.stop()

# ── Global Notification Hook ─────────────────────────────
from components.notifications import check_and_show_notifications
from components.messaging_sidebar import render_messaging_sidebar
check_and_show_notifications()
render_messaging_sidebar()

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


st.markdown("# ⚙️ Admin Panel")
st.markdown("Manage Telegram sync, segments, modules, and video organization.")
st.markdown("---")

# ═══════════════════════════════════════════════════════════
#  Notices
# ═══════════════════════════════════════════════════════════
st.markdown("### 📢 Post Notice")
st.markdown("Broadcast an important message to all students on the dashboard.")
with st.form("notice_form", clear_on_submit=True):
    notice_text = st.text_area("Notice Content", placeholder="Type your notice here...")
    submitted = st.form_submit_button("Post Notice", type="primary")
    if submitted:
        if notice_text.strip():
            add_notice(notice_text.strip())
            st.success("✅ Notice posted successfully!")
        else:
            st.error("Notice cannot be empty.")
st.markdown("---")

# ── Natural sort helper ──────────────────────────────────
_NUM_RE = re.compile(r"(\d+)")
def _natural_key(title):
    nums = _NUM_RE.findall(title)
    return tuple(int(n) for n in nums) if nums else (float("inf"),)


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
                # Use internal FastAPI URL directly for Python requests
                INTERNAL_API_URL = "http://127.0.0.1:8000"
                resp = requests.post(f"{INTERNAL_API_URL}/api/sync", timeout=120)
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
    all_modules = get_all_modules()
    st.info(f"📊 **{len(all_videos)}** videos · **{len(all_segments)}** segments · **{len(all_modules)}** modules")

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
#  Manage Modules (within segments)
# ═══════════════════════════════════════════════════════════

st.markdown("### 📂 Manage Modules")
st.markdown("Modules are sub-folders within segments to organize related lectures together.")

if not segments:
    st.info("Create segments first before adding modules.")
else:
    # Show existing modules grouped by segment
    modules = get_all_modules()
    if modules:
        for mod in modules:
            seg_label = f"{mod.get('segment_icon', '📁')} {mod.get('segment_name', '?')}"
            with st.expander(f"{mod['icon']} {mod['name']}  ·  {seg_label}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    mod_name = st.text_input("Name", value=mod["name"], key=f"mod_name_{mod['id']}")
                with col2:
                    mod_icon = st.text_input("Icon", value=mod["icon"], key=f"mod_icon_{mod['id']}")
                with col3:
                    mod_order = st.number_input("Sort Order", value=mod["sort_order"], key=f"mod_order_{mod['id']}")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Save", key=f"mod_save_{mod['id']}"):
                        update_module(mod["id"], name=mod_name, icon=mod_icon, sort_order=int(mod_order))
                        st.success(f"Updated module: {mod_icon} {mod_name}")
                        st.rerun()
                with c2:
                    if st.button("🗑️ Delete", key=f"mod_del_{mod['id']}"):
                        delete_module(mod["id"])
                        st.success(f"Deleted module: {mod['name']} (videos unassigned)")
                        st.rerun()
    else:
        st.info("No modules yet. Create one below.")

    # ── Add new module ──
    st.markdown("#### ➕ Add New Module")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        mod_seg_options = {f"{s['icon']} {s['name']}": s["id"] for s in segments}
        mod_parent = st.selectbox("Parent Segment", list(mod_seg_options.keys()), key="new_mod_parent")
    with col_m2:
        new_mod_name = st.text_input("Module Name", key="new_mod_name", placeholder="e.g. Mathematical Methods")
    with col_m3:
        new_mod_icon = st.text_input("Module Icon", key="new_mod_icon", value="📂", placeholder="📂")

    if st.button("➕ Add Module"):
        if new_mod_name and mod_parent:
            parent_id = mod_seg_options[mod_parent]
            mod_id = get_or_create_module(new_mod_name, parent_id, new_mod_icon or "📂")
            st.success(f"Created module: {new_mod_icon} {new_mod_name} (ID: {mod_id})")
            st.rerun()
        else:
            st.warning("Please fill in both segment and module name.")

st.markdown("---")


# ═══════════════════════════════════════════════════════════
#  Assign Videos to Modules (Select & Drop)
# ═══════════════════════════════════════════════════════════

st.markdown("### 🎯 Assign Videos to Modules")
st.markdown("Select videos and move them into a module folder.")

modules = get_all_modules()
videos = get_all_videos()

if not modules:
    st.info("Create modules first to start organizing videos.")
elif not videos:
    st.info("No videos synced yet.")
else:
    # Filter by segment
    seg_filter_options = ["All Segments"] + [f"{s['icon']} {s['name']}" for s in segments]
    seg_filter = st.selectbox("Filter by Segment", seg_filter_options, key="assign_seg_filter")

    if seg_filter == "All Segments":
        filtered_videos = videos
    else:
        sel_name = seg_filter.split(" ", 1)[1] if " " in seg_filter else seg_filter
        filtered_videos = [v for v in videos if v.get("segment_name") == sel_name]

    # Sort videos naturally
    filtered_videos = sorted(filtered_videos, key=lambda v: _natural_key(v["title"]))

    # Module filter: show current module assignment
    mod_filter_options = ["All", "Unassigned Only"] + [f"{m['icon']} {m['name']}" for m in modules]
    mod_filter = st.selectbox("Show", mod_filter_options, key="mod_filter_view")

    if mod_filter == "Unassigned Only":
        filtered_videos = [v for v in filtered_videos if not v.get("module_id")]
    elif mod_filter not in ["All", "Unassigned Only"]:
        mod_name = mod_filter.split(" ", 1)[1] if " " in mod_filter else mod_filter
        filtered_videos = [v for v in filtered_videos if v.get("module_name") == mod_name]

    st.markdown(f"**{len(filtered_videos)}** videos shown")

    # Checkboxes for selection
    selected_ids = []
    for v in filtered_videos:
        mod_label = f"📂 {v['module_name']}" if v.get("module_name") else "⬜ Unassigned"
        label = f"**{v['title']}**  ·  {mod_label}"
        if st.checkbox(label, key=f"sel_{v['id']}"):
            selected_ids.append(v["id"])

    if selected_ids:
        st.markdown(f"**{len(selected_ids)} videos selected**")

        # Target module selector
        mod_options = {f"{m['icon']} {m['name']} ({m.get('segment_name', '?')})": m["id"] for m in modules}
        target_options = ["⬜ Unassign (remove from module)"] + list(mod_options.keys())
        target = st.selectbox("Move to:", target_options, key="move_target")

        if st.button("📦 Move Selected Videos", type="primary", use_container_width=True):
            if target == "⬜ Unassign (remove from module)":
                unassign_videos_from_module(selected_ids)
                st.success(f"Unassigned {len(selected_ids)} videos from their modules.")
            else:
                target_id = mod_options[target]
                move_videos_to_module(selected_ids, target_id)
                st.success(f"Moved {len(selected_ids)} videos to {target}")
            st.rerun()

st.markdown("---")


# ═══════════════════════════════════════════════════════════
#  Video Catalog (quick view)
# ═══════════════════════════════════════════════════════════

st.markdown("### 🎬 Video Catalog")

videos = get_all_videos()
if not videos:
    st.info("No videos synced yet.")
else:
    st.markdown(f"**{len(videos)}** videos in the catalog:")

    for v in videos:
        seg_display = f"{v.get('segment_icon', '📁')} {v.get('segment_name', 'Unassigned')}"
        mod_display = f" → {v.get('module_icon', '📂')} {v.get('module_name')}" if v.get("module_name") else ""
        dur_min = v["duration_sec"] / 60 if v["duration_sec"] else 0
        size_mb = v["file_size"] / (1024 * 1024) if v["file_size"] else 0

        with st.expander(f"#{v['telegram_msg_id']} — {v['title']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Segment:** {seg_display}")
                st.markdown(f"**Module:** {mod_display or '—'}")
                st.markdown(f"**Duration:** {dur_min:.1f} min")
            with col2:
                st.markdown(f"**Size:** {size_mb:.1f} MB")
                st.markdown(f"**Telegram Msg ID:** {v['telegram_msg_id']}")
                if v.get("caption"):
                    st.markdown(f"**Caption:** {v['caption'][:200]}")
