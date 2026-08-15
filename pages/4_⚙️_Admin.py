"""
⚙️ Admin — Telegram sync, segment/module management, and video organization.

Allows syncing the Telegram channel, creating modules within segments,
and bulk-assigning videos to modules via select-and-drop.
"""
import re
import streamlit as st
import requests
import sys
import pandas as pd
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
    get_all_notices,
    delete_notice,
    get_all_users_admin,
    update_user_admin,
    delete_user_admin,
    delete_all_messages,
    get_user_segment_access,
    set_user_segment_access,
    get_user_module_access,
    set_user_module_access,
    get_user_video_access,
    set_user_video_access,
    update_video_restricted,
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
st.markdown("### 📢 Manage Notices")
st.markdown("Broadcast an important message to all students on the dashboard.")
with st.form("notice_form", clear_on_submit=True):
    notice_text = st.text_area("Notice Content", placeholder="Type your notice here...")
    submitted = st.form_submit_button("Post Notice", type="primary")
    if submitted:
        if notice_text.strip():
            add_notice(notice_text.strip())
            st.success("✅ Notice posted successfully!")
            st.rerun()
        else:
            st.error("Notice cannot be empty.")

st.markdown("#### Existing Notices")
all_notices = get_all_notices()
if not all_notices:
    st.caption("No notices posted.")
else:
    for notice in all_notices:
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.info(notice["content"])
            with col2:
                if st.button("🗑️ Delete", key=f"del_notice_{notice['id']}", use_container_width=True):
                    delete_notice(notice['id'])
                    st.rerun()

st.markdown("---")

# ═══════════════════════════════════════════════════════════
#  User Management
# ═══════════════════════════════════════════════════════════
st.markdown("### 👥 User Management")
st.markdown("View and edit user records. You can change usernames and display names, or delete users. **Click 'Save User Changes' to apply.**")

users = get_all_users_admin()
df = pd.DataFrame(users)

if not df.empty:
    df = df[['id', 'username', 'display_name', 'created_at', 'last_active']]
    df['created_at'] = pd.to_datetime(df['created_at'], unit='s').dt.strftime('%Y-%m-%d %H:%M')
    df['last_active'] = pd.to_datetime(df['last_active'], unit='s').dt.strftime('%Y-%m-%d %H:%M')
    
    edited_df = st.data_editor(
        df,
        disabled=["id", "created_at", "last_active"],
        num_rows="dynamic",
        use_container_width=True,
        key="user_db_editor"
    )

    if st.button("💾 Save User Changes", type="primary"):
        changes = st.session_state.get("user_db_editor", {})
        
        # Apply edits
        for row_idx_str, edits in changes.get("edited_rows", {}).items():
            row_idx = int(row_idx_str)
            user_id = df.iloc[row_idx]["id"]
            current = df.iloc[row_idx]
            new_username = edits.get("username", current["username"])
            new_display = edits.get("display_name", current["display_name"])
            update_user_admin(int(user_id), new_username, new_display)
            
        # Apply deletions
        for row_idx in changes.get("deleted_rows", []):
            user_id = df.iloc[row_idx]["id"]
            delete_user_admin(int(user_id))
            
        if changes.get("added_rows"):
            st.warning("Cannot add users directly here since passwords are required. Please use the registration page.")
            
        st.success("✅ User database updated successfully!")
        st.rerun()
else:
    st.info("No users found.")

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

            col4, col5 = st.columns([0.8, 0.2])
            with col4:
                new_desc = st.text_input("Description", value=seg.get("description", ""), key=f"seg_desc_{seg['id']}")
            with col5:
                st.markdown("<br>", unsafe_allow_html=True)
                new_restr = st.checkbox("Restricted", value=bool(seg.get("is_restricted", 0)), key=f"seg_restr_{seg['id']}")

            if st.button("💾 Save", key=f"seg_save_{seg['id']}"):
                update_segment(seg["id"], name=new_name, icon=new_icon, description=new_desc, sort_order=int(new_order), is_restricted=new_restr)
                st.success(f"Updated segment: {new_icon} {new_name}")
                st.rerun()

