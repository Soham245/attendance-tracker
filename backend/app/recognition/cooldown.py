"""Runtime-scoped per-student recognition cooldown.

Suppresses repeated events for the SAME student within a short window so the
event stream isn't flooded by every frame of a continuous detection. Other
students are unaffected — each student has its own last-seen timestamp.

In-memory only. No persistence. No background workers — stale entries are
pruned lazily during checks. Attendance persistence has its own (per-day)
duplicate suppression; this layer is purely operational.
"""
from __future__ import annotations

import threading
import time
from typing import Dict

from app.config.settings import settings
from app.core.logging import get_logger


logger = get_logger("attendai.recognition.cooldown")


class RecognitionCooldown:
    """Tracks `student_id -> last_emitted_monotonic_ts`.

    `should_emit` is O(1) amortized. A small lazy prune runs when the registry
    grows past a soft threshold, dropping entries older than the prune window.
    """

    _PRUNE_THRESHOLD = 64  # entries before we consider a pass

    def __init__(
        self,
        cooldown_seconds: float | None = None,
        prune_seconds: float | None = None,
    ) -> None:
        self._cooldown = (
            cooldown_seconds
            if cooldown_seconds is not None
            else settings.RECOGNITION_COOLDOWN_SECONDS
        )
        self._prune = (
            prune_seconds
            if prune_seconds is not None
            else settings.RECOGNITION_COOLDOWN_PRUNE_SECONDS
        )
        self._last: Dict[int, float] = {}
        self._lock = threading.Lock()

    @property
    def cooldown_seconds(self) -> float:
        return self._cooldown

    def should_emit(self, student_id: int) -> bool:
        """Return True if this student is OUT of cooldown; refresh the stamp."""
        try:
            sid = int(student_id)
        except (TypeError, ValueError):
            # Be defensive: never crash the runtime over a bad event.
            logger.warning("Cooldown received non-int student_id=%r", student_id)
            return True

        now = time.monotonic()
        with self._lock:
            last = self._last.get(sid)
            if last is not None and (now - last) < self._cooldown:
                return False
            self._last[sid] = now
            if len(self._last) > self._PRUNE_THRESHOLD:
                self._prune_locked(now)
        return True

    def reset(self) -> None:
        with self._lock:
            self._last.clear()

    def _prune_locked(self, now: float) -> None:
        cutoff = now - self._prune
        stale = [sid for sid, ts in self._last.items() if ts < cutoff]
        for sid in stale:
            self._last.pop(sid, None)
