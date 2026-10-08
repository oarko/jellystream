# JellyStream PHP Frontend

This is the PHP-based web interface for JellyStream. It communicates with the FastAPI backend and provides a user-friendly setup and management interface.

## Features

- ✅ **Setup Wizard** - Easy configuration interface
- ✅ **API Integration** - Communicates with FastAPI backend
- ✅ **Direct Database Access** - Can query SQLite directly
- ✅ **Channel & Collection Management** - Create and manage virtual TV channels and curated
  collections
- ✅ **Configuration Editor** - Edit .env settings via web UI

## Requirements

- PHP 7.4+ (8.0+ recommended)
- PHP Extensions:
  - pdo_sqlite
  - curl
  - json

## Running the PHP Frontend

### Development (PHP Built-in Server)

```bash
# From the jellystream root directory
cd app/web/php
php -S localhost:8080
```

Then visit: http://localhost:8080

### Production (Recommended: systemd via `./setup.sh`)

From the project root, run `./setup.sh` and accept the systemd install prompt — it installs
and starts both the API and this frontend (via Lighttpd) as systemd services automatically.
See [deploy/README.md](../../../deploy/README.md) and
[SERVER_OPTIONS.md](../../../SERVER_OPTIONS.md). The Apache/Nginx options below remain
available if you need to integrate with existing infrastructure instead.

### Production (Apache)

Configure Apache virtual host:

```apache
<VirtualHost *:80>
    ServerName jellystream.local
    DocumentRoot /path/to/jellystream/app/web/php

    <Directory /path/to/jellystream/app/web/php>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

### Production (Nginx + PHP-FPM)

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

    # Proxy API requests to FastAPI backend
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Architecture

### API Client (`includes/api_client.php`)

Handles all communication with the FastAPI backend:

```php
$api = new ApiClient();

// Get channels
$response = $api->getChannels();
if ($response['success']) {
    $channels = $response['data'];
}

// Create a channel
$response = $api->createChannel([
    'name' => 'My Channel',
    'libraries' => [['library_id' => 'library-id-123', 'library_name' => 'Movies', 'collection_type' => 'movies']],
]);
```

> Note: `getStreams()`/`createStream()` still exist on `ApiClient` for the legacy `/api/streams/`
> routes, but new code should use the `channels`-based methods above instead.

### Database Helper (`includes/database.php`)

Direct SQLite database access:

```php
$db = new Database();

// Query database
$channels = $db->query("SELECT * FROM channels");

// Read/write .env configuration
$config = $db->getEnvConfig();
$db->saveEnvConfig($new_config);
```

## File Structure

```
php/
├── config/
│   ├── config.php          # Configuration constants
│   └── ports.php            # getApiBaseUrl() / getClientApiBaseUrl()
├── includes/
│   ├── api_client.php      # FastAPI client (channels, collections, jellyfin, system)
│   └── database.php        # Database helper
├── pages/
│   ├── channels.php         # Channel management list
│   ├── channel_edit.php     # Channel editor
│   ├── collections.php      # Collection list + boxset import
│   ├── collection_edit.php  # Collection browse/cart editor
│   └── system.php           # Version info + update-channel + check-for-updates
├── static/css/style.css     # Shared dark-theme stylesheet
├── index.php               # Main dashboard
├── setup.php               # Setup wizard
└── README.md               # This file
```

## Usage Examples

### Get Jellyfin Libraries

```php
<?php
require_once 'config/config.php';
require_once 'includes/api_client.php';

$api = new ApiClient();
$response = $api->getJellyfinLibraries();

if ($response['success']) {
    $libraries = $response['data']['libraries'];
    foreach ($libraries as $library) {
        echo $library['Name'] . "\n";
    }
}
?>
```

### Query Database Directly

```php
<?php
require_once 'config/config.php';
require_once 'includes/database.php';

$db = new Database();
$channels = $db->query("SELECT * FROM channels WHERE enabled = 1");

foreach ($channels as $channel) {
    echo $channel['name'] . "\n";
}
?>
```

## Development Tips

1. **Enable PHP error reporting** during development:
   - Edit `config/config.php`
   - Set `error_reporting(E_ALL)` and `ini_set('display_errors', 1)`

2. **Test API connectivity**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check database**:
   ```bash
   sqlite3 data/database/jellystream.db "SELECT * FROM channels;"
   ```

## Security Notes

For production:

1. **Disable error display**:
   ```php
   error_reporting(E_ALL);
   ini_set('display_errors', 0);
   ini_set('log_errors', 1);
   ```

2. **Set proper file permissions**:
   ```bash
   chmod 644 *.php
   chmod 755 app/web/php
   ```

3. **Protect .env file**:
   - Ensure `.env` is not web-accessible
   - Add to `.htaccess` if using Apache

4. **Use HTTPS** in production

5. **Validate all user input** before sending to API or database
