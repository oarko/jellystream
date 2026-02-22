"""Genre-based schedule generator.

Fills a channel's schedule by fetching genre-matching items from Jellyfin
and arranging them into sequential time slots starting from where the
current schedule ends (or from now if no schedule exists).
"""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.logging_config import get_logger
from app.integrations.jellyfin import JellyfinClient
from app.models.channel import Channel
from app.models.channel_library import ChannelLibrary
from app.models.genre_filter import GenreFilter
from app.models.schedule_entry import ScheduleEntry

logger = get_logger(__name__)

# Minimum ticks for a valid item (30 seconds = 300,000,000 ticks)
_MIN_TICKS = 300_000_000
_TICKS_PER_SECOND = 10_000_000


def _get_client() -> JellyfinClient:
    return JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=getattr(settings, "JELLYFIN_CLIENT_NAME", "JellyStream"),
        device_name=getattr(settings, "JELLYFIN_DEVICE_NAME", "JellyStream Server"),
        device_id=getattr(settings, "JELLYFIN_DEVICE_ID", None),
    )


async def _fetch_genre_items(
    client: JellyfinClient,
    library_id: str,
    genres: List[str],
    content_type: str,  # "movie" | "episode" | "both"
) -> List[dict]:
    """
    Fetch items from a Jellyfin library filtered by genre.

    Returns a list of raw Jellyfin item dicts that have a non-trivial RunTimeTicks.
    """
    user_id = await client.ensure_user_id()

    # Map content_type to Jellyfin IncludeItemTypes
    type_map = {
        "movie": "Movie",
        "episode": "Episode",
        "both": "Movie,Episode",
    }
    include_types = type_map.get(content_type, "Movie,Episode")

    genres_param = ",".join(genres) if genres else None

    logger.debug(
        f"_fetch_genre_items: library={library_id}, genres={genres}, "
        f"content_type={content_type}, include_types={include_types}"
    )

    import aiohttp

    items: List[dict] = []
    start_index = 0
    page_size = 500

    async with aiohttp.ClientSession() as session:
        while True:
            params: dict = {
                "ParentId": library_id,
                "Recursive": "true",
                "IncludeItemTypes": include_types,
                "Fields": "RunTimeTicks,Genres,SeriesName,ParentIndexNumber,IndexNumber",
                "Limit": page_size,
                "StartIndex": start_index,
                "SortBy": "SortName",
                "SortOrder": "Ascending",
            }
            if genres_param:
                params["Genres"] = genres_param

            url = f"{client.base_url}/Users/{user_id}/Items"
            async with session.get(url, headers=client.headers, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

            batch = data.get("Items", [])
            total = data.get("TotalRecordCount", 0)

            # Filter out items without a playable duration
            valid = [
                item for item in batch
                if (item.get("RunTimeTicks") or 0) >= _MIN_TICKS
            ]
            items.extend(valid)
            logger.debug(
                f"_fetch_genre_items: page start={start_index}, "
                f"batch={len(batch)}, valid={len(valid)}, total={total}"
            )

            start_index += page_size
            if start_index >= total:
                break

    logger.info(
        f"_fetch_genre_items: library={library_id}, genres={genres} → "
        f"{len(items)} playable items"
    )
    return items


async def generate_channel_schedule(
    channel_id: int,
    days: int = 7,
    db: AsyncSession = None,
) -> int:
    """
    Generate `days` days of schedule entries for a channel.

    Starts from:
    - channel.schedule_generated_through if set (extends existing schedule)
    - otherwise from the current UTC time

    Picks items at random from the pool so the schedule varies.

    Returns the count of ScheduleEntry rows created.
    """
    logger.info(f"generate_channel_schedule: channel_id={channel_id}, days={days}")

    # ── Load channel ──────────────────────────────────────────────────────────
    ch_result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = ch_result.scalar_one_or_none()
    if not channel:
        logger.error(f"generate_channel_schedule: channel {channel_id} not found")
        raise ValueError(f"Channel {channel_id} not found")

    # ── Load libraries ────────────────────────────────────────────────────────
    lib_result = await db.execute(
        select(ChannelLibrary).where(ChannelLibrary.channel_id == channel_id)
    )
    libraries = lib_result.scalars().all()
    if not libraries:
        logger.warning(
            f"generate_channel_schedule: channel {channel_id} has no libraries, skipping"
        )
        return 0

    # ── Load genre filters ────────────────────────────────────────────────────
    gf_result = await db.execute(
        select(GenreFilter).where(GenreFilter.channel_id == channel_id)
    )
    genre_filters = gf_result.scalars().all()

    # ── Build item pool ───────────────────────────────────────────────────────
    client = _get_client()
    item_pool: List[dict] = []
    seen_ids: set = set()

    for lib in libraries:
        if genre_filters:
            # Group filters by content_type to minimise API calls
            by_type: dict = {}
            for gf in genre_filters:
                by_type.setdefault(gf.content_type, []).append(gf.genre)

            for content_type, genres in by_type.items():
                try:
                    fetched = await _fetch_genre_items(
                        client, lib.library_id, genres, content_type
                    )
                except Exception as exc:
                    logger.error(
                        f"generate_channel_schedule: fetch failed for "
                        f"library={lib.library_id}, genres={genres}: {exc}",
                        exc_info=True,
                    )
                    continue

                for item in fetched:
                    if item["Id"] not in seen_ids:
                        seen_ids.add(item["Id"])
                        item_pool.append(item)
        else:
            # No genre filters — fetch everything (movies + episodes)
            try:
                fetched = await _fetch_genre_items(client, lib.library_id, [], "both")
            except Exception as exc:
                logger.error(
                    f"generate_channel_schedule: fetch failed for "
                    f"library={lib.library_id} (no filter): {exc}",
                    exc_info=True,
                )
                continue

            for item in fetched:
                if item["Id"] not in seen_ids:
                    seen_ids.add(item["Id"])
                    item_pool.append(item)

    if not item_pool:
        logger.warning(
            f"generate_channel_schedule: channel {channel_id} — "
            f"item pool is empty after fetching all libraries"
        )
        return 0

    logger.info(
        f"generate_channel_schedule: channel {channel_id} — "
        f"{len(item_pool)} unique items in pool"
    )

    # ── Determine start time ──────────────────────────────────────────────────
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if channel.schedule_generated_through and channel.schedule_generated_through > now:
        fill_from = channel.schedule_generated_through
    else:
        fill_from = now

    fill_until = fill_from + timedelta(days=days)
    logger.debug(
        f"generate_channel_schedule: filling {fill_from.isoformat()} → "
        f"{fill_until.isoformat()}"
    )

    # ── Fill schedule ─────────────────────────────────────────────────────────
    cursor = fill_from
    entries_created = 0
    shuffled_pool = item_pool.copy()
    random.shuffle(shuffled_pool)
    pool_index = 0

    new_entries: List[ScheduleEntry] = []

    while cursor < fill_until:
        if pool_index >= len(shuffled_pool):
            # Re-shuffle and loop through pool again
            random.shuffle(shuffled_pool)
            pool_index = 0

        item = shuffled_pool[pool_index]
        pool_index += 1

        ticks = item.get("RunTimeTicks", 0)
        if not ticks or ticks < _MIN_TICKS:
            continue

        duration_seconds = int(ticks // _TICKS_PER_SECOND)
        end_time = cursor + timedelta(seconds=duration_seconds)

        # Build genres JSON string
        genres_list = item.get("Genres", [])
        genres_json = json.dumps(genres_list) if genres_list else None

        entry = ScheduleEntry(
            channel_id=channel_id,
            title=item.get("Name", "Unknown"),
            series_name=item.get("SeriesName"),
            season_number=item.get("ParentIndexNumber"),
            episode_number=item.get("IndexNumber"),
            media_item_id=item["Id"],
            library_id=item.get("ParentId", ""),
            item_type=item.get("Type", "Movie"),
            genres=genres_json,
            start_time=cursor,
            end_time=end_time,
            duration=duration_seconds,
        )
        new_entries.append(entry)
        cursor = end_time
        entries_created += 1

    # ── Persist entries ───────────────────────────────────────────────────────
    for entry in new_entries:
        db.add(entry)

    # ── Update channel.schedule_generated_through ─────────────────────────────
    if new_entries:
        channel.schedule_generated_through = new_entries[-1].end_time

    await db.commit()

    logger.info(
        f"generate_channel_schedule: channel {channel_id} — "
        f"{entries_created} entries created, "
        f"schedule through {channel.schedule_generated_through}"
    )
    return entries_created