# ── Add new segment ──
st.markdown("#### ➕ Add New Segment")
col_new1, col_new2 = st.columns(2)
with col_new1:
    new_seg_name = st.text_input("Segment Name", key="new_seg_name", placeholder="e.g. Physics")
with col_new2:
    new_seg_icon = st.text_input("Icon (emoji)", key="new_seg_icon", value="📁", placeholder="📁")

new_seg_desc = st.text_input("Description", key="new_seg_desc", placeholder="e.g. Physics curriculum and lectures.")

if st.button("➕ Add Segment"):
    if new_seg_name:
        seg_id = get_or_create_segment(new_seg_name, new_seg_icon or "📁", new_seg_desc)
        st.success(f"Created segment: {new_seg_icon} {new_seg_name} (ID: {seg_id})")
        st.rerun()
    else:
        st.warning("Please enter a segment name.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════
#  Segment Access Control
# ═══════════════════════════════════════════════════════════
st.markdown("### 🔒 Segment Access Control")
st.caption("Grant specific users access to restricted segments.")

restricted_segments = [s for s in segments if s.get("is_restricted")]
if restricted_segments:
    users = get_all_users_admin()
    user_opts = {u['id']: f"{u['display_name']} (@{u['username']})" for u in users}
    
    sel_seg = st.selectbox("Select Restricted Segment", options=restricted_segments, format_func=lambda s: f"{s['icon']} {s['name']}")
    if sel_seg:
        current_access = get_user_segment_access(sel_seg['id'])
        selected_users = st.multiselect(
            "Users with access", 
            options=list(user_opts.keys()), 
            default=current_access,
            format_func=lambda uid: user_opts[uid]
        )
        if st.button("Save Access", key="save_access"):
            set_user_segment_access(sel_seg['id'], selected_users)
            st.success(f"Access updated for {sel_seg['name']}")
else:
    st.info("No restricted segments found.")

st.markdown("---")


# ═══════════════════════════════════════════════════════════
#  Module Access Control
# ═══════════════════════════════════════════════════════════
st.markdown("### 🔒 Module Access Control")
st.caption("Grant specific users access to restricted modules.")

modules = get_all_modules()
restricted_modules = [m for m in modules if m.get("is_restricted")]
if restricted_modules:
    users = get_all_users_admin()
    user_opts = {u['id']: f"{u['display_name']} (@{u['username']})" for u in users}
    
    sel_mod = st.selectbox("Select Restricted Module", options=restricted_modules, format_func=lambda m: f"{m['icon']} {m['name']} ({m.get('segment_name', '?')})")
    if sel_mod:
        current_mod_access = get_user_module_access(sel_mod['id'])
        selected_mod_users = st.multiselect(
            "Users with access", 
            options=list(user_opts.keys()), 
            default=current_mod_access,
            format_func=lambda uid: user_opts[uid],
            key="mod_access_select"
        )
        if st.button("Save Access", key="save_mod_access"):
            set_user_module_access(sel_mod['id'], selected_mod_users)
            st.success(f"Access updated for {sel_mod['name']}")
else:
    st.info("No restricted modules found.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════
#  Video Access Control
# ═══════════════════════════════════════════════════════════
st.markdown("### 🔒 Video Access Control")
st.caption("Grant specific users access to restricted videos.")

videos = get_all_videos()
restricted_videos = [v for v in videos if v.get("is_restricted")]
if restricted_videos:
    users = get_all_users_admin()
    user_opts = {u['id']: f"{u['display_name']} (@{u['username']})" for u in users}
    
    sel_vid = st.selectbox("Select Restricted Video", options=restricted_videos, format_func=lambda v: f"{v['title']} ({v.get('segment_name', '?')})")
    if sel_vid:
        current_vid_access = get_user_video_access(sel_vid['id'])
        selected_vid_users = st.multiselect(
            "Users with access", 
            options=list(user_opts.keys()), 
            default=current_vid_access,
            format_func=lambda uid: user_opts[uid],
            key="vid_access_select"
        )
        if st.button("Save Access", key="save_vid_access"):
            set_user_video_access(sel_vid['id'], selected_vid_users)
            st.success(f"Access updated for {sel_vid['title']}")
else:
    st.info("No restricted videos found.")

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
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    mod_name = st.text_input("Name", value=mod["name"], key=f"mod_name_{mod['id']}")
                with col2:
                    mod_icon = st.text_input("Icon", value=mod["icon"], key=f"mod_icon_{mod['id']}")
                with col3:
                    mod_order = st.number_input("Sort Order", value=mod["sort_order"], key=f"mod_order_{mod['id']}")
                with col4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    mod_restr = st.checkbox("Restricted", value=bool(mod.get("is_restricted", 0)), key=f"mod_restr_{mod['id']}")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Save", key=f"mod_save_{mod['id']}"):
                        update_module(mod["id"], name=mod_name, icon=mod_icon, sort_order=int(mod_order), is_restricted=mod_restr)
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
    
    if len(filtered_videos) > 10:
        assign_container = st.container(height=400, border=True)
    else:
        assign_container = st.container()

    with assign_container:
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

    if len(videos) > 6:
        catalog_container = st.container(height=600, border=False)
    else:
        catalog_container = st.container()

    with catalog_container:
        for v in videos:
            seg_display = f"{v.get('segment_icon', '📁')} {v.get('segment_name', 'Unassigned')}"
            mod_display = f" → {v.get('module_icon', '📂')} {v.get('module_name')}" if v.get("module_name") else ""
            dur_min = v["duration_sec"] / 60 if v["duration_sec"] else 0
            size_mb = v["file_size"] / (1024 * 1024) if v["file_size"] else 0
    
            with st.expander(f"#{v['telegram_msg_id']} — {v['title']}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown(f"**Segment:** {seg_display}")
                    st.markdown(f"**Module:** {mod_display or '—'}")
                    st.markdown(f"**Duration:** {dur_min:.1f} min")
                with col2:
                    st.markdown(f"**Size:** {size_mb:.1f} MB")
                    st.markdown(f"**Telegram Msg ID:** {v['telegram_msg_id']}")
                    if v.get("caption"):
                        st.markdown(f"**Caption:** {v['caption'][:200]}")
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    vid_restr = st.checkbox("Restricted", value=bool(v.get("is_restricted", 0)), key=f"vid_restr_{v['id']}")
                    if st.button("💾 Save", key=f"vid_save_{v['id']}"):
                        update_video_restricted(v["id"], vid_restr)
                        st.success("Saved!")
                        st.rerun()

st.markdown("---")


# ═══════════════════════════════════════════════════════════
#  Data Management (Backup & Cleanup)
# ═══════════════════════════════════════════════════════════

st.markdown("### 💾 Data Management")
st.markdown("Backup data to Telegram, delete messages, or force a restore.")

col_backup, col_delete = st.columns(2)

with col_backup:
    st.markdown("#### ☁️ GitHub Backup")
    st.caption(
        "Auto backup is enabled (saves automatically 60s after any change). "
        "Use the button below if you want to manually force an immediate "
        "backup of your data to your private GitHub repo."
    )
    if st.button("💾 Force Backup Now", use_container_width=True, type="primary"):
        with st.spinner("Backing up to GitHub..."):
            try:
                from backend.github_backup import force_backup_sync
                force_backup_sync()
                st.success("✅ Backup saved to GitHub successfully!")
            except Exception as e:
                st.error(f"Backup failed: {e}")

with col_delete:
    st.markdown("#### 🗑️ Delete All Messages")
    st.caption(
        "Permanently delete all group chat and DM messages from the database. "
        "This cannot be undone."
    )
    if st.button("🗑️ Delete All Messages", use_container_width=True, type="secondary"):
        st.session_state["confirm_delete_messages"] = True

    if st.session_state.get("confirm_delete_messages"):
        st.warning("⚠️ Are you sure? This will delete ALL messages (group chat + DMs).")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Yes, Delete All", type="primary", key="confirm_del_msgs"):
                delete_all_messages()
                st.session_state["confirm_delete_messages"] = False
                st.success("✅ All messages deleted.")
                st.rerun()
        with c2:
            if st.button("❌ Cancel", key="cancel_del_msgs"):
                st.session_state["confirm_delete_messages"] = False
                st.rerun()
