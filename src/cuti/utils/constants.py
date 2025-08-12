"""
Shared constants for cuti.
"""

from pathlib import Path

# Default configuration values
DEFAULT_STORAGE_DIR = "~/.cuti"
DEFAULT_CLAUDE_COMMAND = "claude"
DEFAULT_CHECK_INTERVAL = 30
DEFAULT_TIMEOUT = 3600
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8000
DEFAULT_MAX_RETRIES = 3

# File patterns and extensions
MARKDOWN_EXTENSION = ".md"
JSON_EXTENSION = ".json"
CONFIG_FILENAME = "config.json"
STATE_FILENAME = "queue-state.json"
ALIASES_FILENAME = "aliases.json"

# Directory names
QUEUE_DIR = "queue"
COMPLETED_DIR = "completed"
FAILED_DIR = "failed"

# Status indicators for file naming
EXECUTING_SUFFIX = ".executing"
RATE_LIMITED_SUFFIX = ".rate-limited"
CANCELLED_SUFFIX = "cancelled"

# Rate limiting
RATE_LIMIT_COOLDOWN_MINUTES = 5

# Web interface
WEB_STATIC_DIR = "static"
WEB_TEMPLATES_DIR = "templates"

# Agent directories
BUILTIN_AGENTS_DIR = Path(__file__).parent.parent / "builtin_agents"