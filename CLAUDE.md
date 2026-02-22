# JellyStream - Claude Context Document

## Project Overview

**JellyStream** is a virtual TV channel generator built on top of Jellyfin. It creates 24/7 streaming channels with scheduled programming, generates M3U playlists and XMLTV EPG data, and proxies video through ffmpeg with time-offset support so viewers always tune in mid-show at the correct position — just like a real TV channel.

### Core Concept
- User creates a **Channel** (virtual TV channel)
- Channel is configured with one or more **Jellyfin libraries** and **genre filters**
- JellyStream **auto-generates a 7-day schedule** from matching content
- Schedule is **persistent** — same content plays at the same time on all devices
- M3U + XMLTV endpoints expose the channel to Jellyfin Live TV (or any IPTV player)
- When a viewer tunes in, ffmpeg **seeks to the correct offset** — no restarting from the beginning
- A **background scheduler** (APScheduler) runs nightly to extend schedules 48+ hours ahead
- Kodi/Jellyfin sidecar `.nfo` and `.jpg` files are read at schedule generation time to enrich EPG data

### Key Features
- Genre-based auto-schedule generation (fills 7 days from Jellyfin content)
- Multiple libraries per channel (mix Movies + TV Shows on one channel)
- Manual schedule override support
- M3U playlist + XMLTV EPG generation (3-hour lookback, 7-day forward)
- XMLTV enriched with plot, thumbnail, air date, content rating from `.nfo`/`.jpg` sidecars
- ffmpeg stream proxy: H.264/AAC 1080p transcoding with time-offset seeking
- Direct file access for near-instant seek (falls back to Jellyfin HTTP stream)
- Persistent schedules (same time = same content regardless of viewer)
- APScheduler daily background job for schedule maintenance
- Comprehensive debug/notice logging in all modules
- Web interface via PHP + Lighttpd

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python web framework)
- **Database**: SQLite with SQLAlchemy ORM (async via aiosqlite)
- **API Client**: aiohttp for Jellyfin integration
- **Stream Proxy**: ffmpeg via asyncio.create_subprocess_exec
- **Scheduler**: APScheduler (AsyncIOScheduler)
- **Python Version**: 3.11+ (tested on 3.13)

### Frontend
- **Web Server**: Lighttpd with FastCGI
- **Language**: PHP 8.x
- **JavaScript**: Vanilla JS with async/await
- **CSS**: Custom dark theme

## Project Structure

```
jellystream/
├── app/
│   ├── api/              # API endpoints
│   │   ├── __init__.py   # Router registration
│   │   ├── channels.py   # Channel CRUD (replaces streams.py)
│   │   ├── schedules.py  # Schedule management
│   │   ├── jellyfin.py   # Jellyfin integration endpoints
│   │   ├── livetv.py     # M3U/XMLTV generation + stream proxy route
│   │   └── schemas.py    # Pydantic request/response models
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration management
│   │   ├── database.py   # Database initialization + migrations
│   │   └── logging_config.py  # Logging setup (get_logger)
│   ├── integrations/     # External integrations
│   │   └── jellyfin.py   # JellyfinClient with full auth
│   ├── models/           # SQLAlchemy models
│   │   ├── channel.py          # Channel model
│   │   ├── channel_library.py  # Channel ↔ Library join
│   │   ├── genre_filter.py     # Genre filters per channel
│   │   └── schedule_entry.py   # Persistent schedule entries
│   ├── services/         # Business logic services
│   │   ├── schedule_generator.py  # Genre-based schedule builder + NFO parsing
│   │   ├── stream_proxy.py        # ffmpeg stream proxy with offset
│   │   └── scheduler.py           # APScheduler background jobs
│   ├── web/              # Web interface
│   │   ├── php/          # PHP application
│   │   │   ├── includes/
│   │   │   │   ├── api_client.php   # PHP API client
│   │   │   │   └── database.php     # SQLite PDO helper
│   │   │   ├── pages/
│   │   │   │   ├── channels.php              # Channel management list
│   │   │   │   └── channel_edit.php          # Channel editor (libraries, genres, schedule)
│   │   │   └── config/
│   │   │       ├── config.php    # Constants (API_BASE_URL, APP_NAME etc)
│   │   │       └── ports.php     # Port config (NO hardcoded IPs)
│   │   └── static/       # CSS, JS, images
│   └── main.py           # Application entry point (starts scheduler)
├── config/               # Configuration files
├── data/
│   ├── commercials/      # Commercial videos (future)
│   ├── database/         # SQLite database (auto-created)
│   └── logos/            # Channel logos (future)
├── logs/                 # Log files (auto-created, daily rotation)
├── docs/
│   └── API.md            # API documentation
├── tests/
├── setup.sh              # Automated setup script
├── start.sh              # Quick start script
└── run.py                # Application launcher
```

