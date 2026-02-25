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
- **Collections** let users curate named sets of media (movies, shows, seasons, episodes, or other collections) for future use as channel content sources

### Key Features
- Genre-based auto-schedule generation (fills 7 days from Jellyfin content)
- Multiple libraries per channel (mix Movies + TV Shows on one channel)
- Manual schedule override support
- M3U playlist + XMLTV EPG generation (3-hour lookback, 7-day forward)
- XMLTV: episodes use `<title>` = series name, `<sub-title>` = episode title
- XMLTV enriched with plot, thumbnail, air date, content rating from `.nfo`/`.jpg` sidecars
- ffmpeg stream proxy: H.264/AAC 1080p transcoding with time-offset seeking
- Direct file access for near-instant seek (falls back to Jellyfin HTTP stream)
- Persistent schedules (same time = same content regardless of viewer)
- APScheduler daily background job for schedule maintenance
- Collections: curated media sets with browse UI, Jellyfin boxset import, file verification
- Collections-in-Collections: a collection can reference other collections as items
- Shared CSS stylesheet (`static/css/style.css`) — all pages link to it; page-specific styles in inline `<style>` only
- Comprehensive debug/notice logging in all modules
- Web interface via PHP + Lighttpd (binds to `0.0.0.0` for network access)

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python web framework)
- **Database**: SQLite with SQLAlchemy ORM (async via aiosqlite)
- **API Client**: aiohttp for Jellyfin integration
- **Stream Proxy**: ffmpeg via asyncio.create_subprocess_exec
- **Scheduler**: APScheduler (AsyncIOScheduler)
- **Python Version**: 3.11+ (tested on 3.13)

### Frontend
- **Web Server**: Lighttpd with FastCGI (or PHP built-in server for dev)
- **Language**: PHP 8.x
- **JavaScript**: Vanilla JS with async/await
- **CSS**: Shared dark theme in `static/css/style.css`; page-specific rules in inline `<style>`

## Project Structure

```
jellystream/
├── app/
│   ├── api/              # API endpoints
│   │   ├── __init__.py        # Router registration
│   │   ├── channels.py        # Channel CRUD
│   │   ├── collections.py     # Collection CRUD + import + verify + thumbnail
│   │   ├── schedules.py       # Schedule management
│   │   ├── jellyfin.py        # Jellyfin integration endpoints (browse, image proxy, etc.)
│   │   ├── livetv.py          # M3U/XMLTV generation + stream proxy route
│   │   └── schemas.py         # Pydantic request/response models
│   ├── core/             # Core functionality
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database initialization + migrations
│   │   └── logging_config.py  # Logging setup (get_logger)
│   ├── integrations/     # External integrations
│   │   └── jellyfin.py        # JellyfinClient with full auth
│   ├── models/           # SQLAlchemy models
│   │   ├── channel.py
│   │   ├── channel_library.py
│   │   ├── collection.py        # Collection entity
│   │   ├── collection_item.py   # Items within a collection
│   │   ├── genre_filter.py
│   │   └── schedule_entry.py
│   ├── services/         # Business logic services
│   │   ├── collection_service.py  # NFO/thumbnail enrichment + file verify
│   │   ├── schedule_generator.py  # Genre-based schedule builder + NFO parsing
│   │   ├── stream_proxy.py        # ffmpeg stream proxy with offset
│   │   └── scheduler.py           # APScheduler background jobs
│   ├── web/              # Web interface
│   │   ├── php/          # PHP application
│   │   │   ├── includes/
│   │   │   │   ├── api_client.php   # PHP API client (server-side calls)
│   │   │   │   └── database.php     # SQLite PDO helper
│   │   │   ├── pages/
│   │   │   │   ├── channels.php         # Channel management list
│   │   │   │   ├── channel_edit.php     # Channel editor (libraries, genres, schedule, Live TV)
│   │   │   │   ├── collections.php      # Collection list + import boxset modal
│   │   │   │   └── collection_edit.php  # Browse + cart + save (with series drill-down)
│   │   │   ├── config/
│   │   │   │   ├── config.php    # Constants (API_BASE_URL, APP_NAME etc)
│   │   │   │   └── ports.php     # Port config + getApiBaseUrl() + getClientApiBaseUrl()
│   │   │   └── static/
│   │   │       └── css/
│   │   │           └── style.css  # Shared dark-theme stylesheet (all pages link here)
│   │   └── setup.php     # Config wizard (writes .env)
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
├── start-php.sh          # PHP built-in dev server (binds 0.0.0.0)
├── start-lighttpd.sh     # Lighttpd production server (binds 0.0.0.0)
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
- tuner_host_id: String(255) nullable
- listing_provider_id: String(255) nullable
- schedule_generated_through: DateTime nullable
- created_at, updated_at: DateTime server_default
```

