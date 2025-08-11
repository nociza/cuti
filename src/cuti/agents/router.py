"""
Task routing and coordination for multi-agent systems.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
import asyncio
from datetime import datetime

from .base import BaseAgent, AgentCapability, AgentExecutionContext
from .pool import AgentPool
from .context import SharedMemoryManager
from ..core.models import QueuedPrompt, ExecutionResult


class TaskRoutingStrategy(Enum):
    """Task routing strategies."""
    CAPABILITY_BASED = "capability_based"
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    COST_OPTIMIZED = "cost_optimized"
    SPEED_OPTIMIZED = "speed_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"


@dataclass
class RoutingDecision:
    """Decision made by the task router."""
    agent: BaseAgent
    confidence: float
    estimated_time: Optional[int] = None
    estimated_cost: Optional[float] = None
    reasoning: str = ""
    fallback_agents: List[BaseAgent] = field(default_factory=list)


class TaskRouter:
    """Routes tasks to appropriate agents."""
    
    def __init__(self, agent_pool: AgentPool, strategy: TaskRoutingStrategy = TaskRoutingStrategy.CAPABILITY_BASED):
        self.agent_pool = agent_pool
        self.strategy = strategy
        self.routing_history: List[Dict[str, Any]] = []
    
    async def route_task(self, prompt: QueuedPrompt) -> Optional[RoutingDecision]:
        """Route a task to the best agent."""
        
        if self.strategy == TaskRoutingStrategy.CAPABILITY_BASED:
            return await self._route_by_capability(prompt)
        elif self.strategy == TaskRoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin()
        elif self.strategy == TaskRoutingStrategy.LOAD_BALANCED:
            return await self._route_load_balanced(prompt)
        elif self.strategy == TaskRoutingStrategy.COST_OPTIMIZED:
            return await self._route_cost_optimized(prompt)
        elif self.strategy == TaskRoutingStrategy.SPEED_OPTIMIZED:
            return await self._route_speed_optimized(prompt)
        elif self.strategy == TaskRoutingStrategy.QUALITY_OPTIMIZED:
            return await self._route_quality_optimized(prompt)
        else:
            return await self._route_by_capability(prompt)
    
    async def _route_by_capability(self, prompt: QueuedPrompt) -> Optional[RoutingDecision]:
        """Route based on agent capabilities."""
        best_agent = await self.agent_pool.select_best_agent(prompt)
        
        if not best_agent:
            return None
        
        confidence = await best_agent.can_handle_task(prompt)
        estimated_time = await best_agent.estimate_execution_time(prompt)
        estimated_cost = await best_agent.estimate_cost(prompt)
        
        # Get fallback agents
        available_agents = self.agent_pool.get_available_agents()
        fallback_agents = [a for a in available_agents if a != best_agent][:2]
        
        decision = RoutingDecision(
            agent=best_agent,
            confidence=confidence,
            estimated_time=estimated_time,
            estimated_cost=estimated_cost,
            reasoning=f"Selected based on capability match (confidence: {confidence:.2f})",
            fallback_agents=fallback_agents
        )
        
        self._record_routing(prompt, decision)
        return decision
    
    def _route_round_robin(self) -> Optional[RoutingDecision]:
        """Route using round-robin strategy."""
        agent = self.agent_pool.select_agent_round_robin()
        
        if not agent:
            return None
        
        return RoutingDecision(
            agent=agent,
            confidence=0.5,
            reasoning="Selected using round-robin strategy"
        )
    
    async def _route_load_balanced(self, prompt: QueuedPrompt) -> Optional[RoutingDecision]:
        """Route to the least loaded agent."""
        available_agents = self.agent_pool.get_available_agents()
        
        if not available_agents:
            return None
        
        # Find agent with lowest load
        agent_loads = [(a, a.get_current_load()) for a in available_agents]
        agent_loads.sort(key=lambda x: x[1])
        
        best_agent = agent_loads[0][0]
        confidence = await best_agent.can_handle_task(prompt)
        
        return RoutingDecision(
            agent=best_agent,
            confidence=confidence,
            reasoning=f"Selected based on load (current load: {agent_loads[0][1]:.2f})"
        )
    
    async def _route_cost_optimized(self, prompt: QueuedPrompt) -> Optional[RoutingDecision]:
        """Route to minimize cost."""
        available_agents = self.agent_pool.get_available_agents()
        
        if not available_agents:
            return None
        
        # Calculate costs for each agent
        agent_costs = []
        for agent in available_agents:
            cost = await agent.estimate_cost(prompt)
            if cost is not None:
                agent_costs.append((agent, cost))
        
        if not agent_costs:
            # Fallback to capability-based routing
            return await self._route_by_capability(prompt)
        
        # Sort by cost (lowest first)
        agent_costs.sort(key=lambda x: x[1])
        
        best_agent, cost = agent_costs[0]
        confidence = await best_agent.can_handle_task(prompt)
        
        return RoutingDecision(
            agent=best_agent,
            confidence=confidence,
            estimated_cost=cost,
            reasoning=f"Selected for cost optimization (estimated cost: ${cost:.4f})"
        )
    
    async def _route_speed_optimized(self, prompt: QueuedPrompt) -> Optional[RoutingDecision]:
        """Route to minimize execution time."""
        available_agents = self.agent_pool.get_available_agents()
        
        if not available_agents:
            return None
        
        # Estimate times for each agent
        agent_times = []
        for agent in available_agents:
            time = await agent.estimate_execution_time(prompt)
            load = agent.get_current_load()
            # Adjust time based on current load
            adjusted_time = time * (1 + load) if time else None
            if adjusted_time is not None:
                agent_times.append((agent, adjusted_time))
        
        if not agent_times:
            # Fallback to capability-based routing
            return await self._route_by_capability(prompt)
        
        # Sort by time (fastest first)
        agent_times.sort(key=lambda x: x[1])
        
        best_agent, time = agent_times[0]
        confidence = await best_agent.can_handle_task(prompt)
        
        return RoutingDecision(
            agent=best_agent,
            confidence=confidence,
            estimated_time=int(time),
            reasoning=f"Selected for speed optimization (estimated time: {int(time)}s)"
        )
    
    async def _route_quality_optimized(self, prompt: QueuedPrompt) -> Optional[RoutingDecision]:
        """Route to maximize quality/confidence."""
        available_agents = self.agent_pool.get_available_agents()
        
        if not available_agents:
            return None
        
        # Get confidence scores for each agent
        agent_scores = []
        for agent in available_agents:
            confidence = await agent.can_handle_task(prompt)
            # Consider agent's special features
            quality_boost = 0.1 if agent.metadata.special_features else 0
            adjusted_confidence = min(1.0, confidence + quality_boost)
            agent_scores.append((agent, adjusted_confidence))
        
        # Sort by confidence (highest first)
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        
        best_agent, confidence = agent_scores[0]
        estimated_time = await best_agent.estimate_execution_time(prompt)
        estimated_cost = await best_agent.estimate_cost(prompt)
        
        return RoutingDecision(
            agent=best_agent,
            confidence=confidence,
            estimated_time=estimated_time,
            estimated_cost=estimated_cost,
            reasoning=f"Selected for quality optimization (confidence: {confidence:.2f})"
        )
    
    def _record_routing(self, prompt: QueuedPrompt, decision: RoutingDecision):
        """Record routing decision for analysis."""
        self.routing_history.append({
            "timestamp": datetime.now().isoformat(),
            "prompt_id": prompt.id,
            "strategy": self.strategy.value,
            "agent": decision.agent.name,
            "confidence": decision.confidence,
            "estimated_time": decision.estimated_time,
            "estimated_cost": decision.estimated_cost,
            "reasoning": decision.reasoning
        })
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        if not self.routing_history:
            return {"total_routed": 0}
        
        agent_counts = {}
        total_confidence = 0
        
        for record in self.routing_history:
            agent_name = record["agent"]
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
            total_confidence += record["confidence"]
        
        return {
            "total_routed": len(self.routing_history),
            "average_confidence": total_confidence / len(self.routing_history),
            "agent_distribution": agent_counts,
            "current_strategy": self.strategy.value
        }


class CoordinationEngine:
    """Coordinates multi-agent collaboration."""
    
    def __init__(self, agent_pool: AgentPool, router: TaskRouter):
        self.agent_pool = agent_pool
        self.router = router
        self.memory_manager = SharedMemoryManager()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def execute_collaborative_task(
        self,
        prompt: QueuedPrompt,
        agents: Optional[List[str]] = None,
        parallel: bool = False
    ) -> ExecutionResult:
        """Execute a task with multiple agents collaborating."""
        
        session_id = f"collab_{prompt.id}_{datetime.now().timestamp()}"
        
        # Initialize session
        await self.memory_manager.initialize_session(session_id, {
            "task": prompt.content,
            "start_time": datetime.now().isoformat()
        })
        
        self.active_sessions[session_id] = {
            "prompt": prompt,
            "agents": agents or [],
            "parallel": parallel,
            "results": []
        }
        
        try:
            if parallel and agents and len(agents) > 1:
                # Execute in parallel
                result = await self._execute_parallel(session_id, prompt, agents)
            else:
                # Execute sequentially
                result = await self._execute_sequential(session_id, prompt, agents)
            
            # Save session results
            await self.memory_manager.set_context(
                session_id,
                "final_result",
                result.output,
                "coordinator"
            )
            
            return result
            
        finally:
            # Clean up session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def _execute_parallel(
        self,
        session_id: str,
        prompt: QueuedPrompt,
        agent_names: List[str]
    ) -> ExecutionResult:
        """Execute task with multiple agents in parallel."""
        
        tasks = []
        for agent_name in agent_names:
            agent = self.agent_pool.get_agent(agent_name)
            if agent:
                context = AgentExecutionContext(
                    session_id=session_id,
                    shared_memory=await self.memory_manager.get_context(session_id),
                    available_tools=[],
                    coordination_data={"role": "parallel_worker"},
                    collaboration_mode=True
                )
                tasks.append(agent.execute_prompt(prompt, context))
        
        if not tasks:
            return ExecutionResult(
                success=False,
                output="",
                error="No valid agents found",
                execution_time=0,
                tokens_used=0
            )
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        combined_output = []
        total_tokens = 0
        total_time = 0
        errors = []
        
        for i, result in enumerate(results):
            agent_name = agent_names[i] if i < len(agent_names) else f"Agent{i}"
            
            if isinstance(result, Exception):
                errors.append(f"{agent_name}: {str(result)}")
            elif isinstance(result, ExecutionResult):
                if result.success:
                    combined_output.append(f"=== {agent_name} ===\n{result.output}")
                    total_tokens += result.tokens_used
                    total_time = max(total_time, result.execution_time)
                else:
                    errors.append(f"{agent_name}: {result.error}")
        
        if not combined_output and errors:
            return ExecutionResult(
                success=False,
                output="",
                error="\n".join(errors),
                execution_time=total_time,
                tokens_used=total_tokens
            )
        
        return ExecutionResult(
            success=True,
            output="\n\n".join(combined_output),
            error="\n".join(errors) if errors else None,
            execution_time=total_time,
            tokens_used=total_tokens
        )
    
    async def _execute_sequential(
        self,
        session_id: str,
        prompt: QueuedPrompt,
        agent_names: Optional[List[str]]
    ) -> ExecutionResult:
        """Execute task with agents sequentially."""
        
        if not agent_names:
            # Use router to select agent
            decision = await self.router.route_task(prompt)
            if not decision:
                return ExecutionResult(
                    success=False,
                    output="",
                    error="No suitable agent found",
                    execution_time=0,
                    tokens_used=0
                )
            agents_to_use = [decision.agent]
        else:
            agents_to_use = [self.agent_pool.get_agent(name) for name in agent_names]
            agents_to_use = [a for a in agents_to_use if a is not None]
        
        if not agents_to_use:
            return ExecutionResult(
                success=False,
                output="",
                error="No valid agents found",
                execution_time=0,
                tokens_used=0
            )
        
        # Execute with each agent sequentially
        all_outputs = []
        total_tokens = 0
        total_time = 0
        previous_outputs = []
        
        for agent in agents_to_use:
            context = AgentExecutionContext(
                session_id=session_id,
                shared_memory=await self.memory_manager.get_context(session_id),
                available_tools=[],
                coordination_data={
                    "role": "sequential_worker",
                    "position": len(previous_outputs) + 1,
                    "total_agents": len(agents_to_use)
                },
                collaboration_mode=True,
                previous_outputs=previous_outputs
            )
            
            result = await agent.execute_prompt(prompt, context)
            
            if result.success:
                all_outputs.append(result.output)
                previous_outputs.append({
                    "agent": agent.name,
                    "output": result.output
                })
                total_tokens += result.tokens_used
                total_time += result.execution_time
                
                # Update shared memory
                await self.memory_manager.set_context(
                    session_id,
                    f"output_{agent.name}",
                    result.output,
                    agent.name
                )
            else:
                # Try fallback or continue
                continue
        
        if not all_outputs:
            return ExecutionResult(
                success=False,
                output="",
                error="All agents failed to execute",
                execution_time=total_time,
                tokens_used=total_tokens
            )
        
        # Return the last output (or combine them)
        return ExecutionResult(
            success=True,
            output=all_outputs[-1],  # Use last agent's output as final
            error=None,
            execution_time=total_time,
            tokens_used=total_tokens
        )