"""Jellyfin integration API endpoints."""

from fastapi import APIRouter, HTTPException

from app.integrations.jellyfin import JellyfinClient
from app.core.config import settings

router = APIRouter()


@router.get("/libraries")
async def get_libraries():
    """Get Jellyfin libraries."""
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="Jellyfin URL and API key must be configured"
        )

    client = JellyfinClient(settings.JELLYFIN_URL, settings.JELLYFIN_API_KEY)

    try:
        libraries = await client.get_libraries()
        return {"libraries": libraries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{library_id}")
async def get_library_items(library_id: str):
    """Get items from a Jellyfin library."""
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="Jellyfin URL and API key must be configured"
        )

    client = JellyfinClient(settings.JELLYFIN_URL, settings.JELLYFIN_API_KEY)

    try:
        items = await client.get_library_items(library_id)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
