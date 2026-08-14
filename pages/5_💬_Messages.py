"""
💬 Messages — Peer-to-peer messaging system for students and admins.
"""
import streamlit as st
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import (
    init_db,
    get_all_users,
    send_message,
    get_messages_for_user,
    mark_messages_read,
    get_unread_messages,
    get_group_messages,
)

init_db()

st.set_page_config(page_title="Messages — EduStream", page_icon="💬", layout="centered")

# ── Check auth ────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in first.")
    st.page_link("Dashboard.py", label="Go to Login", icon="🔑")
    st.stop()

current_user_id = st.session_state["user_id"]
current_username = st.session_state["username"]
is_admin = (current_username == "vbsoni")  # Simple admin check based on username

# ── Global Notification Hook ─────────────────────────────
# We trigger this at the top so toasts appear even on this page
unread = get_unread_messages(current_user_id)
if unread:
    for msg in unread:
        st.toast(f"**{msg['sender_name']}**: {msg['content'][:50]}...", icon="💬")
    # Marking them read is handled by the Inbox tab when viewed.

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer { visibility: hidden; }
    
    .msg-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .msg-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .msg-sender {
        font-weight: 600;
        color: #a78bfa;
        font-size: 15px;
    }
    .msg-time {
        font-size: 12px;
        color: #9CA3AF;
    }
    .msg-content {
        color: #FAFAFA;
        font-size: 14px;
        line-height: 1.5;
        white-space: pre-wrap;
    }
    .msg-unread-badge {
        background: #EF4444;
        color: white;
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 10px;
        margin-left: 8px;
        font-weight: bold;
    }
    
    /* Group Chat Specific */
    .chat-bubble-me {
        background: rgba(108, 99, 255, 0.2);
        border-right: 3px solid #6C63FF;
        margin-left: 20%;
        border-radius: 12px 0 12px 12px;
    }
    .chat-bubble-other {
        background: rgba(26, 29, 41, 0.8);
        border-left: 3px solid #a78bfa;
        margin-right: 20%;
        border-radius: 0 12px 12px 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("💬 Messages")

tab_group, tab_inbox, tab_compose = st.tabs(["🌍 Group Chat", "📥 Direct Inbox", "✏️ Compose"])

# ═══════════════════════════════════════════════════════════
#  Group Chat Tab
# ═══════════════════════════════════════════════════════════
with tab_group:
    st.markdown("### 🌍 Global Chat")
    st.caption("Talk with everyone in the course!")
    
    # Form for new messages
    with st.form("group_chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            new_group_msg = st.text_input("Message", placeholder="Type your message to the group...", label_visibility="collapsed")
        with col_btn:
            submitted = st.form_submit_button("Send 🚀", use_container_width=True)
            if submitted and new_group_msg.strip():
                send_message(current_user_id, 0, new_group_msg.strip())
                st.rerun()

    st.markdown("---")
    
    # Display group messages (newest at bottom, so we render list as is since SQL order is ASC)
    group_msgs = get_group_messages(50)
    if not group_msgs:
        st.info("No messages yet. Be the first to say hi!")
    else:
        for msg in group_msgs:
            is_me = (msg['sender_id'] == current_user_id)
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

# ═══════════════════════════════════════════════════════════
#  Inbox Tab
# ═══════════════════════════════════════════════════════════
with tab_inbox:
    messages = get_messages_for_user(current_user_id)
    
    if not messages:
        st.info("Your inbox is empty.")
    else:
        unread_ids = []
        for msg in messages:
            if not msg["is_read"]:
                unread_ids.append(msg["id"])
                
            # Format time
            msg_time = datetime.fromtimestamp(msg["created_at"]).strftime("%b %d, %H:%M")
            unread_badge = '<span class="msg-unread-badge">NEW</span>' if not msg['is_read'] else ''
            
            st.markdown(f"""
            <div class="msg-card">
                <div class="msg-header">
                    <span class="msg-sender">👤 {msg['sender_name']} {unread_badge}</span>
                    <span class="msg-time">{msg_time}</span>
                </div>
                <div class="msg-content">{msg['content']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Mark all displayed messages as read
        if unread_ids:
            mark_messages_read(unread_ids)

# ═══════════════════════════════════════════════════════════
#  Compose Tab
# ═══════════════════════════════════════════════════════════
with tab_compose:
    st.markdown("### Send a Message")
    
    users = get_all_users()
    # Filter out current user
    recipient_options = [u for u in users if u["id"] != current_user_id]
    
    if not recipient_options:
        st.info("No other users to message.")
    else:
        # Create selectbox mapping
        options_map = {f"{u['display_name']} (@{u['username']})": u["id"] for u in recipient_options}
        
        if is_admin:
            options_list = ["📢 Broadcast to ALL Users"] + list(options_map.keys())
        else:
            options_list = list(options_map.keys())
            
        selected_target = st.selectbox("To:", options_list)
        msg_text = st.text_area("Message:", height=150, placeholder="Type your message here...")
        
        if st.button("🚀 Send Message", type="primary", use_container_width=True):
            if not msg_text.strip():
                st.error("Message cannot be empty.")
            else:
                if selected_target == "📢 Broadcast to ALL Users":
                    count = 0
                    for u in recipient_options:
                        send_message(current_user_id, u["id"], msg_text.strip())
                        count += 1
                    st.success(f"Broadcast sent to {count} users!")
                else:
                    recipient_id = options_map[selected_target]
                    send_message(current_user_id, recipient_id, msg_text.strip())
                    st.success(f"Message sent to {selected_target.split(' ')[0]}!")
                
                time.sleep(1)
                st.rerun()
