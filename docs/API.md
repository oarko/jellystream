# JellyStream API Documentation

## Base URL

```
http://<host>:8000
```

Set `JELLYSTREAM_PUBLIC_URL` in `.env` to the network-accessible address
(e.g. `http://192.168.1.100:8000`). All M3U stream URLs and XMLTV thumbnail
URLs use this value so Jellyfin can reach JellyStream from a different machine.

## Notes

- All `POST` / `PUT` endpoints accept **JSON body** (`Content-Type: application/json`).
- Legacy routes at `/api/streams/` and `/api/schedules/` (v1) are kept for backward
  compatibility but should not be used in new integrations.
- Interactive Swagger UI: `GET /docs`

---

## Application

### Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "public_url": "http://192.168.1.100:8000"
}
```

`public_url` is `null` when `JELLYSTREAM_PUBLIC_URL` is not configured.

---

## Channels  `/api/channels/`

Channels are virtual TV channels. Each channel has one or more Jellyfin libraries
and/or JellyStream Collections as content sources, plus optional genre filters that
drive automatic schedule generation.

### List channels

**GET** `/api/channels/`

```json
[
  {
    "id": 1,
    "name": "Action Movies",
    "description": "Non-stop action",
    "channel_number": "100.1",
    "enabled": true,
    "channel_type": "video",
    "schedule_type": "genre_auto",
    "schedule_generated_through": "2026-03-01T02:00:00",
    "transcode_max_height": 1080,
    "transcode_preset": "veryfast",
    "hwaccel": "none",
    "hwaccel_device": null,
    "bug_image_path": null,
    "bug_enabled": false,
    "bug_position": "bottom-right",
    "bug_interval_seconds": 0,
    "bug_duration_seconds": 10,
    "bug_scale_percent": 12,
    "bug_max_height_percent": 30,
    "bug_opacity_percent": 100,
    "logo_image_path": null,
    "logo_use_bug_image": false,
    "created_at": "2026-02-01T00:00:00",
    "updated_at": "2026-02-01T00:00:00"
  }
]
```

`transcode_*`/`hwaccel*` control the ffmpeg encode for this channel (see "Live TV" below).
`bug_*` control the on-screen graphic overlay; `bug_image_path` is set by uploading an image
(see "Channel on-screen graphic" below), not by `POST`/`PUT /api/channels/`.
`logo_*` control the channel logo shown in the Jellyfin/IPTV guide (M3U `tvg-logo`, XMLTV
`<icon>`) — see "Channel logo" below. When `logo_use_bug_image` is `true`, the on-screen
graphic image is used as the logo too and `logo_image_path` is ignored (but not deleted).

### Get channel

**GET** `/api/channels/{id}`

Returns channel with its libraries, collection sources, and genre filters.

```json
{
  "id": 1,
  "name": "Action Movies",
  "channel_number": "100.1",
  "enabled": true,
  "channel_type": "video",
  "schedule_type": "genre_auto",
  "libraries": [
    { "library_id": "abc123", "library_name": "Movies", "collection_type": "movies" }
  ],
  "collection_sources": [
    { "collection_id": 2, "collection_name": "Sci-Fi Favourites" }
  ],
  "genre_filters": [
    { "genre": "Action", "content_type": "both", "filter_type": "include" }
  ]
}
```

### Create channel

**POST** `/api/channels/`

```json
{
  "name": "Curated Sci-Fi",
  "channel_number": "101",
  "channel_type": "video",
  "schedule_type": "genre_auto",
  "libraries": [],
  "collection_sources": [
    { "collection_id": 2, "collection_name": "Sci-Fi Favourites" }
  ],
  "genre_filters": [
    { "genre": "Science Fiction", "content_type": "both", "filter_type": "include" }
  ]
}
```

`libraries` and `collection_sources` are both optional (default `[]`). At least one
of the two must be provided.

`channel_type`: `"video"` (default). `"music"` is reserved for a future release.
`schedule_type`: `"genre_auto"` (default) or `"manual"`.
`content_type` in genre filters: `"movie"`, `"episode"`, or `"both"`.
`filter_type` in genre filters: `"include"` fetches matching content; `"exclude"` removes matching items from the pool after fetching.

Transcode and on-screen-graphic settings may also be set at creation (all optional, shown with
their defaults):

```json
{
  "transcode_max_height": 1080,
  "transcode_preset": "veryfast",
  "hwaccel": "none",
  "hwaccel_device": null,
  "bug_enabled": false,
  "bug_position": "bottom-right",
  "bug_interval_seconds": 0,
  "bug_duration_seconds": 10,
  "bug_scale_percent": 12,
  "bug_max_height_percent": 30,
  "bug_opacity_percent": 100,
  "logo_use_bug_image": false
}
```

`transcode_max_height`: `0` or `null` = no downscale. `transcode_preset`: one of `ultrafast`,
`superfast`, `veryfast`, `faster`, `fast`, `medium` (ignored by the `vaapi` hwaccel path).
`hwaccel`: `"none"` | `"vaapi"` | `"qsv"` | `"nvenc"`. `bug_position`: `"top-left"` |
`"top-right"` | `"bottom-left"` | `"bottom-right"` | `"center"`. `bug_interval_seconds`: `0`
means always visible; otherwise the graphic appears for `bug_duration_seconds` every
`bug_interval_seconds`. `bug_scale_percent` caps the graphic's *width* as a % of the video's
width; `bug_max_height_percent` independently caps its *height* as a % of the video's height —
whichever bound is more restrictive wins, aspect ratio is always preserved. `bug_opacity_percent`
(1-100, 100 = fully opaque) blends the graphic into the video; below 100 it's multiplied into
the image's own alpha channel (if any), so a PNG with partial transparency gets proportionally
more transparent rather than having its alpha overridden. The image itself is uploaded
separately — see "Channel on-screen graphic" below. `logo_use_bug_image`: when `true`, this
same image is also used as the channel logo (see "Channel logo" below) instead of a separate
upload.

Genre filters apply equally to library items and collection items. Collection items with
no stored genre metadata pass through include filters (they were manually curated).

On creation, a 7-day schedule is automatically generated if `schedule_type` is `"genre_auto"`.

### Update channel

**PUT** `/api/channels/{id}`

All fields optional. Supplying `libraries` or `genre_filters` replaces the
existing lists entirely.

```json
{
  "name": "Updated Name",
  "enabled": false,
  "libraries": [...],
  "genre_filters": [...]
}
```

### Delete channel

**DELETE** `/api/channels/{id}`

Cascades to all `channel_libraries`, `genre_filters`, and `schedule_entries`.

### Generate schedule

**POST** `/api/channels/{id}/generate-schedule?days=7&reset=true`

| Query param | Default | Description |
|---|---|---|
| `days` | `7` | Number of days to generate |
| `reset` | `false` | If `true`, delete all existing entries first and start from now |

```json
{ "message": "Schedule generated: 142 entries created", "count": 142 }
```

### Register with Jellyfin Live TV

**POST** `/api/channels/{id}/register-livetv`

Registers JellyStream's global M3U and XMLTV endpoints as a TunerHost and
ListingProvider in Jellyfin. Any existing registrations on this channel are
cleaned up first to prevent duplicates.

**Request body:** (only `public_url` is required; the rest default as shown)
```json
{
  "public_url": "http://192.168.1.100:8000",
  "tuner_count": 1,
  "allow_hw_transcoding": false,
  "allow_fmp4_transcoding": false,
  "allow_stream_sharing": true,
  "enable_stream_looping": true,
  "fallback_max_bitrate": 0,
  "ignore_dts": false,
  "read_at_native_framerate": false
}
```

`public_url` must be a network-accessible address that Jellyfin can reach.
Using `localhost` will cause Jellyfin's registration to fail.
`tuner_count`: max simultaneous streams Jellyfin will open against this tuner (`0` = unlimited —
JellyStream's shared per-channel pipeline means multiple Jellyfin clients don't each start a
new ffmpeg process anyway). `fallback_max_bitrate`: `0` = no limit.

**Response:**
```json
{
  "message": "Registered with Jellyfin Live TV",
  "tuner_host_id": "abc123",
  "listing_provider_id": "xyz789"
}
```

### Unregister from Jellyfin Live TV

**DELETE** `/api/channels/{id}/register-livetv`

Removes the TunerHost and ListingProvider registrations from Jellyfin.

### Channel on-screen graphic

Upload, preview, or remove the image used for this channel's "bug" overlay (see `bug_*`
fields above for position/timing/size). Uploading sets `bug_image_path`; whether it's actually
shown on stream is still gated by `bug_enabled`.

**POST** `/api/channels/{id}/bug-image`

Multipart form upload, field name `file`. Accepts `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`,
`.bmp`, max 5MB. Rejected with `400` unless `ffprobe` confirms the file decodes as a real image
(non-zero width/height) — a corrupt upload can never silently break playback later.

```json
{ "message": "Image uploaded", "bug_image_path": "./data/logos/channel_1_bug.png" }
```

**GET** `/api/channels/{id}/bug-image`

Serves the uploaded image directly (for use in an `<img>` tag). `404` if none is uploaded.

**DELETE** `/api/channels/{id}/bug-image`

Removes the file from disk and clears `bug_image_path`.

```json
{ "message": "Image removed" }
```

### Channel logo

Upload, preview, or remove the channel's logo — shown in the Jellyfin/IPTV guide (M3U
`tvg-logo`, XMLTV `<icon>`), not on the video itself. Independent of the on-screen graphic
above by default, but `logo_use_bug_image=true` (set via `PUT /api/channels/{id}`) makes the
bug image double as the logo instead of requiring a second upload.

**GET** `/api/channels/{id}/logo-image`

Serves the channel's *effective* logo image — resolved server-side: the bug image if
`logo_use_bug_image` is `true`, otherwise the dedicated upload. This is the same URL used in
the M3U/XMLTV output, so it always reflects whichever source is actually active. `404` if
neither is set (or the effective file is missing from disk).

**POST** `/api/channels/{id}/logo-image`

Multipart form upload, field name `file`. Same validation as the bug-image upload (type/size/
real-image checks). Uploading here always saves to `logo_image_path`, even while
`logo_use_bug_image` is `true` — it just won't be served (by the GET above, or in the guide)
until the flag is turned off.

```json
{ "message": "Image uploaded", "logo_image_path": "./data/logos/channel_1_logo.png" }
```

**DELETE** `/api/channels/{id}/logo-image`

Removes the dedicated logo file and clears `logo_image_path`. Never touches the bug image,
even if `logo_use_bug_image` is currently `true`.

```json
{ "message": "Image removed" }
```

---

## Schedules  `/api/schedules/`

### Get channel schedule

**GET** `/api/schedules/channel/{channel_id}?start=ISO&end=ISO`

Returns schedule entries in a time window. Defaults to 3 hours back → 7 days forward.

```json
[
  {
    "id": 1001,
    "channel_id": 1,
    "title": "The Matrix",
    "series_name": null,
    "season_number": null,
    "episode_number": null,
    "media_item_id": "abc123",
    "item_type": "Movie",
    "genres": "[\"Action\", \"Science Fiction\"]",
    "start_time": "2026-02-22T19:00:00",
    "end_time": "2026-02-22T21:16:00",
    "duration": 8160,
    "description": "A computer hacker learns...",
    "content_rating": "R",
    "air_date": "1999-03-31",
    "thumbnail_path": "/mnt/media/Movies/The Matrix/The Matrix.jpg"
  }
]
```

### What's playing now

**GET** `/api/schedules/channel/{channel_id}/now`

Returns the single entry currently airing, or `null`.

### Create manual entry

**POST** `/api/schedules/`

```json
{
  "channel_id": 1,
  "title": "Special Event",
  "media_item_id": "abc123",
  "library_id": "lib456",
  "item_type": "Movie",
  "start_time": "2026-03-01T20:00:00",
  "duration": 7200
}
```

### Delete entry

**DELETE** `/api/schedules/{id}`

---

## Jellyfin Integration  `/api/jellyfin/`

### Get current user

**GET** `/api/jellyfin/users`

```json
{ "user": { "Id": "user123", "Name": "Admin", "ServerId": "server456" } }
```

### Get libraries

**GET** `/api/jellyfin/libraries`

```json
{
  "libraries": [
    { "Id": "abc123", "Name": "Movies", "CollectionType": "movies" },
    { "Id": "def456", "Name": "Anime", "CollectionType": "tvshows" }
  ]
}
```

### Get library items

**GET** `/api/jellyfin/items/{parent_id}`

| Query param | Default | Description |
|---|---|---|
| `recursive` | `false` | Recurse into subfolders |
| `limit` | `50` | Items per page |
| `start_index` | `0` | Pagination offset |
| `sort_by` | `SortName` | Sort field |
| `sort_order` | `Ascending` | `Ascending` or `Descending` |
| `include_item_types` | — | Comma-separated types (e.g. `Series,Episode`) |

**Hierarchical navigation for TV shows:**
1. Library → Series (`recursive=false`)
2. Series → Seasons (Series ID as parent)
3. Season → Episodes (Season ID as parent)

### Get genres for a library

**GET** `/api/jellyfin/genres/{library_id}`

Returns all genre names present in the given library. Used by the channel editor to populate the genre filter dropdown.

```json
{
  "genres": ["Action", "Animation", "Comedy", "Crime", "Drama", "Horror", "Science Fiction", "Thriller"]
}
```

---

## Collections  `/api/collections/`

JellyStream Collections are curated lists of media items. They can be used as content
sources for channels (alongside or instead of Jellyfin libraries) and can be imported
from Jellyfin boxsets.

### List collections

**GET** `/api/collections/`

```json
[
  { "id": 1, "name": "Sci-Fi Favourites", "item_count": 24, "jellyfin_id": null,
    "created_at": "2026-02-24T10:00:00", "updated_at": "2026-02-24T10:00:00" }
]
```

### Get collection with items

**GET** `/api/collections/{id}`

Returns the collection metadata plus all items.

### Create collection

**POST** `/api/collections/`

```json
{
  "name": "Sci-Fi Favourites",
  "description": "Optional description",
  "items": [
    {
      "media_item_id": "abc123",
      "item_type": "Movie",
      "title": "Alien",
      "library_id": "lib456",
      "file_path": "/media/Movies/Alien/Alien.mkv",
      "duration": 7080,
      "genres": "[\"Science Fiction\",\"Horror\"]",
      "sort_order": 0
    }
  ]
}
```

Each item is enriched with NFO sidecar metadata (`description`, `content_rating`,
`air_date`) and a local thumbnail path at save time.

### Update collection

**PUT** `/api/collections/{id}`

All fields optional. If `items` is provided, all existing items are replaced.

### Delete collection

**DELETE** `/api/collections/{id}`

Cascades to all `CollectionItem` rows.

### Remove single item

**DELETE** `/api/collections/{id}/items/{item_id}`

### Verify collection files

**GET** `/api/collections/{id}/verify`

Checks every item's `file_path` on the local filesystem.

```json
{
  "collection_id": 1,
  "summary": { "ok": 22, "moved": 1, "deleted": 1, "no_path": 0 },
  "items": [
    { "item_id": 5, "title": "Alien", "item_type": "Movie", "status": "ok" },
    { "item_id": 6, "title": "Aliens", "item_type": "Movie", "status": "moved",
      "new_path": "/mnt/nas/Movies/Aliens/Aliens.mkv" },
    { "item_id": 7, "title": "Alien³", "item_type": "Movie", "status": "deleted" }
  ]
}
```

Status values: `ok`, `moved` (file missing locally but Jellyfin has a new path),
`deleted` (not found anywhere), `no_path` (no path stored).

### Import Jellyfin boxset

**POST** `/api/collections/import/{boxset_id}`

Fetches all items from a Jellyfin boxset, enriches them, and creates a new Collection.
Returns `409` if the boxset has already been imported.

```json
{ "id": 3, "message": "Imported 'Alien Collection' with 6 items" }
```

### Collection item thumbnail

**GET** `/api/collections/thumbnail/{item_id}`

Serves the local `.jpg` sidecar for a `CollectionItem`. Returns 404 if unavailable.

---

## Jellyfin Browse  `/api/jellyfin/`

Additional endpoints for the collection editor UI.

### List boxsets

**GET** `/api/jellyfin/boxsets`

Returns all Jellyfin boxset collections.

```json
[
  { "Id": "box123", "Name": "Alien Collection", "ImageTag": "img456" }
]
```

### Browse items

**GET** `/api/jellyfin/browse`

| Query param | Default | Description |
|---|---|---|
| `library_id` | — | Parent library ID |
| `type` | `Movie` | `Movie` or `Series` |
| `search` | — | Title search term |
| `year_from` | — | Minimum production year |
| `year_to` | — | Maximum production year |
| `limit` | `24` | Items per page |
| `offset` | `0` | Pagination offset |

Returns items with `Path` and `RunTimeTicks` (uses admin endpoint).

### Series seasons

**GET** `/api/jellyfin/series/{series_id}/seasons`

### Season episodes

**GET** `/api/jellyfin/seasons/{season_id}/episodes`

### Item image proxy

**GET** `/api/jellyfin/items/{item_id}/image`

| Query param | Default | Description |
|---|---|---|
| `type` | `Primary` | Image type |
| `maxWidth` | `400` | Max image width |

Proxies the image bytes from Jellyfin, hiding the API key from the browser.

---

## Live TV  `/api/livetv/`

> **Route ordering:** `/m3u/all` and `/xmltv/all` are registered *before*
> `/{channel_id}` variants to prevent FastAPI matching `"all"` as an integer.

### M3U playlist — all channels

**GET** `/api/livetv/m3u/all`

```m3u
#EXTM3U
#EXTINF:-1 tvg-id="1" tvg-name="Action Movies" tvg-chno="100.1" tvg-logo="http://192.168.1.100:8000/api/channels/1/logo-image" group-title="JellyStream",100.1 Action Movies
http://192.168.1.100:8000/api/livetv/stream/1
```

Uses `tvg-chno` (not `channel-number`) which Jellyfin reads for channel numbering. `tvg-logo`
is only present when the channel has an effective logo set (dedicated upload, or
`logo_use_bug_image`) — see "Channel logo" above.

### M3U playlist — single channel

**GET** `/api/livetv/m3u/{channel_id}`

### XMLTV EPG — all channels

**GET** `/api/livetv/xmltv/all`

EPG window: 3 hours back → 7 days forward. Enriched with sidecar metadata when available.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="JellyStream">
  <channel id="1">
    <display-name>Action Movies</display-name>
    <icon src="http://192.168.1.100:8000/api/channels/1/logo-image"/>
  </channel>
  <programme channel="1" start="20260222190000 +0000" stop="20260222211600 +0000">
    <title>The Matrix</title>
    <desc lang="en">A computer hacker learns from mysterious rebels...</desc>
    <icon src="http://192.168.1.100:8000/api/livetv/thumbnail/1001"/>
    <date>19990331</date>
    <category>Movie</category>
    <category>Action</category>
    <rating system="MPAA"><value>R</value></rating>
  </programme>
</tv>
```

