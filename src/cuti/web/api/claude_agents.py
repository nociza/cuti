"""
API endpoints for Claude Code agent management.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


# Pydantic models for request/response
class AgentCreate(BaseModel):
    name: str
    description: str
    prompt: str
    capabilities: List[str] = []
    tools: List[str] = []
    context_files: List[str] = []
    working_directory: Optional[str] = None
    environment: Dict[str, str] = {}


class AgentUpdate(BaseModel):
    description: Optional[str] = None
    prompt: Optional[str] = None
    capabilities: Optional[List[str]] = None
    tools: Optional[List[str]] = None
    context_files: Optional[List[str]] = None
    working_directory: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


class AgentResponse(BaseModel):
    name: str
    description: str
    prompt: str
    capabilities: List[str]
    tools: List[str]
    context_files: List[str]
    working_directory: Optional[str]
    environment: Dict[str, str]
    created_at: Optional[str]
    updated_at: Optional[str]


claude_agents_router = APIRouter(prefix="/claude-agents", tags=["claude-agents"])


@claude_agents_router.get("/", response_model=List[AgentResponse])
async def list_agents(request: Request) -> List[Dict[str, Any]]:
    """List all available Claude Code agents."""
    agent_manager = request.app.state.claude_agent_manager
    agents = agent_manager.list_agents()
    return [agent.to_dict() for agent in agents]


@claude_agents_router.get("/{agent_name}", response_model=AgentResponse)
async def get_agent(request: Request, agent_name: str) -> Dict[str, Any]:
    """Get a specific agent by name."""
    agent_manager = request.app.state.claude_agent_manager
    agent = agent_manager.get_agent(agent_name)
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    return agent.to_dict()


@claude_agents_router.post("/", response_model=AgentResponse)
async def create_agent(request: Request, agent_data: AgentCreate) -> Dict[str, Any]:
    """Create a new Claude Code agent."""
    agent_manager = request.app.state.claude_agent_manager
    
    try:
        agent = agent_manager.create_agent(
            name=agent_data.name,
            description=agent_data.description,
            prompt=agent_data.prompt,
            capabilities=agent_data.capabilities,
            tools=agent_data.tools,
            context_files=agent_data.context_files,
            working_directory=agent_data.working_directory,
            environment=agent_data.environment,
        )
        return agent.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@claude_agents_router.put("/{agent_name}", response_model=AgentResponse)
async def update_agent(
    request: Request, 
    agent_name: str, 
    agent_data: AgentUpdate
) -> Dict[str, Any]:
    """Update an existing Claude Code agent."""
    agent_manager = request.app.state.claude_agent_manager
    
    try:
        agent = agent_manager.update_agent(
            name=agent_name,
            description=agent_data.description,
            prompt=agent_data.prompt,
            capabilities=agent_data.capabilities,
            tools=agent_data.tools,
            context_files=agent_data.context_files,
            working_directory=agent_data.working_directory,
            environment=agent_data.environment,
        )
        return agent.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@claude_agents_router.delete("/{agent_name}")
async def delete_agent(request: Request, agent_name: str) -> Dict[str, str]:
    """Delete a Claude Code agent."""
    agent_manager = request.app.state.claude_agent_manager
    
    try:
        agent_manager.delete_agent(agent_name)
        return {"message": f"Agent '{agent_name}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@claude_agents_router.get("/search/{query}", response_model=List[AgentResponse])
async def search_agents(request: Request, query: str) -> List[Dict[str, Any]]:
    """Search agents by name, description, or capabilities."""
    agent_manager = request.app.state.claude_agent_manager
    agents = agent_manager.search_agents(query)
    return [agent.to_dict() for agent in agents]


@claude_agents_router.get("/suggestions/{prefix}")
async def get_suggestions(request: Request, prefix: str) -> List[Dict[str, str]]:
    """Get agent suggestions for autocomplete."""
    agent_manager = request.app.state.claude_agent_manager
    return agent_manager.get_agent_suggestions(prefix)