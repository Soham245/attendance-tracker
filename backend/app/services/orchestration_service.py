"""Live-attendance session orchestration.

Thin coordinator that:
- starts/stops the recognition runtime (attendance ingestion is always-on,
  managed by the lifespan)
- creates / ends an AttendanceSession row to scope attendance to one class
- derives allowed_student_ids at session start for post-recognition filtering
- aggregates operational visibility across recognition + ingestion +
  active model + recent events

No business logic lives here. Recognition identifies, attendance decides,
orchestration coordinates.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.recognition import model_manager
from app.services import attendance_service, recognition_service, session_service


SESSION_IDLE = "idle"
SESSION_STARTING = "starting"
SESSION_RUNNING = "running"
SESSION_STOPPING = "stopping"
SESSION_FAILED = "failed"


def _session_state_from(runtime_state: str) -> str:
    return {
        "idle": SESSION_IDLE,
        "starting": SESSION_STARTING,
        "running": SESSION_RUNNING,
        "stopping": SESSION_STOPPING,
        "failed": SESSION_FAILED,
    }.get(runtime_state, SESSION_IDLE)


def start_session(
    app_state: Any,
    *,
    db: Session,
    class_id: int,
    faculty_id: int,
    session_name: Optional[str] = None,
    is_admin: bool = False,
) -> Dict[str, Any]:
    """Begin a live attendance session scoped to a class.

    1. Create an AttendanceSession row.
    2. Derive allowed_student_ids from class enrollment.
    3. Store session context on app.state.
    4. Start the recognition runtime.
    """
    # Create the DB session row (validates class + faculty access).
    att_session = session_service.create_session(
        db,
        class_id=class_id,
        faculty_id=faculty_id,
        session_name=session_name,
        is_admin=is_admin,
    )

    # Derive allowed student IDs for this class.
    allowed_ids = session_service.allowed_student_ids(db, class_id)

    # Store on app.state so runtime + ingestion can reference them.
    app_state.active_session = {
        "session_id": att_session.id,
        "class_id": class_id,
        "faculty_id": faculty_id,
        "session_name": att_session.session_name,
    }
    app_state.session_allowed_ids = allowed_ids

    # Start recognition runtime.
    recognition_service.start(app_state)

    return get_status(app_state)


def stop_session(app_state: Any) -> Dict[str, Any]:
    """End the current session.

    1. Stop the recognition runtime.
    2. End the AttendanceSession row.
    3. Clear session context from app.state.
    """
    recognition_service.stop(app_state)

    # End the DB session row.
    active = getattr(app_state, "active_session", None)
    if active and active.get("session_id"):
        try:
            with SessionLocal() as db:
                session_service.end_session(db, active["session_id"])
        except Exception:
            # Session row update failed — log but don't block shutdown.
            import logging
            logging.getLogger("attendai.orchestration").exception(
                "Failed to end session row id=%s", active["session_id"]
            )

    # Clear app.state session context.
    app_state.active_session = None
    app_state.session_allowed_ids = set()

    return get_status(app_state)


def _queue_size(app_state: Any) -> int:
    q = getattr(app_state, "recognition_event_queue", None)
    return q.qsize() if q is not None else 0


def _recent_events(app_state: Any) -> List[Dict[str, Any]]:
    buf = getattr(app_state, "recognition_recent_events", None)
    return list(buf) if buf is not None else []


def _active_model_metadata() -> Optional[Dict[str, Any]]:
    return model_manager.get_active_metadata()


def get_status(app_state: Any) -> Dict[str, Any]:
    recognition_state = recognition_service.get_status(app_state)

    # Include active session info if present.
    active = getattr(app_state, "active_session", None)
    active_session_info = None
    if active:
        active_session_info = {
            "session_id": active.get("session_id"),
            "class_id": active.get("class_id"),
            "session_name": active.get("session_name"),
            "allowed_count": len(getattr(app_state, "session_allowed_ids", set())),
        }

    return {
        "session_state": _session_state_from(recognition_state["state"]),
        "recognition": recognition_state,
        "ingestion": {
            "alive": attendance_service.ingestion_alive(app_state),
            "queue_size": _queue_size(app_state),
        },
        "active_model": _active_model_metadata(),
        "active_session": active_session_info,
        "recent_events": _recent_events(app_state),
        "last_error": recognition_state.get("last_error"),
        "model_health": {
            "model_stale": bool(recognition_state.get("model_stale", False)),
            "model_stale_since": recognition_state.get("model_stale_since"),
            "stale_predictions_seen": int(
                recognition_state.get("stale_predictions_seen", 0)
            ),
            "stale_reasons": getattr(app_state, "model_stale_reasons", None) or [],
        },
        "diagnostics": {
            "metric_stats": recognition_state.get("metric_stats"),
        },
        "runtime_metrics": recognition_state.get("runtime_metrics"),
    }
