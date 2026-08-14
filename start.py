"""
EduStream Launcher - Starts both FastAPI and Streamlit servers.

Usage:
    python start.py

This will start:
  - FastAPI backend on port 8000 (video streaming, auth, progress API)
  - Streamlit frontend on port 8501 (the UI)
"""
import subprocess
import sys
import time
import os
import io

# Fix Windows console encoding for emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure we're running from the project root
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)


def main():
    print()
    print("=" * 60)
    print("  EduStream - Course Platform Launcher")
    print("=" * 60)
    print()

    processes = []

    try:
        # -- Start FastAPI --
        print("[*] Starting FastAPI backend on http://127.0.0.1:8000 ...")
        fastapi_cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.server:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "info",
        ]
        fastapi_proc = subprocess.Popen(
            fastapi_cmd,
            cwd=PROJECT_DIR,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(fastapi_proc)

        # Give FastAPI a moment to start
        time.sleep(2)

        # -- Start Streamlit --
        print()
        print("[*] Starting Streamlit UI on http://localhost:8501 ...")
        print()
        streamlit_cmd = [
            sys.executable, "-m", "streamlit", "run",
            "app.py",
            "--server.port", "8501",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ]
        streamlit_proc = subprocess.Popen(
            streamlit_cmd,
            cwd=PROJECT_DIR,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(streamlit_proc)

        print()
        print("-" * 60)
        print("  Both servers are running!")
        print()
        print("  Open in browser: http://localhost:8501")
        print("  API docs:        http://127.0.0.1:8000/docs")
        print()
        print("  Press Ctrl+C to stop both servers.")
        print("-" * 60)
        print()

        # Wait for either process to exit
        while True:
            for proc in processes:
                retcode = proc.poll()
                if retcode is not None:
                    print(f"\n[!] A process exited with code {retcode}. Shutting down...")
                    raise KeyboardInterrupt
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n[*] Shutting down...")
        for proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass

        # Wait for graceful shutdown
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        print("[*] All servers stopped. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
