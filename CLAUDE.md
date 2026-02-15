# JellyStream - Claude Context Document

## Project Overview

**JellyStream** is a media streaming integration for Jellyfin that allows users to create custom streaming channels with scheduled programming from their Jellyfin libraries. Think of it as creating your own "TV channels" from your media collection.

### Key Features
- Create virtual streaming channels from Jellyfin libraries
- Schedule media playback with precise timing
- Support for commercials and station logos
- RESTful API for automation
- Web interface for management

## Technology Stack

- **Framework**: FastAPI (async Python web framework)
- **Database**: SQLite with SQLAlchemy ORM (async via aiosqlite)
- **Templating**: Jinja2
- **API Client**: aiohttp for Jellyfin integration
- **Python Version**: 3.11+ (tested on 3.13)

## Project Structure

```
jellystream/
├── app/
│   ├── api/              # API endpoints (streams, schedules, jellyfin)
│   ├── core/             # Core functionality (config, database)
│   ├── integrations/     # External integrations (Jellyfin client)
│   ├── models/           # SQLAlchemy models (Stream, Schedule)
│   ├── utils/            # Utility functions
│   ├── web/              # Web interface (static files, templates)
│   └── main.py           # Application entry point
├── config/               # Configuration files
├── data/                 # Runtime data
│   ├── commercials/      # Commercial videos
│   ├── database/         # SQLite database (auto-created)
│   └── logos/            # Channel logos
├── docs/                 # Documentation
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
- `JELLYFIN_CLIENT_NAME` - Application name (optional, default: "JellyStream")
- `JELLYFIN_DEVICE_NAME` - Device name (optional, default: "JellyStream Server")
- `JELLYFIN_DEVICE_ID` - Device UUID (optional, auto-generated if empty)

### Available Jellyfin Endpoints

Currently implemented:
- `GET /api/jellyfin/libraries` - Get all libraries
- `GET /api/jellyfin/items/{library_id}` - Get items from library

Methods in JellyfinClient:
- `get_libraries()` - Fetch all virtual folders
- `get_library_items(library_id)` - Fetch items from specific library
- `get_item_info(item_id)` - Get metadata for specific item
- `get_stream_url(item_id)` - Construct streaming URL for item

## Database Models

### Stream Model
```python
- id: Integer (primary key)
- name: String(255) - Stream/channel name
- description: Text - Optional description
- jellyfin_library_id: String(255) - Jellyfin library ID
- stream_url: String(512) - Stream URL (generated)
- enabled: Boolean - Whether stream is active
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
- `DELETE /api/streams/{id}` - Delete stream

### Schedules
- `GET /api/schedules/` - List all schedules
- `GET /api/schedules/{id}` - Get specific schedule

### Jellyfin Integration
- `GET /api/jellyfin/libraries` - Get Jellyfin libraries
- `GET /api/jellyfin/items/{library_id}` - Get library items

## Current State

### ✅ Completed
- [x] Project structure and directory layout
- [x] Core FastAPI application setup
- [x] Database models and async SQLAlchemy integration
- [x] Automated setup script for Debian/Ubuntu
- [x] API endpoints for streams and schedules
- [x] Jellyfin client with proper authentication
- [x] Web interface scaffolding
- [x] API documentation (Swagger/ReDoc)
- [x] Health check endpoint
- [x] Docker support (Dockerfile, docker-compose.yml)
- [x] Comprehensive documentation

### 🚧 In Progress / Not Yet Implemented
- [ ] Stream scheduling logic
- [ ] Commercial insertion functionality
- [ ] Logo overlay support
- [ ] Background scheduler (APScheduler integration)
- [ ] Video processing (OpenCV integration)
- [ ] Full web UI (currently basic template)
- [ ] Stream playback endpoints
- [ ] User authentication/authorization
- [ ] Database migrations (Alembic)
- [ ] Comprehensive test suite

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

## Testing

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# Get Jellyfin libraries (requires configured .env)
curl http://localhost:8000/api/jellyfin/libraries

# Create a stream
curl -X POST "http://localhost:8000/api/streams/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Channel", "jellyfin_library_id": "abc123"}'
```

### Automated Tests
```bash
pytest
# or with coverage
pytest --cov=app --cov-report=html
```

## Next Steps / TODO

### High Priority
1. Implement stream playback logic
2. Build scheduler for timed content rotation
3. Create functional web UI for stream management
4. Add commercial insertion functionality
5. Implement database migrations with Alembic

### Medium Priority
6. Add user authentication
7. Implement logo overlay system
8. Create playlist management
9. Add support for multiple output formats
10. Implement error logging and monitoring

### Low Priority
11. Add support for multiple Jellyfin servers
12. Create channel guide/EPG
13. Add support for live TV passthrough
14. Implement DVR-style recording
15. Add metrics and analytics

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

---

*Last Updated: 2026-02-15*
*Version: 0.1.0*
*Status: Initial Development - Core functionality complete, scheduling logic pending*
