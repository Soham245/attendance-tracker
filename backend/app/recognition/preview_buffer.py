"""Single-slot MJPEG preview buffer.

The recognition runtime publishes annotated JPEG bytes here; the streaming
endpoint reads the latest frame.  Latest-frame-wins — no queue, no history,
no buildup.  Thread-safe via a simple lock + Event for signaling.

Shutdown: call ``shutdown()`` to unblock any waiters and signal generators
to stop iterating.  Generators should check ``is_shutdown`` after ``wait()``.
"""
from __future__ import annotations

import threading
from typing import Optional


class PreviewBuffer:
    """Holds exactly one JPEG frame.  Writers overwrite; readers get latest."""

    def __init__(self) -> None:
        self._frame: Optional[bytes] = None
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._shutdown = False

    @property
    def is_shutdown(self) -> bool:
        return self._shutdown

    def publish(self, jpeg_bytes: bytes) -> None:
        with self._lock:
            self._frame = jpeg_bytes
        self._event.set()

    def latest(self) -> Optional[bytes]:
        with self._lock:
            return self._frame

    def wait(self, timeout: float = 1.0) -> Optional[bytes]:
        """Block until a new frame is published, timeout, or shutdown."""
        self._event.wait(timeout=timeout)
        self._event.clear()
        if self._shutdown:
            return None
        return self.latest()

    def clear(self) -> None:
        with self._lock:
            self._frame = None
        self._event.clear()

    def shutdown(self) -> None:
        """Signal all waiters to stop. Unblocks any pending ``wait()``."""
        self._shutdown = True
        self._event.set()
