"""Dataset capture runtime: guided biometric enrollment with quality gating.

Owns the capture worker thread + lifecycle state on `app.state.capture_runtime`.
Concurrency is gated by `app.state.capture_lock` (separate from the recognition
lock; coexistence rules are enforced by `services/capture_service.py`).

The runtime drives a 4-phase enrollment flow (front → right → left → front).
Each phase requires N quality-approved samples before advancing. Quality is
evaluated per-frame by `QualityEvaluator` (face size, centeredness, stability).
Annotated preview frames are published to `capture_preview_buffer` for the
frontend MJPEG stream.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from app.config.settings import settings
from app.core.logging import get_logger
from app.recognition.capture_annotator import annotate_capture_frame
from app.recognition.capture_pipeline import CapturePipeline
from app.recognition.capture_quality import PHASES, QualityEvaluator
from app.recognition.preview_buffer import PreviewBuffer


logger = get_logger("attendai.capture")


STATE_IDLE = "idle"
STATE_STARTING = "starting"
STATE_CAPTURING = "capturing"
STATE_STOPPING = "stopping"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"


SampleWriter = Callable[[bytes, int], str]


def initial_state() -> Dict[str, Any]:
    return {
        "state": STATE_IDLE,
        "student_id": None,
        "samples_collected": 0,
        "target_samples": 0,
        "camera_active": False,
        "started_at": None,
        "stopped_at": None,
        "last_error": None,
        "last_sample_filename": None,
        # Guided enrollment fields
        "phase_index": 0,
        "phase_id": None,
        "phase_instruction": None,
        "samples_in_phase": 0,
        "samples_per_phase": 0,
        "quality_guidance": "",
        "quality_acceptable": False,
    }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set(app_state: Any, **patch: Any) -> None:
    app_state.capture_runtime = {**app_state.capture_runtime, **patch}


def get_status(app_state: Any) -> Dict[str, Any]:
    return dict(app_state.capture_runtime)


def is_active(app_state: Any) -> bool:
    return app_state.capture_runtime["state"] in (
        STATE_STARTING,
        STATE_CAPTURING,
        STATE_STOPPING,
    )


def start(
    app_state: Any,
    *,
    student_id: int,
    target_samples: int,
    sample_writer: SampleWriter,
    on_complete: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    if not app_state.capture_lock.acquire(blocking=False):
        raise RuntimeError("Capture runtime already active")

    samples_per_phase = settings.CAPTURE_SAMPLES_PER_PHASE
    total_target = len(PHASES) * samples_per_phase

    _set(
        app_state,
        state=STATE_STARTING,
        student_id=student_id,
        samples_collected=0,
        target_samples=total_target,
        camera_active=False,
        started_at=_utcnow_iso(),
        stopped_at=None,
        last_error=None,
        last_sample_filename=None,
        phase_index=0,
        phase_id=PHASES[0]["id"],
        phase_instruction=PHASES[0]["instruction"],
        samples_in_phase=0,
        samples_per_phase=samples_per_phase,
        quality_guidance="",
        quality_acceptable=False,
    )
    stop_event = threading.Event()
    app_state.capture_stop_event = stop_event

    threading.Thread(
        target=_loop,
        args=(app_state, stop_event, sample_writer, on_complete),
        name="attendai-capture",
        daemon=True,
    ).start()
    return get_status(app_state)


def stop(app_state: Any) -> Dict[str, Any]:
    current = app_state.capture_runtime["state"]
    if current not in (STATE_STARTING, STATE_CAPTURING):
        raise RuntimeError(f"Cannot stop capture runtime in state '{current}'")

    _set(app_state, state=STATE_STOPPING)
    ev = getattr(app_state, "capture_stop_event", None)
    if ev is not None:
        ev.set()
    return get_status(app_state)


# -- worker --------------------------------------------------------------------


def _loop(
    app_state: Any,
    stop_event: threading.Event,
    sample_writer: SampleWriter,
    on_complete: Optional[Callable[[int, int], None]],
) -> None:
    import cv2  # noqa: PLC0415

    cap = None
    preview_buf: PreviewBuffer | None = getattr(app_state, "capture_preview_buffer", None)
    started_at = time.monotonic()
    duration_ceiling = settings.CAPTURE_MAX_DURATION_SECONDS
    throttle = settings.CAPTURE_SAMPLE_THROTTLE_SECONDS
    frame_interval = settings.CAPTURE_FRAME_INTERVAL_SECONDS
    samples_per_phase = settings.CAPTURE_SAMPLES_PER_PHASE
    samples_collected = 0

    try:
        pipeline = CapturePipeline.load()
        evaluator = QualityEvaluator()

        logger.info("Opening capture camera index=%s", settings.CAPTURE_CAMERA_INDEX)
        cap = cv2.VideoCapture(settings.CAPTURE_CAMERA_INDEX)
        if not cap.isOpened():
            raise RuntimeError(
                f"Failed to open camera (index={settings.CAPTURE_CAMERA_INDEX})"
            )
        # Bounded grab timeout so cap.read() doesn't block indefinitely
        # during shutdown on Windows.
        try:
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000)
        except Exception:  # noqa: BLE001 — not all backends support these
            pass
        _set(app_state, state=STATE_CAPTURING, camera_active=True)
        logger.info(
            "Capture started student_id=%s phases=%d samples_per_phase=%d",
            app_state.capture_runtime["student_id"],
            len(PHASES),
            samples_per_phase,
        )

        total_target = len(PHASES) * samples_per_phase
        phase_index = 0
        samples_in_phase = 0
        last_accepted = 0.0

        min_preview_interval = 1.0 / settings.CAPTURE_PREVIEW_MAX_FPS
        last_preview_time = 0.0

        while not stop_event.is_set() and samples_collected < total_target:
            now = time.monotonic()
            if now - started_at > duration_ceiling:
                raise RuntimeError("Capture exceeded maximum duration")

            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(frame_interval)
                continue

            # Detect face for quality evaluation.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_bbox = pipeline._select_face(gray)
            frame_h, frame_w = frame.shape[:2]

            # Extract face crop for sharpness/brightness checks.
            gray_crop = None
            if face_bbox is not None:
                fx, fy, fw, fh = face_bbox
                gray_crop = gray[fy : fy + fh, fx : fx + fw]

            quality = evaluator.evaluate(
                face_bbox, frame_h, frame_w, gray_crop=gray_crop
            )

            # Update status with quality/phase info for frontend polling.
            _set(
                app_state,
                phase_index=phase_index,
                phase_id=PHASES[phase_index]["id"],
                phase_instruction=PHASES[phase_index]["instruction"],
                samples_in_phase=samples_in_phase,
                quality_guidance=quality.guidance,
                quality_acceptable=quality.acceptable,
            )

            # Annotate + publish preview frame (FPS-capped).
            if preview_buf is not None and (now - last_preview_time) >= min_preview_interval:
                try:
                    annotate_capture_frame(
                        frame,
                        quality,
                        phase_label=PHASES[phase_index]["instruction"],
                        phase_index=phase_index,
                        phase_count=len(PHASES),
                        samples_in_phase=samples_in_phase,
                        samples_per_phase=samples_per_phase,
                        total_collected=samples_collected,
                        total_target=total_target,
                    )
                    jpeg = _encode_preview(frame)
                    if jpeg is not None:
                        preview_buf.publish(jpeg)
                    last_preview_time = now
                except Exception:  # noqa: BLE001
                    logger.debug("Capture preview frame failed", exc_info=True)

            # Accept sample only if quality passes and throttle window elapsed.
            if quality.acceptable and (now - last_accepted) >= throttle:
                sample = pipeline.extract_sample(frame)
                if sample is not None:
                    samples_collected += 1
                    try:
                        stored_name = sample_writer(sample, samples_collected)
                    except Exception:
                        samples_collected -= 1
                        raise

                    last_accepted = now
                    samples_in_phase += 1
                    _set(
                        app_state,
                        samples_collected=samples_collected,
                        last_sample_filename=stored_name,
                        samples_in_phase=samples_in_phase,
                    )

                    # Phase advancement.
                    if samples_in_phase >= samples_per_phase:
                        phase_index += 1
                        if phase_index < len(PHASES):
                            samples_in_phase = 0
                            evaluator.reset()
                            # Anchor the current face position so the
                            # evaluator can enforce a real pose shift.
                            if face_bbox is not None and frame_w > 0:
                                anchor_cx = (face_bbox[0] + face_bbox[2] / 2) / frame_w
                                evaluator.anchor_phase(anchor_cx)
                            _set(
                                app_state,
                                phase_index=phase_index,
                                phase_id=PHASES[phase_index]["id"],
                                phase_instruction=PHASES[phase_index]["instruction"],
                                samples_in_phase=0,
                            )
                            logger.info(
                                "Phase advanced to %s (%d/%d)",
                                PHASES[phase_index]["id"],
                                phase_index + 1,
                                len(PHASES),
                            )

            time.sleep(frame_interval)

        if stop_event.is_set() and samples_collected < total_target:
            _set(
                app_state,
                state=STATE_IDLE,
                camera_active=False,
                stopped_at=_utcnow_iso(),
            )
            logger.info(
                "Capture stopped by request (collected=%d/%d)",
                samples_collected, total_target,
            )
        else:
            _set(
                app_state,
                state=STATE_COMPLETED,
                camera_active=False,
                stopped_at=_utcnow_iso(),
            )
            logger.info(
                "Capture completed (collected=%d/%d)",
                samples_collected, total_target,
            )
            if on_complete is not None and samples_collected > 0:
                try:
                    on_complete(
                        app_state.capture_runtime["student_id"], samples_collected
                    )
                except Exception:
                    logger.exception("Capture on_complete callback failed")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Capture runtime failed: %s", exc)
        _set(
            app_state,
            state=STATE_FAILED,
            camera_active=False,
            last_error=str(exc),
            stopped_at=_utcnow_iso(),
        )
    finally:
        logger.info("Releasing capture camera...")
        if cap is not None:
            try:
                cap.release()
            except Exception:  # noqa: BLE001
                logger.warning("Camera release raised; ignoring", exc_info=True)
        logger.info("Capture camera released")
        if preview_buf is not None:
            preview_buf.clear()
        app_state.capture_lock.release()
        logger.info("Capture runtime teardown complete")


def _encode_preview(frame_bgr) -> bytes | None:
    import cv2  # noqa: PLC0415

    h, w = frame_bgr.shape[:2]
    max_w = settings.CAPTURE_PREVIEW_MAX_WIDTH
    if w > max_w:
        scale = max_w / w
        frame_bgr = cv2.resize(frame_bgr, (max_w, int(h * scale)))
    ok, buf = cv2.imencode(
        ".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, settings.CAPTURE_PREVIEW_JPEG_QUALITY]
    )
    return bytes(buf) if ok else None
