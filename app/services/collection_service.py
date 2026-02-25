"""
Collection service — NFO parsing, thumbnail resolution, and file verification
for the Collections feature.

NFO / thumbnail conventions handled:
  Movie:   movie.nfo (or {basename}.nfo fallback) + folder.jpg / {basename}.jpg
  Series:  tvshow.nfo in series root dir + folder.jpg / poster.jpg
  Season:  tvshow.nfo in series root (parent of season dir) + season{NN}-poster.jpg
  Episode: {basename}.nfo + {basename}-thumb.jpg / {basename}.jpg / folder.jpg
"""

import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# ─── Path utilities ────────────────────────────────────────────────────────────

def _apply_path_map(path: Optional[str]) -> Optional[str]:
    """
    Rewrite a Jellyfin server path to a locally accessible path using MEDIA_PATH_MAP.
    Format: "/jellyfin/prefix:/local/prefix"  (single colon separator)
    """
    if not path:
        return None
    path_map = getattr(settings, "MEDIA_PATH_MAP", "") or ""
    if not path_map or ":" not in path_map:
        return path
    jf_prefix, local_prefix = path_map.split(":", 1)
    if path.startswith(jf_prefix):
        remapped = local_prefix + path[len(jf_prefix):]
        logger.debug(f"_apply_path_map: {path!r} → {remapped!r}")
        return remapped
    return path


def _extract_path(item: Dict[str, Any]) -> Optional[str]:
    """Extract local file / directory path from a Jellyfin item dict."""
    path = item.get("Path")
    if not path:
        sources = item.get("MediaSources") or []
        path = sources[0].get("Path") if sources else None
    return _apply_path_map(path) if path else None


# ─── NFO parsing ───────────────────────────────────────────────────────────────

def _parse_nfo(nfo_path: str) -> Dict[str, Any]:
    """Parse a Kodi/Jellyfin NFO XML file and return a metadata dict."""
    if not os.path.isfile(nfo_path):
        return {}
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        def _text(tag: str) -> Optional[str]:
            el = root.find(tag)
            if el is None:
                return None
            return (el.text or "").strip() or None

        # Collect genre tags
        genres = [el.text.strip() for el in root.findall("genre") if el.text and el.text.strip()]

        result: Dict[str, Any] = {}
        if plot := _text("plot"):
            result["description"] = plot
        if mpaa := _text("mpaa"):
            result["content_rating"] = mpaa
        result["air_date"] = _text("aired") or _text("premiered") or _text("year")
        if genres:
            import json
            result["genres"] = json.dumps(genres)
        return result
    except ET.ParseError as exc:
        logger.warning(f"_parse_nfo: failed to parse {nfo_path!r}: {exc}")
        return {}


def _parse_nfo_for_item(file_path: str, item_type: str) -> Dict[str, Any]:
    """
    Locate and parse the correct NFO file based on item_type and file_path.

    - Movie:   movie.nfo in same dir, fallback to {basename}.nfo
    - Series:  tvshow.nfo in file_path (which is the series root directory)
    - Season:  tvshow.nfo in parent of file_path (season dir → series root)
    - Episode: {basename}.nfo next to video file
    """
    if not file_path:
        return {}

    if item_type == "Movie":
        same_dir = os.path.dirname(file_path)
        for candidate in (
            os.path.join(same_dir, "movie.nfo"),
            os.path.splitext(file_path)[0] + ".nfo",
        ):
            result = _parse_nfo(candidate)
            if result:
                logger.debug(f"_parse_nfo_for_item Movie: used {candidate!r}")
                return result
        return {}

    elif item_type == "Series":
        # file_path is the series root directory itself
        series_dir = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
        nfo = os.path.join(series_dir, "tvshow.nfo")
        result = _parse_nfo(nfo)
        if result:
            logger.debug(f"_parse_nfo_for_item Series: used {nfo!r}")
        return result

    elif item_type == "Season":
        # file_path is the season directory; tvshow.nfo lives one level up
        season_dir = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
        series_dir = os.path.dirname(season_dir)
        nfo = os.path.join(series_dir, "tvshow.nfo")
        result = _parse_nfo(nfo)
        if result:
            logger.debug(f"_parse_nfo_for_item Season: used {nfo!r}")
        return result

    elif item_type == "Episode":
        nfo = os.path.splitext(file_path)[0] + ".nfo"
        result = _parse_nfo(nfo)
        if result:
            logger.debug(f"_parse_nfo_for_item Episode: used {nfo!r}")
        return result

    return {}


# ─── Thumbnail resolution ──────────────────────────────────────────────────────

