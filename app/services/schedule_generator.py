"""Genre-based schedule generator.

Fills a channel's schedule by fetching genre-matching items from Jellyfin
and arranging them into sequential time slots starting from where the
current schedule ends (or from now if no schedule exists).
"""

import json
import os
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.logging_config import get_logger
from app.integrations.jellyfin import JellyfinClient
from app.models.channel import Channel
from app.models.channel_library import ChannelLibrary
from app.models.channel_collection_source import ChannelCollectionSource
from app.models.collection_item import CollectionItem
from app.models.genre_filter import GenreFilter
from app.models.schedule_entry import ScheduleEntry

logger = get_logger(__name__)

# Minimum ticks for a valid item (30 seconds = 300,000,000 ticks)
_MIN_TICKS = 300_000_000
_TICKS_PER_SECOND = 10_000_000


def _extract_path(item: dict) -> Optional[str]:
    """
    Extract the local file path from a Jellyfin item dict.

    Tries `Path` first (requires admin/download permission).
    Falls back to `MediaSources[0].Path` which is available to more users.
    """
    path = item.get("Path")
    if not path:
        sources = item.get("MediaSources") or []
        path = sources[0].get("Path") if sources else None
    return path or None


def _apply_path_map(path: Optional[str]) -> Optional[str]:
    """
    Rewrite a Jellyfin server file path to a locally accessible path using
    MEDIA_PATH_MAP (format: "/jellyfin/prefix:/local/prefix").

    Returns the original path unchanged if no mapping is configured or the
    path does not start with the configured Jellyfin prefix.
    """
    if not path:
        return None
    path_map = getattr(settings, "MEDIA_PATH_MAP", "")
    if not path_map or ":" not in path_map:
        return path
    jf_prefix, local_prefix = path_map.split(":", 1)
    if path.startswith(jf_prefix):
        remapped = local_prefix + path[len(jf_prefix):]
        logger.debug(f"_apply_path_map: {path!r} → {remapped!r}")
        return remapped
    return path


def _parse_nfo(file_path: str) -> dict:
    """
    Parse the Kodi/Jellyfin .nfo sidecar next to a media file.

    Looks for <basename>.nfo alongside the video file.
    Returns a dict with keys: description, content_rating, air_date.
    Returns an empty dict if the .nfo doesn't exist or can't be parsed.
    """
    base = os.path.splitext(file_path)[0]
    nfo_path = base + ".nfo"
    if not os.path.isfile(nfo_path):
        return {}
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        def _text(tag: str) -> Optional[str]:
            el = root.find(tag)
            if el is None:
                return None
            # Handle CDATA / stripped whitespace
            return (el.text or "").strip() or None

        result: dict = {}
        if plot := _text("plot"):
            result["description"] = plot
        if mpaa := _text("mpaa"):
            result["content_rating"] = mpaa
        # Prefer <aired> (episode air date), fall back to <year>
        result["air_date"] = _text("aired") or _text("year")

        logger.debug(f"_parse_nfo: {nfo_path!r} → {list(result.keys())}")
        return result
    except ET.ParseError as exc:
        logger.warning(f"_parse_nfo: failed to parse {nfo_path!r}: {exc}")
        return {}


def _find_thumbnail(file_path: str) -> Optional[str]:
    """
    Look for a preview image next to the media file.

    Search order:
    1. <basename>.jpg              — episode-specific thumbnail
    2. <basename>-thumb.jpg        — alternative episode thumbnail
    3. <same dir>/folder.jpg       — movie folder OR flat TV series (no Season subdir)
    4. <parent dir>/folder.jpg     — TV series folder when episode is in a Season X/ subdir

    Returns the absolute path if found, else None.
    """
    base = os.path.splitext(file_path)[0]
    same_dir = os.path.dirname(file_path)
    parent_dir = os.path.dirname(same_dir)
    for candidate in (
        base + ".jpg",
        base + "-thumb.jpg",
        os.path.join(same_dir, "folder.jpg"),
        os.path.join(parent_dir, "folder.jpg"),
    ):
        if os.path.isfile(candidate):
            logger.debug(f"_find_thumbnail: found {candidate!r}")
            return candidate
    return None


def _get_client() -> JellyfinClient:
    return JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=getattr(settings, "JELLYFIN_CLIENT_NAME", "JellyStream"),
        device_name=getattr(settings, "JELLYFIN_DEVICE_NAME", "JellyStream Server"),
        device_id=getattr(settings, "JELLYFIN_DEVICE_ID", None),
    )


