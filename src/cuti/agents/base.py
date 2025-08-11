"""
Base classes for agent abstraction layer.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
import asyncio
from datetime import datetime

from ..core.models import QueuedPrompt, ExecutionResult


class AgentCapability(Enum):
    """Capabilities that agents can provide."""
    CODE_UNDERSTANDING = "code_understanding"
    CODE_GENERATION = "code_generation"
    CODE_REFACTORING = "code_refactoring"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE_DESIGN = "architecture_design"
    SECURITY_ANALYSIS = "security_analysis"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    MULTIMODAL_PROCESSING = "multimodal_processing"
    LARGE_CONTEXT_PROCESSING = "large_context_processing"
    REAL_TIME_COLLABORATION = "real_time_collaboration"
    FILE_SYSTEM_OPERATIONS = "file_system_operations"
    DATABASE_OPERATIONS = "database_operations"
    API_INTEGRATION = "api_integration"
    WEB_BROWSING = "web_browsing"
    DATA_ANALYSIS = "data_analysis"
    MACHINE_LEARNING = "machine_learning"


class AgentStatus(Enum):
    """Agent operational status."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    INITIALIZING = "initializing"


@dataclass
class AgentMetadata:
    """Metadata about an agent."""
    name: str
    version: str
    capabilities: List[AgentCapability]
    max_context_tokens: int
    supports_streaming: bool
    supports_multimodal: bool
    rate_limit_info: Optional[Dict[str, Any]] = None
    cost_per_input_token: Optional[float] = None
    cost_per_output_token: Optional[float] = None
    installation_command: Optional[str] = None
    authentication_required: bool = True
    supported_languages: List[str] = field(default_factory=list)
    special_features: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    type: str
    name: str
    command: Optional[str] = None
    api_key_env: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 3600
    max_concurrent: int = 1
    working_directory: str = "."
    environment_vars: Dict[str, str] = field(default_factory=dict)
    system_prompt: Optional[str] = None
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecutionContext:
    """Context for agent execution."""
    session_id: str
    shared_memory: Dict[str, Any]
    available_tools: List[str]
    coordination_data: Dict[str, Any]
    parent_task_id: Optional[str] = None
    collaboration_mode: bool = False
    previous_outputs: List[Dict[str, Any]] = field(default_factory=list)
    execution_history: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.status = AgentStatus.OFFLINE
        self.metadata = self._initialize_metadata()
        self.current_executions: Dict[str, QueuedPrompt] = {}
        self._initialized = False
        self._health_check_failures = 0
        self._last_health_check = None
        
    @abstractmethod
    def _initialize_metadata(self) -> AgentMetadata:
        """Initialize agent metadata."""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent and test connectivity."""
        pass
    
    @abstractmethod
    async def execute_prompt(
        self, 
        prompt: QueuedPrompt,
        context: AgentExecutionContext
    ) -> ExecutionResult:
        """Execute a prompt with the agent."""
        pass
    
    @abstractmethod
    async def stream_prompt(
        self,
        prompt: QueuedPrompt,
        context: AgentExecutionContext
    ) -> AsyncGenerator[str, None]:
        """Stream execution results."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if agent is healthy and available."""
        pass
    
    @abstractmethod
    async def is_installed(self) -> bool:
        """Check if the agent CLI is installed."""
        pass
    
    @abstractmethod
    async def install(self) -> bool:
        """Install the agent CLI."""
        pass
    
    async def can_handle_task(self, prompt: QueuedPrompt) -> float:
        """
        Return confidence score (0-1) for handling this task.
        Default implementation uses keyword matching.
        """
        content_lower = prompt.content.lower()
        confidence = 0.0
        
        # Check for capability-related keywords
        capability_keywords = {
            AgentCapability.CODE_GENERATION: ['generate', 'create', 'write code', 'implement'],
            AgentCapability.CODE_REFACTORING: ['refactor', 'restructure', 'clean up', 'improve code'],
            AgentCapability.DEBUGGING: ['debug', 'fix', 'error', 'bug', 'issue'],
            AgentCapability.TESTING: ['test', 'unit test', 'integration test', 'testing'],
            AgentCapability.DOCUMENTATION: ['document', 'readme', 'comment', 'explain'],
            AgentCapability.ARCHITECTURE_DESIGN: ['architecture', 'design', 'system', 'structure'],
            AgentCapability.SECURITY_ANALYSIS: ['security', 'vulnerability', 'audit', 'secure'],
            AgentCapability.PERFORMANCE_OPTIMIZATION: ['optimize', 'performance', 'speed up', 'efficient'],
            AgentCapability.DATA_ANALYSIS: ['analyze', 'data', 'statistics', 'insights'],
            AgentCapability.MACHINE_LEARNING: ['ml', 'machine learning', 'model', 'train']
        }
        
        for capability in self.metadata.capabilities:
            if capability in capability_keywords:
                keywords = capability_keywords[capability]
                if any(keyword in content_lower for keyword in keywords):
                    confidence = max(confidence, 0.7)
        
        # Base confidence for general capabilities
        if confidence == 0.0 and self.metadata.capabilities:
            confidence = 0.3
        
        return confidence
    
    def get_current_load(self) -> float:
        """Return current load percentage (0-1)."""
        max_concurrent = self.config.max_concurrent
        current_count = len(self.current_executions)
        return min(1.0, current_count / max_concurrent)
    
    async def estimate_execution_time(self, prompt: QueuedPrompt) -> Optional[int]:
        """
        Estimate execution time in seconds.
        Default implementation based on content length and complexity.
        """
        content_length = len(prompt.content)
        base_time = 10  # Base 10 seconds
        
        # Add time based on content length (1 second per 100 characters)
        length_time = content_length / 100
        
        # Add time for files (5 seconds per file)
        file_time = len(prompt.context_files) * 5
        
        # Estimate total time
        estimated_time = int(base_time + length_time + file_time)
        
        # Cap at timeout
        return min(estimated_time, self.config.timeout)
    
    async def estimate_cost(self, prompt: QueuedPrompt) -> Optional[float]:
        """
        Estimate cost in USD.
        Default implementation based on token counts.
        """
        if not self.metadata.cost_per_input_token or not self.metadata.cost_per_output_token:
            return None
        
        # Rough estimation: 1 token ≈ 4 characters
        estimated_input_tokens = len(prompt.content) / 4
        
        # Add tokens for context files (rough estimate)
        for file_path in prompt.context_files:
            estimated_input_tokens += 500  # Assume 500 tokens per file
        
        # Estimate output tokens (usually 2-3x input for code tasks)
        estimated_output_tokens = estimated_input_tokens * 2.5
        
        input_cost = estimated_input_tokens * self.metadata.cost_per_input_token
        output_cost = estimated_output_tokens * self.metadata.cost_per_output_token
        
        return input_cost + output_cost
    
    def add_execution(self, prompt_id: str, prompt: QueuedPrompt):
        """Track an active execution."""
        self.current_executions[prompt_id] = prompt
        self.status = AgentStatus.BUSY if self.get_current_load() >= 1.0 else AgentStatus.AVAILABLE
    
    def remove_execution(self, prompt_id: str):
        """Remove a completed execution."""
        if prompt_id in self.current_executions:
            del self.current_executions[prompt_id]
            self.status = AgentStatus.AVAILABLE if self._initialized else AgentStatus.OFFLINE
    
    async def prepare_system_prompt(self, context: AgentExecutionContext) -> str:
        """
        Prepare system prompt with context and collaboration instructions.
        """
        system_prompt = self.config.system_prompt or f"You are {self.name}, an AI assistant."
        
        if context.collaboration_mode:
            system_prompt += f"""

You are collaborating with other AI agents on this task.
Session ID: {context.session_id}
Your role: {context.coordination_data.get('role', 'collaborator')}

Previous outputs from other agents:
{context.previous_outputs}

Shared context:
{context.shared_memory}

Please coordinate your response with the overall task objectives.
"""
        
        return system_prompt
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' status={self.status.value}>"