# Port Configuration Guide

## Overview

JellyStream uses two separate ports:
- **PHP Frontend Port** (default: 8080) - Web interface
- **API Backend Port** (default: 8000) - FastAPI REST API

Both ports are **fully configurable** to avoid conflicts with other services.

## Configuration Methods

### Method 1: Setup Wizard (Recommended)

1. Start the PHP frontend:
   ```bash
   ./start-php.sh
   ```

2. Visit the setup page:
   ```
   http://localhost:8080/setup.php
   ```

3. Scroll to **"Port Configuration"** section

4. Set your ports:
   - **PHP Frontend Port**: Port for the web interface (e.g., 8080, 8081, 3000)
   - **API Backend Port**: Port for the FastAPI backend (e.g., 8000, 8001, 5000)

5. Click "Save Configuration"

6. Restart both services

### Method 2: Manual Configuration

#### PHP Frontend Port

Edit `app/web/php/.phpconfig`:

```ini
PHP_FRONTEND_PORT=8080
API_BACKEND_PORT=8000
```

#### API Backend Port

Edit `.env`:

```env
PORT=8000
HOST=0.0.0.0
```

## Port Conflicts

### Common Port Conflicts

- **8000**: Often used by Django, other APIs
- **8080**: Common alternative HTTP port, used by many apps
- **3000**: React, Node.js development servers
- **5000**: Flask default port
- **9000**: PHP-FPM, other services

### Checking Port Availability

```bash
# Check if port is in use
sudo netstat -tulpn | grep :8000
# or
sudo lsof -i :8000

# Check what's using the port
ss -tulwn | grep LISTEN | grep 8000
```

### Suggested Alternative Ports

If defaults are taken, try these:

**For PHP Frontend:**
- 8081, 8082, 8888, 9080, 3000

**For API Backend:**
- 8001, 8002, 9000, 5000, 4000

## Starting with Custom Ports

### Start API Backend

The API backend reads from `.env`:

```bash
source venv/bin/activate
python run.py
# Uses PORT from .env
```

### Start PHP Frontend

The PHP script reads from `.phpconfig`:

```bash
./start-php.sh
# Automatically reads PHP_FRONTEND_PORT from .phpconfig
```

## Deployment Configurations

### Lighttpd

Edit `/etc/lighttpd/conf-available/99-jellystream.conf`:

```lighttpd
server.port = 8080  # Change to your PHP port

# Update API proxy port
$HTTP["url"] =~ "^/api/" {
    proxy.server = ( "" => (
        ( "host" => "127.0.0.1", "port" => 8000 )  # Change to your API port
    ))
}
```

### Nginx

```nginx
server {
    listen 8080;  # Change to your PHP port

    location /api {
        proxy_pass http://localhost:8000;  # Change to your API port
    }
}
```

### Apache

```apache
<VirtualHost *:8080>  # Change to your PHP port
    ProxyPass /api http://localhost:8000/api  # Change to your API port
    ProxyPassReverse /api http://localhost:8000/api
</VirtualHost>
```

## Firewall Configuration

### Allow Custom Ports

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 8080/tcp
sudo ufw allow 8000/tcp
```

**firewalld (Fedora/RHEL):**
```bash
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

**iptables:**
```bash
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

## Reverse Proxy Setup

### Single Port Access

Use a reverse proxy to access both services on one port:

**Nginx Example:**
```nginx
server {
    listen 80;
    server_name jellystream.local;

    # PHP Frontend (root)
    location / {
        proxy_pass http://localhost:8080;
    }

    # API Backend (/api)
    location /api {
        proxy_pass http://localhost:8000/api;
    }
}
```

Now access both through port 80:
- Frontend: http://jellystream.local/
- API: http://jellystream.local/api

## Docker Port Mapping

If using Docker, map ports in `docker-compose.yml`:

```yaml
services:
  jellystream:
    ports:
      - "8000:8000"  # API Backend
      - "8080:8080"  # PHP Frontend
```

Or use custom host ports:

```yaml
services:
  jellystream:
    ports:
      - "5000:8000"  # API on host port 5000
      - "3000:8080"  # PHP on host port 3000
```

## Environment Variables

### All Port-Related Settings

**`.env` (Backend):**
```env
HOST=0.0.0.0        # Listen on all interfaces
PORT=8000           # API backend port
```

**`.phpconfig` (Frontend):**
```ini
PHP_FRONTEND_PORT=8080  # PHP frontend port
API_BACKEND_PORT=8000   # API backend port (for API client)
```

## Troubleshooting

### "Address already in use"

**Find what's using the port:**
```bash
sudo lsof -i :8000
```

**Kill the process:**
```bash
sudo kill <PID>
```

**Or change your port** using the setup wizard or manual configuration.

### "Connection refused" to API

1. Check API is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check `.phpconfig` has correct API_BACKEND_PORT

3. Check firewall isn't blocking the port

### PHP Frontend not accessible

1. Check lighttpd/Apache/Nginx is running
2. Verify server.port matches PHP_FRONTEND_PORT
3. Check firewall rules
4. Review error logs

## Best Practices

1. **Use high ports (>1024)** to avoid needing root
2. **Document your ports** in a README or config file
3. **Use reverse proxy** for production (single port access)
4. **Keep ports consistent** across environments (dev, staging, prod)
5. **Update firewall** rules when changing ports
6. **Test after changes** - verify both services accessible

## Quick Reference

### Default Ports
- PHP Frontend: **8080**
- API Backend: **8000**
- Jellyfin: **8096**

### Configuration Files
- API Port: `.env` → `PORT=8000`
- PHP Port: `.phpconfig` → `PHP_FRONTEND_PORT=8080`
- PHP API Client: `.phpconfig` → `API_BACKEND_PORT=8000`

### Check Configuration
```bash
# View current PHP config
cat app/web/php/.phpconfig

# View current API config
grep PORT .env

# Test connectivity
curl http://localhost:8080  # PHP
curl http://localhost:8000/health  # API
```

---

**Note:** Always restart services after changing port configuration!
