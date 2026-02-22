"""Live TV API endpoints — M3U playlist and XMLTV EPG generation.

IMPORTANT: Literal routes (/m3u/all, /xmltv/all) are registered BEFORE
parameterised routes (/m3u/{channel_id}, /xmltv/{channel_id}) so that
FastAPI does not match "all" as an integer channel_id.
"""

import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.channel import Channel
from app.models.schedule_entry import ScheduleEntry

logger = get_logger(__name__)
router = APIRouter()

# ── helpers ──────────────────────────────────────────────────────────────────

def _base_url() -> str:
    host = settings.HOST.rstrip("/")
    if not host.startswith("http"):
        host = f"http://{host}"
    return f"{host}:{settings.PORT}"


def _m3u_line(channel: Channel) -> str:
    ch_num = channel.channel_number or f"100.{channel.id}"
    stream_url = f"{_base_url()}/api/livetv/stream/{channel.id}"
    lines = (
        f'#EXTINF:-1 channel-id="{channel.id}" channel-number="{ch_num}" '
        f'tvg-name="{channel.name}" tvg-id="{channel.id}" group-title="JellyStream",'
        f'{ch_num} {channel.name}\n'
        f'{stream_url}\n'
    )
    return lines


def _xmltv_channel(channel: Channel) -> str:
    return (
        f'  <channel id="{channel.id}">\n'
        f'    <display-name>{channel.name}</display-name>\n'
        f'  </channel>\n'
    )


def _xmltv_programme(entry: ScheduleEntry) -> str:
    start = entry.start_time.strftime("%Y%m%d%H%M%S +0000")
    stop = entry.end_time.strftime("%Y%m%d%H%M%S +0000")

    lines = (
        f'  <programme channel="{entry.channel_id}" start="{start}" stop="{stop}">\n'
        f'    <title>{_xml_escape(entry.title)}</title>\n'
    )

    if entry.series_name:
        lines += f'    <sub-title>{_xml_escape(entry.series_name)}</sub-title>\n'

    if entry.season_number and entry.episode_number:
        # XMLTV uses 0-based season/episode numbers
        lines += (
            f'    <episode-num system="xmltv_ns">'
            f'{entry.season_number - 1}.{entry.episode_number - 1}.'
            f'</episode-num>\n'
        )

    # item_type as primary category, then genres
    lines += f'    <category>{_xml_escape(entry.item_type)}</category>\n'
    if entry.genres:
        try:
            genre_list = json.loads(entry.genres)
            for g in genre_list:
                lines += f'    <category>{_xml_escape(g)}</category>\n'
        except (json.JSONDecodeError, TypeError):
            pass

    lines += '  </programme>\n'
    return lines


