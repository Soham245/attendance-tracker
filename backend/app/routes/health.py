from fastapi import APIRouter, Request

from app.config.constants import API_TAG_HEALTH
from app.config.settings import settings
from app.database.schemas.response import APIResponse


router = APIRouter(tags=[API_TAG_HEALTH])


@router.get("/health", response_model=APIResponse[dict])
def health_check(request: Request) -> APIResponse[dict]:
    return APIResponse.ok(
        data={
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "database": "ok" if getattr(request.app.state, "db_ready", False) else "unavailable",
        },
        message="Service is healthy",
    )
