# Lighttpd Deployment Guide

## Why Lighttpd?

Lighttpd is an excellent choice for JellyStream PHP frontend deployment:

- ✅ **Lightweight** - Low memory footprint (~2-5MB)
- ✅ **Fast** - Optimized for speed
- ✅ **Simple** - Easy configuration
- ✅ **Built-in FastCGI** - Native PHP support
- ✅ **Efficient** - Great for embedded systems/low-resource servers

## Installation

### Debian/Ubuntu

```bash
sudo apt update
sudo apt install lighttpd php-cgi php-sqlite3 php-curl php-json
```

### Enable required modules

```bash
sudo lighttpd-enable-mod fastcgi
sudo lighttpd-enable-mod fastcgi-php
sudo systemctl restart lighttpd
```

## Configuration

### 1. Basic Lighttpd Configuration

Create `/etc/lighttpd/conf-available/99-jellystream.conf`:

```lighttpd
# JellyStream Lighttpd Configuration

server.document-root = "/path/to/jellystream/app/web/php"
server.port = 8080

# Logging
server.errorlog = "/var/log/lighttpd/jellystream-error.log"
accesslog.filename = "/var/log/lighttpd/jellystream-access.log"

# Index files
index-file.names = ( "index.php", "index.html" )

# PHP FastCGI
fastcgi.server = ( ".php" =>
    ((
        "bin-path" => "/usr/bin/php-cgi",
        "socket" => "/var/run/lighttpd/php.socket",
        "max-procs" => 2,
        "bin-environment" => (
            "PHP_FCGI_CHILDREN" => "4",
            "PHP_FCGI_MAX_REQUESTS" => "1000"
        ),
        "bin-copy-environment" => (
            "PATH", "SHELL", "USER"
        ),
        "broken-scriptfilename" => "enable"
    ))
)

# URL Rewriting (if needed)
url.rewrite-if-not-file = (
    "^/api/(.*)$" => "/api/$1"
)

# Proxy API requests to FastAPI backend
$HTTP["url"] =~ "^/api/" {
    proxy.server = ( "" => (
        ( "host" => "127.0.0.1", "port" => 8000 )
    ))
}
```

### 2. Enable the Configuration

```bash
sudo ln -s /etc/lighttpd/conf-available/99-jellystream.conf /etc/lighttpd/conf-enabled/
sudo systemctl restart lighttpd
```

### 3. Set Permissions

```bash
sudo chown -R www-data:www-data /path/to/jellystream/app/web/php
sudo chmod -R 755 /path/to/jellystream/app/web/php
sudo chmod 775 /path/to/jellystream/data
```

## Alternative: Minimal Configuration

For development or simpler setups, create `/etc/lighttpd/lighttpd.conf`:

```lighttpd
server.modules = (
    "mod_fastcgi",
    "mod_accesslog"
)

server.document-root = "/path/to/jellystream/app/web/php"
server.upload-dirs = ( "/var/cache/lighttpd/uploads" )
server.errorlog = "/var/log/lighttpd/error.log"
server.pid-file = "/run/lighttpd.pid"
server.username = "www-data"
server.groupname = "www-data"
server.port = 8080

index-file.names = ( "index.php", "index.html" )

mimetype.assign = (
    ".html" => "text/html",
    ".txt" => "text/plain",
    ".jpg" => "image/jpeg",
    ".png" => "image/png",
    ".css" => "text/css",
    ".js" => "application/javascript"
)

fastcgi.server = ( ".php" =>
    ((
        "bin-path" => "/usr/bin/php-cgi",
        "socket" => "/tmp/php.socket",
        "max-procs" => 1
    ))
)
```

## Running Both Services

### Method 1: SystemD Services

Create `/etc/systemd/system/jellystream-api.service`:

```ini
[Unit]
Description=JellyStream FastAPI Backend
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/jellystream
Environment="PATH=/path/to/jellystream/venv/bin"
ExecStart=/path/to/jellystream/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable jellystream-api
sudo systemctl start jellystream-api
sudo systemctl enable lighttpd
sudo systemctl start lighttpd
```

### Method 2: Supervisor

Install supervisor:

```bash
sudo apt install supervisor
```

Create `/etc/supervisor/conf.d/jellystream.conf`:

```ini
[program:jellystream-api]
command=/path/to/jellystream/venv/bin/python run.py
directory=/path/to/jellystream
user=your-user
autostart=true
autorestart=true
stderr_logfile=/var/log/jellystream-api.err.log
stdout_logfile=/var/log/jellystream-api.out.log

[program:lighttpd]
command=/usr/sbin/lighttpd -D -f /etc/lighttpd/lighttpd.conf
autostart=true
autorestart=true
stderr_logfile=/var/log/lighttpd-supervisor.err.log
stdout_logfile=/var/log/lighttpd-supervisor.out.log
```

