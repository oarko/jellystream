"""ffmpeg-based stream proxy.

Finds the currently playing ScheduleEntry for a channel, calculates the
elapsed offset, and pipes the media through ffmpeg starting at that offset.
This makes the channel behave like real TV — viewers always join mid-show.

When one entry ends the generator automatically transitions to the next
scheduled entry so the stream runs continuously without the client
needing to reconnect.
"""

import asyncio
import json
import os
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

# How long (seconds) to wait when there is a gap in the schedule before
# re-checking whether a new entry has become available.
_GAP_POLL_INTERVAL = 5


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


async def _detect_preferred_audio_index(source: str) -> Optional[int]:
    """
    Run ffprobe to find the absolute stream index of the first audio track
    matching settings.PREFERRED_AUDIO_LANGUAGE.

    Compares against both 2-letter (en) and 3-letter (eng) ISO 639 codes so
    that files tagged either way are handled correctly.

    Returns the stream index (int) if found, or None to fall back to the
    first audio track.
    """
    want = settings.PREFERRED_AUDIO_LANGUAGE.lower().strip()
    if not want:
        return None

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "a",
            source,
            stdout=PIPE,
            stderr=PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            logger.warning(
                f"_detect_preferred_audio_index: ffprobe timed out for {source!r}"
            )
            return None

        data = json.loads(stdout)
        for stream in data.get("streams", []):
            tags = stream.get("tags") or {}
            lang = (
                tags.get("language") or tags.get("LANGUAGE") or ""
            ).lower().strip()
            if lang and (lang == want or lang[:2] == want[:2]):
                idx = stream.get("index")
                logger.debug(
                    f"_detect_preferred_audio_index: "
                    f"preferred language '{want}' found at stream index {idx}"
                )
                return idx

        logger.debug(
            f"_detect_preferred_audio_index: "
            f"no '{want}' audio track found, using default"
        )

    except Exception as exc:
        logger.warning(f"_detect_preferred_audio_index: ffprobe failed: {exc}")

    return None


def _build_ffmpeg_cmd(
    source: str, offset_seconds: int, audio_stream_index: Optional[int] = None
) -> list:
    # When any -map is present ffmpeg disables automatic stream selection, so
    # we must map both video and audio explicitly.  If ffprobe identified a
    # preferred-language track use its absolute index; otherwise fall back to
    # the first audio stream in the file.
    audio_map = (
        ["-map", f"0:{audio_stream_index}"]
        if audio_stream_index is not None
        else ["-map", "0:a:0"]
    )
    return [
        "ffmpeg",
        # ── Input / seek ─────────────────────────────────────────────────────
        "-ss", str(offset_seconds),    # fast seek in local file / HTTP Range
        "-probesize", "262144",        # 256 KB probe instead of default 5 MB
        "-analyzeduration", "1000000", # 1 s analysis instead of default 5 s
        "-fflags", "nobuffer",         # pass frames through without extra buffering
        "-i", source,
        # ── Stream mapping ────────────────────────────────────────────────────
        "-map", "0:v:0",               # first video stream
        *audio_map,                    # preferred language track or first audio
        # ── Video — H.264 1080p ───────────────────────────────────────────────
        "-vf", "scale=-2:min(1080\\,ih)",  # scale down to 1080p max, keep AR
        "-c:v", "libx264",
        "-preset", "veryfast",         # fast encode, lower CPU than slow/medium
        "-tune", "zerolatency",        # minimize encoder buffering for live use
        "-crf", "20",                  # visually lossless at typical bitrates
        "-maxrate", "8000k",
        "-bufsize", "4000k",
        # ── Audio — AAC stereo ────────────────────────────────────────────────
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",                    # downmix to stereo
        # ── Output ───────────────────────────────────────────────────────────
        "-f", _OUTPUT_FORMAT,          # MPEG-TS container
        "-loglevel", "warning",
        "pipe:1",
    ]


