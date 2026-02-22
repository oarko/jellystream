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

### Key Features
- Genre-based auto-schedule generation (fills 7 days from Jellyfin content)
- Multiple libraries per channel (mix Movies + TV Shows on one channel)
- Manual schedule override support
- M3U playlist + XMLTV EPG generation (3-hour lookback, 7-day forward)
- ffmpeg stream proxy with time-offset seeking
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
│   │   ├── database.py   # Database initialization
│   │   └── logging_config.py  # Logging setup (get_logger)
│   ├── integrations/     # External integrations
│   │   └── jellyfin.py   # JellyfinClient with full auth
│   ├── models/           # SQLAlchemy models
│   │   ├── channel.py          # Channel model
│   │   ├── channel_library.py  # Channel ↔ Library join
│   │   ├── genre_filter.py     # Genre filters per channel
│   │   └── schedule_entry.py   # Persistent schedule entries
│   ├── services/         # Business logic services
│   │   ├── schedule_generator.py  # Genre-based schedule builder
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
- created_at: DateTime server_default
# Index on (channel_id, start_time) for fast EPG lookups
```

## API Endpoints

See [docs/API.md](docs/API.md) for comprehensive documentation.

### Important: All POST/PUT endpoints use JSON request body (Pydantic models), NOT query parameters.

### Application
- `GET /` — Web interface
- `GET /api` — API info
- `GET /health` — Health check
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc

### Channels (`app/api/channels.py`)
- `GET /api/channels/` — List all channels
- `GET /api/channels/{id}` — Get channel with libraries + genre filters
- `POST /api/channels/` — Create channel (JSON body: CreateChannelRequest)
- `PUT /api/channels/{id}` — Update channel (JSON body: UpdateChannelRequest)
- `DELETE /api/channels/{id}` — Delete channel (cascades all related data)
- `POST /api/channels/{id}/generate-schedule` — Manually trigger 7-day schedule gen

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

Fetches genre-matching items from Jellyfin for each of a channel's libraries, then fills time slots sequentially from `schedule_generated_through` (or now). Stores ScheduleEntry rows. Updates `channel.schedule_generated_through`.

**Jellyfin genre filtering uses**:
```
GET /Users/{userId}/Items?ParentId={libraryId}&Genres={genre}&IncludeItemTypes=Movie,Episode&Recursive=true
```

### Stream Proxy (`app/services/stream_proxy.py`)

1. Finds current ScheduleEntry: `start_time <= now < end_time`
2. Calculates `offset = now - start_time` in seconds
3. Calls `JellyfinClient.get_stream_url(media_item_id)` for the direct video URL
4. Launches `ffmpeg -ss {offset} -i {url} -c copy -f mpegts pipe:1`
5. Returns `StreamingResponse` wrapping ffmpeg stdout

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

### JellyfinClient Methods (`app/integrations/jellyfin.py`)
- `ensure_user_id()` — Auto-detect and cache user ID
- `get_current_user()` — First user info
- `get_libraries()` — All user views
- `get_library_items(parent_id, recursive, limit, start_index, sort_by, sort_order, include_item_types)` — Paginated/sorted items
- `get_item_info(item_id)` — Item metadata
- `get_stream_url(item_id)` — `{base_url}/Videos/{item_id}/stream?api_key={key}`
- `register_tuner_host(url, friendly_name, ...)` — Register M3U tuner in Jellyfin Live TV
- `unregister_tuner_host(tuner_host_id)`
- `register_listing_provider(type, xmltv_url, friendly_name)` — Register EPG
- `unregister_listing_provider(provider_id)`

## Configuration (`.env`)

```env
JELLYFIN_URL=http://your-server:8096
JELLYFIN_API_KEY=your-api-key
JELLYFIN_USER_ID=          # Optional, auto-detected
JELLYFIN_CLIENT_NAME=JellyStream
JELLYFIN_DEVICE_NAME=JellyStream Server
JELLYFIN_DEVICE_ID=        # Optional, auto-generated
JELLYFIN_DEFAULT_PAGE_SIZE=50
JELLYFIN_MAX_PAGE_SIZE=1000

HOST=0.0.0.0
PORT=8000

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
- **Never use** `URLSearchParams` as body for POST/PUT (old bug — already fixed)
- `api_client.php` correctly sends `json_encode($data)` as body

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
  - Schedule timeline view
- `setup.php` — Config wizard (writes `.env`)

## Current Status

### ✅ Completed / Stable
- FastAPI application structure
- Jellyfin client with proper auth, user ID auto-detection
- Hierarchical content browsing (Series → Season → Episode)
- Pagination and sorting parameters
- M3U and XMLTV format generation logic
- APScheduler dependency installed
- Logging infrastructure (file + console, rotation)
- PHP frontend base structure

### 🔧 In Progress (Phase 1)
- Redesign data model (Channel, ChannelLibrary, GenreFilter, ScheduleEntry)
- Fix all POST/PUT to use Pydantic JSON body
- Build `schedule_generator.py` service
- Build `stream_proxy.py` with ffmpeg
- Integrate APScheduler
- Add logging to all modules
- Fix livetv.py route ordering bug
- Update PHP for multi-library channel creation + genre filters

### 🚧 Planned (Phase 2+)
- Full web UI with templates and consistent layout
- Channel dashboard with "now playing" and "up next"
- Episode/movie deselection per channel
- Filler content: commercials, bumpers, static image, next-show-immediate
- Channel logo watermark (ffmpeg overlay)
- Holiday schedules by date
- Jellyfin Live TV auto-registration from UI
- Multi-stream dashboard
- User authentication

## Known Issues / Design Decisions

### Route Ordering Bug (Fixed in Phase 1)
FastAPI matches routes in registration order. In `livetv.py`, `/m3u/{channel_id}` was registered before `/m3u/all`, causing `/m3u/all` to be intercepted as `/m3u/{channel_id=all}`.
**Fix**: Always register `/all` literal routes BEFORE `/{id}` parameterized routes.

### ffmpeg Stream Proxy
The live stream endpoint (`/api/livetv/stream/{channel_id}`) proxies video through ffmpeg:
```bash
ffmpeg -ss {offset_seconds} -i {jellyfin_url} -c copy -f mpegts pipe:1
```
- `-ss` before `-i` = fast seek (input seek, not frame-accurate but low latency)
- `-c copy` = no transcoding by default (use `-c:v libx264 -c:a aac` for transcoding)
- `-f mpegts` = MPEG-TS container suitable for streaming

### Schedule Generation
- Jellyfin genre filter: `GET /Users/{userId}/Items?Genres={genre}&Recursive=true`
- Items are fetched for each library separately then merged
- Schedule fills sequentially from `schedule_generated_through` with no gaps
- For TV shows: cycles through seasons/episodes in order
- For Movies: shuffles to avoid repetition

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

## Useful Commands

```bash
make setup          # Run setup.sh
make run            # Start application
./start.sh          # Quick start with venv
make test           # Run tests
make docker-build   # Build Docker image
make docker-run     # Run in Docker
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

*Last Updated: 2026-02-21*
*Version: 0.3.0*
*Status: Active Development — Phase 1 architectural redesign in progress*
