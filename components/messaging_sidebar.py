import streamlit as st
import time
from datetime import datetime

from backend.models import (
    get_group_messages,
    send_message,
    get_messages_for_user,
    mark_messages_read,
    get_all_users
)

@st.fragment(run_every="5s")
def render_global_chat_messages(user_id):
    group_msgs = get_group_messages(15)
    if not group_msgs:
        st.caption("No messages yet. Say hi!")
    else:
        html = '<div style="max-height: 250px; overflow-y: auto;">'
        for msg in group_msgs:
            is_me = (msg['sender_id'] == user_id)
            msg_time = datetime.fromtimestamp(msg["created_at"]).strftime("%H:%M")
            sender_name = "You" if is_me else msg['sender_name']
            
            if is_me:
                html += f"""
                <div style="margin-bottom: 8px; text-align: right;">
                    <div style="display: inline-block; background: rgba(108, 99, 255, 0.2); border-right: 3px solid #6C63FF; padding: 8px 10px; border-radius: 12px 0 12px 12px; text-align: left; max-width: 90%;">
                        <div style="font-size: 10px; color: #a78bfa; margin-bottom: 2px; font-weight: 600;">{sender_name} <span style="font-weight: 400; color:#6B7280;margin-left:4px;">{msg_time}</span></div>
                        <div style="font-size: 12px; color: #FAFAFA; line-height: 1.3; word-wrap: break-word;">{msg['content']}</div>
                    </div>
                </div>
                """
            else:
                html += f"""
                <div style="margin-bottom: 8px; text-align: left;">
                    <div style="display: inline-block; background: rgba(26, 29, 41, 0.8); border-left: 3px solid #a78bfa; padding: 8px 10px; border-radius: 0 12px 12px 12px; text-align: left; max-width: 90%; border: 1px solid rgba(108, 99, 255, 0.15); border-left-width: 3px;">
                        <div style="font-size: 10px; color: #a78bfa; margin-bottom: 2px; font-weight: 600;">{sender_name} <span style="font-weight: 400; color:#6B7280;margin-left:4px;">{msg_time}</span></div>
                        <div style="font-size: 12px; color: #FAFAFA; line-height: 1.3; word-wrap: break-word;">{msg['content']}</div>
                    </div>
                </div>
                """
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)


@st.fragment(run_every="5s")
def render_inbox_messages(user_id):
    inbox_msgs = get_messages_for_user(user_id)
    if not inbox_msgs:
        st.caption("Your inbox is empty.")
    else:
        unread_ids = []
        html = '<div style="max-height: 300px; overflow-y: auto;">'
        for msg in inbox_msgs:
            if not msg["is_read"]:
                unread_ids.append(msg["id"])
                
            msg_time = datetime.fromtimestamp(msg["created_at"]).strftime("%b %d, %H:%M")
            unread_badge = '<span style="background:#EF4444;color:white;font-size:9px;padding:2px 4px;border-radius:4px;margin-left:4px;">NEW</span>' if not msg['is_read'] else ''
            
            html += f"""
            <div style="font-size: 12px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <div style="margin-bottom:2px;">
                    <span style="font-weight: 600; color: #a78bfa;">👤 {msg['sender_name']}</span>
                    {unread_badge}
                </div>
                <div style="font-size: 10px; color: #6B7280; margin-bottom: 4px;">{msg_time}</div>
                <div style="color: #E5E7EB; white-space: pre-wrap;">{msg['content']}</div>
            </div>
            """
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
        if unread_ids:
            mark_messages_read(unread_ids)


def render_messaging_sidebar():
    """Render expandable messaging sections in the sidebar."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
        
    current_username = st.session_state.get("username")
    is_admin = (current_username == "vbsoni")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Messaging")

    # 1. GLOBAL CHAT
    with st.sidebar.expander("🌍 Global Chat", expanded=False):
        with st.form("sb_global_chat_form", clear_on_submit=True):
            new_msg = st.text_input("Message", placeholder="Chat with everyone...", label_visibility="collapsed")
            if st.form_submit_button("Send 🚀", use_container_width=True):
                if new_msg.strip():
                    send_message(user_id, 0, new_msg.strip())
                    st.rerun()

        render_global_chat_messages(user_id)

    # 2. DIRECT INBOX
    with st.sidebar.expander("📥 Direct Inbox", expanded=False):
        render_inbox_messages(user_id)

    # 3. COMPOSE
    with st.sidebar.expander("✏️ Compose DM", expanded=False):
        users = get_all_users()
        recipient_options = [u for u in users if u["id"] != user_id]
        
        if not recipient_options:
            st.caption("No other users to message.")
        else:
            options_map = {f"{u['display_name']} (@{u['username']})": u["id"] for u in recipient_options}
            if is_admin:
                options_list = ["📢 Broadcast to ALL Users"] + list(options_map.keys())
            else:
                options_list = list(options_map.keys())
                
            selected_target = st.selectbox("To:", options_list, key="compose_to")
            msg_text = st.text_area("Message:", height=100, placeholder="Type your message here...", key="compose_msg")
            
            if st.button("Send Message 🚀", type="primary", use_container_width=True, key="compose_btn"):
                if not msg_text.strip():
                    st.error("Message cannot be empty.")
                else:
                    if selected_target == "📢 Broadcast to ALL Users":
                        count = 0
                        for u in recipient_options:
                            send_message(user_id, u["id"], msg_text.strip())
                            count += 1
                        st.success(f"Broadcast sent to {count} users!")
                    else:
                        recipient_id = options_map[selected_target]
                        send_message(user_id, recipient_id, msg_text.strip())
                        st.success(f"Message sent to {selected_target.split(' ')[0]}!")
                    time.sleep(1)
                    st.rerun()
