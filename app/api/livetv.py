"""Live TV API endpoints for M3U and XMLTV generation."""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.stream import Stream
from app.models.schedule import Schedule
from app.core.config import settings

router = APIRouter()


@router.get("/m3u/{stream_id}")
async def get_stream_m3u(stream_id: int, db: AsyncSession = Depends(get_db)):
    """
    Generate M3U playlist for a specific stream.

    Format:
    #EXTINF:-1 channel-id="100.1" channel-number="100.1" tvg-name="My Stream" group-title="JellyStream",100.1 My Stream
    http://localhost:8000/api/livetv/stream/1
    """
    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Generate channel number if not set
    channel_number = stream.channel_number or f"100.{stream.id}"

    # Build stream URL
    stream_url = f"{settings.HOST}:{settings.PORT}/api/livetv/stream/{stream.id}"
    if not stream_url.startswith('http'):
        stream_url = f"http://{stream_url}"

    # Generate M3U
    m3u_content = "#EXTM3U\n"
    m3u_content += f'#EXTINF:-1 channel-id="{stream.id}" channel-number="{channel_number}" '
    m3u_content += f'tvg-name="{stream.name}" tvg-id="{stream.id}" group-title="JellyStream",'
    m3u_content += f'{channel_number} {stream.name}\n'
    m3u_content += f'{stream_url}\n'

    return Response(content=m3u_content, media_type="application/x-mpegURL")


@router.get("/m3u/all")
async def get_all_streams_m3u(db: AsyncSession = Depends(get_db)):
    """
    Generate M3U playlist for all enabled streams.
    """
    result = await db.execute(select(Stream).where(Stream.enabled == True))
    streams = result.scalars().all()

    m3u_content = "#EXTM3U\n"

    for stream in streams:
        channel_number = stream.channel_number or f"100.{stream.id}"
        stream_url = f"http://{settings.HOST}:{settings.PORT}/api/livetv/stream/{stream.id}"

        m3u_content += f'#EXTINF:-1 channel-id="{stream.id}" channel-number="{channel_number}" '
        m3u_content += f'tvg-name="{stream.name}" tvg-id="{stream.id}" group-title="JellyStream",'
        m3u_content += f'{channel_number} {stream.name}\n'
        m3u_content += f'{stream_url}\n'

    return Response(content=m3u_content, media_type="application/x-mpegURL")


@router.get("/xmltv/{stream_id}")
async def get_stream_xmltv(stream_id: int, db: AsyncSession = Depends(get_db)):
    """
    Generate XMLTV EPG data for a specific stream.

    XMLTV format for Electronic Program Guide.
    """
    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Get schedules for this stream
    schedules_result = await db.execute(
        select(Schedule).where(Schedule.stream_id == stream_id)
    )
    schedules = schedules_result.scalars().all()

    # Generate XMLTV
    xmltv_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xmltv_content += '<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    xmltv_content += '<tv generator-info-name="JellyStream">\n'

    # Channel definition
    channel_id = str(stream.id)
    xmltv_content += f'  <channel id="{channel_id}">\n'
    xmltv_content += f'    <display-name>{stream.name}</display-name>\n'
    xmltv_content += '  </channel>\n'

    # Programs from schedules
    for schedule in schedules:
        start_time = schedule.scheduled_time.strftime("%Y%m%d%H%M%S +0000")
        end_time = (schedule.scheduled_time + timedelta(seconds=schedule.duration)).strftime("%Y%m%d%H%M%S +0000")

        xmltv_content += f'  <programme channel="{channel_id}" start="{start_time}" stop="{end_time}">\n'
        xmltv_content += f'    <title>{schedule.title}</title>\n'

        # Add metadata if available
        if schedule.extra_metadata:
            import json
            try:
                metadata = json.loads(schedule.extra_metadata)
                if metadata.get('seriesName'):
                    xmltv_content += f'    <sub-title>{metadata.get("seriesName")}</sub-title>\n'
                if metadata.get('type'):
                    xmltv_content += f'    <category>{metadata.get("type")}</category>\n'
            except:
                pass

        xmltv_content += '  </programme>\n'

    xmltv_content += '</tv>\n'

    return Response(content=xmltv_content, media_type="application/xml")


@router.get("/xmltv/all")
async def get_all_streams_xmltv(db: AsyncSession = Depends(get_db)):
    """
    Generate XMLTV EPG data for all enabled streams.
    """
    result = await db.execute(select(Stream).where(Stream.enabled == True))
    streams = result.scalars().all()

    xmltv_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xmltv_content += '<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    xmltv_content += '<tv generator-info-name="JellyStream">\n'

    # Channel definitions
    for stream in streams:
        channel_id = str(stream.id)
        xmltv_content += f'  <channel id="{channel_id}">\n'
        xmltv_content += f'    <display-name>{stream.name}</display-name>\n'
        xmltv_content += '  </channel>\n'

    # Programs from all schedules
    for stream in streams:
        schedules_result = await db.execute(
            select(Schedule).where(Schedule.stream_id == stream.id)
        )
        schedules = schedules_result.scalars().all()

        channel_id = str(stream.id)
        for schedule in schedules:
            start_time = schedule.scheduled_time.strftime("%Y%m%d%H%M%S +0000")
            end_time = (schedule.scheduled_time + timedelta(seconds=schedule.duration)).strftime("%Y%m%d%H%M%S +0000")

            xmltv_content += f'  <programme channel="{channel_id}" start="{start_time}" stop="{end_time}">\n'
            xmltv_content += f'    <title>{schedule.title}</title>\n'

            if schedule.extra_metadata:
                import json
                try:
                    metadata = json.loads(schedule.extra_metadata)
                    if metadata.get('seriesName'):
                        xmltv_content += f'    <sub-title>{metadata.get("seriesName")}</sub-title>\n'
                    if metadata.get('type'):
                        xmltv_content += f'    <category>{metadata.get("type")}</category>\n'
                except:
                    pass

            xmltv_content += '  </programme>\n'

    xmltv_content += '</tv>\n'

    return Response(content=xmltv_content, media_type="application/xml")


@router.get("/stream/{stream_id}")
async def stream_live_content(stream_id: int, db: AsyncSession = Depends(get_db)):
    """
    Stream live content based on current schedule.

    This endpoint will:
    1. Check current time
    2. Find what should be playing now
    3. Redirect to the actual Jellyfin stream URL
    """
    from app.integrations.jellyfin import JellyfinClient

    result = await db.execute(select(Stream).where(Stream.id == stream_id))
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Get current schedule item
    now = datetime.now()
    schedules_result = await db.execute(
        select(Schedule)
        .where(Schedule.stream_id == stream_id)
        .where(Schedule.scheduled_time <= now)
        .order_by(Schedule.scheduled_time.desc())
    )
    current_schedule = schedules_result.scalars().first()

    if not current_schedule:
        raise HTTPException(status_code=404, detail="No content scheduled at this time")

    # Get Jellyfin stream URL for the media item
    client = JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None
    )

    stream_url = await client.get_stream_url(current_schedule.media_item_id)

    # Redirect to Jellyfin stream
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=stream_url)