async def _resolve_source(entry: ScheduleEntry, channel_id: int) -> str:
    """Return the local file path or Jellyfin HTTP URL for an entry."""
    if entry.file_path and os.path.isfile(entry.file_path):
        logger.info(
            f"_resolve_source: channel={channel_id}, title='{entry.title}' — local file"
        )
        return entry.file_path

    client = _get_client()
    source = await client.get_stream_url(entry.media_item_id)
    if entry.file_path:
        logger.warning(
            f"_resolve_source: '{entry.file_path}' not accessible, "
            f"falling back to Jellyfin HTTP stream"
        )
    else:
        logger.info(
            f"_resolve_source: channel={channel_id}, title='{entry.title}' — HTTP stream"
        )
    return source


async def _continuous_stream_generator(
    channel_id: int, db: AsyncSession, chunk_size: int = 65536
):
    """
    Yield MPEG-TS chunks indefinitely, transitioning between schedule entries
    as each one ends.

    When the current entry's ffmpeg process exits the generator re-queries
    the database for the next entry (time has advanced so the query naturally
    returns the following programme) and starts a new ffmpeg process.

    If there is a gap in the schedule the generator waits _GAP_POLL_INTERVAL
    seconds between retries instead of killing the connection.
    """
    while True:
        entry = await get_current_entry(channel_id, db)

        if not entry:
            logger.debug(
                f"_continuous_stream_generator: gap on channel {channel_id}, "
                f"waiting {_GAP_POLL_INTERVAL}s"
            )
            await asyncio.sleep(_GAP_POLL_INTERVAL)
            continue

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        offset_seconds = max(0, int((now - entry.start_time).total_seconds()))

        try:
            source = await _resolve_source(entry, channel_id)
        except Exception as exc:
            logger.error(
                f"_continuous_stream_generator: could not resolve source for "
                f"entry {entry.id} '{entry.title}': {exc}",
                exc_info=True,
            )
            # Skip to next entry by sleeping until this entry should have ended
            remaining = max(1, int((entry.end_time - now).total_seconds()))
            await asyncio.sleep(min(remaining, 30))
            continue

        audio_idx = await _detect_preferred_audio_index(source)
        cmd = _build_ffmpeg_cmd(source, offset_seconds, audio_idx)
        logger.debug(
            f"_continuous_stream_generator: starting ffmpeg for "
            f"'{entry.title}' (id={entry.id}), offset={offset_seconds}s, "
            f"audio_stream={audio_idx if audio_idx is not None else 'default'}"
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=PIPE, stderr=PIPE
            )
        except FileNotFoundError:
            logger.error("_continuous_stream_generator: ffmpeg not found")
            return  # Cannot recover — end the stream

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
            logger.info(
                f"_continuous_stream_generator: channel={channel_id} "
                f"'{entry.title}' finished, advancing to next entry"
            )

        # Tiny pause to avoid a tight spin if ffmpeg exits instantly (bad source)
        await asyncio.sleep(0.2)


async def stream_channel(channel_id: int, db: AsyncSession) -> StreamingResponse:
    """
    Start a continuous ffmpeg proxy stream for a channel.

    Verifies that something is scheduled right now (returns 404 otherwise),
    then returns a StreamingResponse backed by _continuous_stream_generator
    which automatically transitions to the next entry when the current one ends.
    """
    logger.info(f"stream_channel: channel_id={channel_id}")

    # Initial check — return 404 if nothing is playing so clients don't hang
    entry = await get_current_entry(channel_id, db)
    if not entry:
        logger.warning(f"stream_channel: nothing playing on channel {channel_id}")
        raise HTTPException(
            status_code=404, detail="No content scheduled at this time"
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    offset_seconds = max(0, int((now - entry.start_time).total_seconds()))

    return StreamingResponse(
        _continuous_stream_generator(channel_id, db),
        media_type=_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "X-Channel-Id": str(channel_id),
            "X-Entry-Title": entry.title.encode("ascii", errors="replace").decode("ascii"),
            "X-Offset-Seconds": str(offset_seconds),
        },
    )
