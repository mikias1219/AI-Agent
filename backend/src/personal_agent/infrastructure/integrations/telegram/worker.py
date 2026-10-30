"""Dashboard-owned Telegram polling lifecycle; never starts without an explicit request."""

import logging
import threading

from personal_agent.infrastructure.integrations.telegram.runner import TelegramBotRunner

logger = logging.getLogger(__name__)


class TelegramWorker:
    def __init__(self, runner: TelegramBotRunner) -> None:
        self._runner = runner
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._run, daemon=True, name="telegram-bot")
            self._thread.start()

    def _run(self) -> None:
        try:
            self._runner.run_forever(stop_event=self._stop)
        except Exception:
            logger.exception("Telegram worker stopped after an error.")

    def stop(self) -> None:
        self._stop.set()

    def close(self) -> None:
        self.stop()
        if self._thread:
            self._thread.join(timeout=45)
