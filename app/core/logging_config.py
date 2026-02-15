"""Logging configuration."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import os

from app.core.config import settings


def setup_logging():
    """Configure application logging."""
    # Create logs directory if it doesn't exist
    if settings.LOG_TO_FILE:
        Path(settings.LOG_FILE_PATH).mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler (if enabled)
    if settings.LOG_TO_FILE:
        # Create dated log file
        log_filename = f"jellystream_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_filepath = os.path.join(settings.LOG_FILE_PATH, log_filename)

        file_handler = RotatingFileHandler(
            log_filepath,
            maxBytes=settings.LOG_FILE_MAX_BYTES,
            backupCount=settings.LOG_FILE_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

        # Clean up old logs
        cleanup_old_logs()

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    logger.info(f"Logging initialized - Level: {settings.LOG_LEVEL}")
    if settings.LOG_TO_FILE:
        logger.info(f"Logging to file: {log_filepath}")


def cleanup_old_logs():
    """Remove log files older than LOG_RETENTION_DAYS."""
    if not settings.LOG_TO_FILE:
        return

    log_dir = Path(settings.LOG_FILE_PATH)
    if not log_dir.exists():
        return

    cutoff_date = datetime.now() - timedelta(days=settings.LOG_RETENTION_DAYS)
    deleted_count = 0

    for log_file in log_dir.glob("jellystream_*.log*"):
        try:
            # Get file modification time
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

            if file_mtime < cutoff_date:
                log_file.unlink()
                deleted_count += 1
                logging.debug(f"Deleted old log file: {log_file.name}")
        except Exception as e:
            logging.error(f"Error deleting log file {log_file}: {e}")

    if deleted_count > 0:
        logging.info(f"Cleaned up {deleted_count} old log file(s)")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
