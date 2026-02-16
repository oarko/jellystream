# JellyStream - Claude Context Document

## Project Overview

**JellyStream** is a media streaming integration for Jellyfin that creates virtual Live TV channels with scheduled programming from Jellyfin media libraries. It integrates with Jellyfin's Live TV system as a virtual tuner, providing M3U playlists and XMLTV EPG data.

### Key Features
- Create virtual streaming channels from Jellyfin libraries
- Schedule media playback with precise timing
- Integration with Jellyfin Live TV as virtual TunerHost
- M3U playlist generation for channel lineup
- XMLTV EPG (Electronic Program Guide) generation
- Hierarchical browsing of TV shows (Series → Season → Episode)
- User-configurable sorting and pagination
- RESTful API for automation
- Web interface for stream and schedule management

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python web framework)
- **Database**: SQLite with SQLAlchemy ORM (async via aiosqlite)
- **API Client**: aiohttp for Jellyfin integration
- **Python Version**: 3.11+ (tested on 3.13)

### Frontend
- **Web Server**: Lighttpd with FastCGI
- **Language**: PHP 8.x
- **Templating**: Jinja2 (for Python templates)
- **JavaScript**: Vanilla JS with async/await
- **CSS**: Custom styling

## Project Structure

```
jellystream/
├── app/
│   ├── api/              # API endpoints
│   │   ├── __init__.py   # Router registration
│   │   ├── streams.py    # Stream CRUD operations
│   │   ├── schedules.py  # Schedule management
│   │   ├── jellyfin.py   # Jellyfin integration endpoints
│   │   └── livetv.py     # Live TV integration (M3U/XMLTV)
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration management
│   │   ├── database.py   # Database initialization
│   │   └── logging_config.py
│   ├── integrations/     # External integrations
│   │   └── jellyfin.py   # JellyfinClient with full auth
│   ├── models/           # SQLAlchemy models
│   │   ├── stream.py     # Stream model with Live TV fields
│   │   └── schedule.py   # Schedule model
│   ├── utils/            # Utility functions
│   ├── web/              # Web interface
│   │   ├── php/          # PHP application
│   │   │   ├── includes/
│   │   │   │   └── api_client.php  # PHP API client
│   │   │   └── pages/
│   │   │       └── stream_edit_enhanced.php  # Stream editor
│   │   ├── static/       # CSS, JS, images
│   │   └── templates/    # Jinja2 templates
│   └── main.py           # Application entry point
├── config/               # Configuration files
├── data/                 # Runtime data
│   ├── commercials/      # Commercial videos
│   ├── database/         # SQLite database (auto-created)
│   └── logos/            # Channel logos
├── docs/                 # Documentation
│   └── API.md            # Comprehensive API documentation
├── tests/                # Test suite
├── setup.sh              # Automated setup script
├── start.sh              # Quick start script
└── run.py                # Application launcher
```

## Setup & Installation

### Automated Setup (Recommended)
```bash
./setup.sh
```

The setup script:
- Detects OS (optimized for Debian/Ubuntu)
- Installs python3-venv if needed
- Creates virtual environment
- Installs dependencies
- Sets up configuration

