"""Runtime DB-authoritative identity validator.

Sits between the recognizer (a prediction engine) and the recognition runtime.
The database is the authoritative source of valid operational identities — a
model can still return a label for a student that has since been deleted, so
every confident prediction is checked against the DB before being treated as
operationally valid.

A short TTL cache absorbs the per-frame-per-face hit. Cache entries are
invalidated explicitly on student delete so the runtime sees the change
immediately, not after the TTL expires.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple

from sqlalchemy import select

from app.core.logging import get_logger
from app.database.db import SessionLocal
from app.database.models.student import Student


logger = get_logger("attendai.recognition.identity")


_DEFAULT_TTL_SECONDS = 5.0


class IdentityValidator:
    """Threadsafe `student_id -> exists` cache backed by SQLAlchemy.

    `exists(id)` returns True iff a row with that primary key is present in
    the students table. False is returned for any DB error so the runtime
    fails closed (treating the prediction as stale) rather than emitting
    events that may target a deleted student.
    """

    def __init__(self, ttl_seconds: float = _DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._cache: Dict[int, Tuple[bool, float]] = {}
        self._lock = threading.Lock()

    def exists(self, student_id: int) -> bool:
        try:
            sid = int(student_id)
        except (TypeError, ValueError):
            return False

        now = time.monotonic()
        with self._lock:
            entry = self._cache.get(sid)
            if entry is not None and (now - entry[1]) < self._ttl:
                return entry[0]

        present = self._lookup(sid)
        with self._lock:
            self._cache[sid] = (present, now)
        return present

    def invalidate(self, student_id: int) -> None:
        try:
            sid = int(student_id)
        except (TypeError, ValueError):
            return
        with self._lock:
            self._cache.pop(sid, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def _lookup(self, student_id: int) -> bool:
        try:
            with SessionLocal() as db:
                row = db.execute(
                    select(Student.id).where(
                        Student.id == student_id,
                        Student.status == "active",
                    )
                ).first()
                return row is not None
        except Exception as exc:  # noqa: BLE001 — fail closed, don't crash loop
            logger.warning("Identity lookup failed student_id=%s: %s", student_id, exc)
            return False


# Module-level singleton mirrors the day-guard pattern in attendance_service.
# The recognition runtime and the student delete path both reach for the same
# instance, so cache invalidation is global by construction.
_validator = IdentityValidator()


def get_validator() -> IdentityValidator:
    return _validator


def invalidate(student_id: int) -> None:
    _validator.invalidate(student_id)
