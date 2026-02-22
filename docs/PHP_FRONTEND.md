# PHP Frontend Integration

## Overview

JellyStream now supports a PHP-based frontend alongside the FastAPI backend. This architecture allows you to:

- ✅ **Use PHP** for the web interface (your preference)
- ✅ **Call FastAPI backend** via REST API
- ✅ **Access SQLite database** directly from PHP
- ✅ **Build custom setup pages** easily

## Architecture

```
┌─────────────────┐      HTTP/API       ┌──────────────────┐
│  PHP Frontend   │ ◄─────────────────► │  FastAPI Backend │
│  (Port 8080)    │                     │  (Port 8000)     │
└────────┬────────┘                     └────────┬─────────┘
         │                                       │
         └───────────────┬───────────────────────┘
                         ▼
                  ┌─────────────┐
                  │   SQLite    │
                  │  Database   │
                  └─────────────┘
```

**PHP Frontend** provides:
- Web UI and forms
- Setup wizard
- Configuration editor
- Channel management interface

**FastAPI Backend** provides:
- REST API endpoints
- Jellyfin integration
- Business logic
- Data validation

Both can access the SQLite database directly.

## Running Both Services

###Terminal 1 - FastAPI Backend:
```bash
source venv/bin/activate
python run.py
# Runs on http://localhost:8000
```

### Terminal 2 - PHP Frontend:
```bash
./start-php.sh
# Runs on http://localhost:8080
```

## PHP Components Created

### 1. Configuration (`php/config/config.php`)
- API base URL configuration
- Database path
- Application constants
- Session management

### 2. API Client (`php/includes/api_client.php`)
- `get()`, `post()`, `delete()` methods
- Methods for all API endpoints:
  - `getChannels()` - Get all channels
  - `createChannel($data)` - Create new channel (JSON body)
  - `updateChannel($id, $data)` - Update channel (JSON body)
  - `getJellyfinLibraries()` - Get Jellyfin libraries
  - `getJellyfinGenres($libraryId)` - Get genres for a library
  - And more...

### 3. Database Helper (`php/includes/database.php`)
- Direct SQLite access via PDO
- Query and execute methods
- Helper methods for common operations
- **`.env` file management** - Read/write configuration

### 4. Main Dashboard (`php/index.php`)
- Channel overview
- Quick links
- Status indicators
- Redirects to setup if not configured

### 5. Setup Wizard (`php/setup.php`)
- **Web-based configuration editor**
- Edit all `.env` settings via forms
- Organized by category (App, Jellyfin, Logging)
- Saves configuration without command line

## Usage Examples

### Example 1: Get Channels via API

```php
<?php
require_once 'config/config.php';
require_once 'includes/api_client.php';

$api = new ApiClient();
$response = $api->getChannels();

if ($response['success']) {
    foreach ($response['data'] as $channel) {
        echo $channel['name'] . "\n";
    }
}
?>
```

### Example 2: Direct Database Query

```php
<?php
require_once 'config/config.php';
require_once 'includes/database.php';

$db = new Database();
$channels = $db->query("SELECT * FROM channels");

foreach ($channels as $channel) {
    echo "{$channel['id']}: {$channel['name']}\n";
}
?>
```

### Example 3: Read/Write Configuration

```php
<?php
$db = new Database();

// Read current configuration
$config = $db->getEnvConfig();
echo $config['JELLYFIN_URL'];

// Update configuration
$config['LOG_LEVEL'] = 'DEBUG';
$db->saveEnvConfig($config);
?>
```

## Accessing the Frontend

**Development Mode:**
```bash
./start-php.sh
```
Then visit: http://localhost:8080

**First Time Setup:**
1. Frontend automatically detects if `.env` doesn't exist
2. Redirects to `setup.php`
3. Fill in the form with your Jellyfin details
4. Click "Save Configuration"
5. Restart the FastAPI backend

## Production Deployment

### Option A: Apache

1. Install Apache and PHP:
```bash
sudo apt install apache2 php libapache2-mod-php php-sqlite3 php-curl php-json
```

2. Configure virtual host:
```apache
<VirtualHost *:80>
    ServerName jellystream.local
    DocumentRoot /path/to/jellystream/app/web/php

    <Directory /path/to/jellystream/app/web/php>
        AllowOverride All
        Require all granted
    </Directory>

    # Proxy API requests to FastAPI
    ProxyPass /api http://localhost:8000/api
    ProxyPassReverse /api http://localhost:8000/api
</VirtualHost>
```

### Option B: Nginx + PHP-FPM

1. Install Nginx and PHP-FPM:
```bash
sudo apt install nginx php-fpm php-sqlite3 php-curl php-json
```

2. Configure Nginx:
```nginx
server {
    listen 80;
    server_name jellystream.local;
    root /path/to/jellystream/app/web/php;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    # Proxy API to FastAPI
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

## Benefits of This Approach

1. **Separation of Concerns**
   - PHP handles UI
   - FastAPI handles business logic
   - Both can access database

2. **Flexibility**
   - Can use either PHP or API for data access
   - Easy to build custom pages in PHP
   - FastAPI remains a clean REST API

3. **Development Speed**
   - You know PHP well - build UI quickly
   - No need to learn frontend frameworks
   - Direct database access when needed

4. **Setup Wizard**
   - Web-based configuration
   - No command line needed for users
   - Easy to modify and extend

## Security Considerations

1. **Validate all input** before sending to API
2. **Escape output** with `htmlspecialchars()`
3. **Protect .env file** - not web accessible
4. **Use HTTPS** in production
5. **Set proper PHP error handling** (no display_errors in production)

## Next Steps

You can now:

1. **Create your first channel** — Open `http://localhost:8080`, click "New Channel"
2. **Assign libraries and genre filters** — Select Jellyfin libraries and genres to auto-populate the schedule
3. **Register with Jellyfin Live TV** — Use the channel editor to register the M3U tuner and XMLTV guide
4. **Tune in** — Open Jellyfin, navigate to Live TV, and watch your channel

## Troubleshooting

**"Can't connect to API"**
- Make sure FastAPI is running on port 8000
- Check `API_BASE_URL` in `config/config.php`

**"Database not found"**
- Check `DB_PATH` in `config/config.php`
- Run FastAPI once to create the database

**"PHP extensions missing"**
```bash
sudo apt install php-sqlite3 php-curl php-json
```

## Files

```
jellystream/
├── app/web/php/
│   ├── config/
│   │   ├── config.php          # Constants (API_BASE_URL, APP_NAME)
│   │   └── ports.php           # Dynamic host/port resolution (no hardcoded IPs)
│   ├── includes/
│   │   ├── api_client.php      # FastAPI client (all endpoint wrappers)
│   │   └── database.php        # SQLite PDO helper
│   ├── pages/
│   │   ├── channels.php        # Channel management list
│   │   └── channel_edit.php    # Channel editor (libraries, genres, schedule)
│   ├── index.php               # Main dashboard
│   └── setup.php               # Setup wizard
└── docs/PHP_FRONTEND.md        # This file
```
