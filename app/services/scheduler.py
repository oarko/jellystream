"""APScheduler integration — background schedule maintenance.

Runs a daily job at 2:00 AM UTC that extends the schedule for any
genre_auto channel whose schedule is running low (< 48 hours remaining).
"""

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Singleton scheduler instance (started once at app startup)
scheduler = AsyncIOScheduler(timezone="UTC")

# Extend schedule when fewer than this many hours remain
_LOW_WATERMARK_HOURS = 48

# How many days to generate when extending
_EXTEND_DAYS = 7


async def daily_schedule_job() -> None:
    """
    Daily maintenance job: extend schedules for channels running low.

    A channel is considered "low" when its schedule_generated_through
    is less than 48 hours from now (or is None/past).
    """
    logger.info("daily_schedule_job: started")

    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.channel import Channel
    from app.services.schedule_generator import generate_channel_schedule

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    threshold = now + timedelta(hours=_LOW_WATERMARK_HOURS)

    extended = 0
    errors = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.enabled == True,
                Channel.schedule_type == "genre_auto",
            )
        )
        channels = result.scalars().all()

        logger.info(f"daily_schedule_job: checking {len(channels)} genre_auto channels")

        for channel in channels:
            sgt = channel.schedule_generated_through
            if sgt is None or sgt < threshold:
                logger.info(
                    f"daily_schedule_job: extending schedule for "
                    f"channel '{channel.name}' (id={channel.id}), "
                    f"schedule_generated_through={sgt}"
                )
                try:
                    count = await generate_channel_schedule(
                        channel.id, days=_EXTEND_DAYS, db=db
                    )
                    logger.info(
                        f"daily_schedule_job: channel {channel.id} — "
                        f"{count} new entries created"
                    )
                    extended += 1
                except Exception as exc:
                    logger.error(
                        f"daily_schedule_job: failed to extend channel {channel.id}: {exc}",
                        exc_info=True,
                    )
                    errors += 1
            else:
                remaining_hours = (sgt - now).total_seconds() / 3600
                logger.debug(
                    f"daily_schedule_job: channel {channel.id} has "
                    f"{remaining_hours:.1f}h remaining — OK"
                )

    logger.info(
        f"daily_schedule_job: finished — "
        f"{extended} channels extended, {errors} errors"
    )


def start_scheduler() -> None:
    """
    Register jobs and start the APScheduler background scheduler.

    Call this once from app startup (lifespan handler in main.py).
    """
    if scheduler.running:
        logger.warning("start_scheduler: scheduler is already running")
        return

    scheduler.add_job(
        daily_schedule_job,
        trigger="cron",
        hour=2,
        minute=0,
        id="daily_schedule_job",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1h late execution after restart
    )

    scheduler.start()
    logger.info("start_scheduler: APScheduler started (daily job at 02:00 UTC)")


def stop_scheduler() -> None:
    """
    Gracefully shut down the scheduler.

    Call this from the app shutdown handler.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("stop_scheduler: APScheduler stopped")
    else:
        logger.debug("stop_scheduler: scheduler was not running")