## Database Models

### Channel (`app/models/channel.py`)
```python
- id: Integer (PK)
- name: String(255) NOT NULL
- description: Text nullable
- channel_number: String(10) nullable  # e.g. "100.1"
- enabled: Boolean default=True
- schedule_type: String(20) default="genre_auto"  # "manual" | "genre_auto"
- tuner_host_id: String(255) nullable   # Jellyfin TunerHost registration ID
- listing_provider_id: String(255) nullable  # Jellyfin ListingProvider ID
- schedule_generated_through: DateTime nullable  # furthest end_time in schedule
- created_at, updated_at: DateTime server_default
```

### ChannelLibrary (`app/models/channel_library.py`)
```python
- id: Integer (PK)
- channel_id: Integer FK → channels.id CASCADE DELETE
- library_id: String(255) NOT NULL   # Jellyfin library/view ID
- library_name: String(255) NOT NULL  # cached for display
- collection_type: String(50) NOT NULL  # "movies" | "tvshows" | "mixed"
```

### GenreFilter (`app/models/genre_filter.py`)
```python
- id: Integer (PK)
- channel_id: Integer FK → channels.id CASCADE DELETE
- genre: String(100) NOT NULL   # e.g. "Sci-Fi", "Horror"
- content_type: String(20) default="both"  # "movie" | "episode" | "both"
```

### ScheduleEntry (`app/models/schedule_entry.py`)
```python
- id: Integer (PK)
- channel_id: Integer FK → channels.id CASCADE DELETE
- title: String(255) NOT NULL
- series_name: String(255) nullable
- season_number: Integer nullable
- episode_number: Integer nullable
- media_item_id: String(255) NOT NULL   # Jellyfin item ID
- library_id: String(255) NOT NULL
- item_type: String(50) NOT NULL   # "Movie" | "Episode"
- start_time: DateTime NOT NULL
- end_time: DateTime NOT NULL   # start_time + duration
- duration: Integer NOT NULL   # seconds
- genres: Text nullable   # JSON array string
- file_path: Text nullable   # local path for direct file seek
- description: Text nullable   # <plot> from .nfo sidecar
- content_rating: String(20) nullable   # <mpaa> from .nfo e.g. "TV-14"
- thumbnail_path: Text nullable   # absolute path to .jpg sidecar
- air_date: String(20) nullable   # "YYYY-MM-DD" from <aired> in .nfo
- created_at: DateTime server_default
# Index on (channel_id, start_time) for fast EPG lookups
```

New columns are added via safe `ALTER TABLE` migrations in `database.py`
(silently ignored if the column already exists).

## API Endpoints

See [docs/API.md](docs/API.md) for comprehensive documentation.

### Important: All POST/PUT endpoints use JSON request body (Pydantic models), NOT query parameters.

### Application
- `GET /` — Web interface
- `GET /api` — API info
- `GET /health` — Health check (returns `status` + `public_url`)
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc

### Channels (`app/api/channels.py`)
- `GET /api/channels/` — List all channels
- `GET /api/channels/{id}` — Get channel with libraries + genre filters
- `POST /api/channels/` — Create channel (JSON body: CreateChannelRequest)
- `PUT /api/channels/{id}` — Update channel (JSON body: UpdateChannelRequest)
- `DELETE /api/channels/{id}` — Delete channel (cascades all related data)
- `POST /api/channels/{id}/generate-schedule?days=7&reset=true` — Regenerate schedule
- `POST /api/channels/{id}/register-livetv` — Register global M3U+XMLTV with Jellyfin
- `POST /api/channels/{id}/unregister-livetv` — Remove Jellyfin registration

### Schedules (`app/api/schedules.py`)
- `GET /api/schedules/channel/{channel_id}` — Get schedule (default: -3h to +7d)
- `GET /api/schedules/channel/{channel_id}/now` — What is currently playing
- `POST /api/schedules/` — Create manual entry (JSON body: CreateScheduleEntryRequest)
- `DELETE /api/schedules/{id}` — Delete entry

### Jellyfin Integration (`app/api/jellyfin.py`)
- `GET /api/jellyfin/users` — Get current user
- `GET /api/jellyfin/libraries` — Get all libraries (views)
- `GET /api/jellyfin/items/{parent_id}` — Get items with pagination/sorting/genre filter

