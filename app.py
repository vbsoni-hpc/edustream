"""
EdTech Course Platform — Home Page & Authentication

This is the main entry point for the Streamlit app.
Handles login/register and shows the home dashboard once authenticated.
"""
import streamlit as st
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from config import API_BASE_URL
from backend.models import (
    init_db,
    get_user_by_username,
    create_user,
    get_all_segments,
    get_dashboard_stats,
    get_segment_stats,
)
from backend.auth import hash_password, verify_password, create_access_token
from backend.embedded_server import start_fastapi_background

# ── Initialise DB on first run ────────────────────────────
init_db()

# ── Start FastAPI in background thread (for Streamlit Cloud) ──
start_fastapi_background(port=8000)

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="EduStream — Course Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Glassmorphism card */
    .glass-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.15);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(10px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 16px;
    }
    .glass-card:hover {
        border-color: rgba(108, 99, 255, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(108, 99, 255, 0.12);
    }

    /* Stat card */
    .stat-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.95), rgba(30, 34, 50, 0.8));
        border: 1px solid rgba(108, 99, 255, 0.2);
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
    }
    .stat-value {
        font-size: 36px;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    .stat-label {
        font-size: 13px;
        color: #9CA3AF;
        margin-top: 4px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Segment card */
    .segment-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.12);
        border-radius: 16px;
        padding: 24px;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .segment-card:hover {
        border-color: rgba(108, 99, 255, 0.5);
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(108, 99, 255, 0.15);
    }
    .segment-icon {
        font-size: 40px;
        margin-bottom: 12px;
    }
    .segment-name {
        font-size: 18px;
        font-weight: 700;
        color: #FAFAFA;
        margin-bottom: 8px;
    }
    .segment-meta {
        font-size: 13px;
        color: #9CA3AF;
        margin-bottom: 14px;
    }

    /* Progress bar */
    .progress-outer {
        width: 100%;
        height: 8px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-inner {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #6C63FF, #a78bfa);
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Hero section */
    .hero-title {
        font-size: 42px;
        font-weight: 800;
        background: linear-gradient(135deg, #FAFAFA 0%, #a78bfa 50%, #6C63FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 16px;
        color: #9CA3AF;
        margin-bottom: 32px;
    }

    /* Login form styling */
    .login-container {
        max-width: 420px;
        margin: 60px auto;
        padding: 40px;
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.95), rgba(20, 22, 34, 0.9));
        border: 1px solid rgba(108, 99, 255, 0.2);
        border-radius: 20px;
        backdrop-filter: blur(20px);
    }
    .login-title {
        font-size: 28px;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #FAFAFA, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .login-subtitle {
        text-align: center;
        color: #9CA3AF;
        font-size: 14px;
        margin-bottom: 32px;
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #6C63FF, #5B54E0);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 15px;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #7B73FF, #6C63FF);
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(108, 99, 255, 0.3);
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: rgba(26, 29, 41, 0.5);
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(108, 99, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  Session state helpers
# ═══════════════════════════════════════════════════════════

def is_logged_in() -> bool:
    return st.session_state.get("user_id") is not None


def logout():
    for key in ["user_id", "username", "display_name", "jwt_token"]:
        st.session_state.pop(key, None)


# ═══════════════════════════════════════════════════════════
#  Login / Register Page
# ═══════════════════════════════════════════════════════════

def show_auth_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🎓 EduStream</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Your premium course platform</div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign In", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Please fill in all fields")
                else:
                    user = get_user_by_username(username)
                    if user and verify_password(password, user["password_hash"]):
                        token = create_access_token(user["id"], user["username"])
                        st.session_state["user_id"] = user["id"]
                        st.session_state["username"] = user["username"]
                        st.session_state["display_name"] = user["display_name"]
                        st.session_state["jwt_token"] = token
                        st.rerun()
                    else:
                        st.error("Invalid username or password")

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("Choose a username", key="reg_user")
            new_display = st.text_input("Display name", key="reg_display")
            new_pass = st.text_input("Password", type="password", key="reg_pass")
            new_pass2 = st.text_input("Confirm password", type="password", key="reg_pass2")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                if not new_user or not new_pass:
                    st.error("Username and password are required")
                elif new_pass != new_pass2:
                    st.error("Passwords don't match")
                elif get_user_by_username(new_user):
                    st.error("Username already taken")
                else:
                    hashed = hash_password(new_pass)
                    uid = create_user(new_user, hashed, new_display or new_user)
                    token = create_access_token(uid, new_user)
                    st.session_state["user_id"] = uid
                    st.session_state["username"] = new_user
                    st.session_state["display_name"] = new_display or new_user
                    st.session_state["jwt_token"] = token
                    st.success("Account created! Redirecting...")
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  Home Dashboard
# ═══════════════════════════════════════════════════════════

def show_home():
    user_id = st.session_state["user_id"]
    display_name = st.session_state.get("display_name", "Student")

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(f"### 👤 {display_name}")
        st.caption(f"@{st.session_state['username']}")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()

    # ── Hero ──
    stats = get_dashboard_stats(user_id)

    st.markdown(f'<div class="hero-title">Welcome back, {display_name} 👋</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Continue your learning journey</div>', unsafe_allow_html=True)

    # ── Quick Stats ──
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['total_videos']}</div>
            <div class="stat-label">Total Videos</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['completed_videos']}</div>
            <div class="stat-label">Completed</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        pct = stats['completion_pct']
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{pct:.0f}%</div>
            <div class="stat-label">Progress</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        hours = stats['total_watch_hours']
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{hours:.1f}h</div>
            <div class="stat-label">Watch Time</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Overall progress bar ──
    st.markdown(f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="font-weight:600; color:#FAFAFA;">Overall Progress</span>
            <span style="color:#a78bfa; font-weight:700;">{pct:.0f}%</span>
        </div>
        <div class="progress-outer">
            <div class="progress-inner" style="width:{pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Segment Cards ──
    st.markdown("### 📚 Course Segments")
    segment_stats = get_segment_stats(user_id)

    if not segment_stats:
        st.info("No courses synced yet. Go to the **⚙️ Admin** page to sync your Telegram channel.")
        return

    # Create rows of 3 cards each
    cols_per_row = 3
    for i in range(0, len(segment_stats), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(segment_stats):
                break
            seg = segment_stats[idx]
            seg_pct = (seg["completed_videos"] / seg["total_videos"] * 100) if seg["total_videos"] > 0 else 0
            watch_hrs = seg["watch_seconds"] / 3600

            with col:
                st.markdown(f"""
                <div class="segment-card">
                    <div class="segment-icon">{seg['icon']}</div>
                    <div class="segment-name">{seg['name']}</div>
                    <div class="segment-meta">
                        {seg['total_videos']} videos · {seg['completed_videos']} completed · {watch_hrs:.1f}h watched
                    </div>
                    <div class="progress-outer">
                        <div class="progress-inner" style="width:{seg_pct}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

if is_logged_in():
    show_home()
else:
    show_auth_page()
