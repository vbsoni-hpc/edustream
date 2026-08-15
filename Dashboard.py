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
    get_dashboard_stats,
    get_segment_stats,
    ping_user,
    get_online_users,
    get_leaderboard,
    get_latest_notices,
    is_user_admin,
    get_last_viewed_segment_stats,
    get_user_subscriptions,
    subscribe_to_segment,
    unsubscribe_from_segment,
)
from backend.auth import hash_password, verify_password, create_access_token
from backend.youtube import process_youtube_playlist
# ── Initialise DB on first run ────────────────────────────
init_db()

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

    /* Segment card (Applied to Streamlit Column) */
    div[data-testid="column"]:has(.segment-card-marker) {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.12);
        border-radius: 16px;
        padding: 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    div[data-testid="column"]:has(.segment-card-marker):hover {
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
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .segment-meta {
        font-size: 13px;
        color: #9CA3AF;
        margin-bottom: 14px;
    }
    
    /* Carousel CSS via :has() pseudo-class */
    div[data-testid="stHorizontalBlock"]:has(.segment-card-marker) {
        overflow-x: auto;
        overflow-y: hidden;
        flex-wrap: nowrap !important;
        padding-bottom: 24px;
        margin-bottom: -8px;
        -ms-overflow-style: none;
        scrollbar-width: thin;
        scrollbar-color: rgba(108, 99, 255, 0.5) transparent;
        gap: 1.5rem !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.segment-card-marker)::-webkit-scrollbar {
        height: 8px;
    }
    div[data-testid="stHorizontalBlock"]:has(.segment-card-marker)::-webkit-scrollbar-track {
        background: transparent;
    }
    div[data-testid="stHorizontalBlock"]:has(.segment-card-marker)::-webkit-scrollbar-thumb {
        background-color: rgba(108, 99, 255, 0.5);
        border-radius: 4px;
    }
    div[data-testid="stHorizontalBlock"]:has(.segment-card-marker) > div[data-testid="column"] {
        min-width: 320px !important;
        max-width: 320px !important;
        flex: 0 0 auto !important;
        width: 320px !important;
    }

    /* Progress bar */
    .progress-outer {
        width: 100%;
        height: 8px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 12px;
    }
    .progress-inner {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #6C63FF, #a78bfa);
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Expandable description */
    .segment-details {
        font-size: 13px;
        color: #D1D5DB;
        margin-top: 8px;
    }
    .segment-details summary {
        cursor: pointer;
        color: #a78bfa;
        font-weight: 600;
        outline: none;
        margin-bottom: 4px;
        user-select: none;
    }
    .segment-details p {
        margin: 4px 0 0 0;
        line-height: 1.4;
        background: rgba(0, 0, 0, 0.2);
        padding: 8px;
        border-radius: 6px;
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
    
    /* Subscribe Button override */
    button[data-testid="baseButton-secondary"]:has(div:contains("Subscribe")) {
        background: rgba(108, 99, 255, 0.1) !important;
        border: 1px solid rgba(108, 99, 255, 0.4) !important;
        color: #a78bfa !important;
    }
    button[data-testid="baseButton-secondary"]:has(div:contains("Unsubscribe")) {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.4) !important;
        color: #f87171 !important;
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
    
    /* Online indicator */
    .online-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: #10B981;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    .online-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        margin-right: 6px;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    
    /* Leaderboard */
    .leaderboard-row {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .leaderboard-row:last-child {
        border-bottom: none;
    }
    .lb-rank {
        width: 32px;
        font-weight: 700;
        color: #9CA3AF;
    }
    .lb-rank.gold { color: #FBBF24; font-size: 18px; }
    .lb-rank.silver { color: #9CA3AF; font-size: 18px; }
    .lb-rank.bronze { color: #B45309; font-size: 18px; }
    .lb-name {
        flex-grow: 1;
        font-weight: 600;
        color: #FAFAFA;
    }
    .lb-score {
        font-family: monospace;
        color: #a78bfa;
        font-weight: 600;
        background: rgba(108, 99, 255, 0.1);
        padding: 4px 10px;
        border-radius: 6px;
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
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="collapsedControl"] { display: none; }
            
            /* Center and round the form */
            [data-testid="stForm"] {
                border-radius: 30px;
                background: linear-gradient(135deg, rgba(26, 29, 41, 0.95), rgba(20, 22, 34, 0.9));
                border: 1px solid rgba(108, 99, 255, 0.2);
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Use columns to center the content and reduce width
    col1, col2, col3 = st.columns([1, 1.6, 1])
    
    with col2:
        st.markdown('<div class="login-title" style="font-size: 26px; line-height: 1.3; white-space: normal;">🎓 EduStream - Study with your Friends </div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle"> Your premium course platform </div>', unsafe_allow_html=True)
        
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


# ═══════════════════════════════════════════════════════════
#  YouTube Import Dialog
# ═══════════════════════════════════════════════════════════

@st.dialog("Upload a Course")
def upload_course_dialog():
    st.write("Import a course using a YouTube Playlist URL.")
    url = st.text_input("YouTube Playlist URL", placeholder="https://youtube.com/playlist?... ")
    icon = st.text_input("Segment Icon (emoji)", value="▶️")
    desc = st.text_area("Segment Description", placeholder="Enter optional description")
    
    if st.button("Import"):
        if url:
            with st.spinner("Fetching YouTube data..."):
                try:
                    seg_id = process_youtube_playlist(url, icon, desc)
                    if seg_id is not None:
                        st.success("Successfully imported course!")
                        st.rerun()
                    else:
                        st.error("No valid playlist found.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter a URL")


# ═══════════════════════════════════════════════════════════
#  Home Dashboard
# ═══════════════════════════════════════════════════════════

def show_home():
    user_id = st.session_state["user_id"]
    display_name = st.session_state.get("display_name", "Student")
    is_admin = is_user_admin(user_id)

    # ── Sidebar ──
    with st.sidebar:
        st.caption(f"#### 👤 {display_name} @{st.session_state['username']}")
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

        import streamlit.components.v1 as components
        components.html(
            """
            <script>
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(b => {
                if(b.innerText.includes('Logout')) {
                    b.style.backgroundColor = '#EF4444';
                    b.style.color = 'white';
                    b.style.border = 'none';
                }
            });
            </script>
            """, height=0, width=0
        )

    # ── Hero ──
    stats = get_dashboard_stats(user_id)

    st.markdown(f'<div class="hero-title">Welcome back, {display_name} 👋</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Continue your learning journey</div>', unsafe_allow_html=True)

    # ── Notices ──
    notices = get_latest_notices(3)
    if notices:
        st.markdown("##### 📢 Important Notices")
        for notice in notices:
            st.markdown(notice['content'])
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick Stats ──
    last_seg_stats = get_last_viewed_segment_stats(user_id)

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        if last_seg_stats:
            pct = (last_seg_stats['completed_videos'] / last_seg_stats['total_videos'] * 100) if last_seg_stats['total_videos'] > 0 else 0
            hours = last_seg_stats['watch_seconds'] / 3600
            st.markdown(f"**Last Viewed Course:** {last_seg_stats['icon']} {last_seg_stats['name']} • **Progress:** {pct:.1f}% ({last_seg_stats['completed_videos']}/{last_seg_stats['total_videos']} videos) • **Watch Time:** {hours:.1f}h")
            st.progress(pct / 100)
        else:
            st.markdown("**No recent activity.** Start watching a course to track progress!")
            
    with col2:
        if st.button("➕ Upload a Course", use_container_width=True):
            upload_course_dialog()

    st.markdown("<br>", unsafe_allow_html=True)
    

    # ── Segment Cards ──
    segment_stats = get_segment_stats(user_id)
    segment_stats = [seg for seg in segment_stats if seg['name'] not in ('General', 'Uncategorized')]

    if not segment_stats:
        st.info("No courses synced yet. Go to the **⚙️ Admin** page to sync your Telegram channel.")
        return

    subscribed_ids = set(get_user_subscriptions(user_id))
    my_courses = [s for s in segment_stats if s['id'] in subscribed_ids]

    def render_carousel(title, items, show_empty=False):
        if not items and not show_empty:
            return
            
        st.markdown(f"#### {title}")
        if not items and show_empty:
            st.info("You haven't subscribed to any courses yet. Discover and subscribe below!")
            st.markdown("<br>", unsafe_allow_html=True)
            return
            
        cols = st.columns(len(items))
        for col, seg in zip(cols, items):
            with col:
                seg_pct = (seg["completed_videos"] / seg["total_videos"] * 100) if seg["total_videos"] > 0 else 0
                watch_hrs = seg["watch_seconds"] / 3600
                st.markdown(f"""
                <div class="segment-card-marker" style="display: none;"></div>
                <div class="segment-icon">{seg['icon']}</div>
                <div class="segment-name" title="{seg['name']}">{seg['name']}</div>
                <div class="segment-meta">
                    {seg['total_videos']} videos · {seg['completed_videos']} completed<br>{watch_hrs:.1f}h watched
                </div>
                <div class="progress-outer">
                    <div class="progress-inner" style="width:{seg_pct}%;"></div>
                </div>
                <details class="segment-details">
                    <summary>Description</summary>
                    <p>{seg.get('description') or f"Access materials and track your progress in the {seg['name']} course module."}</p>
                </details>
                """, unsafe_allow_html=True)
                
                # Buttons
                bcol1, bcol2 = st.columns([1, 1])
                with bcol1:
                    if seg['id'] in subscribed_ids:
                        st.page_link("pages/1_📚_My_Courses.py", label="Open", icon="📖", use_container_width=True)
                    else:
                        st.page_link("pages/1_📚_My_Courses.py", label="Open", icon="🔒", disabled=True, use_container_width=True, help="Subscribe to open")
                with bcol2:
                    if seg['id'] in subscribed_ids:
                        if st.button("Unsubscribe", key=f"unsub_{title}_{seg['id']}", use_container_width=True):
                            unsubscribe_from_segment(user_id, seg['id'])
                            st.rerun()
                    else:
                        if st.button("Subscribe", key=f"sub_{title}_{seg['id']}", use_container_width=True):
                            subscribe_to_segment(user_id, seg['id'])
                            st.rerun()
                            
        st.markdown("<br>", unsafe_allow_html=True)

    render_carousel("📚 My Courses", my_courses, show_empty=True)
    render_carousel("🌐 All Courses", segment_stats)

    # ── Leaderboards ──
    st.markdown("#### 🏆 Top Learners")
    lb_col1, lb_col2 = st.columns(2)
    
    def render_leaderboard(data, title):
        html = f'<div class="glass-card"><h5 style="margin-top:0; color:#FAFAFA;">{title}</h5>'
        if not data:
            html += '<p style="color:#9CA3AF; font-size:14px;">No activity yet.</p></div>'
            st.markdown(html, unsafe_allow_html=True)
            return
            
        for i, row in enumerate(data):
            rank_class = "gold" if i == 0 else "silver" if i == 1 else "bronze" if i == 2 else ""
            rank_text = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            hrs = row['total_watch_sec'] / 3600
            
            html += f"""<div class="leaderboard-row">
    <div class="lb-rank {rank_class}">{rank_text}</div>
    <div class="lb-name">{row['display_name']}</div>
    <div class="lb-score">{hrs:.1f}h</div>
</div>"""
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    with lb_col1:
        daily_lb = get_leaderboard(days=1)
        render_leaderboard(daily_lb, "Daily Watch Hours")
        
    with lb_col2:
        weekly_lb = get_leaderboard(days=7)
        render_leaderboard(weekly_lb, "Weekly Watch Hours")


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

if is_logged_in():
    from components.notifications import check_and_show_notifications
    from components.messaging_sidebar import render_messaging_sidebar
    
    check_and_show_notifications()
    render_messaging_sidebar()
    ping_user(st.session_state["user_id"])
    show_home()
else:
    show_auth_page()
