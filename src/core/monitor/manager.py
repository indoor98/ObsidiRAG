"""
watchdog 실행 및 관리
"""

from typing import Callable, Optional
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, PatternMatchingEventHandler
from src.core.monitor.handler import WatchdogHandler


class WatchdogManager:
	"""간단한 watchdog Observer 관리기.

	기능:
	- start/stop/restart
	- 사용자 콜백 등록
	- 예외 발생 시 안전하게 중단
	"""

	def __init__(
		self,
		path: str,
		callback: Optional[Callable[[FileSystemEvent], None]] = None,
		recursive: bool = True,
		logger: Optional[logging.Logger] = None,
	) -> None:
		self.path = path
		self.recursive = recursive
		self.logger = logger or logging.getLogger(__name__)
		self._observer: Optional[Observer] = None
		self._handler: Optional[FileSystemEventHandler, PatternMatchingEventHandler] = None
		if callback is not None:
			self.set_callback(callback)

	def set_callback(self, callback: Callable[[FileSystemEvent], None]) -> None:
		"""파일 이벤트가 발생했을 때 호출할 콜백을 등록합니다."""
		self._handler = WatchdogHandler(callback)

	def start(self) -> None:
		"""Observer를 시작합니다. 이미 시작된 경우는 무시합니다."""
		if self._observer is not None:
			self.logger.debug("Observer already running")
			return

		self._observer = Observer()
		handler = self._handler or WatchdogHandler(lambda e: self.logger.debug(f"event: {e}"))
		self._observer.schedule(handler, self.path, recursive=self.recursive)
		try:
			self._observer.start()
			self.logger.info(f"Started watchdog on: {self.path} (recursive={self.recursive})")
		except Exception as exc:  # pragma: no cover - runtime safety
			self.logger.exception("Failed to start watchdog observer: %s", exc)
			self._observer = None

	def stop(self, timeout: float = 5.0) -> None:
		"""Observer를 중지하고 join 합니다."""
		if not self._observer:
			self.logger.debug("Observer not running")
			return
		try:
			self._observer.stop()
			self._observer.join(timeout)
			self.logger.info("Stopped watchdog observer")
		except Exception as exc:  # pragma: no cover - runtime safety
			self.logger.exception("Error stopping observer: %s", exc)
		finally:
			self._observer = None

	def restart(self) -> None:
		"""Observer를 재시작합니다."""
		self.logger.info("Restarting watchdog observer")
		self.stop()
		self.start()

	@property
	def is_running(self) -> bool:
		return self._observer is not None and getattr(self._observer, "is_alive", lambda: True)()

	def __enter__(self) -> "WatchdogManager":
		self.start()
		return self

	def __exit__(self, exc_type, exc, tb) -> None:
		self.stop()

