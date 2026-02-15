# Recent Changes - JellyStream

## Summary of Changes (2026-02-15)

Two major features have been implemented:

1. **✅ PHP Frontend Integration** - Complete PHP-based web interface
2. **✅ Advanced Logging System** - Configurable logging with file rotation

---

## 1. PHP Frontend Integration

### What Was Added

A complete PHP-based frontend that works alongside the FastAPI backend.

**Created Files:**
- `app/web/php/config/config.php` - Configuration
- `app/web/php/includes/api_client.php` - FastAPI client class
- `app/web/php/includes/database.php` - SQLite database helper
- `app/web/php/index.php` - Main dashboard
- `app/web/php/setup.php` - **Web-based setup wizard**
- `start-php.sh` - PHP server launcher
- `docs/PHP_FRONTEND.md` - Complete documentation

### Key Features

✅ **API Client Class** - Call FastAPI backend from PHP
```php
$api = new ApiClient();
$streams = $api->getStreams();
```

✅ **Direct Database Access** - Query SQLite from PHP
```php
$db = new Database();
$streams = $db->getStreams();
```

✅ **Setup Wizard** - Web-based configuration editor
- Edit all `.env` settings via web form
- No command line required
- Saves configuration automatically

✅ **Dashboard** - Stream overview and management

### How to Use

**Run Both Services:**

Terminal 1 - Backend:
```bash
source venv/bin/activate
python run.py
```

Terminal 2 - Frontend:
```bash
./start-php.sh
```

**Access:**
- PHP Frontend: http://localhost:8080
- FastAPI Backend: http://localhost:8000
- Setup Wizard: http://localhost:8080/setup.php

---

## 2. Advanced Logging System

### What Was Added

Comprehensive logging with configurable levels and automatic file rotation.

**Created Files:**
- `app/core/logging_config.py` - Logging configuration module

**Modified Files:**
- `app/core/config.py` - Added logging settings
- `app/main.py` - Integrated logging
- `.env.example` - Added logging configuration

### Features

✅ **Configurable Log Levels**
- DEBUG, INFO, WARNING, ERROR, CRITICAL
- Set via `.env`: `LOG_LEVEL=DEBUG`

✅ **Dual Output**
- Console: Simple format for readability
- File: Detailed format with timestamps, filenames, line numbers

✅ **Date-Based Log Files**
- Format: `jellystream_2026-02-15.log`
- Easy to identify and manage

✅ **Rotating File Handler**
- Max file size: 10MB (configurable)
- Keeps 5 backup files (configurable)

✅ **Automatic Cleanup**
- Deletes logs older than 30 days (configurable)
- Runs on application startup

✅ **Third-Party Logger Control**
- Reduces noise from uvicorn, fastapi, sqlalchemy
- Set to WARNING level automatically

### Configuration Options

Add to `.env`:

```env
# Logging
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE=True            # Enable file logging
LOG_FILE_PATH=./logs        # Log directory
LOG_FILE_MAX_BYTES=10485760 # 10MB max file size
LOG_FILE_BACKUP_COUNT=5     # Number of backup files
LOG_RETENTION_DAYS=30       # Auto-delete logs older than this
```

### Usage in Code

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical issue!")
```

### Log Format

**Console Output:**
```
2026-02-15 14:30:45 - INFO - Starting JellyStream application...
2026-02-15 14:30:45 - INFO - Database initialized successfully
```

**File Output:**
```
2026-02-15 14:30:45 - app.main - INFO - main.py:42 - Starting JellyStream application...
2026-02-15 14:30:45 - app.core.database - INFO - database.py:38 - Database initialized successfully
```

---

## Testing the Changes

### Test Logging

1. Set log level to DEBUG:
```env
LOG_LEVEL=DEBUG
```

2. Restart the application:
```bash
python run.py
```

3. Check console output - should see detailed logs

4. Check log file:
```bash
ls -la logs/
cat logs/jellystream_2026-02-15.log
```

### Test PHP Frontend

1. Start FastAPI backend:
```bash
source venv/bin/activate
python run.py
```

2. Start PHP frontend:
```bash
./start-php.sh
```

3. Visit http://localhost:8080

4. Try the setup wizard at http://localhost:8080/setup.php

---

## Architecture Diagram

```
                    ┌─────────────────────────┐
                    │   User Browser          │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  PHP Frontend           │
                    │  (Port 8080)            │
                    │  - Dashboard            │
                    │  - Setup Wizard         │
                    │  - Stream Management    │
                    └───┬──────────────────┬──┘
                        │                  │
                        │ API Calls        │ Direct DB Access
                        │                  │
    ┌───────────────────▼──────┐    ┌─────▼────────────────┐
    │  FastAPI Backend         │    │  SQLite Database     │
    │  (Port 8000)             │◄───┤  - streams           │
    │  - REST API              │    │  - schedules         │
    │  - Jellyfin Integration  │    └──────────────────────┘
    │  - Business Logic        │
    │  - Logging System        │
    └──────────────────────────┘
                │
                │ Logs to
                ▼
    ┌──────────────────────────┐
    │  ./logs/                 │
    │  - jellystream_DATE.log  │
    │  - Auto-rotated          │
    │  - Auto-cleaned          │
    └──────────────────────────┘
```

---

## Benefits

### PHP Frontend

1. **Familiar Technology** - You know PHP well
2. **Quick Development** - Build features fast
3. **Web-Based Setup** - No command line for users
4. **Flexible Data Access** - API or direct database
5. **Easy to Extend** - Add pages, forms, features

### Logging System

1. **Better Debugging** - See exactly what's happening
2. **Production Ready** - Automatic rotation and cleanup
3. **Configurable** - Adjust verbosity as needed
4. **Persistent Logs** - Track issues over time
5. **Clean Output** - Reduced noise from libraries

---

## Next Steps

Now that you have these features, you can:

1. **Build More PHP Pages**
   - Stream management CRUD
   - Schedule editor
   - Jellyfin library browser
   - Settings pages

2. **Customize Logging**
   - Add custom log handlers
   - Integrate external logging services
   - Add metrics/monitoring

3. **Enhance Setup Wizard**
   - Test Jellyfin connection
   - Validate configuration
   - Step-by-step wizard

4. **Add Authentication**
   - PHP session-based auth
   - Protect admin pages
   - User management

---

## Files Summary

### New Files Created
- `app/web/php/` directory structure
- `app/core/logging_config.py`
- `start-php.sh`
- `docs/PHP_FRONTEND.md`
- `CHANGES.md` (this file)

### Modified Files
- `app/core/config.py` - Added logging settings
- `app/main.py` - Integrated logging
- `.env.example` - Added logging configuration

### Documentation
- Complete PHP frontend guide
- Logging usage examples
- Architecture diagrams
- Setup instructions

---

**Version:** 0.1.0
**Date:** 2026-02-15
**Status:** Both features fully functional and ready to use
