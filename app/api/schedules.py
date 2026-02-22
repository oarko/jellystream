"""Schedule API endpoints (ScheduleEntry model)."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.schedule_entry import ScheduleEntry
from app.api.schemas import CreateScheduleEntryRequest, UpdateScheduleEntryRequest

logger = get_logger(__name__)
router = APIRouter()


def _entry_to_dict(e: ScheduleEntry) -> dict:
    """Serialize a ScheduleEntry ORM object to a dict."""
    return {
        "id": e.id,
        "channel_id": e.channel_id,
        "title": e.title,
        "series_name": e.series_name,
        "season_number": e.season_number,
        "episode_number": e.episode_number,
        "media_item_id": e.media_item_id,
        "library_id": e.library_id,
        "item_type": e.item_type,
        "genres": e.genres,
        "start_time": e.start_time,
        "end_time": e.end_time,
        "duration": e.duration,
        "created_at": e.created_at,
    }


# ─── GET /api/schedules/channel/{channel_id} ─────────────────────────────────

@router.get("/channel/{channel_id}")
async def get_channel_schedule(
    channel_id: int,
    hours_back: int = Query(default=3, ge=0, le=24),
    hours_forward: int = Query(default=168, ge=1, le=336),  # 7 days max
    db: AsyncSession = Depends(get_db),
):
    """
    Return schedule entries for a channel within a time window.

    Defaults to 3 hours back and 7 days forward from now (UTC).
    Ordered by start_time ascending.
    """
    logger.debug(
        f"get_channel_schedule called: channel_id={channel_id}, "
        f"hours_back={hours_back}, hours_forward={hours_forward}"
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(hours=hours_back)
    window_end = now + timedelta(hours=hours_forward)

    result = await db.execute(
        select(ScheduleEntry)
        .where(
            ScheduleEntry.channel_id == channel_id,
            ScheduleEntry.end_time > window_start,
            ScheduleEntry.start_time < window_end,
        )
        .order_by(ScheduleEntry.start_time)
    )
    entries = result.scalars().all()

    logger.info(
        f"get_channel_schedule: channel_id={channel_id}, "
        f"window={window_start.isoformat()} → {window_end.isoformat()}, "
        f"entries={len(entries)}"
    )
    return [_entry_to_dict(e) for e in entries]


# ─── GET /api/schedules/channel/{channel_id}/now ─────────────────────────────

@router.get("/channel/{channel_id}/now")
async def get_now_playing(channel_id: int, db: AsyncSession = Depends(get_db)):
    """
    Return the schedule entry that is currently playing on a channel.

    Returns 404 if nothing is scheduled at this moment.
    """
    logger.debug(f"get_now_playing called: channel_id={channel_id}")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    result = await db.execute(
        select(ScheduleEntry)
        .where(
            ScheduleEntry.channel_id == channel_id,
            ScheduleEntry.start_time <= now,
            ScheduleEntry.end_time > now,
        )
        .order_by(ScheduleEntry.start_time)
        .limit(1)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        logger.warning(f"get_now_playing: nothing playing on channel {channel_id} at {now.isoformat()}")
        raise HTTPException(status_code=404, detail="Nothing currently scheduled on this channel")

    offset_seconds = (now - entry.start_time).total_seconds()
    logger.info(
        f"get_now_playing: channel_id={channel_id}, "
        f"title='{entry.title}', offset={offset_seconds:.1f}s"
    )
    return {**_entry_to_dict(entry), "current_offset_seconds": int(offset_seconds)}


# ─── GET /api/schedules/{entry_id} ───────────────────────────────────────────

@router.get("/{entry_id}")
async def get_schedule_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single schedule entry by ID."""
    logger.debug(f"get_schedule_entry called: entry_id={entry_id}")
    result = await db.execute(select(ScheduleEntry).where(ScheduleEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        logger.warning(f"get_schedule_entry: entry {entry_id} not found")
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    logger.info(f"get_schedule_entry: returned entry '{entry.title}' (id={entry_id})")
    return _entry_to_dict(entry)


# ─── POST /api/schedules/ ─────────────────────────────────────────────────────

@router.post("/")
async def create_schedule_entry(
    data: CreateScheduleEntryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually create a schedule entry.

    start_time must be an ISO 8601 datetime string (UTC assumed if no tzinfo).
    end_time is computed as start_time + duration seconds.
    """
    logger.debug(
        f"create_schedule_entry called: channel_id={data.channel_id}, "
        f"title='{data.title}', start_time={data.start_time}"
    )

    try:
        start_dt = datetime.fromisoformat(data.start_time.replace("Z", "+00:00"))
        # Strip tzinfo so storage is consistent with auto-generated entries
        start_dt = start_dt.replace(tzinfo=None)
    except ValueError as exc:
        logger.warning(f"create_schedule_entry: invalid start_time='{data.start_time}': {exc}")
        raise HTTPException(status_code=400, detail=f"Invalid start_time format: {exc}")

    end_dt = start_dt + timedelta(seconds=data.duration)

    entry = ScheduleEntry(
        channel_id=data.channel_id,
        title=data.title,
        series_name=data.series_name,
        season_number=data.season_number,
        episode_number=data.episode_number,
        media_item_id=data.media_item_id,
        library_id=data.library_id,
        item_type=data.item_type,
        genres=data.genres,
        start_time=start_dt,
        end_time=end_dt,
        duration=data.duration,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    logger.info(
        f"create_schedule_entry: created entry '{entry.title}' "
        f"(id={entry.id}, channel_id={entry.channel_id})"
    )
    return {"id": entry.id, "message": "Schedule entry created successfully"}


# ─── PUT /api/schedules/{entry_id} ───────────────────────────────────────────

@router.put("/{entry_id}")
async def update_schedule_entry(
    entry_id: int,
    data: UpdateScheduleEntryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a schedule entry.

    Recalculates end_time if start_time or duration changes.
    """
    logger.debug(f"update_schedule_entry called: entry_id={entry_id}")
    result = await db.execute(select(ScheduleEntry).where(ScheduleEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        logger.warning(f"update_schedule_entry: entry {entry_id} not found")
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    if data.title is not None:
        entry.title = data.title
    if data.series_name is not None:
        entry.series_name = data.series_name
    if data.season_number is not None:
        entry.season_number = data.season_number
    if data.episode_number is not None:
        entry.episode_number = data.episode_number
    if data.media_item_id is not None:
        entry.media_item_id = data.media_item_id
    if data.library_id is not None:
        entry.library_id = data.library_id
    if data.item_type is not None:
        entry.item_type = data.item_type
    if data.genres is not None:
        entry.genres = data.genres

    if data.start_time is not None:
        try:
            start_dt = datetime.fromisoformat(data.start_time.replace("Z", "+00:00"))
            entry.start_time = start_dt.replace(tzinfo=None)
        except ValueError as exc:
            logger.warning(f"update_schedule_entry: invalid start_time='{data.start_time}': {exc}")
            raise HTTPException(status_code=400, detail=f"Invalid start_time format: {exc}")

    if data.duration is not None:
        entry.duration = data.duration

    # Recompute end_time whenever start_time or duration changed
    if data.start_time is not None or data.duration is not None:
        entry.end_time = entry.start_time + timedelta(seconds=entry.duration)

    await db.commit()
    await db.refresh(entry)

    logger.info(f"update_schedule_entry: updated entry '{entry.title}' (id={entry_id})")
    return {"id": entry.id, "message": "Schedule entry updated successfully"}


# ─── DELETE /api/schedules/{entry_id} ────────────────────────────────────────

@router.delete("/{entry_id}")
async def delete_schedule_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a single schedule entry."""
    logger.debug(f"delete_schedule_entry called: entry_id={entry_id}")
    result = await db.execute(select(ScheduleEntry).where(ScheduleEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        logger.warning(f"delete_schedule_entry: entry {entry_id} not found")
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    title = entry.title
    await db.delete(entry)
    await db.commit()

    logger.info(f"delete_schedule_entry: deleted entry '{title}' (id={entry_id})")
    return {"message": "Schedule entry deleted successfully"}
