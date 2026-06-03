"""Webcam runtime: opens the camera, drives the per-frame pipeline.

Owns the worker thread + lifecycle state on `app.state.recognition_runtime`.
Concurrency is gated by `app.state.recognition_lock`. The runtime is the
only place that talks to the camera; pipeline modules stay framework-free.
"""
from __future__ import annotations

import queue
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict

from app.config.settings import settings
from app.core.logging import get_logger
from app.recognition.annotator import FaceAnnotation, annotate_frame
from app.recognition.cooldown import RecognitionCooldown
from app.recognition.frame_tracker import FrameTracker
from app.recognition.metrics import RuntimeMetrics
from app.recognition.pipeline import Detection, RecognitionPipeline
from app.recognition.preview_buffer import PreviewBuffer
from app.services.attendance_service import is_attendance_marked


logger = get_logger("attendai.recognition")


STATE_IDLE = "idle"
STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_STOPPING = "stopping"
STATE_FAILED = "failed"


def initial_state() -> Dict[str, Any]:
    return {
        "state": STATE_IDLE,
        "model_loaded": False,
        "camera_active": False,
        "started_at": None,
        "stopped_at": None,
        "last_error": None,
        "last_event": None,
        "events_processed": 0,
        # Stale-model surface: flipped sticky-true the first time the active
        # model predicts a student that is no longer in the DB. Cleared by
        # orchestration on a fresh session start (after retraining).
        "model_stale": False,
        "model_stale_since": None,
        "stale_predictions_seen": 0,
        # Threshold observability: lightweight metric stats over the last
        # N predictions so operators can tune the confidence threshold.
        # Values are unified similarity [0, 1] (higher = better match).
        "metric_stats": None,
        # Runtime performance metrics snapshot (updated periodically).
        "runtime_metrics": None,
    }


def _set(app_state: Any, **patch: Any) -> None:
    app_state.recognition_runtime = {**app_state.recognition_runtime, **patch}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start(app_state: Any) -> Dict[str, Any]:
    """Spawn the recognition worker. Raises RuntimeError if already running."""
    if not app_state.recognition_lock.acquire(blocking=False):
        raise RuntimeError("Recognition runtime already active")

    # Fresh cooldown registry per run — suppression is operational, not durable.
    cooldown = getattr(app_state, "recognition_cooldown", None)
    if cooldown is None:
        app_state.recognition_cooldown = RecognitionCooldown()
    else:
        cooldown.reset()

    _set(
        app_state,
        state=STATE_STARTING,
        model_loaded=False,
        camera_active=False,
        started_at=_utcnow_iso(),
        stopped_at=None,
        last_error=None,
        last_event=None,
        events_processed=0,
        # A fresh session starts with a clean stale-model surface; the new
        # active model is assumed in-sync until proven otherwise.
        model_stale=False,
        model_stale_since=None,
        stale_predictions_seen=0,
    )
    stop_event = threading.Event()
    app_state.recognition_stop_event = stop_event

    threading.Thread(
        target=_loop,
        args=(app_state, stop_event),
        name="attendai-recognition",
        daemon=True,
    ).start()
    return dict(app_state.recognition_runtime)


def stop(app_state: Any) -> Dict[str, Any]:
    """Signal the worker to exit. Raises RuntimeError if not running."""
    current = app_state.recognition_runtime["state"]
    if current not in (STATE_RUNNING, STATE_STARTING):
        raise RuntimeError(f"Cannot stop runtime in state '{current}'")

    _set(app_state, state=STATE_STOPPING)
    ev = getattr(app_state, "recognition_stop_event", None)
    if ev is not None:
        ev.set()
    return dict(app_state.recognition_runtime)


def get_status(app_state: Any) -> Dict[str, Any]:
    return dict(app_state.recognition_runtime)