### Live TV (`app/api/livetv.py`)
**CRITICAL: `/all` routes MUST be registered BEFORE `/{channel_id}` routes**
- `GET /api/livetv/m3u/all` — M3U for all enabled channels
- `GET /api/livetv/m3u/{channel_id}` — M3U for one channel
- `GET /api/livetv/xmltv/all` — XMLTV EPG for all (3hr back, 7d forward)
- `GET /api/livetv/xmltv/{channel_id}` — XMLTV EPG for one channel
- `GET /api/livetv/thumbnail/{entry_id}` — Serve `.jpg` sidecar for a schedule entry
- `HEAD /api/livetv/stream/{channel_id}` — Probe endpoint (Jellyfin uses before GET)
- `GET /api/livetv/stream/{channel_id}` — ffmpeg proxy stream at current offset

## Pydantic Schemas (`app/api/schemas.py`)

```python
class LibraryConfig(BaseModel):
    library_id: str
    library_name: str
    collection_type: str  # "movies" | "tvshows"

class GenreFilterConfig(BaseModel):
    genre: str
    content_type: str = "both"

class CreateChannelRequest(BaseModel):
    name: str
    description: Optional[str] = None
    channel_number: Optional[str] = None
    schedule_type: str = "genre_auto"
    libraries: List[LibraryConfig]
    genre_filters: Optional[List[GenreFilterConfig]] = None

class UpdateChannelRequest(BaseModel):
    # all fields optional
    name, description, channel_number, enabled, schedule_type
    libraries: Optional[List[LibraryConfig]] = None
    genre_filters: Optional[List[GenreFilterConfig]] = None

class CreateScheduleEntryRequest(BaseModel):
    channel_id: int
    title: str
    media_item_id: str
    library_id: str
    item_type: str  # "Movie" | "Episode"
    start_time: str  # ISO datetime
    duration: int   # seconds
    # optional: series_name, season_number, episode_number, genres
```

## Services

### Schedule Generator (`app/services/schedule_generator.py`)

Fetches genre-matching items from Jellyfin for each of a channel's libraries, then
fills time slots sequentially from `schedule_generated_through` (or now). Stores
ScheduleEntry rows. Updates `channel.schedule_generated_through`.

**Uses the admin `/Items` endpoint** (not `/Users/{id}/Items`) so that the `Path`
field is returned regardless of user permission level.

**Fields requested**: `RunTimeTicks,Genres,SeriesName,ParentIndexNumber,IndexNumber,Path,MediaSources`

Path extraction order: `item["Path"]` → `item["MediaSources"][0]["Path"]` → `None`

**Sidecar parsing**: After resolving `file_path`, reads `<basename>.nfo` (Kodi XML)
for `description` / `content_rating` / `air_date`, and looks for `<basename>.jpg`
(or `-thumb.jpg`) as `thumbnail_path`.

**MEDIA_PATH_MAP**: Format `/jellyfin/prefix:/local/prefix` — rewrites Jellyfin server
paths to locally accessible paths. Leave blank when both machines share the same mount.

### Stream Proxy (`app/services/stream_proxy.py`)

1. Finds current ScheduleEntry: `start_time <= now < end_time`
2. Calculates `offset = now - start_time` in seconds
3. Prefers `entry.file_path` (direct local file — near-instant seek); falls back to
   `JellyfinClient.get_stream_url(media_item_id)` (Jellyfin HTTP stream)
4. Launches ffmpeg:
   ```
   ffmpeg -ss {offset} -probesize 262144 -analyzeduration 1000000 -fflags nobuffer
          -i {source}
          -vf scale=-2:min(1080,ih) -c:v libx264 -preset veryfast -tune zerolatency
          -crf 20 -maxrate 8000k -bufsize 4000k
          -c:a aac -b:a 192k -ac 2
          -f mpegts -loglevel warning pipe:1
   ```
5. Returns `StreamingResponse` (`video/mp2t`) wrapping ffmpeg stdout
6. `X-Entry-Title` header is ASCII-encoded (non-ASCII chars replaced with `?`) to avoid
   latin-1 encoding errors in Starlette headers

### Background Scheduler (`app/services/scheduler.py`)

APScheduler `AsyncIOScheduler`, runs `daily_schedule_job` at 2am:
- Queries channels where `schedule_generated_through < now + 48h`
- Calls `generate_channel_schedule(channel_id, days=2)` for each
- Started in `app/main.py` on startup

## Logging Standard

**Every module** imports and uses `get_logger`:

