"""Channel API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.channel import Channel
from app.models.channel_library import ChannelLibrary
from app.models.channel_collection_source import ChannelCollectionSource
from app.models.genre_filter import GenreFilter
from app.api.schemas import CreateChannelRequest, UpdateChannelRequest, RegisterLiveTVRequest

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
        "channel_type": channel.channel_type,
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
        {"genre": gf.genre, "content_type": gf.content_type, "filter_type": gf.filter_type}
        for gf in gf_result.scalars().all()
    ]

    cs_result = await db.execute(
        select(ChannelCollectionSource).where(
            ChannelCollectionSource.channel_id == channel_id
        )
    )
    d["collection_sources"] = [
        {"collection_id": cs.collection_id, "collection_name": cs.collection_name}
        for cs in cs_result.scalars().all()
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
        channel_type=data.channel_type,
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
            filter_type=gf.filter_type,
        ))

    # Persist collection sources
    for cs in (data.collection_sources or []):
        db.add(ChannelCollectionSource(
            channel_id=channel.id,
            collection_id=cs.collection_id,
            collection_name=cs.collection_name,
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
    if data.channel_type is not None:
        channel.channel_type = data.channel_type
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
                filter_type=gf.filter_type,
            ))

    if data.collection_sources is not None:
        await db.execute(
            delete(ChannelCollectionSource).where(
                ChannelCollectionSource.channel_id == channel_id
            )
        )
        for cs in data.collection_sources:
            db.add(ChannelCollectionSource(
                channel_id=channel_id,
                collection_id=cs.collection_id,
                collection_name=cs.collection_name,
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
    reset: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger schedule generation for a channel.

    With reset=true (default from UI): deletes all existing schedule entries
    and regenerates from now.  Without reset: appends from schedule_generated_through.
    """
    logger.debug(
        f"trigger_schedule_generation called: channel_id={channel_id}, days={days}, reset={reset}"
    )
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"trigger_schedule_generation: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    if reset:
        from sqlalchemy import delete as sa_delete
        from app.models.schedule_entry import ScheduleEntry
        deleted = await db.execute(
            sa_delete(ScheduleEntry).where(ScheduleEntry.channel_id == channel_id)
        )
        channel.schedule_generated_through = None
        await db.commit()
        logger.info(
            f"trigger_schedule_generation: reset — deleted all entries for channel {channel_id}"
        )

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


# ─── POST /api/channels/{channel_id}/register-livetv ─────────────────────────

