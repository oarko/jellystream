"""Stream API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.stream import Stream

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_streams(db: AsyncSession = Depends(get_db)):
    """Get all streams."""
    result = await db.execute(select(Stream))
    streams = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "jellyfin_library_id": s.jellyfin_library_id,
            "stream_url": s.stream_url,
            "enabled": s.enabled,
            "tuner_host_id": s.tuner_host_id,
            "listing_provider_id": s.listing_provider_id,
            "channel_number": s.channel_number,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in streams
    ]


@router.get("/{stream_id}")
async def get_stream(stream_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific stream."""
    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    return {
        "id": stream.id,
        "name": stream.name,
        "description": stream.description,
        "jellyfin_library_id": stream.jellyfin_library_id,
        "stream_url": stream.stream_url,
        "enabled": stream.enabled,
        "tuner_host_id": stream.tuner_host_id,
        "listing_provider_id": stream.listing_provider_id,
        "channel_number": stream.channel_number,
        "created_at": stream.created_at,
        "updated_at": stream.updated_at,
    }


@router.post("/")
async def create_stream(
    name: str,
    jellyfin_library_id: str,
    description: str = None,
    channel_number: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Create a new stream."""
    stream = Stream(
        name=name,
        description=description,
        jellyfin_library_id=jellyfin_library_id,
        channel_number=channel_number,
    )
    db.add(stream)
    await db.commit()
    await db.refresh(stream)

    return {"id": stream.id, "message": "Stream created successfully"}


@router.put("/{stream_id}")
async def update_stream(
    stream_id: int,
    name: str = None,
    jellyfin_library_id: str = None,
    description: str = None,
    enabled: bool = None,
    channel_number: str = None,
    tuner_host_id: str = None,
    listing_provider_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Update a stream."""
    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if name is not None:
        stream.name = name
    if jellyfin_library_id is not None:
        stream.jellyfin_library_id = jellyfin_library_id
    if description is not None:
        stream.description = description
    if enabled is not None:
        stream.enabled = enabled
    if channel_number is not None:
        stream.channel_number = channel_number
    if tuner_host_id is not None:
        stream.tuner_host_id = tuner_host_id
    if listing_provider_id is not None:
        stream.listing_provider_id = listing_provider_id

    await db.commit()
    await db.refresh(stream)

    return {"id": stream.id, "message": "Stream updated successfully"}


@router.delete("/{stream_id}")
async def delete_stream(stream_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a stream."""
    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    await db.delete(stream)
    await db.commit()

    return {"message": "Stream deleted successfully"}
