"""
Agents API endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

agents_router = APIRouter(prefix="/agents", tags=["agents"])


class ExecuteRequest(BaseModel):
    prompt: str
    context: Optional[Dict[str, Any]] = None


@agents_router.get("")
async def get_agents(request: Request) -> List[Dict[str, Any]]:
    """Get list of available agents."""
    try:
        # Try to import agent system
        from ...agents.pool import AgentPool
        
        pool = AgentPool()
        agent_names = pool.get_available_agents()
        
        agents = []
        for name in agent_names:
            agent = pool.get_agent(name)
            if agent:
                agents.append({
                    "id": name,
                    "name": name,
                    "type": agent.__class__.__name__,
                    "status": "available",
                    "description": getattr(agent, 'description', f"{name} agent"),
                    "capabilities": getattr(agent, 'capabilities', []),
                    "last_used": None,  # Would need to track this
                })
        
        return agents
        
    except ImportError:
        # Agent system not available
        return []
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