"""API router registration."""
from fastapi import APIRouter

from app.config.settings import settings
from app.routes import (
    attendance,
    auth,
    capture,
    capture_preview,
    classes,
    dataset,
    health,
    lifecycle,
    orchestration,
    preview,
    recognition,
    sessions,
    students,
    training,
    users,
)


api_router = APIRouter(prefix=settings.API_V1_PREFIX)
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(dataset.router)
api_router.include_router(training.router)
api_router.include_router(recognition.router)
api_router.include_router(capture.router)
api_router.include_router(attendance.router)
api_router.include_router(orchestration.router)
api_router.include_router(preview.router)
api_router.include_router(capture_preview.router)
api_router.include_router(users.router)
api_router.include_router(classes.router)
api_router.include_router(sessions.router)
api_router.include_router(lifecycle.router)


__all__ = ["api_router", "health"]
