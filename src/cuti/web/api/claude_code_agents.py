"""
API endpoints for Claude Code agent management using actual .claude/agents directories.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


# Pydantic models for request/response
class AgentCreateSimple(BaseModel):
    name: str
    description: str


class AgentUpdate(BaseModel):
    content: str


class AgentResponse(BaseModel):
    name: str
    description: str
    prompt: str
    capabilities: List[str]
    tools: List[str]
    is_local: bool
    is_builtin: bool = False
    file_path: Optional[str]


claude_code_agents_router = APIRouter(prefix="/claude-code-agents", tags=["claude-code-agents"])


@claude_code_agents_router.get("/", response_model=List[AgentResponse])
async def list_agents(request: Request) -> List[Dict[str, Any]]:
    """List all available Claude Code agents from .claude/agents directories."""
    agent_manager = request.app.state.claude_code_agent_manager
    agent_manager.reload_agents()  # Reload to get latest from disk
    agents = agent_manager.list_agents()
    return [agent.to_dict() for agent in agents]


@claude_code_agents_router.get("/status")
async def get_agent_status(request: Request) -> Dict[str, Any]:
    """Get agent system status including Gemini availability."""
    agent_manager = request.app.state.claude_code_agent_manager
    return {
        "gemini_available": agent_manager.gemini_available,
        "total_agents": len(agent_manager.agents),
        "builtin_agents": sum(1 for a in agent_manager.agents.values() if a.is_builtin),
        "local_agents": sum(1 for a in agent_manager.agents.values() if a.is_local),
        "gemini_agents": sum(1 for a in agent_manager.agents.values() if a.agent_type == "gemini")
    }


@claude_code_agents_router.get("/{agent_name}", response_model=AgentResponse)
async def get_agent(request: Request, agent_name: str) -> Dict[str, Any]:
    """Get a specific agent by name."""
    agent_manager = request.app.state.claude_code_agent_manager
    agent = agent_manager.get_agent(agent_name)
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    return agent.to_dict()


@claude_code_agents_router.post("/create")
async def create_agent(request: Request, agent_data: AgentCreateSimple) -> Dict[str, Any]:
    """Create a new Claude Code agent using Claude's /agent command."""
    agent_manager = request.app.state.claude_code_agent_manager
    
    # Use Claude to flesh out the agent from the simple description
    result = await agent_manager.create_agent_with_claude(
        name=agent_data.name,
        description=agent_data.description
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@claude_code_agents_router.put("/{agent_name}")
async def update_agent(
    request: Request, 
    agent_name: str, 
    agent_data: AgentUpdate
) -> Dict[str, Any]:
    """Update an existing Claude Code agent (local agents only)."""
    agent_manager = request.app.state.claude_code_agent_manager
    
    result = agent_manager.update_agent(
        name=agent_name,
        new_content=agent_data.content
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@claude_code_agents_router.delete("/{agent_name}")
async def delete_agent(request: Request, agent_name: str) -> Dict[str, Any]:
    """Delete a Claude Code agent (local agents only)."""
    agent_manager = request.app.state.claude_code_agent_manager
    
    result = agent_manager.delete_agent(agent_name)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@claude_code_agents_router.get("/search/{query}", response_model=List[AgentResponse])
async def search_agents(request: Request, query: str) -> List[Dict[str, Any]]:
    """Search agents by name or description."""
    agent_manager = request.app.state.claude_code_agent_manager
    agents = agent_manager.search_agents(query)
    return [agent.to_dict() for agent in agents]


@claude_code_agents_router.get("/suggestions/{prefix}")
async def get_suggestions(request: Request, prefix: str) -> List[Dict[str, str]]:
    """Get agent suggestions for autocomplete."""
    agent_manager = request.app.state.claude_code_agent_manager
    return agent_manager.get_agent_suggestions(prefix)


@claude_code_agents_router.post("/reload")
async def reload_agents(request: Request) -> Dict[str, str]:
    """Reload agents from disk."""
    agent_manager = request.app.state.claude_code_agent_manager
    agent_manager.reload_agents()
    return {"message": "Agents reloaded successfully"}