Response includes `Cache-Control: no-cache` headers so Jellyfin always fetches fresh data.

### XMLTV EPG — single channel

**GET** `/api/livetv/xmltv/{channel_id}`

### Thumbnail

**GET** `/api/livetv/thumbnail/{entry_id}`

Serves the `.jpg` sidecar image for a schedule entry (read from `thumbnail_path`).
Returns 404 if no thumbnail is available or the file is not on disk.

### Stream (HEAD probe)

**HEAD** `/api/livetv/stream/{channel_id}`

Returns `200` with `Content-Type: video/mp2t` without starting ffmpeg.
Jellyfin probes streams this way before opening them.

### Stream (GET)

**GET** `/api/livetv/stream/{channel_id}`

Attaches the caller to this channel's shared live MPEG-TS stream, joining mid-programme at the
correct time offset — just like real broadcast TV. **One ffmpeg pipeline is shared per
channel**, not one per request: the first viewer starts it, every later viewer (another device,
Jellyfin re-probing, a browser tab) attaches to the same running stream instead of spawning a
second ffmpeg. The pipeline keeps running for a grace period after the last viewer disconnects,
so a brief reconnect doesn't restart anything. See `app/services/stream_proxy.py` /
`CLAUDE.md` for the full gapless-boundary and hwaccel-fallback design.

