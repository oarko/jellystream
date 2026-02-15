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
