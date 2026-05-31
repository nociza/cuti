"""
Logging configuration for cuti.

Library and service modules should emit diagnostics through ``get_logger(__name__)``
rather than ``print()`` so that output level is configurable (via the ``CUTI_LOG_LEVEL``
environment variable) and library code does not pollute stdout. Reserve ``print()`` /
``rich`` for intentional user-facing CLI output.
"""

import logging
import os
import sys
from pathlib import Path


def _env_level(default: int = logging.WARNING) -> int:
    """Resolve the log level from ``CUTI_LOG_LEVEL`` (name or number)."""
    raw = os.getenv("CUTI_LOG_LEVEL")
    if not raw:
        return default
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    return (
        logging.getLevelName(raw.upper())
        if isinstance(logging.getLevelName(raw.upper()), int)
        else default
    )


def get_logger(name: str = "cuti") -> logging.Logger:
    """Return a configured logger for ``name``.

    Idempotent: handlers are attached once per logger. The level honours the
    ``CUTI_LOG_LEVEL`` environment variable (default: WARNING).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger = setup_logger(name, level=_env_level())
    else:
        logger.setLevel(_env_level())
    return logger


def setup_logger(
    name: str = "cuti",
    level: int = logging.INFO,
    log_file: str | None = None,
    console: bool = True,
) -> logging.Logger:
    """Setup and configure logger for cuti.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional log file path
        console: Whether to log to console (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
