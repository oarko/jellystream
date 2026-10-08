# Setup Guide

This is the fully-manual, step-by-step walkthrough. For the automated path (recommended —
handles the venv, dependencies, `.env`, and optionally installs JellyStream as a systemd
service for you), run `./setup.sh` instead and see the main [README](../README.md) or
[INSTALL.md](../INSTALL.md).

## Prerequisites

- Python 3.11 or higher
- Jellyfin server (9.0 or higher recommended)
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/oarko/jellystream.git
cd jellystream
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

### 4. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and configure your Jellyfin connection. Minimum required:

```env
JELLYFIN_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_api_key_here

# Network address Jellyfin uses to reach JellyStream (must NOT be localhost)
JELLYSTREAM_PUBLIC_URL=http://192.168.1.100:8000
```

Optional settings worth knowing:

```env
# ISO 639-2 language code — preferred audio track for the stream proxy
PREFERRED_AUDIO_LANGUAGE=eng

# Remap Jellyfin file paths to local paths (format: /jf/prefix:/local/prefix)
# Leave empty if JellyStream and Jellyfin share the same file paths
MEDIA_PATH_MAP=
```

#### Getting a Jellyfin API Key

1. Log into your Jellyfin server
2. Go to Dashboard → API Keys
3. Click "+" to create a new API key
4. Give it a name (e.g., "JellyStream")
5. Copy the generated key to your `.env` file

### 5. Initialize Database

The database will be automatically created when you first run the application.

### 6. Run the Application

```bash
python run.py
```

The application will be available at: http://localhost:8000

## Docker Setup

### Using Docker Compose (Recommended)

1. Configure your `.env` file as described above

2. Build and run:

```bash
docker-compose up -d
```

3. View logs:

```bash
docker-compose logs -f
```

4. Stop the container:

```bash
docker-compose down
```

### Using Docker Directly

JellyStream builds as **two** images — API and PHP frontend — not a single combined one, so
`docker build -t jellystream .` won't work as-is. Use `docker-compose` (above) unless you have
a specific reason to run the containers individually:

```bash
docker build -t jellystream-api -f docker/Dockerfile.api .
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  --name jellystream-api \
  jellystream-api
```

See [docs/DOCKER.md](DOCKER.md) for the frontend container and the full two-container setup.

## Verification

1. Check the health endpoint:

```bash
curl http://localhost:8000/health
```

2. Visit the API documentation:

```
http://localhost:8000/docs
```

3. Test Jellyfin connection:

```bash
curl http://localhost:8000/api/jellyfin/libraries
```

## Troubleshooting

### Database Issues

If you encounter database issues, try deleting and recreating:

```bash
rm -rf data/database/jellystream.db
python run.py  # Will recreate the database
```

### Jellyfin Connection Issues

- Verify your Jellyfin server is accessible
- Check that the API key is correct
- Ensure there are no firewall issues
- Try accessing Jellyfin URL from the machine running JellyStream

### Port Already in Use

If port 8000 is already in use, change the PORT in your `.env` file:

```env
PORT=8001
```

## Next Steps

- Read the [API Documentation](API.md)
- Open the web interface at `http://localhost:8000` and create your first channel
- Assign Jellyfin libraries and genre filters to the channel
- Let JellyStream auto-generate a 7-day schedule
- Register the M3U and XMLTV URLs with Jellyfin Live TV
- To update later (git installs only): `./update.sh` — see the **Updates** page in the web UI
  or [deploy/README.md](../deploy/README.md)