### ChannelLibrary (`app/models/channel_library.py`)
```python
- id: Integer (PK)
- channel_id: Integer FK → channels.id CASCADE DELETE
- library_id: String(255) NOT NULL
- library_name: String(255) NOT NULL
- collection_type: String(50) NOT NULL  # "movies" | "tvshows" | "mixed"
```

### GenreFilter (`app/models/genre_filter.py`)
```python
- id: Integer (PK)
- channel_id: Integer FK → channels.id CASCADE DELETE
- genre: String(100) NOT NULL
- content_type: String(20) default="both"  # "movie" | "episode" | "both"
```

### ScheduleEntry (`app/models/schedule_entry.py`)
```python
- id: Integer (PK)
- channel_id: Integer FK → channels.id CASCADE DELETE
- title: String(255) NOT NULL
- series_name, season_number, episode_number: nullable
- media_item_id: String(255) NOT NULL   # Jellyfin item ID
- library_id: String(255) NOT NULL
- item_type: String(50) NOT NULL   # "Movie" | "Episode"
- start_time, end_time: DateTime NOT NULL
- duration: Integer NOT NULL   # seconds
- genres: Text nullable   # JSON array string
- file_path: Text nullable   # local path for direct file seek
- description: Text nullable   # <plot> from .nfo
- content_rating: String(20) nullable   # <mpaa> from .nfo
- thumbnail_path: Text nullable   # absolute path to .jpg sidecar
- air_date: String(20) nullable   # "YYYY-MM-DD" from <aired> in .nfo
- created_at: DateTime server_default
# Index on (channel_id, start_time) for fast EPG lookups
```

New columns added via safe `ALTER TABLE` migrations in `database.py` (silently ignored if column exists).

### Collection (`app/models/collection.py`)
```python
- id: Integer (PK)
- name: String(255) NOT NULL
- description: Text nullable
- jellyfin_id: String(255) nullable  # set when imported from a Jellyfin boxset
- created_at, updated_at: DateTime server_default
```

### CollectionItem (`app/models/collection_item.py`)
Mirrors ScheduleEntry non-time fields for future Phase 2 channel integration.
```python
- id: Integer (PK)
- collection_id: Integer FK → collections.id CASCADE DELETE (indexed)
- media_item_id: String(255) NOT NULL  # Jellyfin item ID, or str(collection.id) for type="Collection"
- item_type: String(50) NOT NULL  # "Movie" | "Episode" | "Series" | "Season" | "Collection"
- title: String(255) NOT NULL
- series_name, season_number, episode_number: nullable
- library_id: String(255) NOT NULL  # "" for Collection-type items
- duration: Integer nullable   # seconds
- genres: Text nullable        # JSON array
- file_path: Text nullable     # local path for verify + seek
- thumbnail_path: Text nullable
- description, content_rating, air_date: nullable
- sort_order: Integer default=0
- created_at: DateTime server_default
# Composite index on (collection_id, item_type)
```

Collections can be nested: `item_type="Collection"` stores the referenced
collection's `id` (as a string) in `media_item_id`, with `library_id=""`.
New tables created by `create_all()` — no ALTER TABLE migrations needed.

## API Endpoints

See [docs/API.md](docs/API.md) for comprehensive documentation.

### Important: All POST/PUT endpoints use JSON request body (Pydantic models), NOT query parameters.