### Manual Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Jellyfin credentials
python run.py
```

## Issues Resolved During Development

### 1. SQLAlchemy Reserved Keyword: `metadata`
**Problem**: Used `metadata` as a column name in Schedule model, which is reserved by SQLAlchemy's Declarative API.

**Solution**: Renamed column to `extra_metadata` in the database model, but still expose it as `metadata` in API responses for backward compatibility.

**Files Changed**:
- `app/models/schedule.py` - Changed column name
- `app/api/schedules.py` - Updated to use `extra_metadata` internally

### 2. DateTime Defaults in Python 3.13
**Problem**: Using `datetime.utcnow` as default caused issues and is deprecated in Python 3.13.

**Solution**: Changed to use SQLAlchemy's `func.now()` for server-side timestamp defaults.

**Files Changed**:
- `app/models/stream.py` - Updated timestamp columns
- `app/models/schedule.py` - Updated timestamp columns

### 3. Missing greenlet Dependency
**Problem**: SQLAlchemy async engine requires `greenlet` library for coroutine support.

**Solution**: Added `greenlet==3.1.1` to requirements.txt.

### 4. Database Directory Not Created
**Problem**: SQLite couldn't create database file because parent directory didn't exist.

**Solution**: Modified `init_db()` to create directory structure automatically.

**File Changed**: `app/core/database.py`

### 5. Debian PEP 668 (externally-managed-environment)
**Problem**: Modern Debian/Ubuntu systems prevent system-wide pip installations.

**Solution**: Created automated setup script that installs python3-venv and creates isolated virtual environment.

**File Created**: `setup.sh`

### 6. Jellyfin Authentication Headers
**Problem**: Initial implementation only used `X-Emby-Token` header, but Jellyfin requires full MediaBrowser authentication with Client, Device, DeviceId, and Version information.

**Solution**: Updated JellyfinClient to construct proper authentication header matching Jellyfin's requirements.

**Files Changed**:
- `app/integrations/jellyfin.py` - Complete authentication header
- `app/core/config.py` - Added client configuration options
- `app/api/jellyfin.py` - Updated to pass all auth parameters
- `.env.example` - Added new configuration options

### 7. Jellyfin User ID Requirement
**Problem**: Jellyfin library endpoints require user ID. Initial implementation used `/Library/VirtualFolders` which doesn't provide CollectionType information.

**Solution**: Implemented user ID auto-detection and updated to use `/Users/{userId}/Views` endpoint. Added `JELLYFIN_USER_ID` configuration option with automatic detection if not set.

**Files Changed**:
- `app/integrations/jellyfin.py` - Added `ensure_user_id()` method, updated `get_libraries()`
- `app/api/jellyfin.py` - Added `GET /api/jellyfin/users` endpoint
- `app/core/config.py` - Added `JELLYFIN_USER_ID` setting
- `.env.example` - Added user ID configuration

### 8. Hierarchical TV Show Browsing
**Problem**: TV libraries have a hierarchy (Series → Season → Episode) that requires multiple API calls to navigate. Using `recursive=true` would return everything at once, causing performance issues.

**Solution**: Implemented level-by-level navigation with breadcrumbs, using `recursive=false` to fetch one level at a time. Added support for navigating into browsable items (Series, Season).

**Files Changed**:
- `app/api/jellyfin.py` - Added pagination and recursive parameters
- `app/integrations/jellyfin.py` - Updated `get_library_items()` with full parameter support
- `app/web/php/pages/stream_edit_enhanced.php` - Implemented hierarchical navigation

### 9. Pagination and Sorting
**Problem**: Large libraries need pagination. Users should be able to sort content in different ways.

**Solution**: Implemented pagination with configurable page sizes and user-selectable sorting (17 different sort options).

**Files Changed**:
- `app/api/jellyfin.py` - Added `limit`, `start_index`, `sort_by`, `sort_order` parameters
- `app/core/config.py` - Added `JELLYFIN_DEFAULT_PAGE_SIZE` and `JELLYFIN_MAX_PAGE_SIZE`
- `app/web/php/pages/stream_edit_enhanced.php` - Added sort controls and pagination UI

### 10. Live TV Integration Discovery
**Problem**: Initial design was to add streams to Jellyfin libraries, but Jellyfin Live TV uses TunerHosts and ListingProviders instead.

**Solution**: Pivoted to integrate with Jellyfin's Live TV system. Streams now register as M3U tuners with XMLTV EPG data. Added database fields to track Jellyfin registration IDs.

**Files Changed**:
- `app/models/stream.py` - Added `tuner_host_id`, `listing_provider_id`, `channel_number`
- `app/api/livetv.py` - Created new file with M3U/XMLTV endpoints
- `app/integrations/jellyfin.py` - Added Live TV registration methods
- `app/api/streams.py` - Updated responses to include Live TV fields

## Jellyfin/Emby Integration

### Important Context

Jellyfin is a fork of Emby and maintains API compatibility with Emby's MediaBrowser API. This is why:

1. **Authentication uses "MediaBrowser" token format** - Legacy from Emby
2. **Many endpoints use `/emby/` or Emby-style paths** - Still supported for compatibility
3. **Headers use `X-Emby-Token`** - Alternative to Authorization header in some cases

### Current Authentication Implementation

The JellyfinClient constructs authentication headers as:

```python
Authorization: MediaBrowser Token="api_key", Client="JellyStream", Device="JellyStream Server", DeviceId="uuid", Version="0.1.0"
```

This format is **required** for proper Jellyfin authentication. The API key alone is insufficient.

### Configuration Options

Set these in `.env`:
- `JELLYFIN_URL` - Server URL (required)
- `JELLYFIN_API_KEY` - API token (required)
- `JELLYFIN_USER_ID` - User ID for API requests (optional, auto-detected if empty)
- `JELLYFIN_CLIENT_NAME` - Application name (optional, default: "JellyStream")
- `JELLYFIN_DEVICE_NAME` - Device name (optional, default: "JellyStream Server")
- `JELLYFIN_DEVICE_ID` - Device UUID (optional, auto-generated if empty)
- `JELLYFIN_DEFAULT_PAGE_SIZE` - Default items per page (optional, default: 50)
- `JELLYFIN_MAX_PAGE_SIZE` - Maximum items per page (optional, default: 1000)

### User ID Auto-Detection

If `JELLYFIN_USER_ID` is not set, JellyfinClient will:
1. Call `/Users` endpoint to get all users
2. Use the first user's ID automatically
3. Cache the user ID for subsequent requests

### Hierarchical Content Navigation

For TV Shows (`CollectionType: "tvshows"`):
1. **Library Level**: Get all Series (recursive=false)
2. **Series Level**: Navigate into Series to get Seasons (parent_id=SeriesId, recursive=false)
3. **Season Level**: Navigate into Season to get Episodes (parent_id=SeasonId, recursive=false)

For Movies (`CollectionType: "movies"`):
- Single level, just fetch all movies from library

### Available Sort Options

Users can sort content by:
- SortName, Name, ProductionYear, PremiereDate, DateCreated, DatePlayed
- CommunityRating, CriticRating, OfficialRating, Runtime
- PlayCount, IsFavorite, IsUnplayed, Random
- SeriesSortName, VideoFrameRate, VideoBitRate, AirTime

Sort order: Ascending or Descending

### Available Jellyfin Endpoints

Currently implemented:
- `GET /api/jellyfin/users` - Get current user info
- `GET /api/jellyfin/libraries` - Get all libraries (views)
- `GET /api/jellyfin/items/{parent_id}` - Get items with pagination/sorting

Methods in JellyfinClient:
- `ensure_user_id()` - Auto-detect user ID if not configured
- `get_current_user()` - Get current user information
- `get_libraries()` - Fetch all user views/libraries
- `get_library_items(parent_id, recursive, limit, start_index, sort_by, sort_order, include_item_types)` - Fetch items with full control
- `get_item_info(item_id)` - Get metadata for specific item
- `get_stream_url(item_id)` - Construct streaming URL for item
- `register_tuner_host(url, friendly_name, ...)` - Register M3U tuner
- `unregister_tuner_host(tuner_host_id)` - Remove tuner
- `register_listing_provider(listing_provider_type, xmltv_url, ...)` - Register EPG provider
- `unregister_listing_provider(provider_id)` - Remove EPG provider

## Database Models

### Stream Model
```python
- id: Integer (primary key)
- name: String(255) - Stream/channel name
- description: Text - Optional description
- jellyfin_library_id: String(255) - Jellyfin library ID
- stream_url: String(512) - Stream URL (generated)
- enabled: Boolean - Whether stream is active
- tuner_host_id: String(255) - Jellyfin TunerHost ID (nullable)
- listing_provider_id: String(255) - Jellyfin ListingProvider ID (nullable)
- channel_number: String(10) - Virtual channel number (e.g., "100.1")
- created_at: DateTime (server default)
- updated_at: DateTime (server default, auto-update)
```

### Schedule Model
```python
- id: Integer (primary key)
- stream_id: Integer (foreign key to streams)
- title: String(255) - Media title
- media_item_id: String(255) - Jellyfin item ID
- scheduled_time: DateTime - When to play
- duration: Integer - Duration in seconds
- extra_metadata: Text - JSON metadata (exposed as "metadata" in API)
- created_at: DateTime (server default)
```

## API Endpoints

See [docs/API.md](docs/API.md) for comprehensive API documentation.

### Application
- `GET /` - Web interface (HTML)
- `GET /api` - API info (JSON)
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

### Streams
- `GET /api/streams/` - List all streams
- `GET /api/streams/{id}` - Get specific stream
- `POST /api/streams/` - Create new stream
- `PUT /api/streams/{id}` - Update stream
- `DELETE /api/streams/{id}` - Delete stream

### Schedules
- `GET /api/schedules/` - List all schedules
- `GET /api/schedules/{id}` - Get specific schedule
- `GET /api/schedules/stream/{stream_id}` - Get schedules for stream
- `POST /api/schedules/` - Create schedule
- `PUT /api/schedules/{id}` - Update schedule
- `DELETE /api/schedules/{id}` - Delete schedule

### Jellyfin Integration
- `GET /api/jellyfin/users` - Get current user
- `GET /api/jellyfin/libraries` - Get Jellyfin libraries
- `GET /api/jellyfin/items/{parent_id}` - Get library items (with pagination/sorting)

### Live TV Integration
- `GET /api/livetv/m3u/{stream_id}` - M3U playlist for stream
- `GET /api/livetv/m3u/all` - M3U playlist for all enabled streams
- `GET /api/livetv/xmltv/{stream_id}` - XMLTV EPG for stream
- `GET /api/livetv/xmltv/all` - XMLTV EPG for all enabled streams
- `GET /api/livetv/stream/{stream_id}` - Live stream endpoint (redirects to current media)

## Live TV Integration with Jellyfin

### How It Works

JellyStream registers with Jellyfin as a virtual Live TV source:

1. **TunerHost Registration**: Jellyfin adds JellyStream as an M3U tuner
   - Type: `m3utuner`
   - URL: `http://localhost:8000/api/livetv/m3u/all`
   - Provides channel lineup via M3U playlist

