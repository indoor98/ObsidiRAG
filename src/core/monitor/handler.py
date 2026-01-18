import time
import os
import asyncio
from watchdog.events import FileSystemEventHandler, PatternMatchingEventHandler
from watchdog.observers import Observer
from uuid import uuid4

from src.databases.file.crud import (
    create_file_status,
    update_file_status,
    delete_file_status,
    get_file_status_by_path,
    rename_file_status,
)
from src.databases.file.models.file_status import FileStatus
from src.databases.file.models.file_status_enum import FileStatusEnum
from src.databases.database import AsyncSessionLocal

class WatchdogHandler(PatternMatchingEventHandler):
    """
    handles events for a specific event target file system path
    """

    def __init__(self, Callback=None):
        super().__init__(
            patterns=["*"], ignore_patterns=["*/.obsidian/workspace.json", "*/env/*"], 
            ignore_directories=True, case_sensitive=True
        )
        self.callback = Callback
        try:
            # capture the running loop if available so we can schedule coroutines
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    async def _create_file_status_async(self, file_status: FileStatus):
        async with AsyncSessionLocal() as session:
            await create_file_status(db=session, file_status=file_status)
    
    async def _update_file_status_async(self, file_path: str, new_status: FileStatusEnum = FileStatusEnum.MODIFIED):
        async with AsyncSessionLocal() as session:
            existing = await get_file_status_by_path(db=session, file_path=file_path)
            if existing:
                await update_file_status(db=session, file_id=existing.id, new_status=new_status)

    async def _delete_file_status_async(self, file_path: str):
        async with AsyncSessionLocal() as session:
            existing = await get_file_status_by_path(db=session, file_path=file_path)
            if existing:
                await delete_file_status(db=session, file_id=existing.id)

    async def _rename_file_status_async(self, old_path: str, new_path: str):
        async with AsyncSessionLocal() as session:
            await rename_file_status(db=session, old_path=old_path, new_path=new_path)

    def on_created(self, event):
        if not event.is_directory:
            print(f"[생성] 파일이 생성되었습니다: {event.src_path}")
            file_status = FileStatus(
                id=uuid4().hex,
                name=os.path.basename(event.src_path),
                path=event.src_path,
                status=FileStatusEnum.PENDING
            )
            # Schedule DB write on the main asyncio loop if available
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._create_file_status_async(file_status), self._loop)
            else:
                # fallback: run in a new event loop (blocking this thread)
                asyncio.run(self._create_file_status_async(file_status))


    def on_modified(self, event):
        if not event.is_directory:
            print(f"[수정] 파일이 수정되었습니다: {event.src_path}")
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._update_file_status_async(event.src_path, FileStatusEnum.MODIFIED), self._loop)
            else:
                asyncio.run(self._update_file_status_async(event.src_path, FileStatusEnum.MODIFIED))

    def on_deleted(self, event):
        if not event.is_directory:
            print(f"[삭제] 파일이 삭제되었습니다: {event.src_path}")
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._delete_file_status_async(event.src_path), self._loop)
            else:
                asyncio.run(self._delete_file_status_async(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            print(f"[이동] 파일이 이동/이름변경 되었습니다: {event.src_path} -> {event.dest_path}")
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._rename_file_status_async(event.src_path, event.dest_path), self._loop)
            else:
                asyncio.run(self._rename_file_status_async(event.src_path, event.dest_path))


# 2. Set up the observer
if __name__ == "__main__":
    path = "/Users/th/Desktop/obsidian/JHM"
    event_handler = WatchdogHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"모니터링을 시작합니다... (경로: {os.path.abspath(path)})")

    try:
        # 스크립트가 종료되지 않도록 무한 루프
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Ctrl+C로 종료 시
        observer.stop()
        print("모니터링을 종료합니다.")
    
    observer.join()