### Application
- `GET /` — Web interface
- `GET /api` — API info
- `GET /health` — Health check (returns `status` + `public_url`)
- `GET /docs` — Swagger UI

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

### Collections (`app/api/collections.py`)
**CRITICAL: `/thumbnail/{id}` MUST be registered BEFORE `/{collection_id}`**
- `GET /api/collections/` — List all (id, name, item_count, jellyfin_id)
- `GET /api/collections/{id}` — Collection + all items
- `POST /api/collections/` — Create (JSON body: CreateCollectionRequest)
- `PUT /api/collections/{id}` — Update metadata + replace items
- `DELETE /api/collections/{id}` — Delete (cascade items)
- `POST /api/collections/import/{boxset_id}` — Import Jellyfin boxset as collection
- `GET /api/collections/{id}/verify` — Check file existence; re-query Jellyfin for moved files
- `DELETE /api/collections/{id}/items/{item_id}` — Remove one item
- `GET /api/collections/thumbnail/{item_id}` — Serve local thumbnail_path for a CollectionItem

### Jellyfin Integration (`app/api/jellyfin.py`)
- `GET /api/jellyfin/users` — Get current user
- `GET /api/jellyfin/libraries` — Get all libraries (views); items keyed by `Id` (not `ItemId`)
- `GET /api/jellyfin/genres/{library_id}` — Genre names present in a library
- `GET /api/jellyfin/items/{parent_id}` — Get items with pagination/sorting/genre filter
- `GET /api/jellyfin/boxsets` — List Jellyfin boxset collections
- `GET /api/jellyfin/browse?library_id=&type=Movie&search=&year_from=&year_to=&limit=&offset=` — Paginated browse (admin endpoint, returns Path field)
- `GET /api/jellyfin/series/{series_id}/seasons` — Seasons for a series
- `GET /api/jellyfin/seasons/{season_id}/episodes` — Episodes for a season (with Path, duration)
- `GET /api/jellyfin/items/{item_id}/image?type=Primary&maxWidth=400` — Proxy Jellyfin image (hides API key from browser)

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
    collection_type: str  # "movies" | "tvshows" | "mixed"

class GenreFilterConfig(BaseModel):
    genre: str
    content_type: str = "both"
    filter_type: str = "include"  # "include" | "exclude"

class CreateChannelRequest(BaseModel):
    name: str
    description: Optional[str] = None
    channel_number: Optional[str] = None
    channel_type: str = "video"
    schedule_type: str = "genre_auto"
    libraries: List[LibraryConfig]
    genre_filters: Optional[List[GenreFilterConfig]] = None

class UpdateChannelRequest(BaseModel):
    # all fields optional
    name, description, channel_number, enabled, channel_type, schedule_type
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

class CollectionItemInput(BaseModel):
    media_item_id: str
    item_type: str          # "Movie" | "Episode" | "Series" | "Season" | "Collection"
    title: str
    library_id: str         # "" for Collection-type items
    series_name: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    duration: Optional[int] = None
    genres: Optional[str] = None   # JSON array string
    file_path: Optional[str] = None
    sort_order: int = 0

class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[CollectionItemInput] = []

class UpdateCollectionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[CollectionItemInput]] = None  # if present, replaces all items
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

### Collection Service (`app/services/collection_service.py`)

Provides NFO parsing, thumbnail finding, and file verification for CollectionItems.

**NFO conventions by item type:**
- `Movie` → `movie.nfo` in same dir (fallback: `{basename}.nfo`)
- `Series` → `tvshow.nfo` in series root dir (`file_path` is the directory)
- `Season` → `tvshow.nfo` in parent of season dir
- `Episode` → `{basename}.nfo` next to video file

**Thumbnail conventions by item type:**
- `Movie` → `folder.jpg` | `{basename}.jpg` | `{basename}-thumb.jpg`
- `Series` → `folder.jpg` | `poster.jpg` in series root
- `Season` → `season{NN:02d}-poster.jpg` in series root | `folder.jpg` in season dir
- `Episode` → `{basename}-thumb.jpg` | `{basename}.jpg` | `folder.jpg`