```python
from app.core.logging_config import get_logger
logger = get_logger(__name__)

async def my_function(param):
    logger.debug(f"my_function called: param={param}")
    try:
        result = await do_work()
        logger.info(f"my_function completed successfully")
        return result
    except SomeError as e:
        logger.error(f"my_function failed: {e}", exc_info=True)
        raise
```

Log files: `./logs/jellystream_YYYY-MM-DD.log`
Rotation: 10MB, 5 backups
Retention: 30 days

## Jellyfin Integration Details

### Authentication
```
Authorization: MediaBrowser Token="api_key", Client="JellyStream", Device="JellyStream Server", DeviceId="uuid", Version="0.1.0"
```

### Hierarchical Content Navigation
- Library → Series (recursive=false)
- Series → Seasons (parent_id=SeriesId, recursive=false)
- Season → Episodes (parent_id=SeasonId, recursive=false)
- For genre-based fetching: recursive=true with Genres= filter

### User ID Auto-Detection
If `JELLYFIN_USER_ID` not set → calls `/Users` → uses first user's Id automatically.

### TunerHost Registration
Jellyfin requires `"Id": ""` and `"Source": ""` as explicit empty strings in the
POST payload to `/LiveTv/TunerHosts` — omitting them causes a 500 deserialization error.

### Global vs Per-Channel Registration
One tuner pointing to `m3u/all` covers all channels. New channels appear automatically
in Jellyfin without re-registration. The `register-livetv` endpoint cleans up any
existing `tuner_host_id` / `listing_provider_id` before creating new ones.

### JellyfinClient Methods (`app/integrations/jellyfin.py`)
- `ensure_user_id()` — Auto-detect and cache user ID
- `get_current_user()` — First user info
- `get_libraries()` — All user views
- `get_library_items(...)` — Paginated/sorted items
- `get_item_info(item_id)` — Item metadata
- `get_stream_url(item_id)` — `{base_url}/Videos/{item_id}/stream?api_key={key}`
- `register_tuner_host(url, friendly_name, ...)` — Register M3U tuner in Jellyfin Live TV
- `unregister_tuner_host(tuner_host_id)`
- `register_listing_provider(type, xmltv_url, friendly_name)` — Register EPG
- `unregister_listing_provider(provider_id)`

## Configuration (`.env`)

```env
JELLYFIN_URL=http://your-server:8096
JELLYFIN_API_KEY=your-api-key          # Admin key recommended (needed for Path field)
JELLYFIN_USER_ID=                      # Optional, auto-detected
JELLYFIN_CLIENT_NAME=JellyStream
JELLYFIN_DEVICE_NAME=JellyStream Server
JELLYFIN_DEVICE_ID=                    # Optional, auto-generated

HOST=0.0.0.0
PORT=8000

# Must be a network-accessible IP — Jellyfin fetches M3U/XMLTV from this address.
# Using localhost will cause Jellyfin registration to fail.
JELLYSTREAM_PUBLIC_URL=http://192.168.1.100:8000

# Path prefix rewrite: /jellyfin/prefix:/local/prefix
# Leave blank when JellyStream and Jellyfin share the same mount point.
MEDIA_PATH_MAP=

LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=./logs
LOG_FILE_MAX_BYTES=10485760
LOG_FILE_BACKUP_COUNT=5
LOG_RETENTION_DAYS=30

COMMERCIALS_PATH=./data/commercials
LOGOS_PATH=./data/logos
SCHEDULER_ENABLED=true
```

## PHP Frontend (`app/web/php/`)

### API Contract
- **All POST/PUT** send `Content-Type: application/json` with `JSON.stringify(data)` body
- **Never use** `URLSearchParams` as body for POST/PUT
- `api_client.php` correctly sends `json_encode($data)` as body
- `healthCheck()` calls `/health` (root), not `/api/health` — strips `/api` suffix from base URL

### Port Configuration (`config/ports.php`)
- `API_BASE_URL` must NOT use hardcoded IPs
- Use `$_SERVER['HTTP_HOST']` or environment variable
- Defaults: `http://localhost:8000/api`

### Key PHP Files
- `api_client.php` — HTTP client with all endpoint wrappers
- `config.php` — Constants: `API_BASE_URL`, `APP_NAME`, `API_TIMEOUT`
- `ports.php` — Dynamic host/port resolution (no hardcoded IPs)
- `index.php` — Dashboard: channels overview, what's playing now
- `pages/channels.php` — Channel management list
- `pages/channel_edit.php` — Channel editor with:
  - Library multi-select (add multiple Jellyfin libraries)
  - Genre filter list (genre name + content type)
  - Schedule type toggle (Manual vs Auto/Genre)
  - Regenerate Schedule button (`reset=true` — wipes and rebuilds from now)
  - Register/Unregister with Jellyfin Live TV
  - Localhost warning banner when public URL resolves to local address