2. **ListingProvider Registration**: Jellyfin uses JellyStream for EPG data
   - Type: `xmltv`
   - Path: `http://localhost:8000/api/livetv/xmltv/all`
   - Provides program guide via XMLTV format

3. **Stream Playback**: When user plays a channel in Jellyfin Live TV:
   - Jellyfin requests M3U playlist from JellyStream
   - M3U points to `/api/livetv/stream/{stream_id}`
   - JellyStream checks current time and schedule
   - Redirects to appropriate Jellyfin media item stream URL

### M3U Playlist Format

```m3u
#EXTM3U
#EXTINF:-1 channel-id="1" channel-number="100.1" tvg-name="Classic Movies" tvg-id="1" group-title="JellyStream",100.1 Classic Movies
http://localhost:8000/api/livetv/stream/1
```

### XMLTV EPG Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="JellyStream">
  <channel id="1">
    <display-name>Classic Movies</display-name>
  </channel>
  <programme channel="1" start="20240101200000 +0000" stop="20240101225500 +0000">
    <title>The Godfather</title>
    <category>Movie</category>
  </programme>
</tv>
```

### Registration with Jellyfin

**TunerHost Registration** (POST to Jellyfin `/LiveTv/TunerHosts`):
```json
{
  "Type": "m3utuner",
  "Url": "http://localhost:8000/api/livetv/m3u/all",
  "UserAgent": "JellyStream",
  "FriendlyName": "JellyStream Virtual Tuner",
  "ImportFavoritesOnly": false,
  "AllowHWTranscoding": true,
  "EnableStreamLooping": false,
  "Source": "Other",
  "TunerCount": 10,
  "DeviceId": "jellystream-tuner"
}
```

**ListingProvider Registration** (POST to Jellyfin `/LiveTv/ListingProviders`):
```json
{
  "Type": "xmltv",
  "Path": "http://localhost:8000/api/livetv/xmltv/all",
  "ListingsId": "jellystream-epg"
}
```

After registration, store the returned IDs in the stream's `tuner_host_id` and `listing_provider_id` fields.

## Web Interface

### PHP Application Structure

The web interface is built with PHP and uses a custom API client to communicate with the FastAPI backend.

**Key Files**:
- `app/web/php/includes/api_client.php` - PHP API client with methods for all endpoints
- `app/web/php/pages/stream_edit_enhanced.php` - Stream editor with hierarchical browsing

### Stream Editor Features

1. **Hierarchical Content Browser**:
   - Breadcrumb navigation (Library → Series → Season → Episode)
   - Non-recursive API calls for efficient loading
   - Visual indicators for browsable items (Series, Season)

2. **Pagination Controls**:
   - Previous/Next buttons
   - Configurable page size (50, 100, 200, 500)
   - Current page indicator

3. **Sort Controls**:
   - 17 sort options in dropdown
   - Ascending/Descending toggle
   - Real-time content re-sorting

4. **Schedule Management**:
   - Visual timeline of scheduled content
   - Drag-and-drop scheduling (planned)
   - Add/edit/delete schedule entries
   - Duration display and editing

5. **Stream Configuration**:
   - Name, description, library selection
   - Channel number assignment
   - Enable/disable toggle

## Current State

### ✅ Completed
- [x] Project structure and directory layout
- [x] Core FastAPI application setup
- [x] Database models with Live TV fields
- [x] Automated setup script for Debian/Ubuntu
- [x] Full CRUD API endpoints for streams and schedules
- [x] Jellyfin client with proper authentication and user ID handling
- [x] Hierarchical content browsing with pagination
- [x] User-selectable sorting (17 options)
- [x] Live TV integration (M3U/XMLTV endpoints)
- [x] M3U playlist generation
- [x] XMLTV EPG data generation
- [x] Live stream endpoint with schedule-based playback
- [x] Web interface with stream editor
- [x] PHP API client
- [x] Breadcrumb navigation for TV shows
- [x] API documentation (Swagger/ReDoc)
- [x] Comprehensive documentation (API.md)
- [x] Health check endpoint
- [x] Docker support (Dockerfile, docker-compose.yml)

### 🚧 In Progress / Planned
- [ ] Schedule conflict detection
- [ ] Drag-and-drop schedule builder
- [ ] Commercial insertion functionality
- [ ] Logo overlay support
- [ ] Background scheduler for automatic schedule updates
- [ ] Real-time stream playback with ffmpeg
- [ ] Video processing (OpenCV integration)
- [ ] User authentication/authorization
- [ ] Database migrations (Alembic)
- [ ] Comprehensive test suite
- [ ] Channel preview/monitoring
- [ ] Schedule templates (e.g., "Weekend Movie Marathon")
- [ ] Multi-stream management dashboard

## Dependencies

### Core Dependencies
- `fastapi==0.115.0` - Web framework
- `uvicorn[standard]==0.32.0` - ASGI server
- `sqlalchemy==2.0.35` - ORM
- `aiosqlite==0.20.0` - Async SQLite driver
- `greenlet==3.1.1` - Async support for SQLAlchemy
- `pydantic-settings==2.6.1` - Settings management
- `aiohttp==3.11.2` - HTTP client for Jellyfin
- `jinja2==3.1.4` - Templating

### Future Use
- `apscheduler==3.10.4` - Background task scheduling
- `opencv-python==4.10.0.84` - Video processing
- `ffmpeg-python` - Stream transcoding/processing

## Running the Application

### Development
```bash
source venv/bin/activate
python run.py
# or
uvicorn app.main:app --reload
```

### Production
```bash
# Direct
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker
docker-compose up -d
```

### Access Points
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- M3U Playlist: http://localhost:8000/api/livetv/m3u/all
- XMLTV EPG: http://localhost:8000/api/livetv/xmltv/all

## Important Notes

### Python 3.13 Compatibility
The project has been tested on Python 3.13 (Debian testing). Key considerations:
- Use `func.now()` for database timestamps instead of `datetime.utcnow`
- Ensure `greenlet` is installed for async SQLAlchemy support

### Virtual Environment is Required
On Debian/Ubuntu systems, you **must** use a virtual environment due to PEP 668. The setup script handles this automatically.

### Database Auto-Creation
The database and required directories are created automatically on first run. No manual database setup is needed.

### Jellyfin API Key
To get a Jellyfin API key:
1. Open Jellyfin web interface
2. Go to Dashboard → API Keys
3. Click + to create new key
4. Copy to `.env` file

### Jellyfin User ID
If not specified in `.env`, the application will automatically detect and use the first available user ID from your Jellyfin server.

### API Routing Structure
The API uses prefix-based routing:
- Main app includes routers with `/api` prefix
- Individual routers have their own prefixes (e.g., `/streams`, `/schedules`)
- Final paths combine: `/api` + router prefix (e.g., `/api/streams/`)

## Testing

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# Get Jellyfin libraries
curl http://localhost:8000/api/jellyfin/libraries

# Get current user
curl http://localhost:8000/api/jellyfin/users

# Create a stream
curl -X POST "http://localhost:8000/api/streams/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Channel", "jellyfin_library_id": "abc123", "channel_number": "100.1"}'

# Get M3U playlist
curl http://localhost:8000/api/livetv/m3u/all

# Get XMLTV EPG
curl http://localhost:8000/api/livetv/xmltv/all
```

