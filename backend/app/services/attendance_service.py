"""Attendance domain: consume recognition events + query persisted records.

The recognition runtime publishes events to `app.state.recognition_event_queue`;
an ingestion worker (owned by this module, started in the lifespan) drains
the queue and calls `consume_event` for each item. The runtime stays
unaware of attendance rules — recognition identifies, attendance decides.

Uniqueness enforcement is two-layered:

1. **In-memory guard** (`_day_guard`): a fast-path set of `(student_id, day)`
   tuples that have already been persisted.  Populated on successful insert,
   invalidated on admin delete.  Avoids redundant DB queries when the runtime
   keeps recognising the same student after the recognition cooldown expires.

2. **DB check** (`_existing_for_day`): authoritative per-day duplicate query.
   Still runs as defence-in-depth whenever the guard misses (cold start,
   process restart, guard race).
"""
from __future__ import annotations

import queue
import threading
from datetime import date as date_t, datetime, time, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import get_logger
from app.database.db import SessionLocal
from app.database.models.attendance import Attendance
from app.database.models.student import Student


logger = get_logger("attendai.attendance")


# ---------------------------------------------------------------------------
# In-memory per-day attendance guard
# ---------------------------------------------------------------------------

class _DayGuard:
    """Thread-safe set of (student_id, date_iso) already persisted today.

    Acts as a fast-path so the ingestion worker can skip the DB query for
    students whose attendance was already recorded this run.  Invalidated
    entry-by-entry on admin delete so re-recognition can insert again.
    """

    def __init__(self) -> None:
        self._marked: Set[Tuple[int, str]] = set()
        self._lock = threading.Lock()

    def is_marked(self, student_id: int, day: date_t) -> bool:
        with self._lock:
            return (student_id, day.isoformat()) in self._marked

    def mark(self, student_id: int, day: date_t) -> None:
        with self._lock:
            self._marked.add((student_id, day.isoformat()))

    def unmark(self, student_id: int, day: date_t) -> None:
        with self._lock:
            self._marked.discard((student_id, day.isoformat()))

    def reset(self) -> None:
        with self._lock:
            self._marked.clear()


_day_guard = _DayGuard()


def is_attendance_marked(student_id: int, day: date_t) -> bool:
    """Public read-only query on the guard.

    Lets the recognition runtime skip event emission for students whose
    attendance is already persisted today, without importing guard internals.
    """
    return _day_guard.is_marked(student_id, day)


# ---- Persistence -----------------------------------------------------------


def _existing_for_day(db: Session, student_id: int, day: date_t) -> Optional[Attendance]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    return db.execute(
        select(Attendance)
        .where(Attendance.student_id == student_id)
        .where(Attendance.recognized_at >= start)
        .where(Attendance.recognized_at <= end)
    ).scalar_one_or_none()


def _coerce_recognized_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Invalid recognized_at") from exc
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    raise ValueError("recognized_at must be a datetime or ISO string")


