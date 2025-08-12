"""
Agents API endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from ...services.claude_orchestration import ClaudeOrchestrationManager, AgentConfig

agents_router = APIRouter(prefix="/agents", tags=["agents"])

# Global orchestration manager instance
orchestration_manager = None


def get_orchestration_manager() -> ClaudeOrchestrationManager:
    """Get or create the orchestration manager instance."""
    global orchestration_manager
    if orchestration_manager is None:
        orchestration_manager = ClaudeOrchestrationManager(Path.cwd())
    return orchestration_manager


class ExecuteRequest(BaseModel):
    prompt: str
    context: Optional[Dict[str, Any]] = None


class ToggleAgentRequest(BaseModel):
    enabled: bool


class CreateAgentRequest(BaseModel):
    name: str
    description: str
    capabilities: List[str] = []
    usage_instructions: str = ""
    priority: int = 0


class HotSwapRequest(BaseModel):
    agent_names: List[str]


@agents_router.get("")
async def get_agents(request: Request) -> List[Dict[str, Any]]:
    """Get list of available agents."""
    try:
        manager = get_orchestration_manager()
        await manager.initialize()
        
        status = await manager.get_agent_status()
        agents = []
        
        for name, info in status["agents"].items():
            agents.append({
                "id": name,
                "name": name,
                "enabled": info["enabled"],
                "description": info["description"],
                "capabilities": info["capabilities"],
                "priority": info["priority"],
                "type": "claude" if "gemini" not in name else "gemini",
                "status": "active" if info["enabled"] else "inactive"
            })
        
        return agents
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents: {str(e)}")


@agents_router.get("/{agent_id}")
async def get_agent_details(request: Request, agent_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific agent."""
    try:
        from ...agents.pool import AgentPool
        
        pool = AgentPool()
        agent = pool.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        return {
            "id": agent_id,
            "name": agent_id,
            "type": agent.__class__.__name__,
            "status": "available",
            "description": getattr(agent, 'description', f"{agent_id} agent"),
            "capabilities": getattr(agent, 'capabilities', []),
            "configuration": getattr(agent, 'config', {}),
            "statistics": {
                "total_requests": 0,  # Would need to track this
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_response_time": 0,
            }
        }
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Agent system not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent details: {str(e)}")


@agents_router.post("/{agent_id}/execute")
async def execute_with_agent(
    request: Request, 
    agent_id: str, 
    execute_request: ExecuteRequest
) -> Dict[str, Any]:
    """Execute a prompt with a specific agent."""
    try:
        from ...agents.pool import AgentPool
        
        pool = AgentPool()
        agent = pool.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Execute the prompt with the agent
        start_time = datetime.now()
        
        # This would need to be implemented in the agent interface
        result = agent.execute(execute_request.prompt, execute_request.context)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "agent_id": agent_id,
            "prompt": execute_request.prompt,
            "result": result,
            "execution_time": execution_time,
            "timestamp": start_time.isoformat(),
            "status": "completed"
        }
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Agent system not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute with agent: {str(e)}")


@agents_router.get("/routing/strategies")
async def get_routing_strategies(request: Request) -> List[Dict[str, Any]]:
    """Get available routing strategies."""
    try:
        from ...agents.router import AgentRouter
        
        router = AgentRouter()
        strategies = router.get_available_strategies()
        
        return [
            {
                "name": strategy,
                "description": f"Route using {strategy} strategy",
                "active": strategy == router.get_current_strategy()
            }
            for strategy in strategies
        ]
        
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get routing strategies: {str(e)}")


@agents_router.post("/routing/strategy")
async def set_routing_strategy(
    request: Request, 
    strategy_request: Dict[str, str]
) -> Dict[str, str]:
    """Set the active routing strategy."""
    strategy = strategy_request.get("strategy")
    
    if not strategy:
        raise HTTPException(status_code=400, detail="Strategy name required")
    
    try:
        from ...agents.router import AgentRouter
        
        router = AgentRouter()
        success = router.set_strategy(strategy)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")
        
        return {"message": f"Routing strategy set to {strategy}"}
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Agent system not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set routing strategy: {str(e)}")


@agents_router.get("/timeline")
async def get_agent_timeline(request: Request) -> List[Dict[str, Any]]:
    """Get agent execution timeline."""
    try:
        # This would need to be tracked by the agent system
        # For now, return empty timeline
        return []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent timeline: {str(e)}")


@agents_router.post("/{agent_id}/toggle")
async def toggle_agent(
    request: Request,
    agent_id: str,
    toggle_request: ToggleAgentRequest
) -> Dict[str, Any]:
    """Toggle an agent's enabled status."""
    try:
        manager = get_orchestration_manager()
        await manager.initialize()
        
        success = await manager.toggle_agent(agent_id, toggle_request.enabled)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Broadcast update via WebSocket
        from .websocket import broadcast_message
        await broadcast_message({
            "type": "agent_toggled",
            "agent_id": agent_id,
            "enabled": toggle_request.enabled,
            "timestamp": datetime.now().isoformat()
        }, "agents")
        
        return {
            "agent_id": agent_id,
            "enabled": toggle_request.enabled,
            "message": f"Agent {agent_id} {'enabled' if toggle_request.enabled else 'disabled'}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle agent: {str(e)}")


@agents_router.post("/create")
async def create_custom_agent(
    request: Request,
    create_request: CreateAgentRequest
) -> Dict[str, Any]:
    """Create a new custom agent."""
    try:
        manager = get_orchestration_manager()
        await manager.initialize()
        
        agent = AgentConfig(
            name=create_request.name,
            description=create_request.description,
            capabilities=create_request.capabilities,
            usage_instructions=create_request.usage_instructions,
            priority=create_request.priority
        )
        
        success = await manager.add_custom_agent(agent)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Agent {create_request.name} already exists")
        
        return {
            "agent_id": create_request.name,
            "message": f"Custom agent {create_request.name} created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@agents_router.delete("/{agent_id}")
async def delete_agent(request: Request, agent_id: str) -> Dict[str, str]:
    """Delete a custom agent."""
    try:
        manager = get_orchestration_manager()
        await manager.initialize()
        
        success = await manager.remove_agent(agent_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete agent {agent_id} (not found or built-in)"
            )
        
        return {"message": f"Agent {agent_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")


@agents_router.post("/hot-swap")
async def hot_swap_agents(
    request: Request,
    swap_request: HotSwapRequest
) -> Dict[str, Any]:
    """Perform a hot swap of the agent pool."""
    try:
        manager = get_orchestration_manager()
        await manager.initialize()
        
        await manager.hot_swap_agents(swap_request.agent_names)
        
        # Broadcast update via WebSocket
        from .websocket import broadcast_message
        await broadcast_message({
            "type": "agents_hot_swapped",
            "active_agents": swap_request.agent_names,
            "timestamp": datetime.now().isoformat()
        }, "agents")
        
        return {
            "active_agents": swap_request.agent_names,
            "message": f"Hot-swapped agent pool with {len(swap_request.agent_names)} agents"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to hot-swap agents: {str(e)}")


@agents_router.get("/orchestration/status")
async def get_orchestration_status(request: Request) -> Dict[str, Any]:
    """Get the current orchestration status."""
    try:
        manager = get_orchestration_manager()
        await manager.initialize()
        
        status = await manager.get_agent_status()
        
        return {
            "total_agents": status["total_count"],
            "active_agents": status["active_count"],
            "agents": status["agents"],
            "claude_md_path": str(manager.claude_md_path),
            "claude_md_exists": manager.claude_md_path.exists(),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orchestration status: {str(e)}")