At a high level, per schedule entry:
1. The first entry is picked by wall clock (`start_time ≤ now < end_time`, joining mid-show at
   the right offset); later entries always follow playback order, never the clock again
   (schedule lengths come from stored metadata and can drift from real file duration)
2. Prefers direct file access (`file_path`) for near-instant seek; falls back to Jellyfin HTTP stream
3. Probes audio tracks with `ffprobe` and selects the track matching `PREFERRED_AUDIO_LANGUAGE` (falls back to first audio track)
4. Encodes to H.264/AAC MPEG-TS, scaled to the channel's `transcode_max_height` (or passed
   through at full resolution if unset). If the channel has `hwaccel` set, tries software-decode
   + hardware-encode first (hardware decode is deliberately never used — see CLAUDE.md), falling
   back to full software (`libx264`) on failure
5. If `bug_enabled` and a valid `bug_image_path` are set, overlays the on-screen graphic via an
   ffmpeg `filter_complex` instead of the plain filter chain, sized to fit within both
   `bug_scale_percent` (width) and `bug_max_height_percent` (height) — whichever is more
   restrictive wins, aspect ratio preserved — and blended at `bug_opacity_percent`
6. Every segment after the first gets a continuous `-output_ts_offset` so MPEG-TS timestamps
   never reset at channel-item boundaries (a reset breaks Jellyfin Live TV and most ffmpeg-based
   players)