- `setup.php` — Config wizard (writes `.env`)

## Current Status

### ✅ Phase 1 Complete
- Channel model with multi-library + genre filter support
- Genre-based auto-schedule generation (7-day fill, daily APScheduler extension)
- ffmpeg stream proxy: H.264 1080p / AAC stereo, time-offset seeking
- Direct file access (faster seek), HTTP fallback
- Kodi `.nfo` + `.jpg` sidecar parsing → stored in `ScheduleEntry`
- XMLTV enriched with `<desc>`, `<icon>`, `<date>`, `<rating>`
- Thumbnail serving endpoint (`/api/livetv/thumbnail/{entry_id}`)
- HEAD probe endpoint for Jellyfin stream compatibility
- M3U uses `tvg-chno` (correct Jellyfin channel number attribute)
- One-click Jellyfin Live TV registration (global M3U + XMLTV)
- `JELLYSTREAM_PUBLIC_URL` used in all M3U stream + XMLTV icon URLs
- Logging in all modules

### 🚧 Planned (Phase 2+)
- Full web UI with templates and consistent layout
- Channel dashboard with "now playing" and "up next"
- Episode/movie deselection per channel
- Filler content: commercials, bumpers, static image, next-show-immediate
- Channel logo watermark (ffmpeg overlay)
- Holiday schedules by date
- Multi-stream dashboard
- User authentication

## Known Issues / Design Decisions

### Route Ordering
FastAPI matches routes in registration order. Always register `/all` literal routes
BEFORE `/{id}` parameterised routes in `livetv.py` or "all" matches as an integer.

### ffmpeg Stream Proxy
```
ffmpeg -ss {offset} -probesize 262144 -analyzeduration 1000000 -fflags nobuffer
       -i {source}
       -vf scale=-2:min(1080,ih) -c:v libx264 -preset veryfast -tune zerolatency
       -crf 20 -maxrate 8000k -bufsize 4000k
       -c:a aac -b:a 192k -ac 2
       -f mpegts pipe:1
```
- `-ss` before `-i` = fast input seek
- `-probesize 262144` + `-analyzeduration 1000000` = reduced startup delay
- `-tune zerolatency` = minimises encoder buffering
- H.264 + AAC ensures broad client compatibility (Jellyfin, Android TV, VLC)

### HTTP Header Encoding
Starlette encodes response headers as latin-1. Titles with non-ASCII characters
(e.g. en-dash `–`) must be ASCII-encoded before use in `X-Entry-Title` header:
```python
entry.title.encode("ascii", errors="replace").decode("ascii")
```

### Schedule Generation Items Endpoint
Uses `/Items` (admin endpoint) instead of `/Users/{id}/Items` so that the `Path`
field is returned regardless of the configured user's permission level.

### Jellyfin EPG Refresh
The "Refresh Guide Data" button on the guide page processes cached data.
To force an actual re-download: Dashboard → Scheduled Tasks → **Refresh Guide** → Run.
XMLTV responses include `Cache-Control: no-cache` headers.

### Schedule Reset vs Append
`generate-schedule?reset=true` deletes all existing entries before generating.
Without `reset`, new entries are appended from `schedule_generated_through`.
The UI "Regenerate Schedule" button always passes `reset=true`.

## Development Environment

- **OS**: Kubuntu 25.10 / Debian testing
- **Python**: 3.13
- **User**: oarko
- **Virtual env**: `venv/` (required on Debian/Ubuntu due to PEP 668)
- **Database**: `data/database/jellystream.db` (auto-created)
- **Config**: `.env` (not committed to git)
- **Logs**: `logs/` (auto-created)

## Running the Application

```bash
source venv/bin/activate
python run.py
# Access: http://localhost:8000
# API docs: http://localhost:8000/docs
# M3U: http://localhost:8000/api/livetv/m3u/all
# XMLTV: http://localhost:8000/api/livetv/xmltv/all
```

## References

- [Jellyfin API Documentation](https://api.jellyfin.org/)
- [Jellyfin Live TV Documentation](https://jellyfin.org/docs/general/server/live-tv/)
- [M3U Playlist Format](https://en.wikipedia.org/wiki/M3U)
- [XMLTV EPG Format](http://wiki.xmltv.org/index.php/XMLTVFormat)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [ffmpeg Documentation](https://ffmpeg.org/documentation.html)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

---

*Last Updated: 2026-02-22*
*Version: 0.4.0*
*Status: Phase 1 complete — Phase 2 planning*