def _find_thumbnail_for_item(
    file_path: str,
    item_type: str,
    season_number: Optional[int] = None,
) -> Optional[str]:
    """
    Find the best local thumbnail image for a collection item.

    - Movie:   folder.jpg | {basename}.jpg | {basename}-thumb.jpg  (same dir)
    - Series:  folder.jpg | poster.jpg  (series root dir)
    - Season:  season{NN:02d}-poster.jpg in series root, fallback folder.jpg
    - Episode: {basename}-thumb.jpg | {basename}.jpg | folder.jpg  (same dir)
    """
    if not file_path:
        return None

    if item_type == "Movie":
        same_dir = os.path.dirname(file_path)
        base = os.path.splitext(file_path)[0]
        candidates = [
            os.path.join(same_dir, "folder.jpg"),
            base + ".jpg",
            base + "-thumb.jpg",
        ]

    elif item_type == "Series":
        series_dir = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
        candidates = [
            os.path.join(series_dir, "folder.jpg"),
            os.path.join(series_dir, "poster.jpg"),
        ]

    elif item_type == "Season":
        season_dir = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
        series_dir = os.path.dirname(season_dir)
        candidates = []
        if season_number is not None:
            candidates.append(os.path.join(series_dir, f"season{season_number:02d}-poster.jpg"))
        candidates += [
            os.path.join(season_dir, "folder.jpg"),
            os.path.join(series_dir, "folder.jpg"),
        ]

    elif item_type == "Episode":
        same_dir = os.path.dirname(file_path)
        base = os.path.splitext(file_path)[0]
        candidates = [
            base + "-thumb.jpg",
            base + ".jpg",
            os.path.join(same_dir, "folder.jpg"),
        ]

    else:
        return None

    for candidate in candidates:
        if os.path.isfile(candidate):
            logger.debug(f"_find_thumbnail_for_item {item_type}: found {candidate!r}")
            return candidate

    return None


# ─── Item enrichment ──────────────────────────────────────────────────────────

def enrich_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a dict with at minimum {media_item_id, item_type, title, file_path, library_id},
    parse NFO sidecars and locate the best thumbnail image.

    Returns the input dict enriched with: description, content_rating, air_date,
    genres (if not already set), thumbnail_path.
    """
    file_path = item.get("file_path")
    item_type = item.get("item_type", "Movie")
    season_number = item.get("season_number")

    logger.debug(f"enrich_item: type={item_type}, file_path={file_path!r}")

    nfo_data = _parse_nfo_for_item(file_path or "", item_type)
    thumbnail = _find_thumbnail_for_item(file_path or "", item_type, season_number)

    enriched = dict(item)
    # Only set from NFO if not already provided by caller
    for key in ("description", "content_rating", "air_date", "genres"):
        if not enriched.get(key) and nfo_data.get(key):
            enriched[key] = nfo_data[key]
    if thumbnail:
        enriched["thumbnail_path"] = thumbnail

    return enriched


# ─── Collection verification ───────────────────────────────────────────────────

async def verify_collection(items: list, client: Any) -> List[Dict[str, Any]]:
    """
    Check each CollectionItem's file_path:
      - "ok"       — file exists on local filesystem
      - "moved"    — file missing locally but Jellyfin knows a new path
      - "deleted"  — file missing and Jellyfin no longer has the item
      - "no_path"  — item has no file_path stored

    Args:
        items:  List of CollectionItem ORM objects
        client: JellyfinClient instance

    Returns:
        List of dicts: {item_id, title, item_type, status, new_path?}
    """
    results = []
    for item in items:
        if not item.file_path:
            results.append({
                "item_id": item.id,
                "title": item.title,
                "item_type": item.item_type,
                "status": "no_path",
            })
            continue

        if os.path.exists(item.file_path):
            results.append({
                "item_id": item.id,
                "title": item.title,
                "item_type": item.item_type,
                "status": "ok",
            })
            continue

        # File is missing — query Jellyfin for updated path
        logger.debug(
            f"verify_collection: {item.title!r} missing at {item.file_path!r}, "
            f"querying Jellyfin for item {item.media_item_id}"
        )
        try:
            jf_item = await client.get_item_info(item.media_item_id)
            new_path = _extract_path(jf_item)
            if new_path and os.path.exists(new_path):
                logger.info(
                    f"verify_collection: {item.title!r} moved → {new_path!r}"
                )
                results.append({
                    "item_id": item.id,
                    "title": item.title,
                    "item_type": item.item_type,
                    "status": "moved",
                    "new_path": new_path,
                })
            else:
                logger.info(
                    f"verify_collection: {item.title!r} not found in Jellyfin or path still missing"
                )
                results.append({
                    "item_id": item.id,
                    "title": item.title,
                    "item_type": item.item_type,
                    "status": "deleted",
                })
        except Exception as exc:
            # Jellyfin 404 or network error → treat as deleted
            logger.warning(
                f"verify_collection: Jellyfin lookup for {item.media_item_id!r} failed: {exc}"
            )
            results.append({
                "item_id": item.id,
                "title": item.title,
                "item_type": item.item_type,
                "status": "deleted",
            })

    return results
