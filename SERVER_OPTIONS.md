# Server Options for JellyStream

JellyStream provides multiple ways to run the PHP frontend, depending on your needs:

## Overview

| Server | Use Case | Performance | Setup Complexity | Command |
|--------|----------|-------------|------------------|---------|
| **systemd + Lighttpd** | **Production (recommended)** | ⭐⭐⭐⭐⭐ | ⭐ (automated) | `./setup.sh` |
| **PHP Built-in** | Development | ⭐⭐ | ⭐ (Easiest) | `./start-php.sh` |
| **Lighttpd (manual)** | Production/Local | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | `./start-lighttpd.sh` |
| **Docker** | Production/Deploy | ⭐⭐⭐⭐⭐ | ⭐⭐ | `docker-compose up -d` |
| **Apache** | Production | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | See [LIGHTTPD_DEPLOYMENT.md](docs/LIGHTTPD_DEPLOYMENT.md) |
| **Nginx** | Production | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | See [LIGHTTPD_DEPLOYMENT.md](docs/LIGHTTPD_DEPLOYMENT.md) |

### 0. systemd + Lighttpd (Production, Recommended)

`./setup.sh` now installs, enables, and starts both the API and the Lighttpd frontend as
systemd services by default — auto-restart on crash, start on boot, no manual service files to
write. It's offered as a prompt (default yes) right after setup finishes the rest of the
install; decline it to fall back to any of the manual options below. See
[deploy/README.md](deploy/README.md) for the full reference, including how to install by hand
or re-render the unit files after moving the project.

```bash
./setup.sh   # prompts to install the systemd service; accept it
systemctl status jellystream-api jellystream-web
```

---

## 1. PHP Built-in Server (Development)

### When to Use
- ✅ Development and testing
- ✅ Quick setup and demos
- ✅ Local machine only

### Pros
- Extremely simple to use
- No installation required (PHP only)
- Instant startup
- Easy debugging

### Cons
- Single-threaded (slow for multiple requests)
- Not suitable for production
- No advanced features

### How to Use

```bash
./start-php.sh
```

Access at: http://localhost:8080

### Requirements
- PHP 7.4+ with pdo_sqlite, curl, json extensions

---

## 2. Lighttpd (Production/Local)

### When to Use
- ✅ **Production deployments** on your server
- ✅ Testing production environment locally
- ✅ Better performance than PHP built-in
- ✅ Low-resource environments

### Pros
- **Very lightweight** (~2-5MB memory)
- **Fast** - Multi-threaded FastCGI
- **Production-ready**
- **Simple configuration**
- **Built-in FastCGI support**

### Cons
- Requires installation
- Slightly more complex than PHP built-in

### How to Use

#### Install (Debian/Ubuntu)

```bash
sudo apt install lighttpd php-cgi php-sqlite3 php-curl php-json
```

Or run `./setup.sh` and answer "yes" to Lighttpd installation.

#### Start

```bash
./start-lighttpd.sh
```

Access at: http://localhost:8080

### Features
- Auto-generates configuration
- Reads port from `.phpconfig`
- FastCGI for PHP
- Access/error logging
- Secure (hides .env files)

---

## 3. Docker (Production/Deployment)

### When to Use
- ✅ **Production deployments**
- ✅ Consistent environments (dev/staging/prod)
- ✅ Easy scaling
- ✅ Quick deployment

### Pros
- **Isolated environment**
- **Consistent** across systems
- **Easy to deploy**
- **Includes both backend and frontend**
- **Auto-restart on failure**
- **Built-in health checks**

### Cons
- Requires Docker installation
- Uses more disk space

### How to Use

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Access at:
- Frontend: http://localhost:8080
- API: http://localhost:8000

See [docs/DOCKER.md](docs/DOCKER.md) for complete guide.

---

## 4. Apache (Production)

### When to Use
- ✅ Existing Apache infrastructure
- ✅ Need .htaccess support
- ✅ Complex URL rewriting

