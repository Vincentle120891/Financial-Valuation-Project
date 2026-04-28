"""
Logging Configuration

Provides structured logging with rotation and multiple handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    from python_json_logger import jsonlogger


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    rotation_mb: int = 10,
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Optional file path for log output
        rotation_mb: Log file rotation size in MB
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    if log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if log_file:
        try:
            from logging.handlers import RotatingFileHandler
            
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=rotation_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, level.upper()))
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")
    
    # Suppress noisy third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
