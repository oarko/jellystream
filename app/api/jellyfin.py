"""Jellyfin integration API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.integrations.jellyfin import JellyfinClient
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

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


def _make_client() -> JellyfinClient:
    """Helper — build a JellyfinClient from settings."""
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        raise HTTPException(status_code=400, detail="Jellyfin not configured")
    return JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=settings.JELLYFIN_CLIENT_NAME,
        device_name=settings.JELLYFIN_DEVICE_NAME,
        device_id=settings.JELLYFIN_DEVICE_ID or None,
    )


@router.get("/boxsets")
async def get_boxsets():
    """Return all Jellyfin boxset collections."""
    logger.debug("get_boxsets called")
    client = _make_client()
    try:
        items = await client.get_boxsets()
        return {"boxsets": items}
    except Exception as e:
        logger.error(f"get_boxsets failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browse")
async def browse_items(
    library_id: str = Query(..., description="Jellyfin library/view ID"),
    type: str = Query("Movie", description="Item type: Movie | Series | Season | Episode"),
    search: str = Query("", description="Free-text search term"),
    year_from: Optional[int] = Query(None, description="Minimum production year"),
    year_to: Optional[int] = Query(None, description="Maximum production year"),
    limit: int = Query(24, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Paginated browse of Jellyfin content for the Collections UI.

    Uses the admin /Items endpoint so the Path field is always returned,
    regardless of user permission level.
    """
    logger.debug(
        f"browse_items: library={library_id}, type={type}, search={search!r}, "
        f"years={year_from}-{year_to}, limit={limit}, offset={offset}"
    )
    client = _make_client()
    try:
        data = await client.browse_items(
            parent_id=library_id,
            include_types=type,
            search_term=search,
            start_year=year_from,
            end_year=year_to,
            limit=limit,
            start_index=offset,
        )
        return data
    except Exception as e:
        logger.error(f"browse_items failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/{series_id}/seasons")
async def get_series_seasons(series_id: str):
    """Return seasons for a TV series."""
    logger.debug(f"get_series_seasons: series_id={series_id}")
    client = _make_client()
    try:
        data = await client.browse_items(
            parent_id=series_id,
            include_types="Season",
            fields="Path,IndexNumber,ProductionYear,PrimaryImageAspectRatio",
            recursive=False,
        )
        return data
    except Exception as e:
        logger.error(f"get_series_seasons failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/seasons/{season_id}/episodes")
async def get_season_episodes(season_id: str):
    """Return episodes for a season, with path and duration fields."""
    logger.debug(f"get_season_episodes: season_id={season_id}")
    client = _make_client()
    try:
        data = await client.browse_items(
            parent_id=season_id,
            include_types="Episode",
            fields="Path,MediaSources,RunTimeTicks,ParentIndexNumber,IndexNumber,Overview,PremiereDate",
            recursive=False,
        )
        return data
    except Exception as e:
        logger.error(f"get_season_episodes failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{item_id}/image")
async def proxy_item_image(
    item_id: str,
    type: str = Query("Primary", description="Image type: Primary | Backdrop | Thumb"),
    maxWidth: int = Query(400, ge=50, le=1920),
):
    """
    Proxy a Jellyfin item image to the browser.

    Proxying through JellyStream keeps the Jellyfin API key out of the browser
    and works even when the Jellyfin URL is not directly accessible from the client.
    """
    logger.debug(f"proxy_item_image: item_id={item_id}, type={type}, maxWidth={maxWidth}")
    client = _make_client()
    try:
        image_bytes, content_type = await client.get_item_image(
            item_id=item_id,
            image_type=type,
            max_width=maxWidth,
        )
        return Response(content=image_bytes, media_type=content_type)
    except Exception as e:
        logger.warning(f"proxy_item_image: failed for {item_id}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")
