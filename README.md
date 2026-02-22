# JellyStream

A virtual TV channel generator built on top of Jellyfin. JellyStream creates 24/7 streaming channels with persistent, genre-based schedules, generates M3U playlists and XMLTV EPG data, and proxies video through ffmpeg with time-offset support — so viewers always tune in mid-show at the correct position, just like a real TV channel.

## How It Works

1. Create a **Channel** and assign one or more Jellyfin libraries to it
2. Add **genre filters** to include only matching content (and optionally exclude genres)
3. JellyStream **auto-generates a 7-day schedule** from matching Jellyfin items
4. The schedule is **persistent** — the same content plays at the same time on every device
5. Point Jellyfin Live TV (or any IPTV player) at the M3U and XMLTV endpoints
6. When a viewer tunes in, ffmpeg **seeks to the correct time offset** — no restarting from the beginning
7. A **background scheduler** (APScheduler) runs nightly to keep schedules 48+ hours ahead

## Features

- **Genre-based auto-scheduling** — fills 7 days forward from Jellyfin content matching your genre filters
- **Genre include/exclude** — include genres you want, exclude genres you don't (e.g. Action channel that excludes Animation)
- **Multiple libraries per channel** — mix Movies and TV Shows on one channel
- **Persistent EPG** — schedules stored in SQLite; same time slot = same content regardless of viewer
- **M3U + XMLTV endpoints** — 3-hour lookback, 7-day forward window for full EPG coverage
- **ffmpeg stream proxy with time-offset** — `-ss` seek so viewers join at the correct position
- **Preferred audio language** — configurable ISO 639-2 code (e.g. `eng`, `jpn`); falls back to first track
- **Jellyfin Live TV registration** — register the M3U tuner and XMLTV listing provider directly from the UI
- **APScheduler background job** — daily 2 AM job extends schedules for channels running low
- **Web interface** — PHP + Lighttpd frontend for managing channels and viewing schedules
- **Comprehensive logging** — daily rotating log files with configurable level

## Prerequisites

- Python 3.11+
- [Jellyfin](https://jellyfin.org/) server with API key
- **ffmpeg** and **ffprobe** (required for stream proxy and audio language detection)
- PHP 8.x + Lighttpd (for the web interface; included in Docker)

## Quick Start

### Automated Setup (Recommended)

```bash
git clone <repository-url>
cd jellystream
./setup.sh
```

`setup.sh` will:
- Install system packages (python3-venv, ffmpeg on Debian/Ubuntu)
- Create a virtual environment and install Python dependencies
- Copy `.env.example` → `.env` and prompt for Jellyfin URL and API key

Then start the application:

```bash
./start.sh
```

### Manual Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set JELLYFIN_URL and JELLYFIN_API_KEY at minimum
python3 run.py
```

### Docker

```bash
cp .env.example .env
# Edit .env with your Jellyfin details
docker compose up -d
```

The API is on port `8000`, the web interface on port `8080`.

## Configuration

Copy `.env.example` to `.env` and set the values for your environment. Minimum required:

```env
JELLYFIN_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_api_key_here
JELLYSTREAM_PUBLIC_URL=http://your-jellystream-host:8000  # must be reachable by Jellyfin
```

Key optional settings:

| Variable | Default | Description |
|---|---|---|
| `PREFERRED_AUDIO_LANGUAGE` | `eng` | ISO 639-2 code for preferred audio track (`eng`, `jpn`, `fre`, …) |
| `MEDIA_PATH_MAP` | _(empty)_ | Remap Jellyfin file paths for direct local access (`/jf/prefix:/local/prefix`) |
| `SCHEDULER_ENABLED` | `True` | Enable/disable the nightly schedule-extension job |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |

See `.env.example` for the full list.

## Access Points

Once running:

| URL | Description |
|---|---|
| `http://localhost:8000/` | Web interface (served via PHP/Lighttpd on port 8080 in Docker) |
| `http://localhost:8000/docs` | Swagger API documentation |
| `http://localhost:8000/api/livetv/m3u/all` | M3U playlist (all channels) |
| `http://localhost:8000/api/livetv/xmltv/all` | XMLTV EPG (all channels) |
| `http://localhost:8000/api/livetv/stream/{id}` | Live stream for channel `{id}` |

## Project Structure

```
jellystream/
├── app/
│   ├── api/              # FastAPI route handlers
│   │   ├── channels.py       # Channel CRUD (JSON body, Pydantic)
│   │   ├── schedules.py      # Schedule entries + "now playing"
│   │   ├── livetv.py         # M3U, XMLTV, stream proxy route
│   │   ├── jellyfin.py       # Jellyfin library/genre browser
│   │   └── schemas.py        # Pydantic request/response models
│   ├── core/             # Config, database init, logging
│   ├── integrations/     # JellyfinClient (auth, items, stream URL)
│   ├── models/           # SQLAlchemy models
│   │   ├── channel.py
│   │   ├── channel_library.py
│   │   ├── genre_filter.py
│   │   └── schedule_entry.py
│   ├── services/         # Business logic
│   │   ├── schedule_generator.py  # Genre-based 7-day schedule builder
│   │   ├── stream_proxy.py        # ffmpeg proxy with time-offset + language selection
│   │   └── scheduler.py           # APScheduler daily job
│   └── web/
│       └── php/          # Lighttpd + PHP web interface
├── data/
│   ├── database/         # SQLite database (auto-created)
│   ├── commercials/      # (reserved for future filler content)
│   └── logos/            # (reserved for future channel logos)
├── docker/               # Docker build files
├── docs/                 # API documentation
├── logs/                 # Rotating log files (auto-created)
├── .env.example          # Configuration template
├── docker-compose.yml
├── requirements.txt
├── run.py                # Application launcher
├── setup.sh              # Automated setup script
└── start.sh              # Quick start with venv activation
```

## Registering with Jellyfin Live TV

1. In the JellyStream web UI, open a channel and click **Register with Jellyfin Live TV**
2. Enter the public JellyStream URL (must be reachable from the Jellyfin server, e.g. `http://192.168.1.100:8000`)
3. JellyStream registers a single M3U tuner and XMLTV listing provider in Jellyfin — all channels are covered by one registration
4. In Jellyfin → Dashboard → Live TV, refresh the guide and all JellyStream channels will appear

## Planned (not yet implemented)

- Filler content: commercials, bumpers, static images between shows
- Channel logo watermark (ffmpeg overlay)
- Episode/movie deselection per channel
- Holiday schedule overrides
- User authentication for the web interface

## API Documentation

Interactive Swagger docs are available at `http://localhost:8000/docs` when the server is running. See [docs/API.md](docs/API.md) for static documentation.

## License

MIT License
