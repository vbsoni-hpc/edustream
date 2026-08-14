import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.models import get_unread_messages

def check_and_show_notifications():
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
    unread = get_unread_messages(user_id)
    if unread:
        for msg in unread:
            st.toast(f"**{msg['sender_name']}**: {msg['content'][:60]}...", icon="💬")
