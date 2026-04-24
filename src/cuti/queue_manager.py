"""Backward-compatible export for legacy ``cuti.queue_manager`` imports."""

from .services.queue_service import QueueManager

__all__ = ["QueueManager"]
