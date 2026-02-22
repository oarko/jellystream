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


@router.get("/genres/{library_id}")
async def get_library_genres(library_id: str):
    """
    Return genres that exist in a specific Jellyfin library.

    Uses /Genres?parentId={library_id} so only genres actually present in
    that library are returned — prevents the user typing a genre that doesn't exist.
    """
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        raise HTTPException(status_code=400, detail="Jellyfin not configured")

    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=settings.JELLYFIN_CLIENT_NAME,
        device_name=settings.JELLYFIN_DEVICE_NAME,
        device_id=settings.JELLYFIN_DEVICE_ID or None,
    )
    try:
        genres = await client.get_genres(library_id)
        return {"genres": genres}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{parent_id}")
async def get_library_items(
    parent_id: str,
    recursive: bool = False,
    limit: int = None,
    start_index: int = 0,
    sort_by: str = "SortName",
    sort_order: str = "Ascending",
    include_item_types: str = None
):
    """
    Get items from a Jellyfin parent (library, series, season).

    Args:
        parent_id: Parent ID (library, series, or season)
        recursive: If True, gets all descendants. If False, only direct children.
        limit: Number of items to return (defaults to JELLYFIN_DEFAULT_PAGE_SIZE)
        start_index: Starting index for pagination
        sort_by: Field to sort by (SortName, PremiereDate, etc.)
        sort_order: Ascending or Descending
        include_item_types: Filter by type (e.g., "Series,Season,Episode")
    """
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="Jellyfin URL and API key must be configured"
        )

    # Use default page size if not specified
    if limit is None:
        limit = settings.JELLYFIN_DEFAULT_PAGE_SIZE

    # Enforce max page size
    limit = min(limit, settings.JELLYFIN_MAX_PAGE_SIZE)

    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=settings.JELLYFIN_CLIENT_NAME,
        device_name=settings.JELLYFIN_DEVICE_NAME,
        device_id=settings.JELLYFIN_DEVICE_ID or None
    )

    try:
        items = await client.get_library_items(
            parent_id=parent_id,
            recursive=recursive,
            limit=limit,
            start_index=start_index,
            sort_by=sort_by,
            sort_order=sort_order,
            include_item_types=include_item_types
        )
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