**`enrich_item(item: dict) -> dict`**: Runs NFO parse + thumbnail find, returns enriched dict.

**`verify_collection(items, client)`**: For each item — checks `os.path.isfile(file_path)`;
if missing, re-queries Jellyfin for new path; returns status: `ok` | `moved` | `deleted` | `no_path`.
Items with `item_type="Collection"` return `no_path` (no file to verify).

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
- Library views endpoint returns items with key `Id` (NOT `ItemId`)

### User ID Auto-Detection
If `JELLYFIN_USER_ID` not set → calls `/Users` → uses first user's Id automatically.

### TunerHost Registration
Jellyfin requires `"Id": ""` and `"Source": ""` as explicit empty strings in the
POST payload to `/LiveTv/TunerHosts` — omitting them causes a 500 deserialization error.

### Global vs Per-Channel Registration
One tuner pointing to `m3u/all` covers all channels. New channels appear automatically
in Jellyfin without re-registration.

### JellyfinClient Methods (`app/integrations/jellyfin.py`)
- `ensure_user_id()` — Auto-detect and cache user ID
- `get_current_user()` — First user info
- `get_libraries()` — All user views (returns list with `Id`, `Name`, `CollectionType`)
- `get_genres(library_id)` — Sorted list of genre names present in a library
- `get_library_items(...)` — Paginated/sorted items
- `get_item_info(item_id)` — Item metadata
- `get_stream_url(item_id)` — `{base_url}/Videos/{item_id}/stream?api_key={key}`
- `get_boxsets()` — All Jellyfin boxset collections
- `browse_items(parent_id, include_types, fields, search_term, start_year, end_year, limit, start_index, recursive)` — Admin `/Items` endpoint browse
- `get_item_image(item_id, image_type, max_width) -> tuple[bytes, str]` — Raw image bytes for proxying
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

# Preferred audio language (ISO 639-2 code, e.g. eng, jpn, fra)
PREFERRED_AUDIO_LANGUAGE=eng

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
- `api_client.php` uses `getApiBaseUrl()` for server-side PHP calls (localhost is fine)
- **Client-side JS** must use `getClientApiBaseUrl()` — uses `$_SERVER['HTTP_HOST']` so
  the URL resolves correctly from remote browsers, not just from the server itself
- `healthCheck()` calls `/health` (root), not `/api/health` — strips `/api` suffix from base URL

### Port Configuration (`config/ports.php`)
Two functions for different call contexts:
- `getApiBaseUrl()` — server-side PHP (api_client.php); uses `localhost` or `JELLYSTREAM_API_HOST`
- `getClientApiBaseUrl()` — embedded in page JavaScript; uses `$_SERVER['HTTP_HOST']` host portion
  so remote browsers hit the correct IP (not localhost on their own machine)
- All pages use `getClientApiBaseUrl()` in `const API_BASE = '...'` JS declarations
- All browser-rendered `href` links to the API also use `getClientApiBaseUrl()`

### Shared CSS (`static/css/style.css`)
Single stylesheet linked by all pages via `<link rel="stylesheet" href="/static/css/style.css">`.
Contains: body/container, `.card`, `.btn` variants, form inputs, tables, `.badge` variants,
`.modal`, `.toggle-row`/`.switch`, `.links`/`.link-btn`, status messages, empty state, form-actions.
Page-specific layout (grids, panels, drill-down) stays in inline `<style>` blocks only.

### Key PHP Files
- `includes/api_client.php` — HTTP client with all endpoint wrappers (channels, collections, jellyfin)
- `config/config.php` — Constants: `API_BASE_URL`, `APP_NAME`, `API_TIMEOUT`
- `config/ports.php` — `getApiBaseUrl()` + `getClientApiBaseUrl()` (no hardcoded IPs)
- `index.php` — Dashboard: channels overview, what's playing now, Collections quick link
- `pages/channels.php` — Channel management list
- `pages/channel_edit.php` — Channel editor with:
  - Library multi-select (add multiple Jellyfin libraries)
  - Genre filter list with include/exclude and content type
  - Schedule type toggle (Manual vs Auto/Genre)
  - Regenerate Schedule button (`reset=true` — wipes and rebuilds from now)
  - Register/Unregister with Jellyfin Live TV
  - Localhost warning banner when public URL resolves to local address