**Response headers:**
- `X-Channel-Id` — channel ID
- `X-Entry-Title` — ASCII-sanitised title (non-ASCII replaced with `?` — Starlette headers are latin-1)
- `X-Offset-Seconds` — seek offset applied to the first segment this viewer joined on

**Errors:**
- `404` — nothing scheduled right now
- `503` — ffmpeg not installed

---

## Sidecar Metadata

JellyStream reads Kodi/Jellyfin standard sidecar files placed next to each video:

| File | Content |
|---|---|
| `<basename>.nfo` | Kodi XML with `<plot>`, `<mpaa>`, `<aired>` |
| `<basename>.jpg` | Preview thumbnail |
| `<basename>-thumb.jpg` | Alternative thumbnail name |

These are read at **schedule generation time** and stored in `schedule_entries`.
The data appears in the XMLTV guide (`<desc>`, `<icon>`, `<date>`, `<rating>`).

No path mapping is needed when JellyStream and Jellyfin share the same mount point
(e.g. both access media at `/mnt/media`). Use `MEDIA_PATH_MAP` in `.env` when the
paths differ between machines:

```env
# Format: /jellyfin/prefix:/local/prefix
MEDIA_PATH_MAP=/media:/mnt/nas/media
```

---

## Jellyfin Live TV Setup