def consume_event(
    db: Session, event: Dict[str, Any], app_state: Any = None
) -> Optional[Attendance]:
    """Validate + persist one recognition event.

    Returns the new `Attendance` row on success, or `None` when the event is
    ignored (duplicate for the day, unknown student, low confidence, malformed).
    Never raises for routine validation failures — those are logged and dropped
    so the ingestion loop keeps moving.
    """
    try:
        student_id = int(event["student_id"])
        confidence = float(event["confidence"])
        recognized_at = _coerce_recognized_at(event["recognized_at"])
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Dropping malformed recognition event: %s (%s)", event, exc)
        return None

    # Confidence is unified similarity [0, 1] (higher = better match). The
    # runtime already gated unknowns; this is defense in depth in case an
    # upstream change loosens the runtime threshold.
    if confidence < settings.RECOGNITION_SIMILARITY_THRESHOLD:
        logger.info(
            "Dropping low-confidence event student_id=%s sim=%.4f (threshold=%.4f)",
            student_id, confidence, settings.RECOGNITION_SIMILARITY_THRESHOLD,
        )
        return None

    student = db.get(Student, student_id)
    if student is None:
        # The runtime's identity validator should have suppressed this before
        # it ever reached the queue. Reaching here implies a cache race or a
        # bypassed gate — louder log so it surfaces in operations.
        logger.warning(
            "Stale recognition reached ingestion (validator gap) student_id=%s",
            student_id,
        )
        return None

    day = recognized_at.astimezone(timezone.utc).date()

    # Fast path: in-memory guard says this student already has attendance today.
    if _day_guard.is_marked(student_id, day):
        return None

    # Slow path: authoritative DB check (cold start, guard miss, race).
    if _existing_for_day(db, student_id, day) is not None:
        _day_guard.mark(student_id, day)  # warm the guard for next time
        logger.info(
            "Duplicate attendance suppressed student_id=%s date=%s", student_id, day
        )
        return None

    # Stamp active session_id if a class-scoped session is running.
    active_session_id = None
    if app_state is not None:
        active = getattr(app_state, "active_session", None)
        if active:
            active_session_id = active.get("session_id")

    record = Attendance(
        student_id=student_id,
        session_id=active_session_id,
        recognized_at=recognized_at,
        confidence=confidence,
        status="present",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    _day_guard.mark(student_id, day)
    logger.info(
        "Attendance recorded student_id=%s date=%s confidence=%.2f",
        student_id, day, confidence,
    )
    return record


# ---- Queries ---------------------------------------------------------------


def get_attendance(db: Session, attendance_id: int) -> Attendance:
    from fastapi import status

    from app.core.exceptions import AppException

    record = db.get(Attendance, attendance_id)
    if record is None:
        raise AppException(
            "Attendance record not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="attendance_not_found",
        )
    return record


def delete_attendance(db: Session, attendance_id: int) -> Dict[str, Any]:
    """Delete an attendance record by id. Raises 404 if it doesn't exist.

    Returns the deleted record's `(student_id, recognized_at)` so the route
    can invalidate matching entries in the runtime's recent-recognitions
    deque — keeping the operator-facing feed in sync with persisted truth.
    """
    record = get_attendance(db, attendance_id)
    student_id = record.student_id
    recognized_at = record.recognized_at
    day = recognized_at.astimezone(timezone.utc).date()
    db.delete(record)
    db.commit()
    # Invalidate the guard so the student can be re-recognised for this day.
    _day_guard.unmark(student_id, day)
    logger.info("Attendance deleted id=%s student_id=%s date=%s", attendance_id, student_id, day)
    return {"student_id": student_id, "recognized_at": recognized_at}


def invalidate_recent_event(
    app_state: Any, student_id: int, recognized_at: datetime
) -> int:
    """Drop matching entries from the runtime's recent-recognitions deque.

    Matches on `(student_id, recognized_at)` — `consume_event` persists the
    event's `recognized_at` verbatim, so the same value identifies both sides.
    Also clears `last_event` if it pointed at the removed entry.

    Returns the number of deque entries removed (0 when the runtime isn't
    holding the event anymore — already rotated out, or never started).
    """
    target_iso = recognized_at.astimezone(timezone.utc).isoformat()

    def _matches(evt: Dict[str, Any]) -> bool:
        try:
            if int(evt.get("student_id")) != int(student_id):
                return False
        except (TypeError, ValueError):
            return False
        evt_at = evt.get("recognized_at")
        if not isinstance(evt_at, str):
            return False
        try:
            evt_dt = datetime.fromisoformat(evt_at)
        except ValueError:
            return evt_at == target_iso
        if evt_dt.tzinfo is None:
            evt_dt = evt_dt.replace(tzinfo=timezone.utc)
        return evt_dt == recognized_at.astimezone(timezone.utc)

    removed = 0
    recent = getattr(app_state, "recognition_recent_events", None)
    if recent is not None:
        kept = [evt for evt in recent if not _matches(evt)]
        removed = len(recent) - len(kept)
        if removed:
            recent.clear()
            recent.extend(kept)

    runtime_state = getattr(app_state, "recognition_runtime", None)
    if isinstance(runtime_state, dict):
        last = runtime_state.get("last_event")
        if isinstance(last, dict) and _matches(last):
            app_state.recognition_runtime = {**runtime_state, "last_event": None}

    if removed:
        logger.info(
            "Recent recognition invalidated student_id=%s recognized_at=%s removed=%d",
            student_id, target_iso, removed,
        )
    return removed


def list_attendance(
    db: Session,
    *,
    student_id: Optional[int] = None,
    session_id: Optional[int] = None,
    class_id: Optional[int] = None,
    on_date: Optional[date_t] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Attendance], int]:
    from app.database.models.attendance_session import AttendanceSession

    stmt = select(Attendance)
    count_stmt = select(func.count()).select_from(Attendance)

    if class_id is not None:
        stmt = stmt.join(AttendanceSession, Attendance.session_id == AttendanceSession.id).where(
            AttendanceSession.class_id == class_id
        )
        count_stmt = count_stmt.join(
            AttendanceSession, Attendance.session_id == AttendanceSession.id
        ).where(AttendanceSession.class_id == class_id)

    if student_id is not None:
        stmt = stmt.where(Attendance.student_id == student_id)
        count_stmt = count_stmt.where(Attendance.student_id == student_id)
    if session_id is not None:
        stmt = stmt.where(Attendance.session_id == session_id)
        count_stmt = count_stmt.where(Attendance.session_id == session_id)
    if on_date is not None:
        start = datetime.combine(on_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(on_date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(Attendance.recognized_at >= start, Attendance.recognized_at <= end)
        count_stmt = count_stmt.where(
            Attendance.recognized_at >= start, Attendance.recognized_at <= end
        )

    total = db.scalar(count_stmt) or 0
    items = (
        db.execute(stmt.order_by(Attendance.recognized_at.desc()).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return list(items), total


# ---- Ingestion worker ------------------------------------------------------


def _ingestion_loop(
    event_queue: "queue.Queue[Dict[str, Any]]",
    stop_event: threading.Event,
    app_state: Any = None,
) -> None:
    logger.info("Attendance ingestion worker started")
    while not stop_event.is_set():
        try:
            event = event_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            with SessionLocal() as db:
                record = consume_event(db, event, app_state=app_state)
                # Notify the runtime metrics collector when attendance is persisted.
                if record is not None and app_state is not None:
                    collector = getattr(app_state, "runtime_metrics_collector", None)
                    if collector is not None:
                        collector.record_attendance_marked()
        except Exception as exc:  # noqa: BLE001 — keep the worker alive
            logger.exception("Failed to ingest recognition event: %s", exc)
    logger.info("Attendance ingestion worker stopped")


def start_ingestion(app_state: Any) -> threading.Thread:
    stop_event = threading.Event()
    app_state.attendance_stop_event = stop_event
    thread = threading.Thread(
        target=_ingestion_loop,
        args=(app_state.recognition_event_queue, stop_event, app_state),
        name="attendai-attendance",
        daemon=True,
    )
    thread.start()
    app_state.attendance_thread = thread
    return thread


def stop_ingestion(app_state: Any) -> None:
    """Signal the ingestion worker to stop.

    Sets the stop event; the lifespan handles the bounded thread join.
    """
    stop_event = getattr(app_state, "attendance_stop_event", None)
    if stop_event is not None:
        stop_event.set()


def ingestion_alive(app_state: Any) -> bool:
    thread = getattr(app_state, "attendance_thread", None)
    return thread is not None and thread.is_alive()
