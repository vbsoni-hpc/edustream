# 🎓 EduStream — EdTech Course Platform

A full-stack EdTech platform that **streams course videos from a Telegram channel** (via MTProto), organizes them into course segments, and tracks per-user progress & watch hours — all without downloading any video to disk.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 📡 **Stream from Telegram** — Videos stream directly from Telegram via MTProto (Telethon). No downloads to disk.
- 🎬 **Video.js Player** — Full-featured player with seeking, playback speed, and auto-resume
- ✅ **Completion Tracking** — Auto-marks videos complete when finished, with confetti animation
- ⏱️ **Watch Hour Analytics** — Tracks watch time per video, per segment, with daily activity charts
- 📐 **Auto-Segment Detection** — Organizes videos by `#hashtags` in Telegram captions
- 👥 **Multi-User Login** — Each user gets their own progress (JWT + bcrypt auth)
- 📊 **Dashboard** — Plotly charts showing completion %, watch hours, and daily activity
- 🌙 **Premium Dark UI** — Glassmorphism cards, gradient effects, smooth animations

## 🏗️ Architecture

```
Browser → Streamlit (UI, port 8501)
       → FastAPI (background thread, port 8000)
            → Telethon MTProto → Telegram Servers
            → SQLite (users, progress, videos)
```

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/vbsoni-hpc/edustream.git
cd edustream
pip install -r requirements.txt
```

### 2. Configure Telegram

Get API credentials from [my.telegram.org](https://my.telegram.org):

```bash
cp .env.example .env
# Edit .env and fill in:
#   TELEGRAM_API_ID=your_id
#   TELEGRAM_API_HASH=your_hash
#   TELEGRAM_CHANNEL=@your_channel
#   JWT_SECRET=random_secret_string
```

### 3. Run

```bash
python start.py
```

Open **http://localhost:8501** in your browser.

> **First-time only:** Telethon will prompt in the terminal for your phone number + verification code. The session is saved for future runs.

### 4. Setup

1. **Register** an account on the login page
2. Go to **⚙️ Admin** → click **🔄 Sync Now** to pull videos from Telegram
3. Browse **📚 Courses** and start watching!

## ☁️ Deploy on Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set **Main file path** to `Dashboard.py`
4. Add secrets in the Streamlit Cloud dashboard:

```toml
TELEGRAM_API_ID = "your_api_id"
TELEGRAM_API_HASH = "your_api_hash"
TELEGRAM_CHANNEL = "@your_channel"
JWT_SECRET = "your_random_secret"
```

> ⚠️ **Note:** Telegram requires a one-time phone auth. You'll need to authenticate locally first, then the session file handles future logins.

## 📁 Project Structure

```
├── Dashboard.py                    # Home page + login/register
├── pages/
│   ├── 1_📚_Courses.py       # Browse segments & videos
│   ├── 2_🎬_Player.py        # Video player with tracking
│   ├── 3_📊_Dashboard.py     # Analytics dashboard
│   └── 4_⚙️_Admin.py         # Sync & segment management
├── backend/
│   ├── server.py             # FastAPI (streaming, auth, progress)
│   ├── telegram_client.py    # Telethon MTProto wrapper
│   ├── auth.py               # JWT + bcrypt
│   ├── models.py             # SQLite schema + CRUD
│   └── embedded_server.py    # FastAPI-in-thread for Cloud
├── components/
│   └── video_player.py       # Custom Video.js component
├── config.py                 # Settings (env + Streamlit secrets)
├── start.py                  # Local launcher (both servers)
└── requirements.txt
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit + Custom Video.js |
| Backend API | FastAPI + Uvicorn |
| Telegram | Telethon (MTProto) |
| Database | SQLite + aiosqlite |
| Auth | JWT (python-jose) + bcrypt |
| Charts | Plotly |

## 📄 License

MIT