JellyStream registers one global tuner and one EPG provider covering all channels.
New channels appear automatically in Jellyfin without re-registration.

### Via UI

1. Open a channel in the JellyStream web interface
2. Fill in **Public URL** (the network IP:port Jellyfin can reach)
3. Click **Register with Jellyfin Live TV**

### Via API (manual)

```bash
# Register tuner
POST /api/channels/{id}/register-livetv
{ "public_url": "http://192.168.1.100:8000" }
```

After registration, Jellyfin Live TV:
- M3U source: `http://192.168.1.100:8000/api/livetv/m3u/all`
- EPG source: `http://192.168.1.100:8000/api/livetv/xmltv/all`

### Force EPG refresh in Jellyfin

The **Refresh Guide Data** button on the guide page processes cached data.
To force an immediate re-download:

**Option A:** Dashboard → Live TV → Guide Providers → edit provider → Save
**Option B:** Dashboard → Scheduled Tasks → **Refresh Guide** → Run ▶

---

## System / Updates  `/api/system/`

All endpoints here are read-only except the channel-preference write. Applying an update is
always done via `./update.sh`, run by the admin — not through the API — because the systemd
service account's own code tree is intentionally read-only (see `deploy/README.md`).

### Version info

**GET** `/api/system/version`

```json
{
  "git_available": true,
  "branch": "main",
  "commit": "3f14483d0a4ac7a789b307b793c98291719e7ae",
  "commit_short": "3f14483",
  "commit_date": "2026-09-18T17:36:09-04:00",
  "dirty": false,
  "channel": "main"
}
```

