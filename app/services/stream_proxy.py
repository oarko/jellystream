"""ffmpeg-based stream proxy.

Finds the currently playing ScheduleEntry for a channel, calculates the
elapsed offset, and pipes the media through ffmpeg starting at that offset.
This makes the channel behave like real TV — viewers always join mid-show.
"""

import asyncio
from asyncio.subprocess import PIPE
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import get_logger
from app.integrations.jellyfin import JellyfinClient
from app.models.schedule_entry import ScheduleEntry

logger = get_logger(__name__)

# ffmpeg output format sent to Jellyfin Live TV clients
_OUTPUT_FORMAT = "mpegts"
_MEDIA_TYPE = "video/mp2t"


def _get_client() -> JellyfinClient:
    return JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=getattr(settings, "JELLYFIN_CLIENT_NAME", "JellyStream"),
        device_name=getattr(settings, "JELLYFIN_DEVICE_NAME", "JellyStream Server"),
        device_id=getattr(settings, "JELLYFIN_DEVICE_ID", None),
    )


async def get_current_entry(
    channel_id: int, db: AsyncSession
) -> Optional[ScheduleEntry]:
    """
    Return the ScheduleEntry that spans the current UTC time for a channel.

    Returns None if nothing is scheduled right now.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    logger.debug(
        f"get_current_entry: channel_id={channel_id}, now={now.isoformat()}"
    )

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

    if entry:
        offset = (now - entry.start_time).total_seconds()
        logger.debug(
            f"get_current_entry: found '{entry.title}' "
            f"(id={entry.id}), offset={offset:.1f}s"
        )
    else:
        logger.debug(f"get_current_entry: no entry found for channel {channel_id}")

    return entry


async def _stream_generator(process: asyncio.subprocess.Process, chunk_size: int = 65536):
    """Yield chunks from ffmpeg stdout until the process exits."""
    try:
        while True:
            chunk = await process.stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()
        logger.debug("_stream_generator: ffmpeg process ended")


async def stream_channel(channel_id: int, db: AsyncSession) -> StreamingResponse:
    """
    Proxy the current schedule item for a channel through ffmpeg.

    Steps:
    1. Find the ScheduleEntry that is currently playing.
    2. Calculate elapsed offset (now - start_time).
    3. Build the Jellyfin direct-stream URL.
    4. Spawn ffmpeg seeking to the offset, outputting MPEG-TS to stdout.
    5. Return a StreamingResponse wrapping ffmpeg's stdout pipe.
    """
    logger.info(f"stream_channel: channel_id={channel_id}")

    entry = await get_current_entry(channel_id, db)
    if not entry:
        logger.warning(f"stream_channel: nothing playing on channel {channel_id}")
        raise HTTPException(
            status_code=404, detail="No content scheduled at this time"
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    offset_seconds = max(0, int((now - entry.start_time).total_seconds()))

    client = _get_client()
    jellyfin_url = await client.get_stream_url(entry.media_item_id)

    logger.info(
        f"stream_channel: channel={channel_id}, "
        f"title='{entry.title}', offset={offset_seconds}s, "
        f"jellyfin_item={entry.media_item_id}"
    )

    cmd = [
        "ffmpeg",
        "-ss", str(offset_seconds),       # seek before input for speed
        "-i", jellyfin_url,
        "-c", "copy",                      # no re-encoding
        "-f", _OUTPUT_FORMAT,
        "-loglevel", "warning",
        "pipe:1",                          # output to stdout
    ]

    logger.debug(f"stream_channel: ffmpeg cmd = {' '.join(cmd[:6])} ...")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=PIPE,
            stderr=PIPE,
        )
    except FileNotFoundError:
        logger.error("stream_channel: ffmpeg not found — is it installed?")
        raise HTTPException(
            status_code=503,
            detail="ffmpeg is not installed on the server",
        )

    return StreamingResponse(
        _stream_generator(process),
        media_type=_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "X-Channel-Id": str(channel_id),
            "X-Entry-Title": entry.title,
            "X-Offset-Seconds": str(offset_seconds),
        },
    )
