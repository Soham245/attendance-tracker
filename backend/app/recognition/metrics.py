"""Lightweight runtime metrics collector for recognition benchmarking.

Bounded-memory, rolling-window aggregation. Designed to be fed from the
recognition loop's hot path with minimal overhead — each ``record_*`` call
does at most a deque append + a few integer increments.

All latency values are in **milliseconds** (float). Similarity values are
in the unified [0, 1] range. Counters are monotonic within a session.

Thread safety: single-writer (the recognition loop thread) + multi-reader
(status polls). Reads of primitive counters are atomic on CPython. The
``snapshot()`` method copies from deques under a lightweight lock to avoid
torn reads on the ring buffers.

No unbounded storage. No historical persistence. Resets on session start.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


# Ring buffer sizes — tuned for bounded memory at ~12 FPS.
_LATENCY_RING = 120       # ~10 seconds of frame timings
_SIMILARITY_RING = 200    # ~200 recent similarity values


@dataclass
class FrameTimings:
    """Timing breakdown for a single frame, in milliseconds."""
    detection_ms: float = 0.0
    alignment_ms: float = 0.0
    embedding_ms: float = 0.0
    gallery_ms: float = 0.0
    total_ms: float = 0.0
    face_count: int = 0


class RuntimeMetrics:
    """Aggregates operational metrics for one recognition session.

    Usage::

        metrics = RuntimeMetrics()

        # In the frame loop:
        metrics.record_frame(timings)
        metrics.record_recognition(similarity, accepted=True)

        # From status polls:
        snap = metrics.snapshot()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # -- Latency ring buffers (ms) --
        self._frame_latency: Deque[float] = deque(maxlen=_LATENCY_RING)
        self._detection_latency: Deque[float] = deque(maxlen=_LATENCY_RING)
        self._alignment_latency: Deque[float] = deque(maxlen=_LATENCY_RING)
        self._embedding_latency: Deque[float] = deque(maxlen=_LATENCY_RING)
        self._gallery_latency: Deque[float] = deque(maxlen=_LATENCY_RING)

        # -- Face counts per frame --
        self._face_counts: Deque[int] = deque(maxlen=_LATENCY_RING)

        # -- Recognition quality --
        self._similarities: Deque[float] = deque(maxlen=_SIMILARITY_RING)

        # -- Monotonic counters (session lifetime) --
        self._frames_processed: int = 0
        self._total_detections: int = 0
        self._accepted: int = 0
        self._rejected: int = 0
        self._stale: int = 0
        self._unknown: int = 0  # faces with no prediction
        self._out_of_class: int = 0  # recognized but not in session class

        # -- Faculty-facing operational metrics --
        self._seen_student_ids: set = set()  # unique students recognized this session
        self._attendance_marked: int = 0      # attendance records persisted this session

        # -- FPS tracking --
        self._fps_window: Deque[float] = deque(maxlen=30)  # timestamps
        self._session_start: float = time.monotonic()

        # -- Backend info (set once on load) --
        self._detector_backend: str = ""
        self._recognizer_backend: str = ""
        self._gallery_size: int = 0

    # ------------------------------------------------------------------
    # Configuration (called once at session start)
    # ------------------------------------------------------------------

    def set_backends(
        self,
        detector: str,
        recognizer: str,
        gallery_size: int = 0,
    ) -> None:
        self._detector_backend = detector
        self._recognizer_backend = recognizer
        self._gallery_size = gallery_size

    def set_gallery_size(self, size: int) -> None:
        self._gallery_size = size

    # ------------------------------------------------------------------
    # Hot-path recording (called every frame)
    # ------------------------------------------------------------------

    def record_frame(self, timings: FrameTimings) -> None:
        """Record timing breakdown for one processed frame."""
        now = time.monotonic()
        with self._lock:
            self._frame_latency.append(timings.total_ms)
            self._detection_latency.append(timings.detection_ms)
            if timings.alignment_ms > 0:
                self._alignment_latency.append(timings.alignment_ms)
            if timings.embedding_ms > 0:
                self._embedding_latency.append(timings.embedding_ms)
            if timings.gallery_ms > 0:
                self._gallery_latency.append(timings.gallery_ms)
            self._face_counts.append(timings.face_count)
            self._frames_processed += 1
            self._total_detections += timings.face_count
            self._fps_window.append(now)

    def record_recognition(
        self,
        similarity: float,
        *,
        accepted: bool,
    ) -> None:
        """Record one recognition prediction (after threshold check)."""
        with self._lock:
            self._similarities.append(similarity)
            if accepted:
                self._accepted += 1
            else:
                self._rejected += 1

    def record_student_seen(self, student_id: int) -> None:
        """Track unique student IDs recognized this session."""
        self._seen_student_ids.add(student_id)

    def record_attendance_marked(self) -> None:
        """Increment when an attendance record is persisted."""
        self._attendance_marked += 1

    def record_stale(self, count: int = 1) -> None:
        self._stale += count

    def record_unknown(self, count: int = 1) -> None:
        self._unknown += count

    def record_out_of_class(self, count: int = 1) -> None:
        """Count recognized students filtered out by class scope."""
        self._out_of_class += count

    # ------------------------------------------------------------------
    # Snapshot (called from status polls — low frequency)
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of all metrics."""
        with self._lock:
            frame_lat = list(self._frame_latency)
            det_lat = list(self._detection_latency)
            align_lat = list(self._alignment_latency)
            emb_lat = list(self._embedding_latency)
            gal_lat = list(self._gallery_latency)
            face_counts = list(self._face_counts)
            sims = list(self._similarities)
            fps_times = list(self._fps_window)

        return {
            "backends": {
                "detector": self._detector_backend,
                "recognizer": self._recognizer_backend,
                "gallery_size": self._gallery_size,
            },
            "counters": {
                "frames_processed": self._frames_processed,
                "total_detections": self._total_detections,
                "accepted": self._accepted,
                "rejected": self._rejected,
                "stale": self._stale,
                "unknown": self._unknown,
                "out_of_class": self._out_of_class,
            },
            "operational": {
                "unique_students_present": len(self._seen_student_ids),
                "attendance_marked": self._attendance_marked,
            },
            "latency": {
                "frame": _latency_stats(frame_lat),
                "detection": _latency_stats(det_lat),
                "alignment": _latency_stats(align_lat),
                "embedding": _latency_stats(emb_lat),
                "gallery": _latency_stats(gal_lat),
            },
            "detection": {
                "avg_faces_per_frame": _mean(face_counts),
                "fps": _compute_fps(fps_times),
            },
            "recognition": _similarity_stats(sims),
            "uptime_seconds": round(time.monotonic() - self._session_start, 1),
        }


# ----------------------------------------------------------------------
# Pure helper functions (no side effects, no allocations on empty input)
# ----------------------------------------------------------------------

def _latency_stats(values: List[float]) -> Optional[Dict[str, float]]:
    """Compute p50/p95/mean/max over a latency sample."""
    if not values:
        return None
    n = len(values)
    s = sorted(values)
    return {
        "mean": round(sum(s) / n, 2),
        "p50": round(s[n // 2], 2),
        "p95": round(s[min(int(n * 0.95), n - 1)], 2),
        "max": round(s[-1], 2),
        "samples": n,
    }


def _similarity_stats(values: List[float]) -> Optional[Dict[str, Any]]:
    """Compute aggregated recognition quality metrics."""
    if not values:
        return None
    n = len(values)
    s = sorted(values)
    return {
        "count": n,
        "mean": round(sum(s) / n, 4),
        "min": round(s[0], 4),
        "max": round(s[-1], 4),
        "p50": round(s[n // 2], 4),
        "p95": round(s[min(int(n * 0.95), n - 1)], 4),
        "worst_accepted": round(s[0], 4),  # min similarity that passed threshold
    }


def _mean(values: List[int | float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _compute_fps(timestamps: List[float]) -> float:
    """Estimate FPS from a window of frame timestamps."""
    if len(timestamps) < 2:
        return 0.0
    span = timestamps[-1] - timestamps[0]
    if span <= 0:
        return 0.0
    return round((len(timestamps) - 1) / span, 1)
