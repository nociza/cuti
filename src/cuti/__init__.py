"""
cuti - Production-ready claude code utils with command queuing, web interface, and monitoring.
"""

__version__ = "0.1.0"
__author__ = "claude-code, nociza"
__description__ = "Production-ready claude code utils with command queuing, prompt aliases, web interface, and monitoring."

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