`dirty: true` means the working tree has uncommitted changes — `./update.sh` will refuse to
run until they're committed, stashed, or discarded. `git_available: false` (with the other
fields `null`) means this isn't a git checkout.

### Check for updates

**GET** `/api/system/update-check?channel=main`

Compares local `HEAD` against the tip of the given branch on GitHub, via GitHub's public REST
API — no local `git fetch` is performed. Omit `channel` to use the saved preference.

```json
{
  "channel": "main",
  "local_commit": "3f14483d0a4ac7a789b307b793c98291719e7ae",
  "local_commit_short": "3f14483",
  "latest_commit": "08dedf8302e58c637c64c8823f5327f1968a918",
  "latest_commit_short": "08dedf8",
  "latest_commit_date": "2026-09-18T20:18:03Z",
  "latest_commit_message": "Merge pull request #5 from oarko/nightly",
  "update_available": true
}
```

`400` if `channel` isn't `main` or `nightly`. `503` if GitHub is unreachable or this isn't a
git checkout.

### Set update channel

**PUT** `/api/system/update-channel`

```json
{ "channel": "nightly" }
```

Persists the choice to `.env` (`UPDATE_CHANNEL`) via a targeted single-line edit — never a
full-file rewrite — and takes effect immediately for subsequent `GET` calls in this process
(no restart needed). `./update.sh`, run without an explicit branch argument, reads the same
value.

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `JELLYFIN_URL` | — | Jellyfin server URL |
| `JELLYFIN_API_KEY` | — | Jellyfin API key (admin recommended) |
| `JELLYFIN_USER_ID` | auto | Optional; auto-detected from first user |
| `JELLYSTREAM_PUBLIC_URL` | — | Network IP/hostname used in M3U stream URLs and XMLTV icons so Jellyfin can reach JellyStream. Must NOT be `localhost`. Example: `http://192.168.1.100:8000` |
| `MEDIA_PATH_MAP` | — | Path prefix rewrite (`/jf/prefix:/local/prefix`). Only needed when JellyStream and Jellyfin mount media at different paths. |
| `HOST` | `0.0.0.0` | Bind address. **Keep as `0.0.0.0`** — binds to all interfaces so both the PHP web UI (via localhost) and Jellyfin (via network IP) can reach the API. Setting a specific IP breaks PHP→API calls. |
| `PORT` | `8000` | Listen port |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `PREFERRED_AUDIO_LANGUAGE` | `eng` | ISO 639-2 code for preferred audio track (`eng`, `jpn`, `fre`, …) |
| `SCHEDULER_ENABLED` | `true` | Enable APScheduler background jobs |
| `UPDATE_CHANNEL` | `main` | Branch `./update.sh` pulls and the web UI's update-check compares against. `main` (stable) or `nightly` (latest). Also settable via `PUT /api/system/update-channel`. |