def _xml_escape(text: str) -> str:
    """Minimal XML character escaping."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _xmltv_header() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
        '<tv generator-info-name="JellyStream">\n'
    )


# ─── GET /api/livetv/m3u/all ─────────────────────────────────────────────────
# MUST be registered before /m3u/{channel_id}

@router.get("/m3u/all")
async def get_all_m3u(db: AsyncSession = Depends(get_db)):
    """Generate M3U playlist for all enabled channels."""
    logger.debug("get_all_m3u called")

    result = await db.execute(
        select(Channel)
        .where(Channel.enabled == True)
        .order_by(Channel.channel_number, Channel.id)
    )
    channels = result.scalars().all()

    m3u = "#EXTM3U\n"
    for ch in channels:
        m3u += _m3u_line(ch)

    logger.info(f"get_all_m3u: returned {len(channels)} channels")
    return Response(content=m3u, media_type="application/x-mpegURL")


# ─── GET /api/livetv/xmltv/all ───────────────────────────────────────────────
# MUST be registered before /xmltv/{channel_id}

@router.get("/xmltv/all")
async def get_all_xmltv(db: AsyncSession = Depends(get_db)):
    """Generate XMLTV EPG for all enabled channels (EPG window: -3h to +7d)."""
    logger.debug("get_all_xmltv called")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(hours=3)
    window_end = now + timedelta(days=7)

    result = await db.execute(
        select(Channel)
        .where(Channel.enabled == True)
        .order_by(Channel.channel_number, Channel.id)
    )
    channels = result.scalars().all()

    xmltv = _xmltv_header()

    # Channel definitions
    for ch in channels:
        xmltv += _xmltv_channel(ch)

    # Programme entries
    for ch in channels:
        entries_result = await db.execute(
            select(ScheduleEntry)
            .where(
                ScheduleEntry.channel_id == ch.id,
                ScheduleEntry.end_time > window_start,
                ScheduleEntry.start_time < window_end,
            )
            .order_by(ScheduleEntry.start_time)
        )
        entries = entries_result.scalars().all()
        for entry in entries:
            xmltv += _xmltv_programme(entry)

    xmltv += "</tv>\n"

    total_entries = sum(1 for line in xmltv.splitlines() if "<programme " in line)
    logger.info(
        f"get_all_xmltv: {len(channels)} channels, "
        f"~{total_entries} programme entries in window"
    )
    return Response(content=xmltv, media_type="application/xml")


# ─── GET /api/livetv/m3u/{channel_id} ────────────────────────────────────────

@router.get("/m3u/{channel_id}")
async def get_channel_m3u(channel_id: int, db: AsyncSession = Depends(get_db)):
    """Generate M3U playlist for a single channel."""
    logger.debug(f"get_channel_m3u called: channel_id={channel_id}")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"get_channel_m3u: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    m3u = "#EXTM3U\n" + _m3u_line(channel)

    logger.info(f"get_channel_m3u: returned M3U for channel '{channel.name}'")
    return Response(content=m3u, media_type="application/x-mpegURL")


# ─── GET /api/livetv/xmltv/{channel_id} ──────────────────────────────────────

@router.get("/xmltv/{channel_id}")
async def get_channel_xmltv(channel_id: int, db: AsyncSession = Depends(get_db)):
    """Generate XMLTV EPG for a single channel (EPG window: -3h to +7d)."""
    logger.debug(f"get_channel_xmltv called: channel_id={channel_id}")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"get_channel_xmltv: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(hours=3)
    window_end = now + timedelta(days=7)

    entries_result = await db.execute(
        select(ScheduleEntry)
        .where(
            ScheduleEntry.channel_id == channel_id,
            ScheduleEntry.end_time > window_start,
            ScheduleEntry.start_time < window_end,
        )
        .order_by(ScheduleEntry.start_time)
    )
    entries = entries_result.scalars().all()

    xmltv = _xmltv_header()
    xmltv += _xmltv_channel(channel)
    for entry in entries:
        xmltv += _xmltv_programme(entry)
    xmltv += "</tv>\n"

    logger.info(
        f"get_channel_xmltv: channel '{channel.name}', "
        f"{len(entries)} entries in EPG window"
    )
    return Response(content=xmltv, media_type="application/xml")


# ─── GET /api/livetv/stream/{channel_id} ─────────────────────────────────────

@router.get("/stream/{channel_id}")
async def stream_channel(channel_id: int, db: AsyncSession = Depends(get_db)):
    """
    Proxy the current scheduled item for a channel through ffmpeg.

    Seeks to the correct offset so the viewer joins the stream mid-programme,
    matching what real broadcast TV does.
    """
    logger.debug(f"stream_channel called: channel_id={channel_id}")

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        logger.warning(f"stream_channel: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel.enabled:
        logger.warning(f"stream_channel: channel {channel_id} is disabled")
        raise HTTPException(status_code=403, detail="Channel is disabled")

    try:
        from app.services.stream_proxy import stream_channel as proxy_stream
        logger.info(f"stream_channel: delegating to stream_proxy for channel '{channel.name}'")
        return await proxy_stream(channel_id, db)
    except ImportError:
        logger.error("stream_channel: stream_proxy service not yet available")
        raise HTTPException(status_code=503, detail="Stream proxy service not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"stream_channel: unexpected error for channel {channel_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