### Automated Tests
```bash
pytest
# or with coverage
pytest --cov=app --cov-report=html
```

## Next Steps / TODO

### High Priority
1. Implement drag-and-drop schedule builder in web UI
2. Add schedule conflict detection and warnings
3. Build background scheduler for automatic schedule management
4. Implement real-time stream playback with ffmpeg
5. Add channel preview functionality

### Medium Priority
6. Add user authentication and multi-user support
7. Implement commercial insertion functionality
8. Create logo overlay system
9. Add schedule templates (movie marathons, series binges)
10. Implement database migrations with Alembic
11. Create multi-stream dashboard view
12. Add schedule import/export (JSON, CSV)

### Low Priority
13. Add support for multiple Jellyfin servers
14. Implement DVR-style recording
15. Add metrics and analytics
16. Create mobile-responsive UI
17. Add webhook notifications for schedule events
18. Implement schedule auto-fill based on library content

## Useful Commands

```bash
# Setup
make setup          # Run setup.sh
make install        # Install dependencies
make install-dev    # Install dev dependencies

# Running
make run            # Start application
./start.sh          # Quick start with venv

# Development
make test           # Run tests
make test-cov       # Run tests with coverage
make format         # Format code with black
make lint           # Check code quality

# Docker
make docker-build   # Build Docker image
make docker-run     # Run in Docker
make docker-stop    # Stop Docker container
make docker-logs    # View Docker logs

# Cleanup
make clean          # Remove cache files
```