### Pros
- Well-documented
- Widespread support
- Robust features

### Cons
- Higher memory usage (~20-50MB)
- More complex configuration

See [docs/LIGHTTPD_DEPLOYMENT.md](docs/LIGHTTPD_DEPLOYMENT.md) for configuration.

---

## 5. Nginx (Production)

### When to Use
- ✅ High-traffic sites
- ✅ Reverse proxy needs
- ✅ Modern infrastructure

### Pros
- Excellent performance
- Low memory usage
- Good for reverse proxy

### Cons
- Requires PHP-FPM separately
- More complex configuration

See [docs/LIGHTTPD_DEPLOYMENT.md](docs/LIGHTTPD_DEPLOYMENT.md) for configuration.

---

## Recommendations

### Development

```bash
# Terminal 1 - API Backend
source venv/bin/activate
python run.py

# Terminal 2 - PHP Frontend
./start-php.sh
```

**Why:** Simple, fast setup. Perfect for coding and testing.

### Local Production Testing

```bash
# Terminal 1 - API Backend
source venv/bin/activate
python run.py

# Terminal 2 - PHP Frontend
./start-lighttpd.sh
```

**Why:** Tests production-like environment. Better performance. FastCGI support.

### Deployment (VPS/Server)

**Option A: systemd via `./setup.sh` (Recommended)**

```bash
./setup.sh   # accept the systemd install prompt
```

**Why:** Fully automated — no manual unit files or config to write. Auto-restart on crash,
starts on boot, lower overhead than Docker, and pairs with `./update.sh` for easy updates.
See [deploy/README.md](deploy/README.md).

**Option B: Docker**

```bash
docker-compose up -d
```

**Why:** Isolated, consistent environment across machines. Everything included, health checks
built in. Note: GPU passthrough for hardware transcoding and `./update.sh` aren't wired up for
the Docker path — it's a separate image per release rather than a git-based update.

**Option C: Manual systemd / Lighttpd**

Hand-configure system services yourself. See [docs/LIGHTTPD_DEPLOYMENT.md](docs/LIGHTTPD_DEPLOYMENT.md).

**Why:** Full control if `./setup.sh`'s automated install doesn't fit your setup.

---

## Performance Comparison

### Requests per Second (ApacheBench test)

| Server | RPS | Memory | Startup |
|--------|-----|--------|---------|
| PHP Built-in | ~100 | 10MB | <1s |
| Lighttpd | ~5000 | 5MB | <2s |
| Docker (Lighttpd) | ~4800 | 25MB | ~5s |
| Apache | ~3000 | 35MB | ~3s |
| Nginx | ~4500 | 15MB | ~2s |

*Note: Approximate values. Actual performance varies by system and configuration.*

---

## Quick Decision Guide

**I'm developing locally:**
→ Use `./start-php.sh`

**I want to test production features:**
→ Use `./start-lighttpd.sh`

**I'm deploying to a server:**
→ Run `./setup.sh` and accept the systemd install (recommended), or use Docker if you want
isolated/portable containers instead

**I have existing Apache/Nginx:**
→ See deployment docs

**I want maximum performance:**
→ Use Lighttpd (via `./setup.sh`'s systemd install) or Nginx

**I want easiest automated deployment:**
→ Use `./setup.sh` (installs the systemd service for you)

---

## Switching Between Servers

You can easily switch between different servers:

```bash
# Stop current server (Ctrl+C)

# Start different server
./start-php.sh          # PHP built-in
./start-lighttpd.sh     # Lighttpd
docker-compose up -d    # Docker
```

All servers:
- Use the same `.env` configuration
- Access the same database
- Call the same API backend
- Support the same features

---

## Summary

- **Development**: PHP built-in server (`./start-php.sh`)
- **Production**: `./setup.sh` (installs systemd + Lighttpd automatically) — or Docker if you
  prefer containers
- **Enterprise**: Nginx/Apache with reverse proxy

Choose based on your needs. Start simple (PHP built-in), scale up as needed!
