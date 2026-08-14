import streamlit as st
from datetime import datetime

from backend.models import get_group_messages, send_message

def render_chat_widget():
    """Render a collapsible global chat widget in the sidebar."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    st.sidebar.markdown("---")
    with st.sidebar.expander("🌍 Global Chat", expanded=False):
        # We use a form to prevent full page reload issues and clear input easily
        with st.form("sidebar_chat_form", clear_on_submit=True):
            new_msg = st.text_input("Message", placeholder="Chat with everyone...", label_visibility="collapsed")
            if st.form_submit_button("Send 🚀", use_container_width=True):
                if new_msg.strip():
                    send_message(user_id, 0, new_msg.strip())
                    st.rerun()

        group_msgs = get_group_messages(15)
        if not group_msgs:
            st.caption("No messages yet. Say hi!")
        else:
            # Add some basic CSS for the sidebar chat to make it compact
            st.markdown("""
            <style>
                .sb-chat-msg {
                    font-size: 13px;
                    margin-bottom: 8px;
                    line-height: 1.3;
                }
                .sb-chat-sender {
                    font-weight: 600;
                    color: #a78bfa;
                }
                .sb-chat-time {
                    font-size: 10px;
                    color: #6B7280;
                    margin-left: 4px;
                }
                .sb-chat-content {
                    color: #E5E7EB;
                    display: block;
                    margin-top: 2px;
                }
            </style>
            """, unsafe_allow_html=True)
            
            html = '<div style="max-height: 400px; overflow-y: auto;">'
            for msg in group_msgs:
                is_me = (msg['sender_id'] == user_id)
                msg_time = datetime.fromtimestamp(msg["created_at"]).strftime("%H:%M")
                sender_name = "You" if is_me else msg['sender_name']
                
                html += f"""
                <div class="sb-chat-msg">
                    <span class="sb-chat-sender">{sender_name}</span>
                    <span class="sb-chat-time">{msg_time}</span>
                    <span class="sb-chat-content">{msg['content']}</span>
                </div>
                """
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
