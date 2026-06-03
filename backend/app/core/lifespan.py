"""ASGI lifespan: startup readiness + shutdown cleanup.

Initializes logging, verifies infrastructure (DB ping, storage directory),
and reserves slots on `app.state` for runtime systems that later milestones
will populate (recognition engine, sync manager, runtime cache, realtime hub).
Reserving the slots up-front keeps consumers from sprinkling `getattr`s.

Shutdown sequence
-----------------
1. Signal recognition + capture runtimes to stop (non-blocking).
2. Shutdown MJPEG preview buffers so streaming generators exit.
3. Signal attendance ingestion worker to stop.
4. Wait with bounded timeouts for each worker thread to exit.
5. Dispose the DB connection pool.

Every step logs entry + exit so operators can pinpoint exactly where any
remaining delay occurs.
"""
from __future__ import annotations

import queue
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import settings
from app.core.logging import configure_logging, get_logger
from app.database import models  # noqa: F401  — register models on Base.metadata
from app.database.db import engine
from app.database.migrations.runner import run_migrations
from app.recognition import capture_runtime, runtime as recognition_runtime
from app.recognition.cooldown import RecognitionCooldown
from app.recognition.preview_buffer import PreviewBuffer
from app.services import attendance_service, training_service
from app.utils.paths import ensure_dir


logger = get_logger("attendai.lifespan")

# Maximum seconds to wait for each worker thread during shutdown.
_THREAD_JOIN_TIMEOUT = 3.0


def _check_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("Database not reachable at startup: %s", exc)
        return False


def _stop_runtime_if_active(app_state: Any) -> None:
    """Signal the recognition runtime to stop (non-blocking)."""
    try:
        state = app_state.recognition_runtime.get("state", "idle")
        if state in ("starting", "running"):
            logger.info("Stopping recognition runtime (state=%s)...", state)
            recognition_runtime.stop(app_state)
        elif state == "stopping":
            logger.info("Recognition runtime already stopping")
    except Exception:  # noqa: BLE001
        logger.debug("Recognition runtime stop raised (may already be idle)", exc_info=True)


def _stop_capture_if_active(app_state: Any) -> None:
    """Signal the capture runtime to stop (non-blocking)."""
    try:
        state = app_state.capture_runtime.get("state", "idle")
        if state in ("starting", "capturing"):
            logger.info("Stopping capture runtime (state=%s)...", state)
            capture_runtime.stop(app_state)
        elif state == "stopping":
            logger.info("Capture runtime already stopping")
    except Exception:  # noqa: BLE001
        logger.debug("Capture runtime stop raised (may already be idle)", exc_info=True)