## References

- [Jellyfin API Documentation](https://api.jellyfin.org/)
- [Jellyfin Live TV Documentation](https://jellyfin.org/docs/general/server/live-tv/)
- [M3U Playlist Format](https://en.wikipedia.org/wiki/M3U)
- [XMLTV EPG Format](http://wiki.xmltv.org/index.php/XMLTVFormat)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Project Documentation](docs/)

## Development Environment

### Original Development Context
- **OS**: Kubuntu 25.10 (Questing Quokka)
- **Python**: 3.13
- **User**: oarko
- **Setup Method**: Automated setup.sh script

### Known Working Configuration
- Virtual environment in `venv/`
- SQLite database at `data/database/jellystream.db`
- Configuration in `.env` (not committed to git)
- Lighttpd web server for PHP interface (optional)

## Architecture Decisions

### Why Live TV Integration Instead of Library Integration?
After exploring the Jellyfin API, we discovered that Jellyfin's Live TV system is the appropriate integration point for virtual channels. This provides:
- Native channel guide (EPG) support in Jellyfin UI
- Seamless integration with Jellyfin's Live TV features
- Standard M3U/XMLTV format compatibility
- Better user experience (channels appear in Live TV section)

### Why Non-Recursive Hierarchical Navigation?
For large TV libraries, recursive API calls would return thousands of items at once, causing:
- Long load times
- High memory usage
- Poor user experience

Level-by-level navigation provides:
- Fast, responsive UI
- Efficient API usage
- Intuitive browsing experience
- Better pagination control

### Why PHP for Web Interface?
While the backend is Python/FastAPI, the web interface uses PHP because:
- Lightweight and fast for simple UI
- Easy integration with existing web servers (Lighttpd, Apache, Nginx)
- Separation of concerns (backend API vs frontend presentation)
- Flexibility for users to replace with any frontend framework

---

*Last Updated: 2026-02-15*
*Version: 0.2.0*
*Status: Active Development - Core functionality and Live TV integration complete, schedule management UI in progress*
