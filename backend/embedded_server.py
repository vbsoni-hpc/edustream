"""
Embedded FastAPI server — runs in a background thread inside the Streamlit process.

This is needed for Streamlit Cloud deployment where we can't run
separate processes. The FastAPI server starts on a background thread
when the Streamlit app first loads.
"""
import threading
import logging
import asyncio
import uvicorn
import time

logger = logging.getLogger(__name__)

_server_started = False
_lock = threading.Lock()


def start_fastapi_background(host: str = "127.0.0.1", port: int = 8000):
    """
    Start the FastAPI server in a background daemon thread.
    Safe to call multiple times — only starts once.
    """
    global _server_started

    with _lock:
        if _server_started:
            return
        _server_started = True

    def _run():
        try:
            # Import here to avoid circular imports
            from backend.server import app

            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.serve())
        except Exception as e:
            logger.error(f"FastAPI background server failed: {e}")
            global _server_started
            _server_started = False

    thread = threading.Thread(target=_run, daemon=True, name="fastapi-bg")
    thread.start()
    
    # Give the server a moment to start
    time.sleep(1)
    logger.info(f"FastAPI background server started on {host}:{port}")


def is_server_running() -> bool:
    """Check if the background FastAPI server is running."""
    return _server_started
