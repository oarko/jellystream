"""API routes."""

from fastapi import APIRouter

from app.api import streams, schedules, channels, jellyfin, livetv, collections

router = APIRouter()

# Legacy streams router (kept for backward compatibility)
router.include_router(streams.router, prefix="/streams", tags=["streams"])

# New channels router (replaces streams for Phase 1+)
router.include_router(channels.router, prefix="/channels", tags=["channels"])

router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
router.include_router(jellyfin.router, prefix="/jellyfin", tags=["jellyfin"])
router.include_router(livetv.router, prefix="/livetv", tags=["livetv"])
router.include_router(collections.router, prefix="/collections", tags=["collections"])