def _collection_item_to_dict(item: CollectionItem) -> dict:
    """
    Convert a CollectionItem ORM row to the same dict format the schedule
    fill loop expects from Jellyfin.  Pre-fills ``_nfo`` and ``_thumbnail``
    keys so the fill loop skips sidecar I/O for these items.
    """
    return {
        "Id": item.media_item_id,
        "Name": item.title,
        "Type": item.item_type,
        "SeriesName": item.series_name,
        "ParentIndexNumber": item.season_number,
        "IndexNumber": item.episode_number,
        "RunTimeTicks": (item.duration or 0) * _TICKS_PER_SECOND,
        "Genres": json.loads(item.genres or "[]"),
        "Path": item.file_path,
        "ParentId": item.library_id or "",
        "_nfo": {
            "description": item.description,
            "content_rating": item.content_rating,
            "air_date": item.air_date,
        },
        "_thumbnail": item.thumbnail_path,
    }


async def _resolve_collection_to_items(
    collection_id: int,
    db: AsyncSession,
    client: JellyfinClient,
    _depth: int = 0,
) -> List[dict]:
    """
    Resolve a collection to a flat list of playable (Movie/Episode) item dicts.

    - Movie / Episode rows → converted directly via _collection_item_to_dict()
    - Series / Season rows → Jellyfin admin /Items query to expand to episodes
    - Collection rows     → recursive resolve (up to depth 3)
    """
    if _depth > 3:
        logger.warning("_resolve_collection_to_items: max recursion depth reached")
        return []

    ci_result = await db.execute(
        select(CollectionItem).where(CollectionItem.collection_id == collection_id)
    )
    collection_items = ci_result.scalars().all()
    logger.debug(
        f"_resolve_collection_to_items: collection_id={collection_id}, "
        f"rows={len(collection_items)}, depth={_depth}"
    )

    resolved: List[dict] = []
    import aiohttp

    async with aiohttp.ClientSession() as session:
        user_id = await client.ensure_user_id()
        for ci in collection_items:
            if ci.item_type in ("Movie", "Episode"):
                d = _collection_item_to_dict(ci)
                if d["RunTimeTicks"] >= _MIN_TICKS:
                    resolved.append(d)

            elif ci.item_type in ("Series", "Season"):
                # Expand to episodes via Jellyfin admin endpoint
                params = {
                    "ParentId": ci.media_item_id,
                    "Recursive": "true",
                    "IncludeItemTypes": "Episode",
                    "Fields": "RunTimeTicks,Genres,SeriesName,ParentIndexNumber,IndexNumber,Path,MediaSources",
                    "UserId": user_id,
                    "SortBy": "SortName",
                    "SortOrder": "Ascending",
                }
                url = f"{client.base_url}/Items"
                try:
                    async with session.get(url, headers=client.headers, params=params) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                    for ep in data.get("Items", []):
                        if (ep.get("RunTimeTicks") or 0) >= _MIN_TICKS:
                            resolved.append(ep)
                except Exception as exc:
                    logger.error(
                        f"_resolve_collection_to_items: failed to expand "
                        f"{ci.item_type} id={ci.media_item_id}: {exc}",
                        exc_info=True,
                    )

            elif ci.item_type == "Collection":
                try:
                    nested = await _resolve_collection_to_items(
                        int(ci.media_item_id), db, client, _depth + 1
                    )
                    resolved.extend(nested)
                except Exception as exc:
                    logger.error(
                        f"_resolve_collection_to_items: failed to resolve nested "
                        f"collection id={ci.media_item_id}: {exc}",
                        exc_info=True,
                    )

    logger.info(
        f"_resolve_collection_to_items: collection_id={collection_id} → "
        f"{len(resolved)} playable items"
    )
    return resolved