- `pages/collections.php` — Collection list: table with Name/Source/Items/Actions,
  inline verify results per row, Import Jellyfin Boxset modal
- `pages/collection_edit.php` — Two-column browse + cart + save:
  - Left: library picker + 📦 Collections toggle; sub-tabs (Movies/Series) auto-shown
    only for `mixed`/`boxsets` libraries; library type auto-detected from `data-type` attribute
  - Browse modes: Jellyfin grid (movies/series/seasons/episodes drill-down) or internal collections list
  - Right: sticky cart panel with type-badges, thumbnails, remove buttons; name/description; Save
  - Collection items show `📦` icon; `item_type="Collection"` stores sub-collection ID
- `setup.php` — Config wizard (writes `.env`)

### collection_edit.php JS Architecture
```javascript
const cart = new Map();        // media_item_id (string) → item data
let browseState = {
    libraryId, type,           // type: 'Movie' | 'Series' | 'Collection'
    search, yearFrom, yearTo,
    page, limit, totalItems,
    mode,                      // 'browse' | 'seasons' | 'episodes'
    seriesId, seriesTitle, seasonId, seasonTitle, seasonNumber, seriesLibraryId,
};
// Key functions: onLibraryChange(), setType('Collection'), setSubType('Movie'|'Series'),
// browse(), drillSeries(), drillSeason(), browseCollections(), renderCollectionList(),
// toggleCollectionInCart(), renderCart(), saveCollection()
```

`renderCart()` always does `container.innerHTML = ''` first (never uses `getElementById`
on elements it may have already destroyed).

## Current Status

### ✅ Phase 1 Complete
- Channel model with multi-library + genre filter support
- Genre-based auto-schedule generation (7-day fill, daily APScheduler extension)
- ffmpeg stream proxy: H.264 1080p / AAC stereo, time-offset seeking
- Direct file access (faster seek), HTTP fallback
- Kodi `.nfo` + `.jpg` sidecar parsing → stored in `ScheduleEntry`
- XMLTV: `<title>` = series name, `<sub-title>` = episode title for TV episodes
- XMLTV enriched with `<desc>`, `<icon>`, `<date>`, `<rating>`
- Thumbnail serving endpoint (`/api/livetv/thumbnail/{entry_id}`)
- HEAD probe endpoint for Jellyfin stream compatibility
- M3U uses `tvg-chno` (correct Jellyfin channel number attribute)
- One-click Jellyfin Live TV registration (global M3U + XMLTV)
- `JELLYSTREAM_PUBLIC_URL` used in all M3U stream + XMLTV icon URLs
- Logging in all modules

### ✅ Phase 1.5 — Collections (complete)
- `Collection` + `CollectionItem` models (new DB tables, no migrations needed)
- Full collection CRUD API (`/api/collections/`)
- Jellyfin boxset import: fetches items via admin `/Items`, enriches with NFO/thumbnails
- Browse UI: library picker auto-detects content type from `CollectionType`; sub-tabs only for mixed
- Series → Season → Episode drill-down with per-level add buttons and "Add whole season"
- Collections-in-Collections: `item_type="Collection"` references another collection by ID
- File verification: checks local path, re-queries Jellyfin if missing, reports moved/deleted
- Image proxy endpoint (`/api/jellyfin/items/{id}/image`) keeps Jellyfin API key server-side
- Shared `static/css/style.css` stylesheet
- `getClientApiBaseUrl()` fixes JS fetch from remote browsers (HTTP_HOST-based, not localhost)
- Both frontend servers bind to `0.0.0.0` for network access

### 🚧 Planned (Phase 2+)
- Collections as channel content source (Phase 2 integration)
- Channel dashboard with "now playing" and "up next"
- Episode/movie deselection per channel
- Filler content: commercials, bumpers, static image, next-show-immediate
- Channel logo watermark (ffmpeg overlay)
- Holiday schedules by date
- Multi-stream dashboard
- User authentication

