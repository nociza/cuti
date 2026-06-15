"""cuti - Production-ready Claude Code utilities with queuing and a read-only ops console."""

__version__ = "0.1.73"
__author__ = "claude-code, nociza"
__description__ = "Production-ready Claude Code utilities with command queuing, prompt aliases, and a read-only ops console."

# Import main components for convenience
from .core.models import PromptStatus, QueuedPrompt
from .services.aliases import PromptAliasManager
from .services.history import PromptHistoryManager
from .services.queue_service import QueueManager

__all__ = [
    "QueueManager",
    "QueuedPrompt",
    "PromptStatus",
    "PromptAliasManager",
    "PromptHistoryManager",
]