def _loop(app_state: Any, stop_event: threading.Event) -> None:
    """Worker: load model, open camera, process frames until stop_event."""
    import cv2  # noqa: PLC0415

    cap = None
    # Orchestration exposes the deque on app.state; fall back to a local one
    # if it wasn't initialized (e.g. tests bypassing the lifespan).
    recent: deque = getattr(
        app_state, "recognition_recent_events", deque(maxlen=settings.RECOGNITION_EVENT_BUFFER)
    )
    preview_buf: PreviewBuffer | None = getattr(app_state, "preview_buffer", None)
    tracker = FrameTracker()
    metric_ring: deque[float] = deque(maxlen=100)
    metrics = RuntimeMetrics()
    try:
        pipeline = RecognitionPipeline.load_from_active()
        _set(app_state, model_loaded=True)
        logger.info("Recognition model loaded")

        # Populate backend info for the metrics collector and expose on app.state
        # so other subsystems (e.g. attendance ingestion) can record metrics.
        gallery_size = 0
        if hasattr(pipeline.recognizer, "_gallery"):
            gallery_size = pipeline.recognizer._gallery.size
        metrics.set_backends(
            detector=pipeline.detector.backend_name,
            recognizer=pipeline.recognizer.backend_name,
            gallery_size=gallery_size,
        )
        app_state.runtime_metrics_collector = metrics

        logger.info("Opening camera index=%s", settings.RECOGNITION_CAMERA_INDEX)
        cap = cv2.VideoCapture(settings.RECOGNITION_CAMERA_INDEX)
        if not cap.isOpened():
            raise RuntimeError(
                f"Failed to open camera (index={settings.RECOGNITION_CAMERA_INDEX})"
            )
        # Bounded grab timeout: prevents cap.read() from blocking indefinitely
        # during shutdown on Windows. 2000ms is generous enough for any webcam
        # frame but short enough that the stop-event check runs promptly.
        try:
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000)
        except Exception:  # noqa: BLE001 — not all backends support these
            pass
        _set(app_state, state=STATE_RUNNING, camera_active=True)
        logger.info("Recognition runtime running")

        min_preview_interval = 1.0 / settings.PREVIEW_MAX_FPS
        last_preview_time = 0.0

        processed = 0
        while not stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                time.sleep(settings.RECOGNITION_FRAME_INTERVAL_SECONDS)
                continue

            processed += 1
            result = pipeline.process_frame_full(frame)

            # Feed frame timings into the metrics collector.
            metrics.record_frame(result.timings)

            # Count unknown faces (detected but no prediction).
            n_unknown = sum(
                1 for d in result.detections
                if d.student_id is None and not d.stale
            )
            if n_unknown:
                metrics.record_unknown(n_unknown)

            # DB-authority surface: any stale prediction in this frame flips
            # the sticky model_stale flag. The pipeline has already dropped
            # those predictions from `result.events`, so no operational
            # processing (cooldown, attendance, recent feed) runs for them.
            if result.stale_ids:
                metrics.record_stale(len(result.stale_ids))
                current = app_state.recognition_runtime
                patch: Dict[str, Any] = {
                    "stale_predictions_seen": current.get(
                        "stale_predictions_seen", 0
                    ) + len(result.stale_ids),
                }
                if not current.get("model_stale"):
                    patch["model_stale"] = True
                    patch["model_stale_since"] = _utcnow_iso()
                    logger.warning(
                        "Stale model artifact detected (predicted ids=%s); "
                        "retraining required",
                        result.stale_ids,
                    )
                _set(app_state, **patch)

            # Feed every valid detection into the multi-frame tracker.
            # ev.confidence is unified similarity [0, 1] from the backend.
            for ev in result.events:
                tracker.record(ev.student_id, ev.confidence, processed)
                metric_ring.append(ev.confidence)
                metrics.record_recognition(ev.confidence, accepted=True)

            # Lazy prune every 64 frames so the tracker dict stays bounded.
            if processed % 64 == 0:
                tracker.prune(processed)

            # Update metric stats periodically (every 10 frames) for
            # threshold observability without per-frame dict churn.
            if processed % 10 == 0:
                patch_update: Dict[str, Any] = {}
                if metric_ring:
                    patch_update["metric_stats"] = _compute_metric_stats(metric_ring)
                patch_update["runtime_metrics"] = metrics.snapshot()
                _set(app_state, **patch_update)

            # --- Class-scope filter (B5) ---
            # If a class-scoped session is active, only students in that class
            # may produce attendance. Recognised students NOT in the class are
            # tagged out_of_class: they appear with name + warning in the live
            # preview but NEVER emit events, NEVER enter the recent feed,
            # NEVER create attendance, and NEVER affect counts.
            allowed_ids: set[int] = getattr(app_state, "session_allowed_ids", set())
            out_of_class_ids: set[int] = set()
            class_filtered_events = []
            for ev in result.events:
                if allowed_ids and ev.student_id not in allowed_ids:
                    out_of_class_ids.add(ev.student_id)
                    continue
                class_filtered_events.append(ev)

            # Telemetry: count out-of-class detections per frame.
            if out_of_class_ids:
                metrics.record_out_of_class(len(out_of_class_ids))

            # Four-stage gate before publishing:
            #  0. Class-scope — reject students not enrolled (handled above).
            #  1. Multi-frame confirmation — student must persist across frames.
            #  2. Attendance guard — skip students already marked for today.
            #  3. Cooldown — suppress rapid bursts for the same student.
            # All are per-student; other students pass through unaffected.
            cooldown: RecognitionCooldown = app_state.recognition_cooldown
            emitted = []
            marked_set: set[int] = set()
            for ev in class_filtered_events:
                try:
                    if not tracker.is_confirmed(ev.student_id):
                        continue
                    rec_day = datetime.fromisoformat(ev.recognized_at).date()
                    if is_attendance_marked(ev.student_id, rec_day):
                        marked_set.add(ev.student_id)
                        continue
                    if cooldown.should_emit(ev.student_id):
                        # Replace raw frame similarity with smoothed value.
                        smoothed = tracker.smoothed_metric(ev.student_id)
                        if smoothed is not None:
                            ev = type(ev)(
                                student_id=ev.student_id,
                                confidence=round(smoothed, 2),
                                recognized_at=ev.recognized_at,
                                student_name=ev.student_name,
                                student_code=ev.student_code,
                            )
                        emitted.append(ev)
                except Exception as exc:  # noqa: BLE001 — gates must never crash loop
                    logger.exception("Emission gate failed; emitting anyway: %s", exc)
                    emitted.append(ev)

            # Publish emittable events to queue + recent deque.
            # Out-of-class students are guaranteed absent from `emitted`.
            if emitted:
                for ev in emitted:
                    metrics.record_student_seen(ev.student_id)
                latest = emitted[-1].to_dict()
                recent.append(latest)
                _set(app_state, last_event=latest, events_processed=processed)
                event_queue = getattr(app_state, "recognition_event_queue", None)
                if event_queue is not None:
                    for ev in emitted:
                        try:
                            event_queue.put_nowait(ev.to_dict())
                        except queue.Full:
                            logger.warning("Recognition event queue full; dropping event")
            else:
                _set(app_state, events_processed=processed)

            # Annotate + publish preview frame (FPS-capped).
            now_mono = time.monotonic()
            if preview_buf is not None and (now_mono - last_preview_time) >= min_preview_interval:
                try:
                    emitted_ids = {ev.student_id for ev in emitted}
                    annotations = _build_annotations(
                        result.detections, marked_set, emitted_ids, out_of_class_ids,
                    )
                    annotate_frame(frame, annotations)
                    jpeg = _encode_preview(frame)
                    if jpeg is not None:
                        preview_buf.publish(jpeg)
                    last_preview_time = now_mono
                except Exception:  # noqa: BLE001
                    logger.debug("Preview frame failed", exc_info=True)

            time.sleep(settings.RECOGNITION_FRAME_INTERVAL_SECONDS)

        _set(
            app_state,
            state=STATE_IDLE,
            camera_active=False,
            stopped_at=_utcnow_iso(),
        )
        logger.info("Recognition runtime stopped cleanly (processed=%d)", processed)
    except Exception as exc:  # noqa: BLE001 — propagate to status
        logger.exception("Recognition runtime failed: %s", exc)
        _set(
            app_state,
            state=STATE_FAILED,
            camera_active=False,
            last_error=str(exc),
            stopped_at=_utcnow_iso(),
        )
    finally:
        logger.info("Releasing recognition camera...")
        if cap is not None:
            try:
                cap.release()
            except Exception:  # noqa: BLE001
                logger.warning("Camera release raised; ignoring", exc_info=True)
        logger.info("Recognition camera released")
        if preview_buf is not None:
            preview_buf.clear()
        app_state.recognition_lock.release()
        logger.info("Recognition runtime teardown complete")


