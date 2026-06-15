"""
Multi-agent orchestration system for cuti.
"""

from .base import (
    AgentCapability,
    AgentConfig,
    AgentExecutionContext,
    AgentMetadata,
    AgentStatus,
    BaseAgent,
)
from .context import SharedMemoryManager
from .pool import AgentPool
from .router import CoordinationEngine, RoutingDecision, TaskRouter, TaskRoutingStrategy

__all__ = [
    # Base classes
    'BaseAgent',
    'AgentCapability',
    'AgentStatus',
    'AgentMetadata',
    'AgentExecutionContext',
    'AgentConfig',

    # Management
    'AgentPool',

    # Routing
    'TaskRouter',
    'TaskRoutingStrategy',
    'RoutingDecision',
    'CoordinationEngine',

    # Context
    'SharedMemoryManager'
]