## Known Issues / Design Decisions

### Route Ordering
FastAPI matches routes in registration order. Always register literal routes BEFORE
parameterised routes. Critical cases:
- `livetv.py`: `/m3u/all`, `/xmltv/all`, `/thumbnail/{id}` BEFORE `/{channel_id}` variants
- `collections.py`: `/thumbnail/{item_id}` BEFORE `/{collection_id}`

### XMLTV Title Format
TV episodes: `<title>` carries the **series name**, `<sub-title>` carries the episode title.
Movies: `<title>` only. This matches the XMLTV spec and Jellyfin's guide display.

### getClientApiBaseUrl() vs getApiBaseUrl()
PHP server-side calls use `getApiBaseUrl()` (localhost). Browser JS must use
`getClientApiBaseUrl()` which extracts the host from `$_SERVER['HTTP_HOST']` so
remote browsers call the server's IP, not their own localhost. Set
`JELLYSTREAM_API_HOST` env var to override both (for reverse-proxy setups).

### Jellyfin Library Views — Key Name
`GET /Users/{id}/Views` returns items with key `Id` (not `ItemId`).
PHP must use `$lib['Id']` when reading library ID from the API response.

### PHP Frontend Server Binding
Both `start-php.sh` and `start-lighttpd.sh` must bind to `0.0.0.0` (not `localhost`)
to be accessible from other machines on the network.
- `start-php.sh`: `PHP_HOST="0.0.0.0"` → `php -S 0.0.0.0:8080`
- `start-lighttpd.sh`: `server.bind = "0.0.0.0"` in generated config

### Collections-in-Collections
`item_type="Collection"` items store the referenced collection's integer ID as a
string in `media_item_id`, and `library_id=""`. The `verify_collection` service
returns `status="no_path"` for these (no file to check) — this is expected.

### renderCart() DOM Safety
`renderCart()` always resets `container.innerHTML = ''` first, then repopulates.
It never relies on `getElementById` for elements that were children of the container
(they get destroyed by the innerHTML reset). The empty-state message is recreated
inline (`container.innerHTML = '<div class="cart-empty">...'`) rather than toggled.

### ffmpeg Stream Proxy
```
ffmpeg -ss {offset} -probesize 262144 -analyzeduration 1000000 -fflags nobuffer
       -i {source}
       -vf scale=-2:min(1080,ih) -c:v libx264 -preset veryfast -tune zerolatency
       -crf 20 -maxrate 8000k -bufsize 4000k
       -c:a aac -b:a 192k -ac 2
       -f mpegts pipe:1
```

### HTTP Header Encoding
Starlette encodes response headers as latin-1. Titles with non-ASCII characters
must be ASCII-encoded before use in `X-Entry-Title` header:
```python
entry.title.encode("ascii", errors="replace").decode("ascii")
```

### Schedule Generation Items Endpoint
Uses `/Items` (admin endpoint) instead of `/Users/{id}/Items` so that the `Path`
field is returned regardless of the configured user's permission level.

### Jellyfin EPG Refresh
The "Refresh Guide Data" button processes cached data.
To force a re-download: Dashboard → Scheduled Tasks → **Refresh Guide** → Run.
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
# Backend
source venv/bin/activate
python run.py
# API: http://localhost:8000  |  Docs: http://localhost:8000/docs

# Frontend (dev)
./start-php.sh        # PHP built-in server, port 8080, binds 0.0.0.0

# Frontend (production)
./start-lighttpd.sh   # Lighttpd + FastCGI, port 8080, binds 0.0.0.0

# Web UI: http://<server-ip>:8080
# M3U:    http://<server-ip>:8000/api/livetv/m3u/all
# XMLTV:  http://<server-ip>:8000/api/livetv/xmltv/all
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

*Last Updated: 2026-02-23*
*Version: 0.5.0*
*Status: Phase 1 + Collections (1.5) complete — Phase 2 planning*