def _compute_metric_stats(ring: deque) -> Dict[str, Any]:
    """Lightweight stats over the recent similarity ring buffer.

    Values are unified similarity [0, 1]. Histogram buckets are 0.1-wide
    bands: ``"0.0-0.1"``, ``"0.1-0.2"``, ..., ``"0.9-1.0"``.
    """
    vals = sorted(ring)
    n = len(vals)
    if n == 0:
        return {}
    mid = n // 2
    median = vals[mid] if n % 2 == 1 else (vals[mid - 1] + vals[mid]) / 2
    histogram: Dict[str, int] = {}
    for v in vals:
        lo = min(int(v * 10) / 10, 0.9)  # clamp so 1.0 falls into "0.9-1.0"
        bucket = f"{lo:.1f}-{lo + 0.1:.1f}"
        histogram[bucket] = histogram.get(bucket, 0) + 1
    return {
        "count": n,
        "min": round(vals[0], 4),
        "max": round(vals[-1], 4),
        "mean": round(sum(vals) / n, 4),
        "median": round(median, 4),
        "threshold": settings.RECOGNITION_SIMILARITY_THRESHOLD,
        "histogram": histogram,
    }


def _build_annotations(
    detections: list[Detection],
    marked_set: set[int],
    emitted_ids: set[int],
    out_of_class_ids: set[int] | None = None,
) -> list[FaceAnnotation]:
    ooc = out_of_class_ids or set()
    anns: list[FaceAnnotation] = []
    for det in detections:
        if det.stale:
            status = "stale"
        elif det.student_id is None:
            status = "unknown"
        elif det.student_id in ooc:
            status = "out_of_class"
        elif det.student_id in emitted_ids:
            status = "marked"
        elif det.student_id in marked_set:
            status = "already_marked"
        else:
            status = "already_marked"
        anns.append(
            FaceAnnotation(
                bbox=det.bbox,
                label=det.student_name,
                confidence=det.confidence,
                status=status,
            )
        )
    return anns


def _encode_preview(frame_bgr) -> bytes | None:  # type: ignore[type-arg]
    import cv2  # noqa: PLC0415

    h, w = frame_bgr.shape[:2]
    max_w = settings.PREVIEW_MAX_WIDTH
    if w > max_w:
        scale = max_w / w
        frame_bgr = cv2.resize(frame_bgr, (max_w, int(h * scale)))
    ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, settings.PREVIEW_JPEG_QUALITY])
    return bytes(buf) if ok else None
