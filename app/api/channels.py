"""Channel API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.channel import Channel
from app.models.channel_library import ChannelLibrary
from app.models.genre_filter import GenreFilter
from app.api.schemas import CreateChannelRequest, UpdateChannelRequest

logger = get_logger(__name__)
router = APIRouter()


def _channel_to_dict(channel: Channel) -> dict:
    """Serialize a Channel ORM object to a dict."""
    return {
        "id": channel.id,
        "name": channel.name,
        "description": channel.description,
        "channel_number": channel.channel_number,
        "enabled": channel.enabled,
        "schedule_type": channel.schedule_type,
        "tuner_host_id": channel.tuner_host_id,
        "listing_provider_id": channel.listing_provider_id,
        "schedule_generated_through": channel.schedule_generated_through,
        "created_at": channel.created_at,
        "updated_at": channel.updated_at,
    }


async def _attach_relations(channel_id: int, d: dict, db: AsyncSession) -> dict:
    """Attach libraries and genre_filters to a channel dict."""
    lib_result = await db.execute(
        select(ChannelLibrary).where(ChannelLibrary.channel_id == channel_id)
    )
    d["libraries"] = [
        {
            "library_id": lib.library_id,
            "library_name": lib.library_name,
            "collection_type": lib.collection_type,
        }
        for lib in lib_result.scalars().all()
    ]

    gf_result = await db.execute(
        select(GenreFilter).where(GenreFilter.channel_id == channel_id)
    )
    d["genre_filters"] = [
        {"genre": gf.genre, "content_type": gf.content_type}
        for gf in gf_result.scalars().all()
    ]
    return d


# ─── GET /api/channels/ ───────────────────────────────────────────────────────

@router.get("/")
async def get_channels(db: AsyncSession = Depends(get_db)):
    """Return all channels with their libraries and genre filters."""
    logger.debug("get_channels called")
    result = await db.execute(select(Channel).order_by(Channel.id))
    channels = result.scalars().all()

    output = []
    for ch in channels:
        d = await _attach_relations(ch.id, _channel_to_dict(ch), db)
        output.append(d)

    logger.info(f"get_channels: returned {len(output)} channels")
    return output


# ─── GET /api/channels/{channel_id} ──────────────────────────────────────────

@router.get("/{channel_id}")
async def get_channel(channel_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single channel with its libraries and genre filters."""
    logger.debug(f"get_channel called: channel_id={channel_id}")
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"get_channel: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    d = await _attach_relations(channel_id, _channel_to_dict(channel), db)
    logger.info(f"get_channel: returned channel '{channel.name}' (id={channel_id})")
    return d


# ─── POST /api/channels/ ─────────────────────────────────────────────────────

@router.post("/")
async def create_channel(data: CreateChannelRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new channel.

    Accepts a JSON body with name, description, channel_number, schedule_type,
    a list of library configs, and optional genre filters.

    If schedule_type is 'genre_auto', triggers initial 7-day schedule generation.
    """
    logger.debug(
        f"create_channel called: name='{data.name}', "
        f"libraries={len(data.libraries)}, "
        f"genre_filters={len(data.genre_filters or [])}, "
        f"schedule_type={data.schedule_type}"
    )

    channel = Channel(
        name=data.name,
        description=data.description,
        channel_number=data.channel_number,
        schedule_type=data.schedule_type,
    )
    db.add(channel)
    await db.flush()  # Assign ID without committing

    # Persist library associations
    for lib in data.libraries:
        db.add(ChannelLibrary(
            channel_id=channel.id,
            library_id=lib.library_id,
            library_name=lib.library_name,
            collection_type=lib.collection_type,
        ))

    # Persist genre filters
    for gf in (data.genre_filters or []):
        db.add(GenreFilter(
            channel_id=channel.id,
            genre=gf.genre,
            content_type=gf.content_type,
        ))

    await db.commit()
    await db.refresh(channel)
    logger.info(f"create_channel: created channel '{channel.name}' (id={channel.id})")

    # Kick off initial schedule generation for auto-schedule channels
    if channel.schedule_type == "genre_auto":
        try:
            from app.services.schedule_generator import generate_channel_schedule
            count = await generate_channel_schedule(channel.id, days=7, db=db)
            logger.info(
                f"create_channel: initial schedule generated — "
                f"{count} entries for channel {channel.id}"
            )
        except Exception as e:
            logger.error(
                f"create_channel: schedule generation failed for channel {channel.id}: {e}",
                exc_info=True
            )

    return {"id": channel.id, "message": "Channel created successfully"}


# ─── PUT /api/channels/{channel_id} ──────────────────────────────────────────

@router.put("/{channel_id}")
async def update_channel(
    channel_id: int,
    data: UpdateChannelRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing channel.

    Providing 'libraries' replaces all existing library associations.
    Providing 'genre_filters' replaces all existing genre filters.
    Omitting either field leaves them unchanged.
    """
    logger.debug(f"update_channel called: channel_id={channel_id}")
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"update_channel: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    if data.name is not None:
        channel.name = data.name
    if data.description is not None:
        channel.description = data.description
    if data.channel_number is not None:
        channel.channel_number = data.channel_number
    if data.enabled is not None:
        channel.enabled = data.enabled
    if data.schedule_type is not None:
        channel.schedule_type = data.schedule_type

    if data.libraries is not None:
        await db.execute(
            delete(ChannelLibrary).where(ChannelLibrary.channel_id == channel_id)
        )
        for lib in data.libraries:
            db.add(ChannelLibrary(
                channel_id=channel_id,
                library_id=lib.library_id,
                library_name=lib.library_name,
                collection_type=lib.collection_type,
            ))

    if data.genre_filters is not None:
        await db.execute(
            delete(GenreFilter).where(GenreFilter.channel_id == channel_id)
        )
        for gf in data.genre_filters:
            db.add(GenreFilter(
                channel_id=channel_id,
                genre=gf.genre,
                content_type=gf.content_type,
            ))

    await db.commit()
    await db.refresh(channel)
    logger.info(f"update_channel: updated channel '{channel.name}' (id={channel_id})")
    return {"id": channel.id, "message": "Channel updated successfully"}


# ─── DELETE /api/channels/{channel_id} ───────────────────────────────────────

@router.delete("/{channel_id}")
async def delete_channel(channel_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a channel.

    Cascades to channel_libraries, genre_filters, and schedule_entries
    via database FK constraints.
    """
    logger.debug(f"delete_channel called: channel_id={channel_id}")
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"delete_channel: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    name = channel.name
    await db.delete(channel)
    await db.commit()
    logger.info(f"delete_channel: deleted channel '{name}' (id={channel_id})")
    return {"message": "Channel deleted successfully"}


# ─── POST /api/channels/{channel_id}/generate-schedule ───────────────────────

@router.post("/{channel_id}/generate-schedule")
async def trigger_schedule_generation(
    channel_id: int,
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger schedule generation for a channel.

    Generates 'days' days of schedule content starting from where
    the current schedule ends (or from now if no schedule exists).
    """
    logger.debug(
        f"trigger_schedule_generation called: channel_id={channel_id}, days={days}"
    )
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"trigger_schedule_generation: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    try:
        from app.services.schedule_generator import generate_channel_schedule
        count = await generate_channel_schedule(channel_id, days=days, db=db)
        logger.info(
            f"trigger_schedule_generation: {count} entries created for channel {channel_id}"
        )
        return {"message": f"Schedule generated: {count} entries created", "count": count}
    except Exception as e:
        logger.error(
            f"trigger_schedule_generation: failed for channel {channel_id}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
