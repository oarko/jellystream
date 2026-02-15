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
│  └─ Uvicorn
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
API_PORT=8000    # Backend port
PORT=8000        # Backend internal port
```

See complete guide: [PORT_CONFIGURATION.md](../PORT_CONFIGURATION.md)

### Complete Documentation

See [docs/DOCKER.md](DOCKER.md) for:
- Detailed setup instructions
- Production deployment
- Troubleshooting
- Best practices
- Development mode
- Backup/restore procedures
