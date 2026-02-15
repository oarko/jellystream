"""Jellyfin integration API endpoints."""

from fastapi import APIRouter, HTTPException

from app.integrations.jellyfin import JellyfinClient
from app.core.config import settings

router = APIRouter()


@router.get("/users")
async def get_users():
    """Get Jellyfin users (for discovering user IDs)."""
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="Jellyfin URL and API key must be configured"
        )

    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=settings.JELLYFIN_CLIENT_NAME,
        device_name=settings.JELLYFIN_DEVICE_NAME,
        device_id=settings.JELLYFIN_DEVICE_ID or None
    )

    try:
        users = await client.get_users()
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/libraries")
async def get_libraries():
    """Get Jellyfin libraries."""
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="Jellyfin URL and API key must be configured"
        )

    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=settings.JELLYFIN_CLIENT_NAME,
        device_name=settings.JELLYFIN_DEVICE_NAME,
        device_id=settings.JELLYFIN_DEVICE_ID or None
    )

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

    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=settings.JELLYFIN_CLIENT_NAME,
        device_name=settings.JELLYFIN_DEVICE_NAME,
        device_id=settings.JELLYFIN_DEVICE_ID or None
    )

    try:
        items = await client.get_library_items(library_id)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
