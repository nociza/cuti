"""
Agent pool management for multi-agent orchestration.
"""

import asyncio
from typing import Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseAgent, AgentConfig, AgentStatus, AgentCapability
from .claude_agent import ClaudeAgent
from .gemini_agent import GeminiAgent
from ..core.models import QueuedPrompt


class AgentType(Enum):
    """Supported agent types."""
    CLAUDE = "claude"
    GEMINI = "gemini"
    GPT4 = "gpt4"
    LLAMA = "llama"
    CUSTOM = "custom"


@dataclass
class AgentPoolConfig:
    """Configuration for agent pool."""
    max_agents: int = 10
    enable_auto_scaling: bool = True
    health_check_interval: int = 60
    load_balancing_strategy: str = "round_robin"
    fallback_enabled: bool = True


class AgentPool:
    """Manages a pool of AI agents."""
    
    # Agent type registry
    AGENT_REGISTRY: Dict[AgentType, Type[BaseAgent]] = {
        AgentType.CLAUDE: ClaudeAgent,
        AgentType.GEMINI: GeminiAgent,
    }
    
    def __init__(self, config: Optional[AgentPoolConfig] = None):
        self.config = config or AgentPoolConfig()
        self.agents: Dict[str, BaseAgent] = {}
        self._initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._current_index = 0  # For round-robin
    
    async def initialize(self):
        """Initialize the agent pool."""
        if self._initialized:
            return
        
        # Start health check task
        if self.config.health_check_interval > 0:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        self._initialized = True
    
    async def shutdown(self):
        """Shutdown the agent pool."""
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Clean up agents
        self.agents.clear()
        self._initialized = False
    
    async def add_agent(self, agent_config: AgentConfig) -> bool:
        """Add an agent to the pool."""
        try:
            # Determine agent type
            agent_type = AgentType(agent_config.type.lower())
            
            if agent_type not in self.AGENT_REGISTRY:
                print(f"Unsupported agent type: {agent_type}")
                return False
            
            # Check pool capacity
            if len(self.agents) >= self.config.max_agents:
                print(f"Agent pool at maximum capacity ({self.config.max_agents})")
                return False
            
            # Create agent instance
            agent_class = self.AGENT_REGISTRY[agent_type]
            agent = agent_class(agent_config)
            
            # Initialize agent
            if await agent.initialize():
                self.agents[agent_config.name] = agent
                print(f"Added {agent_type.value} agent '{agent_config.name}' to pool")
                return True
            else:
                print(f"Failed to initialize {agent_type.value} agent '{agent_config.name}'")
                return False
                
        except Exception as e:
            print(f"Error adding agent: {e}")
            return False
    
    async def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent from the pool."""
        if agent_name in self.agents:
            del self.agents[agent_name]
            print(f"Removed agent '{agent_name}' from pool")
            return True
        return False
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get a specific agent by name."""
        return self.agents.get(agent_name)
    
    def get_available_agents(self) -> List[BaseAgent]:
        """Get all available agents."""
        return [
            agent for agent in self.agents.values()
            if agent.status == AgentStatus.AVAILABLE
        ]
    
    def get_agents_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """Get agents with a specific capability."""
        return [
            agent for agent in self.agents.values()
            if capability in agent.metadata.capabilities
        ]
    
    async def select_best_agent(self, prompt: QueuedPrompt) -> Optional[BaseAgent]:
        """Select the best agent for a given prompt."""
        available_agents = self.get_available_agents()
        
        if not available_agents:
            return None
        
        # Score each agent
        agent_scores = []
        for agent in available_agents:
            confidence = await agent.can_handle_task(prompt)
            load = agent.get_current_load()
            
            # Combine confidence and load into a score
            # Higher confidence and lower load = better score
            score = confidence * (1 - load * 0.5)
            agent_scores.append((agent, score))
        
        # Sort by score (highest first)
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the best agent
        if agent_scores:
            best_agent, score = agent_scores[0]
            if score > 0.3:  # Minimum threshold
                return best_agent
        
        return None
    
    def select_agent_round_robin(self) -> Optional[BaseAgent]:
        """Select an agent using round-robin strategy."""
        available_agents = self.get_available_agents()
        
        if not available_agents:
            return None
        
        # Round-robin selection
        agent = available_agents[self._current_index % len(available_agents)]
        self._current_index += 1
        
        return agent
    
    async def _health_check_loop(self):
        """Periodically check agent health."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Check health of all agents
                for agent in self.agents.values():
                    try:
                        is_healthy = await agent.health_check()
                        if not is_healthy and agent.status == AgentStatus.AVAILABLE:
                            agent.status = AgentStatus.ERROR
                            print(f"Agent '{agent.name}' failed health check")
                    except Exception as e:
                        print(f"Error checking health of agent '{agent.name}': {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in health check loop: {e}")
    
    def get_pool_stats(self) -> Dict:
        """Get statistics about the agent pool."""
        total_agents = len(self.agents)
        available_agents = len(self.get_available_agents())
        busy_agents = len([a for a in self.agents.values() if a.status == AgentStatus.BUSY])
        error_agents = len([a for a in self.agents.values() if a.status == AgentStatus.ERROR])
        
        # Get capability coverage
        all_capabilities = set()
        for agent in self.agents.values():
            all_capabilities.update(agent.metadata.capabilities)
        
        return {
            "total_agents": total_agents,
            "available_agents": available_agents,
            "busy_agents": busy_agents,
            "error_agents": error_agents,
            "capabilities_covered": len(all_capabilities),
            "agents": [
                {
                    "name": agent.name,
                    "type": agent.__class__.__name__,
                    "status": agent.status.value,
                    "load": agent.get_current_load(),
                    "capabilities": [cap.value for cap in agent.metadata.capabilities]
                }
                for agent in self.agents.values()
            ]
        }
    
    def __repr__(self) -> str:
        return f"<AgentPool agents={len(self.agents)} available={len(self.get_available_agents())}>"