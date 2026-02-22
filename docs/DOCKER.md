# Docker Deployment Guide

## Overview

JellyStream provides a complete Docker setup with two containers:

1. **API Backend** - FastAPI application (Python)
2. **Frontend** - PHP + Lighttpd web interface

Both containers communicate over a private Docker network.

## Quick Start

```bash
# 1. Configure
cp .env.example .env
nano .env  # Add your Jellyfin details

# 2. Build and start
docker-compose up -d

# 3. Access
# Frontend: http://localhost:8080
# API: http://localhost:8000/docs
```

## Architecture

```
Docker Compose Environment
├─ Frontend Container (Port 8080)
│  ├─ Lighttpd
│  ├─ PHP 8.1
│  └─ PHP Application
│
├─ API Container (Port 8000)
│  ├─ Python 3.11
│  ├─ FastAPI
│  └─ run.py launcher
│
└─ Shared Volumes
   ├─ data/ (database, media)
   └─ logs/ (application logs)
```

## Features

✅ **Lighttpd** - Lightweight web server with PHP support
✅ **Multi-container** - Separate API and frontend
✅ **Health checks** - Automatic container monitoring
✅ **Auto-restart** - Containers restart on failure
✅ **Persistent data** - Volumes for database and logs
✅ **Configurable ports** - Via environment variables
✅ **Private network** - Isolated container communication

## Management

### Start/Stop

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart frontend
docker-compose restart api
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f api
```

### Execute Commands

```bash
# Shell into API container
docker-compose exec api bash

# Shell into frontend container
docker-compose exec frontend sh

# Check PHP version
docker-compose exec frontend php -v
```

## Configuration

### Ports

Edit `.env`:

```env
PHP_PORT=8080    # Frontend port
PORT=8000        # Backend port
```

### Required Settings

```env
# Jellyfin connection (required)
JELLYFIN_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_api_key_here

# Public URL Jellyfin uses to reach JellyStream (must NOT be localhost)
JELLYSTREAM_PUBLIC_URL=http://192.168.1.100:8000
```

### Optional Settings

```env
# ISO 639-2 language code for preferred audio track (default: eng)
PREFERRED_AUDIO_LANGUAGE=eng

# Remap Jellyfin file paths to local paths (/jf/prefix:/local/prefix)
MEDIA_PATH_MAP=

# Scheduler (default: true)
SCHEDULER_ENABLED=true

# Logging
LOG_LEVEL=INFO
```
