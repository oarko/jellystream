# JellyStream PHP Frontend

This is the PHP-based web interface for JellyStream. It communicates with the FastAPI backend and provides a user-friendly setup and management interface.

## Features

- ✅ **Setup Wizard** - Easy configuration interface
- ✅ **API Integration** - Communicates with FastAPI backend
- ✅ **Direct Database Access** - Can query SQLite directly
- ✅ **Stream Management** - Create and manage streams
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

// Get streams
$response = $api->getStreams();
if ($response['success']) {
    $streams = $response['data'];
}

// Create stream
$response = $api->createStream('My Channel', 'library-id-123');
```

### Database Helper (`includes/database.php`)

Direct SQLite database access:

```php
$db = new Database();

// Query database
$streams = $db->getStreams();

// Read/write .env configuration
$config = $db->getEnvConfig();
$db->saveEnvConfig($new_config);
```

## File Structure

```
php/
├── config/
│   └── config.php          # Configuration constants
├── includes/
│   ├── api_client.php      # FastAPI client
│   └── database.php        # Database helper
├── pages/
│   └── (additional pages)
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
$streams = $db->query("SELECT * FROM streams WHERE enabled = 1");

foreach ($streams as $stream) {
    echo $stream['name'] . "\n";
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
   sqlite3 data/database/jellystream.db "SELECT * FROM streams;"
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
