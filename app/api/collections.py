"""Collections API — CRUD, Jellyfin boxset import, file verification, thumbnail serving."""

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import get_logger
from app.integrations.jellyfin import JellyfinClient
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.api.schemas import CreateCollectionRequest, UpdateCollectionRequest
from app.services.collection_service import enrich_item, verify_collection, _extract_path

logger = get_logger(__name__)
router = APIRouter()

_BROWSE_FIELDS = (
    "Path,MediaSources,RunTimeTicks,Genres,SeriesName,"
    "ParentIndexNumber,IndexNumber,Overview,PremiereDate,ProductionYear"
)


def _make_client() -> JellyfinClient:
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


def _item_to_dict(item: CollectionItem) -> dict:
    return {
        "id": item.id,
        "collection_id": item.collection_id,
        "media_item_id": item.media_item_id,
        "item_type": item.item_type,
        "title": item.title,
        "series_name": item.series_name,
        "season_number": item.season_number,
        "episode_number": item.episode_number,
        "library_id": item.library_id,
        "duration": item.duration,
        "genres": item.genres,
        "description": item.description,
        "content_rating": item.content_rating,
        "air_date": item.air_date,
        "file_path": item.file_path,
        "thumbnail_path": item.thumbnail_path,
        "sort_order": item.sort_order,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _collection_to_dict(col: Collection, item_count: int = 0) -> dict:
    return {
        "id": col.id,
        "name": col.name,
        "description": col.description,
        "jellyfin_id": col.jellyfin_id,
        "item_count": item_count,
        "created_at": col.created_at.isoformat() if col.created_at else None,
        "updated_at": col.updated_at.isoformat() if col.updated_at else None,
    }


# ─── CRITICAL: literal routes BEFORE parameterised routes ────────────────────

@router.get("/thumbnail/{item_id}")
async def get_collection_thumbnail(item_id: int, db: AsyncSession = Depends(get_db)):
    """Serve the local thumbnail_path for a CollectionItem."""
    logger.debug(f"get_collection_thumbnail: item_id={item_id}")
    result = await db.execute(select(CollectionItem).where(CollectionItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not item.thumbnail_path or not os.path.isfile(item.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    return FileResponse(item.thumbnail_path, media_type="image/jpeg")


# ─── Collection CRUD ──────────────────────────────────────────────────────────

@router.get("/")
async def list_collections(db: AsyncSession = Depends(get_db)):
    """List all collections with item counts."""
    logger.debug("list_collections called")
    result = await db.execute(select(Collection).order_by(Collection.name))
    collections = result.scalars().all()

    out = []
    for col in collections:
        count_result = await db.execute(
            select(func.count()).where(CollectionItem.collection_id == col.id)
        )
        count = count_result.scalar() or 0
        out.append(_collection_to_dict(col, count))

    logger.info(f"list_collections: returned {len(out)} collections")
    return out


@router.get("/{collection_id}")
async def get_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    """Get a collection with all its items."""
    logger.debug(f"get_collection: collection_id={collection_id}")
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    items_result = await db.execute(
        select(CollectionItem)
        .where(CollectionItem.collection_id == collection_id)
        .order_by(CollectionItem.sort_order, CollectionItem.title)
    )
    items = items_result.scalars().all()

    data = _collection_to_dict(col, len(items))
    data["items"] = [_item_to_dict(i) for i in items]
    return data


@router.post("/")
async def create_collection(
    data: CreateCollectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a collection and populate it with items.

    Each item in the request is enriched with NFO metadata and a local
    thumbnail path before being persisted.
    """
    logger.debug(f"create_collection: name={data.name!r}, items={len(data.items)}")

    col = Collection(
        name=data.name,
        description=data.description,
    )
    db.add(col)
    await db.flush()  # assigns col.id

    for idx, item_in in enumerate(data.items):
        raw = item_in.model_dump()
        raw["sort_order"] = idx
        enriched = enrich_item(raw)

        db.add(CollectionItem(
            collection_id=col.id,
            media_item_id=enriched["media_item_id"],
            item_type=enriched["item_type"],
            title=enriched["title"],
            series_name=enriched.get("series_name"),
            season_number=enriched.get("season_number"),
            episode_number=enriched.get("episode_number"),
            library_id=enriched["library_id"],
            duration=enriched.get("duration"),
            genres=enriched.get("genres"),
            description=enriched.get("description"),
            content_rating=enriched.get("content_rating"),
            air_date=enriched.get("air_date"),
            file_path=enriched.get("file_path"),
            thumbnail_path=enriched.get("thumbnail_path"),
            sort_order=enriched.get("sort_order", idx),
        ))

    await db.commit()
    await db.refresh(col)
    logger.info(f"create_collection: created collection id={col.id} with {len(data.items)} items")
    return {"id": col.id, "message": f"Collection '{col.name}' created with {len(data.items)} items"}


@router.put("/{collection_id}")
async def update_collection(
    collection_id: int,
    data: UpdateCollectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a collection's metadata and optionally replace all items."""
    logger.debug(f"update_collection: collection_id={collection_id}")
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    if data.name is not None:
        col.name = data.name
    if data.description is not None:
        col.description = data.description

    if data.items is not None:
        # Replace all items
        await db.execute(
            delete(CollectionItem).where(CollectionItem.collection_id == collection_id)
        )
        for idx, item_in in enumerate(data.items):
            raw = item_in.model_dump()
            raw["sort_order"] = idx
            enriched = enrich_item(raw)
            db.add(CollectionItem(
                collection_id=collection_id,
                media_item_id=enriched["media_item_id"],
                item_type=enriched["item_type"],
                title=enriched["title"],
                series_name=enriched.get("series_name"),
                season_number=enriched.get("season_number"),
                episode_number=enriched.get("episode_number"),
                library_id=enriched["library_id"],
                duration=enriched.get("duration"),
                genres=enriched.get("genres"),
                description=enriched.get("description"),
                content_rating=enriched.get("content_rating"),
                air_date=enriched.get("air_date"),
                file_path=enriched.get("file_path"),
                thumbnail_path=enriched.get("thumbnail_path"),
                sort_order=enriched.get("sort_order", idx),
            ))

    await db.commit()
    logger.info(f"update_collection: updated collection id={collection_id}")
    return {"id": collection_id, "message": "Collection updated"}


@router.delete("/{collection_id}")
async def delete_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a collection and all its items (cascade)."""
    logger.debug(f"delete_collection: collection_id={collection_id}")
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    await db.delete(col)
    await db.commit()
    logger.info(f"delete_collection: deleted collection id={collection_id}")
    return {"message": "Collection deleted"}


@router.delete("/{collection_id}/items/{item_id}")
async def remove_collection_item(
    collection_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove a single item from a collection."""
    logger.debug(f"remove_collection_item: collection_id={collection_id}, item_id={item_id}")
    result = await db.execute(
        select(CollectionItem).where(
            CollectionItem.id == item_id,
            CollectionItem.collection_id == collection_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in this collection")
    await db.delete(item)
    await db.commit()
    logger.info(f"remove_collection_item: removed item id={item_id}")
    return {"message": "Item removed"}


# ─── Verify ───────────────────────────────────────────────────────────────────

@router.get("/{collection_id}/verify")
async def verify_collection_files(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify that all items in the collection still exist on the local filesystem.

    For missing items:
    - Queries Jellyfin to detect if the file has moved.
    - Returns status "moved" (with new_path) or "deleted".
    """
    logger.debug(f"verify_collection_files: collection_id={collection_id}")
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    items_result = await db.execute(
        select(CollectionItem).where(CollectionItem.collection_id == collection_id)
    )
    items = items_result.scalars().all()

    client = _make_client()
    verification = await verify_collection(items, client)

    summary = {s: sum(1 for r in verification if r["status"] == s)
               for s in ("ok", "moved", "deleted", "no_path")}
    logger.info(
        f"verify_collection_files: collection_id={collection_id} "
        f"summary={summary}"
    )
    return {
        "collection_id": collection_id,
        "summary": summary,
        "items": verification,
    }


# ─── Jellyfin boxset import ───────────────────────────────────────────────────

@router.post("/import/{boxset_id}")
async def import_jellyfin_boxset(
    boxset_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Import a Jellyfin boxset collection.

    Fetches all items within the boxset, enriches them with local NFO / thumbnail
    metadata, and creates a new Collection record.
    """
    logger.debug(f"import_jellyfin_boxset: boxset_id={boxset_id}")
    client = _make_client()

    try:
        boxset_info = await client.get_item_info(boxset_id)
    except Exception as exc:
        logger.error(f"import_jellyfin_boxset: failed to fetch boxset info: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not fetch boxset: {exc}")

    boxset_name = boxset_info.get("Name", f"Boxset {boxset_id}")

    # Check for an existing import of this boxset
    existing = await db.execute(
        select(Collection).where(Collection.jellyfin_id == boxset_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Boxset '{boxset_name}' has already been imported",
        )

    # Fetch all items in the boxset
    try:
        data = await client.browse_items(
            parent_id=boxset_id,
            include_types="Movie,Series,Episode",
            fields=_BROWSE_FIELDS,
            recursive=True,
        )
    except Exception as exc:
        logger.error(f"import_jellyfin_boxset: failed to fetch items: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not fetch boxset items: {exc}")

    jf_items = data.get("Items", [])
    logger.info(f"import_jellyfin_boxset: boxset '{boxset_name}' has {len(jf_items)} items")

    col = Collection(name=boxset_name, jellyfin_id=boxset_id)
    db.add(col)
    await db.flush()

    for idx, jf_item in enumerate(jf_items):
        ticks = jf_item.get("RunTimeTicks") or 0
        duration = int(ticks / 10_000_000) if ticks else None
        genres_list = jf_item.get("Genres") or []
        import json
        raw = {
            "media_item_id": jf_item.get("Id", ""),
            "item_type": jf_item.get("Type", "Movie"),
            "title": jf_item.get("Name", "Unknown"),
            "library_id": jf_item.get("ParentId", ""),
            "series_name": jf_item.get("SeriesName"),
            "season_number": jf_item.get("ParentIndexNumber"),
            "episode_number": jf_item.get("IndexNumber"),
            "duration": duration,
            "genres": json.dumps(genres_list) if genres_list else None,
            "file_path": _extract_path(jf_item),
            "sort_order": idx,
        }
        enriched = enrich_item(raw)
        db.add(CollectionItem(
            collection_id=col.id,
            media_item_id=enriched["media_item_id"],
            item_type=enriched["item_type"],
            title=enriched["title"],
            series_name=enriched.get("series_name"),
            season_number=enriched.get("season_number"),
            episode_number=enriched.get("episode_number"),
            library_id=enriched["library_id"],
            duration=enriched.get("duration"),
            genres=enriched.get("genres"),
            description=enriched.get("description"),
            content_rating=enriched.get("content_rating"),
            air_date=enriched.get("air_date"),
            file_path=enriched.get("file_path"),
            thumbnail_path=enriched.get("thumbnail_path"),
            sort_order=idx,
        ))

    await db.commit()
    await db.refresh(col)
    logger.info(
        f"import_jellyfin_boxset: imported collection id={col.id} "
        f"('{boxset_name}') with {len(jf_items)} items"
    )
    return {
        "id": col.id,
        "message": f"Imported '{boxset_name}' with {len(jf_items)} items",
    }
