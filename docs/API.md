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
and optional genre filters that drive automatic schedule generation.

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
    "created_at": "2026-02-01T00:00:00",
    "updated_at": "2026-02-01T00:00:00"
  }
]
```

### Get channel

**GET** `/api/channels/{id}`

Returns channel with its libraries and genre filters.

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
  "genre_filters": [
    { "genre": "Action", "content_type": "both", "filter_type": "include" }
  ]
}
```

### Create channel

**POST** `/api/channels/`

```json
{
  "name": "Action Movies",
  "description": "Non-stop action",
  "channel_number": "100.1",
  "channel_type": "video",
  "schedule_type": "genre_auto",
  "libraries": [
    { "library_id": "abc123", "library_name": "Movies", "collection_type": "movies" }
  ],
  "genre_filters": [
    { "genre": "Action", "content_type": "both", "filter_type": "include" },
    { "genre": "Animation", "content_type": "both", "filter_type": "exclude" }
  ]
}
```

`channel_type`: `"video"` (default). `"music"` is reserved for a future release.
`schedule_type`: `"genre_auto"` (default) or `"manual"`.
`content_type` in genre filters: `"movie"`, `"episode"`, or `"both"`.
`filter_type` in genre filters: `"include"` (default) fetches matching content; `"exclude"` removes matching items from the pool after fetching.

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

**Request body:**
```json
{
  "public_url": "http://192.168.1.100:8000"
}
```

`public_url` must be a network-accessible address that Jellyfin can reach.
Using `localhost` will cause Jellyfin's registration to fail.

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

## Live TV  `/api/livetv/`

> **Route ordering:** `/m3u/all` and `/xmltv/all` are registered *before*
> `/{channel_id}` variants to prevent FastAPI matching `"all"` as an integer.

### M3U playlist — all channels

**GET** `/api/livetv/m3u/all`

```m3u
#EXTM3U
#EXTINF:-1 tvg-id="1" tvg-name="Action Movies" tvg-chno="100.1" group-title="JellyStream",100.1 Action Movies
http://192.168.1.100:8000/api/livetv/stream/1
```

Uses `tvg-chno` (not `channel-number`) which Jellyfin reads for channel numbering.

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

Proxies the current schedule item through ffmpeg at the correct time offset so
the viewer always joins mid-programme — just like real broadcast TV.

1. Finds the `ScheduleEntry` spanning `now` (`start_time ≤ now < end_time`)
2. Calculates `offset = now − start_time` in seconds
3. Prefers direct file access (`file_path`) for near-instant seek; falls back to Jellyfin HTTP stream
4. Probes audio tracks with `ffprobe` and selects the track matching `PREFERRED_AUDIO_LANGUAGE` (falls back to first audio track)
5. Runs:
   ```
   ffmpeg -ss {offset} -probesize 262144 -analyzeduration 1000000 -fflags nobuffer
          -i {source}
          -map 0:v:0  -map 0:{audio_index}
          -vf scale=-2:min(1080,ih) -c:v libx264 -preset veryfast -tune zerolatency
          -crf 20 -maxrate 8000k -bufsize 4000k
          -c:a aac -b:a 192k -ac 2
          -f mpegts -loglevel warning pipe:1
   ```
5. Returns `StreamingResponse` (`video/mp2t`) wrapping ffmpeg stdout

**Response headers:**
- `X-Channel-Id` — channel ID
- `X-Entry-Title` — ASCII-sanitised title
- `X-Offset-Seconds` — seek offset applied

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

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `JELLYFIN_URL` | — | Jellyfin server URL |
| `JELLYFIN_API_KEY` | — | Jellyfin API key (admin recommended) |
| `JELLYFIN_USER_ID` | auto | Optional; auto-detected from first user |
| `JELLYSTREAM_PUBLIC_URL` | — | Network-accessible URL for M3U/XMLTV/thumbnail URLs |
| `MEDIA_PATH_MAP` | — | Path prefix rewrite (`/jf/prefix:/local/prefix`) |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Listen port |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `PREFERRED_AUDIO_LANGUAGE` | `eng` | ISO 639-2 code for preferred audio track (`eng`, `jpn`, `fre`, …) |
| `SCHEDULER_ENABLED` | `true` | Enable APScheduler background jobs |

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
