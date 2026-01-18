from src.core.monitor.manager import WatchdogManager


from fastapi import FastAPI
from contextlib import asynccontextmanager
import subprocess
import sys
import os
from pathlib import Path
import socket
import time

from src.config import FILE_PATH
from src.databases.database import get_db, init_db

from src.core.indexing.api import router as indexing_router
from src.core.monitor.api import router as monitor_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize database (async)
    await init_db()
    print("Database initialized.")
    # Start Streamlit as a background subprocess
    streamlit_proc = None
    try:
        project_root = Path(__file__).resolve().parent.parent
        streamlit_script = project_root / "src" / "ui" / "streamlit_app.py"
        streamlit_port = int(os.getenv("STREAMLIT_PORT", "8501"))
        cmd = [sys.executable, "-m", "streamlit", "run", str(streamlit_script), "--server.port", str(streamlit_port), "--server.headless", "true"]
        log_file = project_root / "streamlit.log"
        lf = open(log_file, "a")
        streamlit_proc = subprocess.Popen(cmd, cwd=str(project_root), stdout=lf, stderr=subprocess.STDOUT)
        print(f"Started Streamlit (pid={streamlit_proc.pid}) on port {streamlit_port}, logging to {log_file}")

        # wait for port to become available
        def _port_open(host: str, port: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex((host, port)) == 0

        host = "127.0.0.1"
        timeout = 10
        start = time.time()
        while time.time() - start < timeout:
            if _port_open(host, streamlit_port):
                print(f"Streamlit reachable at http://{host}:{streamlit_port}")
                break
            if streamlit_proc.poll() is not None:
                # process exited
                print("Streamlit process exited early; check streamlit.log for details")
                break
            time.sleep(0.5)
        else:
            print(f"Streamlit did not become reachable on port {streamlit_port} within {timeout}s; see {log_file}")
    except Exception as exc:
        print("Failed to start Streamlit:", exc)

    manager = WatchdogManager(FILE_PATH)
    try:
        manager.start()
        print("Watchdog observer started.")
        yield
    finally:
        manager.stop()
        print("Watchdog observer stopped.")
        if streamlit_proc:
            try:
                streamlit_proc.terminate()
                streamlit_proc.wait(timeout=5)
                print("Streamlit subprocess terminated.")
            except Exception:
                try:
                    streamlit_proc.kill()
                except Exception:
                    pass

app = FastAPI(lifespan=lifespan)
app.include_router(indexing_router)
app.include_router(monitor_router)

@app.get("/")
async def root():
    return {"status": "RAG System is running"}