"""cuti - Provider-aware AI development runtime with a read-only ops console."""

__version__ = "0.1.73"
__author__ = "claude-code, nociza"
__description__ = "Provider-aware local AI development runtime with containers, auth/config mounting, and a read-only ops console."

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