def _join_thread(name: str, app_state: Any, attr: str) -> None:
    """Join a worker thread by attribute name with a bounded timeout."""
    thread = getattr(app_state, attr, None)
    if thread is None or not isinstance(thread, threading.Thread):
        return
    if not thread.is_alive():
        logger.info("%s already exited", name)
        return
    logger.info("Waiting for %s to exit (timeout=%ss)...", name, _THREAD_JOIN_TIMEOUT)
    thread.join(timeout=_THREAD_JOIN_TIMEOUT)
    if thread.is_alive():
        logger.warning("%s did not exit within timeout — proceeding", name)
    else:
        logger.info("%s exited cleanly", name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info(
        "Starting %s v%s [env=%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
    )

    storage_path = ensure_dir(settings.STORAGE_DIR)
    logger.info("Storage directory ready: %s", storage_path)

    app.state.db_ready = _check_database()
    logger.info("Database readiness: %s", "ok" if app.state.db_ready else "unavailable")

    # Run additive schema migrations (idempotent, tracked in _schema_migrations).
    if app.state.db_ready:
        try:
            run_migrations(engine)
        except Exception:
            logger.exception("Schema migration failed — proceeding with existing schema")
    else:
        logger.warning("Skipping schema migrations — database not reachable")

    # Reserved runtime slots — populated in later milestones.
    app.state.recognition_engine = None
    app.state.sync_manager = None
    app.state.runtime_cache = {}
    app.state.realtime_hub = None

    # Training subsystem state — see app.services.training_service.
    app.state.training_state = training_service.initial_state()
    app.state.training_lock = threading.Lock()

    # Recognition runtime state — see app.recognition.runtime.
    app.state.recognition_runtime = recognition_runtime.initial_state()
    app.state.recognition_lock = threading.Lock()
    app.state.recognition_stop_event = None
    app.state.recognition_recent_events = deque(
        maxlen=settings.RECOGNITION_EVENT_BUFFER
    )
    # Per-student cooldown registry — suppresses repeated runtime events for
    # the same student. In-memory only; reset on each runtime start.
    app.state.recognition_cooldown = RecognitionCooldown()
    # Single-slot MJPEG preview buffer — published by recognition runtime,
    # consumed by the /preview/stream endpoint.
    app.state.preview_buffer = PreviewBuffer()

    # Dataset capture runtime — see app.recognition.capture_runtime. Holds
    # its own lock; coexistence with the recognition runtime is enforced in
    # services/capture_service.py (only one runtime touches the camera).
    app.state.capture_runtime = capture_runtime.initial_state()
    app.state.capture_lock = threading.Lock()
    app.state.capture_stop_event = None
    # Capture preview buffer — same pattern as recognition preview.
    app.state.capture_preview_buffer = PreviewBuffer()

    # Class-scoped attendance session context — populated by orchestration
    # when a session starts, cleared when it ends.
    app.state.active_session = None          # dict with session_id, class_id, etc.
    app.state.session_allowed_ids = set()    # set of student IDs in the class

    # Recognition -> attendance event channel + ingestion worker.
    app.state.recognition_event_queue = queue.Queue(maxsize=1000)
    attendance_service.start_ingestion(app.state)

    logger.info("Startup complete — listening on %s:%s", settings.HOST, settings.PORT)
    try:
        yield
    finally:
        t0 = time.monotonic()
        logger.info("Shutdown initiated — tearing down runtimes")

        # 1. Signal runtimes to stop (non-blocking; sets their stop events).
        _stop_runtime_if_active(app.state)
        _stop_capture_if_active(app.state)

        # 2. Shutdown preview buffers so MJPEG streaming generators exit.
        logger.info("Shutting down preview buffers...")
        preview: PreviewBuffer | None = getattr(app.state, "preview_buffer", None)
        if preview is not None:
            preview.shutdown()
        cap_preview: PreviewBuffer | None = getattr(app.state, "capture_preview_buffer", None)
        if cap_preview is not None:
            cap_preview.shutdown()
        logger.info("Preview buffers shut down")

        # 3. Signal attendance ingestion to stop.
        logger.info("Stopping attendance ingestion...")
        attendance_service.stop_ingestion(app.state)

        # 4. Wait for worker threads with bounded timeouts.
        #    Thread attribute names are set by each subsystem's start function.
        _join_thread("attendance ingestion", app.state, "attendance_thread")

        # Recognition and capture workers are daemon threads and will be
        # cleaned up by process exit, but we still wait briefly so camera
        # resources are released cleanly.
        # The recognition/capture locks are held by the worker while running;
        # a successful acquire means the worker has exited.
        for name, lock_attr in [
            ("recognition runtime", "recognition_lock"),
            ("capture runtime", "capture_lock"),
        ]:
            lock = getattr(app.state, lock_attr, None)
            if lock is None:
                continue
            logger.info("Waiting for %s worker to exit...", name)
            acquired = lock.acquire(timeout=_THREAD_JOIN_TIMEOUT)
            if acquired:
                lock.release()
                logger.info("%s worker exited", name)
            else:
                logger.warning("%s worker did not exit within timeout — proceeding", name)

        # 5. Dispose DB pool.
        logger.info("Disposing database connection pool...")
        engine.dispose()

        elapsed = time.monotonic() - t0
        logger.info("Shutdown complete (%.1fs)", elapsed)
