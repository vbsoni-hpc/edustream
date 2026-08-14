"""
Application configuration — loads settings from .env file or Streamlit secrets.

Priority: Streamlit secrets > .env > os.getenv defaults
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)


def _get_secret(key: str, default: str = "") -> str:
    """Try Streamlit secrets first, then env vars."""
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


# ── Telegram ──────────────────────────────────────────────
TELEGRAM_API_ID = int(_get_secret("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = _get_secret("TELEGRAM_API_HASH")
TELEGRAM_CHANNEL = _get_secret("TELEGRAM_CHANNEL")
TELEGRAM_STRING_SESSION = _get_secret("TELEGRAM_STRING_SESSION")

# ── Auth ──────────────────────────────────────────────────
JWT_SECRET = _get_secret("JWT_SECRET", "default-insecure-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

# ── Database ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "edtech.db"

# ── FastAPI ───────────────────────────────────────────────
FASTAPI_HOST = "127.0.0.1"
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "8000"))
API_BASE_URL = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}"

# ── Telethon session file ─────────────────────────────────
SESSION_DIR = DATA_DIR
SESSION_NAME = str(DATA_DIR / "telegram_session")

# ── Defaults ──────────────────────────────────────────────
DEFAULT_SEGMENT_ICONS = {
    "Math": "📐",
    "Methods": "🧪",
    "Physics": "⚛️",
    "Chemistry": "🧬",
    "General": "📁",
}