@router.post("/{channel_id}/register-livetv")
async def register_livetv(
    channel_id: int,
    data: RegisterLiveTVRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register JellyStream with Jellyfin Live TV.

    Creates a single global TunerHost (pointing at /api/livetv/m3u/all) and a
    single global ListingProvider (pointing at /api/livetv/xmltv/all), so that
    ALL channels — including ones added later — are served by one registration.

    The returned Jellyfin IDs are stored on this channel row so they can be used
    to unregister later.  public_url must be the JellyStream base URL as
    reachable from the Jellyfin server (e.g. "http://192.168.1.100:8000").
    """
    logger.debug(
        f"register_livetv called: channel_id={channel_id}, "
        f"public_url={data.public_url}, tuner_count={data.tuner_count}"
    )

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        logger.warning(f"register_livetv: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    # Global endpoints — all channels covered by a single Jellyfin tuner
    base = data.public_url.rstrip("/")
    m3u_url   = f"{base}/api/livetv/m3u/all"
    xmltv_url = f"{base}/api/livetv/xmltv/all"

    from app.core.config import settings
    from app.integrations.jellyfin import JellyfinClient

    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
    )

    # ── Clean up any stale registrations before creating new ones ─────────────
    # This prevents duplicate tuners/providers when retrying after a partial
    # failure (e.g. tuner failed but listing provider already succeeded).
    if channel.tuner_host_id:
        logger.info(
            f"register_livetv: removing stale tuner {channel.tuner_host_id} "
            f"before re-registering"
        )
        try:
            await client.unregister_tuner_host(channel.tuner_host_id)
        except Exception as exc:
            logger.warning(f"register_livetv: stale tuner removal failed (ignored): {exc}")
        channel.tuner_host_id = None

    if channel.listing_provider_id:
        logger.info(
            f"register_livetv: removing stale listing provider "
            f"{channel.listing_provider_id} before re-registering"
        )
        try:
            await client.unregister_listing_provider(channel.listing_provider_id)
        except Exception as exc:
            logger.warning(
                f"register_livetv: stale listing provider removal failed (ignored): {exc}"
            )
        channel.listing_provider_id = None

    errors = []

    # ── Register tuner host ────────────────────────────────────────────────────
    try:
        tuner = await client.register_tuner_host(
            url=m3u_url,
            friendly_name="JellyStream",
            tuner_count=data.tuner_count,
            allow_hw_transcoding=data.allow_hw_transcoding,
            allow_fmp4_transcoding=data.allow_fmp4_transcoding,
            allow_stream_sharing=data.allow_stream_sharing,
            enable_stream_looping=data.enable_stream_looping,
            fallback_max_bitrate=data.fallback_max_bitrate,
            ignore_dts=data.ignore_dts,
            read_at_native_framerate=data.read_at_native_framerate,
        )
        channel.tuner_host_id = tuner.get("Id")
        logger.info(
            f"register_livetv: tuner registered id={channel.tuner_host_id} "
            f"(global, all channels) triggered by channel {channel_id}"
        )
    except Exception as exc:
        logger.error(
            f"register_livetv: tuner registration failed for channel {channel_id}: {exc}",
            exc_info=True,
        )
        errors.append(f"TunerHost: {exc}")

    # ── Register listing provider ──────────────────────────────────────────────
    try:
        provider = await client.register_listing_provider(
            listing_provider_type="xmltv",
            xmltv_url=xmltv_url,
            friendly_name="JellyStream EPG",
        )
        channel.listing_provider_id = provider.get("Id")
        logger.info(
            f"register_livetv: listing provider registered id={channel.listing_provider_id} "
            f"for channel {channel_id}"
        )
    except Exception as exc:
        logger.error(
            f"register_livetv: listing provider registration failed "
            f"for channel {channel_id}: {exc}",
            exc_info=True,
        )
        errors.append(f"ListingProvider: {exc}")

    await db.commit()
    await db.refresh(channel)

    if errors:
        raise HTTPException(
            status_code=502,
            detail=f"Partial registration failure: {'; '.join(errors)}",
        )

    return {
        "message": "Channel registered with Jellyfin Live TV",
        "tuner_host_id": channel.tuner_host_id,
        "listing_provider_id": channel.listing_provider_id,
        "m3u_url": m3u_url,
        "xmltv_url": xmltv_url,
    }


# ─── DELETE /api/channels/{channel_id}/register-livetv ───────────────────────

@router.delete("/{channel_id}/register-livetv")
async def unregister_livetv(channel_id: int, db: AsyncSession = Depends(get_db)):
    """
    Unregister this channel from Jellyfin Live TV.

    Removes the TunerHost and ListingProvider from Jellyfin, then clears
    the stored IDs from the channel row.
    """
    logger.debug(f"unregister_livetv called: channel_id={channel_id}")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        logger.warning(f"unregister_livetv: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel.tuner_host_id and not channel.listing_provider_id:
        logger.info(f"unregister_livetv: channel {channel_id} is not registered, nothing to do")
        return {"message": "Channel is not registered with Jellyfin Live TV"}

    from app.core.config import settings
    from app.integrations.jellyfin import JellyfinClient

    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
    )

    errors = []

    if channel.tuner_host_id:
        try:
            await client.unregister_tuner_host(channel.tuner_host_id)
            logger.info(
                f"unregister_livetv: removed tuner {channel.tuner_host_id} "
                f"for channel {channel_id}"
            )
            channel.tuner_host_id = None
        except Exception as exc:
            logger.error(
                f"unregister_livetv: failed to remove tuner "
                f"{channel.tuner_host_id}: {exc}",
                exc_info=True,
            )
            errors.append(f"TunerHost: {exc}")

    if channel.listing_provider_id:
        try:
            await client.unregister_listing_provider(channel.listing_provider_id)
            logger.info(
                f"unregister_livetv: removed listing provider "
                f"{channel.listing_provider_id} for channel {channel_id}"
            )
            channel.listing_provider_id = None
        except Exception as exc:
            logger.error(
                f"unregister_livetv: failed to remove listing provider "
                f"{channel.listing_provider_id}: {exc}",
                exc_info=True,
            )
            errors.append(f"ListingProvider: {exc}")

    await db.commit()
    await db.refresh(channel)

    if errors:
        raise HTTPException(
            status_code=502,
            detail=f"Partial unregistration failure: {'; '.join(errors)}",
        )

    return {"message": "Channel unregistered from Jellyfin Live TV"}
