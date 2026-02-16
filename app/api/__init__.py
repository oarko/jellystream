"""API routes."""

from fastapi import APIRouter

from app.api import streams, schedules, jellyfin, livetv

router = APIRouter()

router.include_router(streams.router, prefix="/streams", tags=["streams"])
router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
router.include_router(jellyfin.router, prefix="/jellyfin", tags=["jellyfin"])
router.include_router(livetv.router, prefix="/livetv", tags=["livetv"])
