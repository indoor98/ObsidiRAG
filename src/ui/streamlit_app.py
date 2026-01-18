"""
Simple Streamlit app to list file statuses from the async database.

Run:
    pip install streamlit
    streamlit run ui/streamlit_app.py

Notes:
- This app runs the project's async DB calls in a separate thread event loop when needed.
- Ensure `DATABASE_URL` is configured and the app has been initialized (or `uvicorn` started with `init_db()` ran).
"""

import streamlit as st
import asyncio
import threading
from typing import Any, List, Dict

from src.databases.file.crud import list_all_file_statuses
from src.databases.file.models.file_status_enum import FileStatusEnum
from src.databases.database import AsyncSessionLocal
import os
import requests


def _run_coro_in_thread(coro):
    """Run coroutine in a dedicated thread/event-loop and return result."""
    try:
        # Preferred path if no running loop
        return asyncio.run(coro)
    except RuntimeError:
        # If an event loop is already running (e.g., inside Streamlit), run in separate thread
        result_container = {}

        def _runner():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(coro)
                result_container["result"] = result
            finally:
                loop.close()

        t = threading.Thread(target=_runner)
        t.start()
        t.join()
        return result_container.get("result")


async def _fetch_all_statuses() -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        rows = await list_all_file_statuses(session)
        # convert ORM objects (if any) to dicts
        out = []
        for r in rows:
            try:
                out.append({
                    "id": getattr(r, "id", None),
                    "name": getattr(r, "name", None),
                    "path": getattr(r, "path", None),
                    "status": getattr(r, "status", None),
                })
            except Exception:
                out.append(dict(r))
        return out


def get_all_statuses_sync():
    return _run_coro_in_thread(_fetch_all_statuses())


st.set_page_config(page_title="ObsidiRAG - File Statuses", layout="wide")
st.title("ObsidiRAG — File Statuses")

with st.sidebar:
    st.markdown("### Controls")
    def _safe_rerun():
        try:
            st.experimental_rerun()
        except Exception:
            # fallback for non-Streamlit runtimes or unexpected errors
            st.session_state["_refresh_toggle"] = not st.session_state.get("_refresh_toggle", False)

    if st.button("Refresh"):
        _safe_rerun()

status_options = ["ALL"] + [status.value for status in FileStatusEnum]
status_filter = st.sidebar.selectbox("Filter by status", options=status_options, index=0)

st.info("Fetching records...")
rows = get_all_statuses_sync() or []

if status_filter != "ALL":
    rows = [r for r in rows if (r.get("status") or "").upper() == status_filter]

selected_ids = []
if not rows:
    st.write("No file statuses found.")
else:
    st.write("Select rows to index:")
    cols = st.columns([0.05, 0.2, 0.55, 0.2])
    cols[0].write("")
    cols[1].write("**Name**")
    cols[2].write("**Path**")
    cols[3].write("**Status**")
    for r in rows:
        cb_col, name_col, path_col, status_col = st.columns([0.05, 0.2, 0.55, 0.2])
        key = f"select_{r.get('id') or r.get('path')}"
        checked = cb_col.checkbox("", key=key)
        name_col.write(r.get("name"))
        path_col.write(r.get("path"))
        status_col.write(r.get("status"))
        if checked:
            selected_ids.append(r.get("path"))

    st.markdown("---")
    api_url = os.getenv("API_URL", "http://127.0.0.1:8000")
    if st.button("Start Indexing"):
        if not selected_ids:
            st.warning("No files selected for indexing.")
        else:
            try:
                resp = requests.post(f"{api_url}/api/indexing/run", json={"paths": selected_ids}, timeout=10)
                if resp.status_code == 200:
                    st.success("Indexing started for selected files.")
                else:
                    st.error(f"Indexing API returned {resp.status_code}: {resp.text}")
            except Exception as e:
                st.error(f"Failed to call indexing API: {e}")

st.markdown("---")
st.markdown("Run with: `streamlit run ui/streamlit_app.py`")