async def _get_collection_pool(
    channel_id: int,
    include_filters: list,
    exclude_genres: set,
    db: AsyncSession,
    client: JellyfinClient,
) -> List[dict]:
    """
    Build a deduplicated pool of items from all ChannelCollectionSource rows
    linked to *channel_id*, then apply include/exclude genre filters.
    """
    cs_result = await db.execute(
        select(ChannelCollectionSource).where(
            ChannelCollectionSource.channel_id == channel_id
        )
    )
    sources = cs_result.scalars().all()
    if not sources:
        return []

    logger.debug(
        f"_get_collection_pool: channel_id={channel_id}, "
        f"sources={[s.collection_id for s in sources]}"
    )

    raw: List[dict] = []
    seen_ids: set = set()
    for src in sources:
        try:
            items = await _resolve_collection_to_items(src.collection_id, db, client)
        except Exception as exc:
            logger.error(
                f"_get_collection_pool: failed to resolve collection "
                f"{src.collection_id}: {exc}",
                exc_info=True,
            )
            continue
        for item in items:
            item_id = item.get("Id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                raw.append(item)

    # Apply include genre filter.
    # Items with no genres stored are passed through — they were manually curated
    # into the collection and may simply lack genre metadata.
    if include_filters:
        include_genres_all: set = set()
        for gf in include_filters:
            include_genres_all.add(gf.genre)
        raw = [
            item for item in raw
            if not (item.get("Genres") or [])
            or any(g in include_genres_all for g in item["Genres"])
        ]

    # Apply exclude genre filter
    if exclude_genres:
        raw = [
            item for item in raw
            if not any(g in exclude_genres for g in (item.get("Genres") or []))
        ]

    logger.info(
        f"_get_collection_pool: channel_id={channel_id} → "
        f"{len(raw)} items after genre filtering"
    )
    return raw


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
                "Fields": "RunTimeTicks,Genres,SeriesName,ParentIndexNumber,IndexNumber,Path,MediaSources",
                "Limit": page_size,
                "StartIndex": start_index,
                "SortBy": "SortName",
                "SortOrder": "Ascending",
            }
            if genres_param:
                params["Genres"] = genres_param

            # Use the admin /Items endpoint (API-key level access) so that
            # the Path field is returned regardless of user permission level.
            params["UserId"] = user_id
            url = f"{client.base_url}/Items"
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

    # ── Load genre filters ────────────────────────────────────────────────────
    gf_result = await db.execute(
        select(GenreFilter).where(GenreFilter.channel_id == channel_id)
    )
    genre_filters = gf_result.scalars().all()

    # ── Separate include vs exclude genre filters ─────────────────────────────
    include_filters = [gf for gf in genre_filters if gf.filter_type != "exclude"]
    exclude_genres = {gf.genre for gf in genre_filters if gf.filter_type == "exclude"}

    if exclude_genres:
        logger.info(
            f"generate_channel_schedule: channel {channel_id} — "
            f"will exclude genres: {sorted(exclude_genres)}"
        )

    # ── Build item pool ───────────────────────────────────────────────────────
    client = _get_client()
    item_pool: List[dict] = []
    seen_ids: set = set()

    for lib in (libraries or []):
        if include_filters:
            # Group include filters by content_type to minimise API calls
            by_type: dict = {}
            for gf in include_filters:
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
            # No include filters — fetch everything (movies + episodes)
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

    # ── Merge items from collection sources ───────────────────────────────────
    try:
        collection_items = await _get_collection_pool(
            channel_id, include_filters, exclude_genres, db, client
        )
        for ci in collection_items:
            ci_id = ci.get("Id")
            if ci_id and ci_id not in seen_ids:
                seen_ids.add(ci_id)
                item_pool.append(ci)
    except Exception as exc:
        logger.error(
            f"generate_channel_schedule: collection pool failed for "
            f"channel {channel_id}: {exc}",
            exc_info=True,
        )

    # ── Apply exclude genre filter (library items only — collection pool is
    #    already filtered, but exclude again to be safe) ─────────────────────
    if exclude_genres and item_pool:
        before = len(item_pool)
        item_pool = [
            item for item in item_pool
            if not any(g in exclude_genres for g in (item.get("Genres") or []))
        ]
        removed = before - len(item_pool)
        if removed:
            logger.info(
                f"generate_channel_schedule: channel {channel_id} — "
                f"removed {removed} items matching excluded genres"
            )

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

        if "_nfo" in item:
            # Collection item — metadata is pre-filled, skip sidecar I/O
            nfo = item["_nfo"]
            thumb = item.get("_thumbnail")
            local_path = _apply_path_map(item.get("Path"))
        else:
            local_path = _apply_path_map(_extract_path(item))
            nfo = _parse_nfo(local_path) if local_path else {}
            thumb = _find_thumbnail(local_path) if local_path else None

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
            file_path=local_path,
            description=nfo.get("description"),
            content_rating=nfo.get("content_rating"),
            air_date=nfo.get("air_date"),
            thumbnail_path=thumb,
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
