"""Schedule API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.schedule import Schedule

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_schedules(db: AsyncSession = Depends(get_db)):
    """Get all schedules."""
    result = await db.execute(select(Schedule))
    schedules = result.scalars().all()
    return [
        {
            "id": s.id,
            "stream_id": s.stream_id,
            "title": s.title,
            "media_item_id": s.media_item_id,
            "scheduled_time": s.scheduled_time,
            "duration": s.duration,
            "metadata": s.extra_metadata,
            "created_at": s.created_at,
        }
        for s in schedules
    ]


@router.get("/stream/{stream_id}")
async def get_stream_schedules(stream_id: int, db: AsyncSession = Depends(get_db)):
    """Get all schedules for a specific stream."""
    result = await db.execute(select(Schedule).where(Schedule.stream_id == stream_id))
    schedules = result.scalars().all()
    return [
        {
            "id": s.id,
            "stream_id": s.stream_id,
            "title": s.title,
            "media_item_id": s.media_item_id,
            "scheduled_time": s.scheduled_time,
            "duration": s.duration,
            "metadata": s.extra_metadata,
            "created_at": s.created_at,
        }
        for s in schedules
    ]


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "id": schedule.id,
        "stream_id": schedule.stream_id,
        "title": schedule.title,
        "media_item_id": schedule.media_item_id,
        "scheduled_time": schedule.scheduled_time,
        "duration": schedule.duration,
        "metadata": schedule.extra_metadata,
        "created_at": schedule.created_at,
    }


@router.post("/")
async def create_schedule(
    stream_id: int,
    title: str,
    media_item_id: str,
    scheduled_time: str,
    duration: int,
    metadata: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Create a new schedule entry."""
    from datetime import datetime

    # Parse datetime
    try:
        scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    schedule = Schedule(
        stream_id=stream_id,
        title=title,
        media_item_id=media_item_id,
        scheduled_time=scheduled_dt,
        duration=duration,
        extra_metadata=metadata
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return {
        "id": schedule.id,
        "message": "Schedule created successfully"
    }


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    title: str = None,
    media_item_id: str = None,
    scheduled_time: str = None,
    duration: int = None,
    metadata: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if title is not None:
        schedule.title = title
    if media_item_id is not None:
        schedule.media_item_id = media_item_id
    if scheduled_time is not None:
        from datetime import datetime
        try:
            schedule.scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format")
    if duration is not None:
        schedule.duration = duration
    if metadata is not None:
        schedule.extra_metadata = metadata

    await db.commit()
    await db.refresh(schedule)

    return {
        "id": schedule.id,
        "message": "Schedule updated successfully"
    }


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await db.delete(schedule)
    await db.commit()

    return {"message": "Schedule deleted successfully"}
