"""Multi-frame recognition confirmation and confidence smoothing.

Gates event emission on sustained identity: a student must appear in at
least N of the last M frames (with acceptable confidence) before the
runtime treats the recognition as operationally confirmed.  This
dramatically reduces single-frame false positives and identity flickering.

Also provides an exponential moving average (EMA) of the recognition
metric so the emitted confidence is smoothed rather than jittery
frame-to-frame. The tracker is metric-agnostic — it smooths whatever
value the backend produces (LBPH distance, cosine similarity, or the
unified similarity score from the abstraction layer).

In-memory only. Per-runtime-session (the runtime constructs a fresh
instance on start). Threadsafe but designed for single-writer (the
recognition loop thread).
"""
from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from app.config.settings import settings
from app.core.logging import get_logger


logger = get_logger("attendai.recognition.tracker")


@dataclass(frozen=True)
class _Observation:
    frame_num: int
    distance: float


class FrameTracker:
    """Per-student sliding window of recent observations.

    Usage from the runtime loop::

        tracker.record(student_id, similarity, frame_num)
        if tracker.is_confirmed(student_id):
            smoothed = tracker.smoothed_metric(student_id)
            # emit recognition event with smoothed confidence
    """

    def __init__(
        self,
        window: int | None = None,
        required: int | None = None,
        alpha: float | None = None,
    ) -> None:
        self._window = window if window is not None else settings.RECOGNITION_CONFIRM_WINDOW
        self._required = required if required is not None else settings.RECOGNITION_CONFIRM_REQUIRED
        self._alpha = alpha if alpha is not None else settings.RECOGNITION_SMOOTHING_ALPHA
        self._tracks: Dict[int, deque[_Observation]] = defaultdict(
            lambda: deque(maxlen=self._window)
        )
        self._ema: Dict[int, float] = {}
        self._lock = threading.Lock()

    def record(self, student_id: int, distance: float, frame_num: int) -> None:
        """Append an observation for this student in the current frame."""
        with self._lock:
            self._tracks[student_id].append(
                _Observation(frame_num=frame_num, distance=distance)
            )
            prev = self._ema.get(student_id)
            if prev is None:
                self._ema[student_id] = distance
            else:
                self._ema[student_id] = self._alpha * distance + (1 - self._alpha) * prev

    def is_confirmed(self, student_id: int) -> bool:
        """True if the student appeared in >= required of the last window frames."""
        with self._lock:
            track = self._tracks.get(student_id)
            if track is None or len(track) < self._required:
                return False
            return len(track) >= self._required

    def smoothed_metric(self, student_id: int) -> Optional[float]:
        """Return the EMA-smoothed metric value, or None if no observations.

        The smoothed value has the same semantics as whatever the caller
        recorded — if recording unified similarity, the result is smoothed
        similarity; if recording raw distance, smoothed distance.
        """
        with self._lock:
            return self._ema.get(student_id)

    # Backward-compat alias — will be removed in a future cleanup.
    def smoothed_distance(self, student_id: int) -> Optional[float]:
        return self.smoothed_metric(student_id)

    def prune(self, current_frame: int) -> None:
        """Drop students whose newest observation is too old.

        Called lazily from the runtime loop; not on every frame — only when
        the track count grows beyond a soft threshold.
        """
        cutoff = current_frame - self._window * 3
        with self._lock:
            stale = [
                sid for sid, track in self._tracks.items()
                if track and track[-1].frame_num < cutoff
            ]
            for sid in stale:
                del self._tracks[sid]
                self._ema.pop(sid, None)

    def reset(self) -> None:
        with self._lock:
            self._tracks.clear()
            self._ema.clear()