Reload supervisor:

```bash
sudo supervisorctl reloadstart jellystream-api
sudo supervisorctl start lighttpd
```

## Port Configuration

### Change PHP Frontend Port

Edit setup wizard at http://localhost:8080/setup.php or manually edit:

`app/web/php/.phpconfig`:
```ini
PHP_FRONTEND_PORT=8080
API_BACKEND_PORT=8000
```

### Change API Backend Port

Edit `.env`:
```env
PORT=8000
```

Then update Lighttpd proxy configuration to match.

## Performance Tuning

### For Low-Resource Environments

```lighttpd
# Reduce processes
fastcgi.server = ( ".php" =>
    ((
        "bin-path" => "/usr/bin/php-cgi",
        "socket" => "/tmp/php.socket",
        "max-procs" => 1,
        "bin-environment" => (
            "PHP_FCGI_CHILDREN" => "2",
            "PHP_FCGI_MAX_REQUESTS" => "500"
        )
    ))
)

# Connection limits
server.max-connections = 100
server.max-keep-alive-requests = 50
```

### For High-Traffic Sites

```lighttpd
# Increase processes
fastcgi.server = ( ".php" =>
    ((
        "bin-path" => "/usr/bin/php-cgi",
        "socket" => "/tmp/php.socket",
        "max-procs" => 4,
        "bin-environment" => (
            "PHP_FCGI_CHILDREN" => "8",
            "PHP_FCGI_MAX_REQUESTS" => "10000"
        )
    ))
)

# Higher limits
server.max-connections = 1024
server.max-keep-alive-requests = 100
```

## SSL/TLS Configuration

For HTTPS support:

```lighttpd
$SERVER["socket"] == ":443" {
    ssl.engine = "enable"
    ssl.pemfile = "/etc/lighttpd/ssl/jellystream.pem"
    ssl.ca-file = "/etc/lighttpd/ssl/ca.crt"
}

# Redirect HTTP to HTTPS
$HTTP["scheme"] == "http" {
    url.redirect = (".*" => "https://%0$0")
}
```

## Testing

### Check Lighttpd Configuration

```bash
sudo lighttpd -t -f /etc/lighttpd/lighttpd.conf
```

### Monitor Logs

```bash
sudo tail -f /var/log/lighttpd/error.log
sudo tail -f /var/log/lighttpd/access.log
```

### Test PHP

Create `/path/to/jellystream/app/web/php/test.php`:

```php
<?php
phpinfo();
?>
```

Visit: http://localhost:8080/test.php

### Check Performance

```bash
# Memory usage
ps aux | grep lighttpd

# Connections
netstat -an | grep :8080
```

## Troubleshooting

### "File not found" error

- Check `server.document-root` path
- Verify file permissions
- Ensure index files exist

### "502 Bad Gateway" for API

- Check FastAPI is running on port 8000
- Verify proxy configuration
- Check firewall rules

### PHP not executing

- Verify FastCGI module is enabled
- Check PHP-CGI is installed
- Review error logs

### High memory usage

- Reduce `max-procs` in FastCGI config
- Lower `PHP_FCGI_CHILDREN`
- Monitor with `htop` or `ps`

## Advantages Over Apache/Nginx

### vs Apache
- **Lower memory** - ~2-5MB vs 20-50MB
- **Simpler config** - Less complexity
- **Faster startup** - Quick boot times

### vs Nginx
- **Built-in FastCGI** - No separate PHP-FPM needed
- **Simpler syntax** - Easier to learn
- **Lower complexity** - Fewer moving parts

## Production Checklist

- [ ] Set correct file permissions
- [ ] Configure SSL/TLS
- [ ] Set up log rotation
- [ ] Configure firewall rules
- [ ] Enable automatic startup
- [ ] Monitor resource usage
- [ ] Set up backups
- [ ] Test failover scenarios
- [ ] Document configuration
- [ ] Set up monitoring/alerts

## Resources

- [Lighttpd Official Docs](https://redmine.lighttpd.net/projects/lighttpd/wiki)
- [FastCGI Configuration](https://redmine.lighttpd.net/projects/lighttpd/wiki/Docs_ModFastCGI)
- [Performance Tuning](https://redmine.lighttpd.net/projects/lighttpd/wiki/TutorialConfiguration)

---

**Note:** This configuration is optimized for JellyStream. Adjust paths and ports according to your setup.
