"""
Claude Code Agent Manager - Manages custom AI agents for specialized tasks.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class Agent:
    """Represents a Claude Code agent configuration."""
    
    def __init__(
        self,
        name: str,
        description: str,
        prompt: str,
        capabilities: List[str] = None,
        tools: List[str] = None,
        context_files: List[str] = None,
        working_directory: Optional[str] = None,
        environment: Dict[str, str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs
    ):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.capabilities = capabilities or []
        self.tools = tools or []
        self.context_files = context_files or []
        self.working_directory = working_directory
        self.environment = environment or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "context_files": self.context_files,
            "working_directory": self.working_directory,
            "environment": self.environment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Create agent from dictionary."""
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class ClaudeAgentManager:
    """Manages Claude Code agents for specialized tasks."""
    
    # Default agents that come pre-configured
    DEFAULT_AGENTS = [
        {
            "name": "code-reviewer",
            "description": "Reviews code for quality, security, and best practices",
            "prompt": "Review the provided code for:\n- Code quality and style\n- Security vulnerabilities\n- Performance issues\n- Best practices\n- Potential bugs\n\nProvide constructive feedback with specific suggestions.",
            "capabilities": ["code-analysis", "security-review", "performance-analysis"],
            "tools": ["grep", "read", "edit"]
        },
        {
            "name": "test-writer",
            "description": "Writes comprehensive test suites",
            "prompt": "Write comprehensive tests for the provided code:\n- Unit tests\n- Integration tests where appropriate\n- Edge cases\n- Error handling\n\nUse the appropriate testing framework for the language.",
            "capabilities": ["test-generation", "coverage-analysis"],
            "tools": ["write", "read", "bash"]
        },
        {
            "name": "docs-generator",
            "description": "Generates and updates documentation",
            "prompt": "Generate or update documentation:\n- Function/class documentation\n- README files\n- API documentation\n- Usage examples\n\nEnsure documentation is clear, comprehensive, and follows best practices.",
            "capabilities": ["documentation", "markdown"],
            "tools": ["write", "read", "edit"]
        },
        {
            "name": "refactor-assistant",
            "description": "Helps refactor and improve code structure",
            "prompt": "Refactor the code to improve:\n- Readability\n- Maintainability\n- Performance\n- Code reuse\n- Design patterns\n\nExplain the reasoning behind each change.",
            "capabilities": ["refactoring", "design-patterns", "optimization"],
            "tools": ["read", "edit", "multi_edit"]
        },
        {
            "name": "bug-hunter",
            "description": "Identifies and fixes bugs in code",
            "prompt": "Analyze the code for bugs:\n- Logic errors\n- Edge cases\n- Race conditions\n- Memory leaks\n- Type errors\n\nProvide fixes with explanations.",
            "capabilities": ["debugging", "error-analysis"],
            "tools": ["read", "grep", "edit", "bash"]
        }
    ]
    
    def __init__(self, storage_dir: str = "~/.cuti"):
        """Initialize the agent manager."""
        self.storage_dir = Path(storage_dir).expanduser()
        self.agents_file = self.storage_dir / "agents.json"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load agents or initialize with defaults
        self.agents = self._load_agents()
    
    def _load_agents(self) -> Dict[str, Agent]:
        """Load agents from storage."""
        if self.agents_file.exists():
            try:
                with open(self.agents_file, 'r') as f:
                    data = json.load(f)
                    return {
                        name: Agent.from_dict(agent_data)
                        for name, agent_data in data.items()
                    }
            except Exception:
                pass
        
        # Initialize with default agents
        agents = {}
        for agent_data in self.DEFAULT_AGENTS:
            agent = Agent(**agent_data)
            agents[agent.name] = agent
        
        self._save_agents(agents)
        return agents
    
    def _save_agents(self, agents: Dict[str, Agent] = None):
        """Save agents to storage."""
        if agents is None:
            agents = self.agents
        
        data = {
            name: agent.to_dict()
            for name, agent in agents.items()
        }
        
        with open(self.agents_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def list_agents(self) -> List[Agent]:
        """List all available agents."""
        return list(self.agents.values())
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get a specific agent by name."""
        return self.agents.get(name)
    
    def create_agent(
        self,
        name: str,
        description: str,
        prompt: str,
        capabilities: List[str] = None,
        tools: List[str] = None,
        context_files: List[str] = None,
        working_directory: Optional[str] = None,
        environment: Dict[str, str] = None,
    ) -> Agent:
        """Create a new agent."""
        if name in self.agents:
            raise ValueError(f"Agent '{name}' already exists")
        
        agent = Agent(
            name=name,
            description=description,
            prompt=prompt,
            capabilities=capabilities,
            tools=tools,
            context_files=context_files,
            working_directory=working_directory,
            environment=environment,
        )
        
        self.agents[name] = agent
        self._save_agents()
        return agent
    
    def update_agent(
        self,
        name: str,
        description: Optional[str] = None,
        prompt: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        context_files: Optional[List[str]] = None,
        working_directory: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> Agent:
        """Update an existing agent."""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
        
        agent = self.agents[name]
        
        if description is not None:
            agent.description = description
        if prompt is not None:
            agent.prompt = prompt
        if capabilities is not None:
            agent.capabilities = capabilities
        if tools is not None:
            agent.tools = tools
        if context_files is not None:
            agent.context_files = context_files
        if working_directory is not None:
            agent.working_directory = working_directory
        if environment is not None:
            agent.environment = environment
        
        agent.updated_at = datetime.now()
        self._save_agents()
        return agent
    
    def delete_agent(self, name: str):
        """Delete an agent."""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
        
        # Don't allow deleting default agents
        if any(a["name"] == name for a in self.DEFAULT_AGENTS):
            raise ValueError(f"Cannot delete default agent '{name}'")
        
        del self.agents[name]
        self._save_agents()
    
    def search_agents(self, query: str) -> List[Agent]:
        """Search agents by name or description."""
        query_lower = query.lower()
        results = []
        
        for agent in self.agents.values():
            if (query_lower in agent.name.lower() or 
                query_lower in agent.description.lower() or
                any(query_lower in cap.lower() for cap in agent.capabilities)):
                results.append(agent)
        
        return results
    
    def get_agent_suggestions(self, prefix: str) -> List[Dict[str, str]]:
        """Get agent suggestions for autocomplete."""
        suggestions = []
        
        if prefix == '_all' or prefix == '':
            # Return all agents if no prefix
            for agent in self.agents.values():
                suggestions.append({
                    "name": agent.name,
                    "description": agent.description,
                    "command": f"@{agent.name}"
                })
        else:
            # Filter by prefix
            prefix_lower = prefix.lower()
            for agent in self.agents.values():
                if agent.name.lower().startswith(prefix_lower):
                    suggestions.append({
                        "name": agent.name,
                        "description": agent.description,
                        "command": f"@{agent.name}"
                    })
        
        return suggestions[:8]  # Limit to 8 suggestions