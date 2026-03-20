"""cuti - Production-ready Claude Code utilities with queuing and a read-only ops console."""

__version__ = "0.1.0"
__author__ = "claude-code, nociza"
__description__ = "Production-ready Claude Code utilities with command queuing, prompt aliases, and a read-only ops console."

# Import main components for convenience
from .services.queue_service import QueueManager
from .core.models import QueuedPrompt, PromptStatus
from .services.aliases import PromptAliasManager
from .services.history import PromptHistoryManager

__all__ = [
    "QueueManager",
    "QueuedPrompt", 
    "PromptStatus",
    "PromptAliasManager",
    "PromptHistoryManager",
]