---

## Error Responses

```json
{ "detail": "Channel not found" }          // 404
{ "detail": "No content scheduled at this time" }  // 404 on stream
{ "detail": "ffmpeg is not installed on the server" }  // 503
```

---

## ScheduleEntry fields

| Field | Type | Source |
|---|---|---|
| `title` | string | Jellyfin item name |
| `series_name` | string\|null | Jellyfin `SeriesName` |
| `season_number` | int\|null | Jellyfin `ParentIndexNumber` |
| `episode_number` | int\|null | Jellyfin `IndexNumber` |
| `media_item_id` | string | Jellyfin item ID |
| `item_type` | `Movie`\|`Episode` | Jellyfin `Type` |
| `genres` | JSON string | Jellyfin `Genres` |
| `start_time` | datetime UTC | Computed at generation |
| `end_time` | datetime UTC | `start_time + duration` |
| `duration` | int (seconds) | From `RunTimeTicks` |
| `file_path` | string\|null | From Jellyfin `Path` / `MediaSources` |
| `description` | string\|null | `<plot>` from `.nfo` sidecar |
| `content_rating` | string\|null | `<mpaa>` from `.nfo` sidecar |
| `thumbnail_path` | string\|null | `.jpg` sidecar next to video |
| `air_date` | string\|null | `<aired>` from `.nfo` sidecar |
