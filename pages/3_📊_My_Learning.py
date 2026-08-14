"""
📊 Dashboard — Analytics & progress charts.

Shows overall completion, per-segment watch hours, and daily activity.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import (
    init_db,
    get_dashboard_stats,
    get_segment_stats,
    get_module_stats,
    get_daily_watch_activity,
    get_user_progress,
)

init_db()

st.set_page_config(page_title="Dashboard — EduStream", page_icon="📊", layout="wide")

# ── Check auth ────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please log in first.")
    st.page_link("Dashboard.py", label="Go to Login", icon="🔑")
    st.stop()

user_id = st.session_state["user_id"]
display_name = st.session_state.get("display_name", "Student")

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer { visibility: hidden; }

    .dash-stat {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.95), rgba(30, 34, 50, 0.8));
        border: 1px solid rgba(108, 99, 255, 0.15);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
    }
    .dash-stat-value {
        font-size: 40px;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    .dash-stat-label {
        font-size: 12px;
        color: #6B7280;
        margin-top: 6px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
    }
    .chart-card {
        background: linear-gradient(135deg, rgba(26, 29, 41, 0.9), rgba(26, 29, 41, 0.6));
        border: 1px solid rgba(108, 99, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
    }
    .chart-title {
        font-size: 16px;
        font-weight: 700;
        color: #FAFAFA;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ── Data ──────────────────────────────────────────────────
stats = get_dashboard_stats(user_id)
seg_stats = get_segment_stats(user_id)
daily_activity = get_daily_watch_activity(user_id, 30)


# ── Header ────────────────────────────────────────────────
st.markdown("# 📊 Learning Dashboard")
st.markdown(f"Your progress overview, **{display_name}**")
st.markdown("---")


# ── Stat Cards ────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="dash-stat">
        <div class="dash-stat-value">{stats['completed_videos']}/{stats['total_videos']}</div>
        <div class="dash-stat-label">Videos Completed</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="dash-stat">
        <div class="dash-stat-value">{stats['completion_pct']:.0f}%</div>
        <div class="dash-stat-label">Completion Rate</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="dash-stat">
        <div class="dash-stat-value">{stats['total_watch_hours']:.1f}h</div>
        <div class="dash-stat-label">Total Watch Time</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    # Calculate average session length
    progress_data = get_user_progress(user_id)
    sessions = len([p for p in progress_data if p["watch_seconds"] > 0])
    avg_session = (stats["total_watch_seconds"] / sessions / 60) if sessions > 0 else 0
    st.markdown(f"""
    <div class="dash-stat">
        <div class="dash-stat-value">{avg_session:.0f}m</div>
        <div class="dash-stat-label">Avg Session</div>
    </div>
    """, unsafe_allow_html=True)


st.markdown("<br>", unsafe_allow_html=True)


# ── Charts ────────────────────────────────────────────────
col_donut, col_bar = st.columns(2)

# ── Completion donut ──
with col_donut:
    st.markdown('<div class="chart-card"><div class="chart-title">📈 Overall Completion</div>', unsafe_allow_html=True)

    fig_donut = go.Figure(data=[go.Pie(
        labels=["Completed", "Remaining"],
        values=[stats["completed_videos"], max(stats["total_videos"] - stats["completed_videos"], 0)],
        hole=0.7,
        marker=dict(
            colors=["#6C63FF", "rgba(255,255,255,0.06)"],
            line=dict(color="#0E1117", width=3)
        ),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} videos<extra></extra>",
    )])
    fig_donut.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color="#9CA3AF", size=12)
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=20, r=20, t=20, b=40),
        annotations=[dict(
            text=f"<b>{stats['completion_pct']:.0f}%</b>",
            x=0.5, y=0.5,
            font_size=32,
            font_color="#FAFAFA",
            showarrow=False,
        )],
    )
    st.plotly_chart(fig_donut, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Watch hours by segment ──
with col_bar:
    st.markdown('<div class="chart-card"><div class="chart-title">⏱️ Watch Hours by Segment</div>', unsafe_allow_html=True)

    if seg_stats:
        seg_names = [f"{s['icon']} {s['name']}" for s in seg_stats]
        seg_hours = [s["watch_seconds"] / 3600 for s in seg_stats]

        fig_bar = go.Figure(data=[go.Bar(
            x=seg_hours,
            y=seg_names,
            orientation="h",
            marker=dict(
                color=seg_hours,
                colorscale=[[0, "#6C63FF"], [1, "#a78bfa"]],
            ),
            hovertemplate="<b>%{y}</b><br>%{x:.1f} hours<extra></extra>",
        )])
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=10, r=20, t=10, b=40),
            xaxis=dict(
                title="Hours",
                gridcolor="rgba(255,255,255,0.05)",
                color="#6B7280",
            ),
            yaxis=dict(
                color="#FAFAFA",
                autorange="reversed",
            ),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No segments to display yet.")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Daily activity ────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="chart-card"><div class="chart-title">📅 Daily Watch Activity (Last 30 Days)</div>', unsafe_allow_html=True)

if daily_activity:
    dates = [d["date"] for d in daily_activity]
    minutes = [d["watch_seconds"] / 60 for d in daily_activity]

    fig_activity = go.Figure(data=[go.Bar(
        x=dates,
        y=minutes,
        marker=dict(
            color=minutes,
            colorscale=[[0, "rgba(108,99,255,0.3)"], [0.5, "#6C63FF"], [1, "#a78bfa"]],
        ),
        hovertemplate="<b>%{x}</b><br>%{y:.0f} minutes<extra></extra>",
    )])
    fig_activity.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=250,
        margin=dict(l=40, r=20, t=10, b=40),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.03)",
            color="#6B7280",
        ),
        yaxis=dict(
            title="Minutes",
            gridcolor="rgba(255,255,255,0.05)",
            color="#6B7280",
        ),
    )
    st.plotly_chart(fig_activity, use_container_width=True)
else:
    st.info("No watch activity recorded yet. Start watching some videos!")

st.markdown('</div>', unsafe_allow_html=True)


# ── Detailed segment breakdown ────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 📋 Segment Breakdown")

if seg_stats:
    for seg in seg_stats:
        seg_pct = (seg["completed_videos"] / seg["total_videos"] * 100) if seg["total_videos"] > 0 else 0
        watch_h = seg["watch_seconds"] / 3600

        col_info, col_bar = st.columns([2, 3])
        with col_info:
            st.markdown(f"**{seg['icon']} {seg['name']}** — {seg['completed_videos']}/{seg['total_videos']} done · {watch_h:.1f}h watched")
        with col_bar:
            st.progress(min(seg_pct / 100, 1.0), text=f"{seg_pct:.0f}%")

# ── Detailed module breakdown ─────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 📂 Module Breakdown")

module_stats = get_module_stats(user_id)
if module_stats:
    from collections import defaultdict
    mod_by_seg = defaultdict(list)
    for m in module_stats:
        mod_by_seg[m["segment_name"]].append(m)
    
    for seg_name, mods in mod_by_seg.items():
        st.markdown(f"**{seg_name}**")
        for m in mods:
            m_pct = (m["completed_videos"] / m["total_videos"] * 100) if m["total_videos"] > 0 else 0
            m_watch_h = m["watch_seconds"] / 3600
            
            c1, c2 = st.columns([2, 3])
            with c1:
                st.markdown(f"&nbsp;&nbsp;&nbsp;↳ {m['icon']} {m['name']} — {m['completed_videos']}/{m['total_videos']} done · {m_watch_h:.1f}h")
            with c2:
                st.progress(min(m_pct / 100, 1.0), text=f"{m_pct:.0f}%")
else:
    st.info("No modules to display.")
