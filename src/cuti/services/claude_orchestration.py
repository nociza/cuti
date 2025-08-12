"""CLAUDE.md orchestration manager for dynamic agent pool configuration."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import asyncio
from dataclasses import dataclass, field

from cuti.utils.logger import get_logger
from cuti.utils.constants import BUILTIN_AGENTS_DIR

logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent in the orchestration system."""
    
    name: str
    enabled: bool = True
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    priority: int = 0
    usage_instructions: str = ""
    context_files: List[str] = field(default_factory=list)
    
    def to_claude_instruction(self) -> str:
        """Convert agent config to Claude instruction format."""
        instruction = f"@{self.name}: {self.description}"
        if self.capabilities:
            instruction += f"\n  Capabilities: {', '.join(self.capabilities)}"
        if self.usage_instructions:
            instruction += f"\n  Usage: {self.usage_instructions}"
        return instruction


class ClaudeOrchestrationManager:
    """Manages the CLAUDE.md file for dynamic agent orchestration."""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.claude_md_path = self.project_root / "CLAUDE.md"
        self.agents: Dict[str, AgentConfig] = {}
        self.active_agents: Set[str] = set()
        self._lock = asyncio.Lock()
        
        # Load built-in agents
        self._load_builtin_agents()
        
    def _load_builtin_agents(self):
        """Load built-in agent configurations."""
        builtin_agents = {
            "code-reviewer": AgentConfig(
                name="code-reviewer",
                description="Comprehensive code review with best practices and security analysis",
                capabilities=["code analysis", "security review", "performance optimization", "best practices"],
                usage_instructions="Use for reviewing code changes, PRs, or entire codebases"
            ),
            "docs-generator": AgentConfig(
                name="docs-generator",
                description="Automatic documentation generation for code and APIs",
                capabilities=["API docs", "code comments", "README generation", "docstrings"],
                usage_instructions="Use for creating or updating documentation"
            ),
            "test-writer": AgentConfig(
                name="test-writer",
                description="Comprehensive test suite creation",
                capabilities=["unit tests", "integration tests", "e2e tests", "test coverage"],
                usage_instructions="Use for writing tests for existing code"
            ),
            "refactor-assistant": AgentConfig(
                name="refactor-assistant",
                description="Code refactoring and modernization",
                capabilities=["code cleanup", "pattern implementation", "dependency updates"],
                usage_instructions="Use for improving code quality and structure"
            ),
            "ui-design-expert": AgentConfig(
                name="ui-design-expert",
                description="UI/UX design and frontend implementation",
                capabilities=["UI design", "CSS styling", "responsive design", "accessibility"],
                usage_instructions="Use for frontend development and design tasks"
            ),
            "gemini-codebase-analysis": AgentConfig(
                name="gemini-codebase-analysis",
                description="Deep codebase analysis using Gemini's large context window",
                capabilities=["large file analysis", "cross-file dependencies", "architecture review"],
                usage_instructions="Use for analyzing large codebases or complex systems"
            )
        }
        
        self.agents.update(builtin_agents)
        
    async def load_config(self, config_path: Optional[Path] = None):
        """Load agent configuration from file."""
        if config_path is None:
            config_path = self.project_root / ".cuti" / "agents.json"
            
        if not config_path.exists():
            # Initialize with default config
            await self.save_config(config_path)
            return
            
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                
            # Load active agents
            self.active_agents = set(data.get("active_agents", []))
            
            # Load custom agents
            for agent_data in data.get("custom_agents", []):
                agent = AgentConfig(**agent_data)
                self.agents[agent.name] = agent
                
            logger.info(f"Loaded {len(self.agents)} agents, {len(self.active_agents)} active")
            
        except Exception as e:
            logger.error(f"Failed to load agent config: {e}")
            
    async def save_config(self, config_path: Optional[Path] = None):
        """Save agent configuration to file."""
        if config_path is None:
            config_path = self.project_root / ".cuti" / "agents.json"
            
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            custom_agents = [
                {
                    "name": agent.name,
                    "enabled": agent.enabled,
                    "description": agent.description,
                    "capabilities": agent.capabilities,
                    "priority": agent.priority,
                    "usage_instructions": agent.usage_instructions,
                    "context_files": agent.context_files
                }
                for agent in self.agents.values()
                if not agent.name.startswith("builtin-")
            ]
            
            data = {
                "active_agents": list(self.active_agents),
                "custom_agents": custom_agents,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved agent config to {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save agent config: {e}")
            
    async def toggle_agent(self, agent_name: str, enabled: bool) -> bool:
        """Toggle an agent's active status."""
        async with self._lock:
            if agent_name not in self.agents:
                logger.warning(f"Agent {agent_name} not found")
                return False
                
            if enabled:
                self.active_agents.add(agent_name)
            else:
                self.active_agents.discard(agent_name)
                
            # Update CLAUDE.md file
            await self.update_claude_md()
            
            # Save configuration
            await self.save_config()
            
            logger.info(f"Agent {agent_name} {'enabled' if enabled else 'disabled'}")
            return True
            
    async def add_custom_agent(self, agent: AgentConfig) -> bool:
        """Add a custom agent to the orchestration system."""
        async with self._lock:
            if agent.name in self.agents:
                logger.warning(f"Agent {agent.name} already exists")
                return False
                
            self.agents[agent.name] = agent
            
            # Save configuration
            await self.save_config()
            
            logger.info(f"Added custom agent: {agent.name}")
            return True
            
    async def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent from the orchestration system."""
        async with self._lock:
            if agent_name not in self.agents:
                logger.warning(f"Agent {agent_name} not found")
                return False
                
            # Don't allow removing built-in agents
            if agent_name in ["code-reviewer", "docs-generator", "test-writer", 
                             "refactor-assistant", "ui-design-expert", "gemini-codebase-analysis"]:
                logger.warning(f"Cannot remove built-in agent {agent_name}")
                return False
                
            del self.agents[agent_name]
            self.active_agents.discard(agent_name)
            
            # Update CLAUDE.md file
            await self.update_claude_md()
            
            # Save configuration
            await self.save_config()
            
            logger.info(f"Removed agent: {agent_name}")
            return True
            
    async def update_claude_md(self):
        """Update the CLAUDE.md file with current agent configuration."""
        content = self._generate_claude_md_content()
        
        try:
            with open(self.claude_md_path, 'w') as f:
                f.write(content)
                
            logger.info(f"Updated CLAUDE.md with {len(self.active_agents)} active agents")
            
        except Exception as e:
            logger.error(f"Failed to update CLAUDE.md: {e}")
            
    def _generate_claude_md_content(self) -> str:
        """Generate the content for CLAUDE.md file."""
        lines = [
            "# Claude Code Configuration",
            "",
            "This file contains configuration and context for Claude Code usage within this project.",
            "It is dynamically managed by the cuti orchestration system.",
            "",
            f"Last updated: {datetime.now().isoformat()}",
            "",
            "## Overall Instructions",
            "",
            "You are a seasoned engineering manager and professional software engineer. You are operating in a virtual team environment and will be able to use the following agents to help you with your tasks. Use @ to mention an agent to ask it to do something.",
            "",
            "## Agents To Use",
            "",
            "You should use the following agents to help you with your tasks: ",
            ""
        ]
        
        if not self.active_agents:
            lines.append("*No agents currently active. Enable agents through the cuti web interface.*")
        else:
            # Sort agents by priority
            sorted_agents = sorted(
                [self.agents[name] for name in self.active_agents if name in self.agents],
                key=lambda a: (-a.priority, a.name)
            )
            
            for agent in sorted_agents:
                lines.append(f"### {agent.to_claude_instruction()}")
                lines.append("")
                
        lines.extend([
            "",
            "## Agent Usage Instructions",
            "",
            "To use an agent, mention it with @ followed by the agent name.",
            "For example: @code-reviewer please review this function",
            "",
            "Agents can be enabled/disabled through the cuti web interface at http://localhost:8000/agents",
            "",
            "## Development Commands",
            "",
            "### Setup and Installation",
            "```bash",
            "# Initial setup",
            "python run.py setup",
            "",
            "# Development installation with uv",
            "uv install -e .",
            "```",
            "",
            "### Running the Application",
            "```bash",
            "# Start web interface",
            "python run.py web",
            "",
            "# Start CLI",
            "python run.py cli",
            "",
            "# Check agent status",
            "cuti agent list",
            "```",
            "",
            "## Orchestration Configuration",
            "",
            "This file is automatically managed by the cuti orchestration system.",
            "Manual changes will be overwritten when agents are toggled or updated.",
            "",
            "To modify agent configuration:",
            "1. Use the web interface at http://localhost:8000/agents",
            "2. Use the CLI: `cuti agent toggle <agent-name>`",
            "3. Modify `.cuti/agents.json` and reload",
            ""
        ])
        
        return "\n".join(lines)
        
    async def get_agent_status(self) -> Dict:
        """Get the current status of all agents."""
        return {
            "agents": {
                name: {
                    "enabled": name in self.active_agents,
                    "description": agent.description,
                    "capabilities": agent.capabilities,
                    "priority": agent.priority
                }
                for name, agent in self.agents.items()
            },
            "active_count": len(self.active_agents),
            "total_count": len(self.agents)
        }
        
    async def hot_swap_agents(self, agent_names: List[str]):
        """Perform a hot swap of the agent pool."""
        async with self._lock:
            # Clear current active agents
            self.active_agents.clear()
            
            # Add new agents
            for name in agent_names:
                if name in self.agents:
                    self.active_agents.add(name)
                    
            # Update CLAUDE.md immediately
            await self.update_claude_md()
            
            # Save configuration
            await self.save_config()
            
            logger.info(f"Hot-swapped agent pool: {', '.join(self.active_agents)}")
            
    async def initialize(self):
        """Initialize the orchestration manager."""
        await self.load_config()
        await self.update_claude_md()
        logger.info("Claude orchestration manager initialized")