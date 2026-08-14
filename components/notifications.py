import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.models import get_unread_messages, get_max_group_message_id, get_new_group_messages_since

@st.fragment(run_every="5s")
def check_and_show_notifications():
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
        
    if "notified_private_ids" not in st.session_state:
        st.session_state["notified_private_ids"] = set()
        
    # 1. Private messages
    unread = get_unread_messages(user_id)
    if unread:
        for msg in unread:
            if msg["id"] not in st.session_state["notified_private_ids"]:
                st.toast(f"**{msg['sender_name']}**: {msg['content'][:60]}...", icon="💬")
                st.session_state["notified_private_ids"].add(msg["id"])
                
    # 2. Global messages
    if "last_global_message_id" not in st.session_state:
        st.session_state["last_global_message_id"] = get_max_group_message_id()
    else:
        new_global = get_new_group_messages_since(st.session_state["last_global_message_id"])
        if new_global:
            for msg in new_global:
                # Don't toast if the user sent it themselves
                if msg["sender_id"] != user_id:
                    st.toast(f"**🌍 {msg['sender_name']}**: {msg['content'][:60]}...", icon="🌍")
            st.session_state["last_global_message_id"] = new_global[-1]["id"]
