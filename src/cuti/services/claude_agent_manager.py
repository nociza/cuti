"""
Claude Code Agent Manager - Reads and manages Claude Code agents from .claude/agents directories.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess
import asyncio


class ClaudeAgent:
    """Represents a Claude Code agent from markdown files."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        prompt: str = "",
        file_path: Optional[Path] = None,
        is_local: bool = False,
        **kwargs
    ):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.file_path = file_path
        self.is_local = is_local
        # Extract capabilities and tools from prompt if available
        self.capabilities = self._extract_capabilities(prompt)
        self.tools = self._extract_tools(prompt)
    
    def _extract_capabilities(self, prompt: str) -> List[str]:
        """Extract capabilities from the agent prompt."""
        capabilities = []
        # Look for common capability keywords
        capability_keywords = [
            'code review', 'testing', 'documentation', 'refactoring', 
            'debugging', 'security', 'performance', 'design', 'architecture'
        ]
        prompt_lower = prompt.lower()
        for keyword in capability_keywords:
            if keyword in prompt_lower:
                capabilities.append(keyword.replace(' ', '-'))
        return capabilities
    
    def _extract_tools(self, prompt: str) -> List[str]:
        """Extract mentioned tools from the agent prompt."""
        tools = []
        # Look for tool mentions
        tool_keywords = ['read', 'write', 'edit', 'bash', 'grep', 'search']
        prompt_lower = prompt.lower()
        for tool in tool_keywords:
            if tool in prompt_lower:
                tools.append(tool)
        return tools
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "is_local": self.is_local,
            "file_path": str(self.file_path) if self.file_path else None
        }


class ClaudeCodeAgentManager:
    """Manages Claude Code agents from .claude/agents directories."""
    
    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the agent manager."""
        self.working_dir = Path(working_directory) if working_directory else Path.cwd()
        self.local_agents_dir = self.working_dir / ".claude" / "agents"
        self.global_agents_dir = Path.home() / ".claude" / "agents"
        self.agents: Dict[str, ClaudeAgent] = {}
        self._load_agents()
    
    def _load_agents(self):
        """Load agents from both local and global directories."""
        self.agents = {}
        
        # Load global agents first
        if self.global_agents_dir.exists():
            for agent_file in self.global_agents_dir.glob("*.md"):
                agent = self._parse_agent_file(agent_file, is_local=False)
                if agent:
                    self.agents[agent.name] = agent
        
        # Load local agents (override global if same name)
        if self.local_agents_dir.exists():
            for agent_file in self.local_agents_dir.glob("*.md"):
                agent = self._parse_agent_file(agent_file, is_local=True)
                if agent:
                    self.agents[agent.name] = agent
    
    def _parse_agent_file(self, file_path: Path, is_local: bool) -> Optional[ClaudeAgent]:
        """Parse an agent markdown file."""
        try:
            content = file_path.read_text()
            name = file_path.stem
            
            # Extract description from first heading or first paragraph
            description = ""
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # Remove heading markers
                    description = re.sub(r'^#+\s*', '', line)
                    break
                elif line and not line.startswith('```'):
                    description = line
                    break
            
            # The entire content is the prompt
            prompt = content
            
            return ClaudeAgent(
                name=name,
                description=description or f"Agent: {name}",
                prompt=prompt,
                file_path=file_path,
                is_local=is_local
            )
        except Exception as e:
            print(f"Error parsing agent file {file_path}: {e}")
            return None
    
    def reload_agents(self):
        """Reload agents from disk."""
        self._load_agents()
    
    def list_agents(self) -> List[ClaudeAgent]:
        """List all available agents."""
        return list(self.agents.values())
    
    def get_agent(self, name: str) -> Optional[ClaudeAgent]:
        """Get a specific agent by name."""
        return self.agents.get(name)
    
    def search_agents(self, query: str) -> List[ClaudeAgent]:
        """Search agents by name or description."""
        query_lower = query.lower()
        results = []
        
        for agent in self.agents.values():
            if (query_lower in agent.name.lower() or 
                query_lower in agent.description.lower()):
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
                    "command": f"@{agent.name}",
                    "is_local": agent.is_local
                })
        else:
            # Filter by prefix
            prefix_lower = prefix.lower()
            for agent in self.agents.values():
                if agent.name.lower().startswith(prefix_lower):
                    suggestions.append({
                        "name": agent.name,
                        "description": agent.description,
                        "command": f"@{agent.name}",
                        "is_local": agent.is_local
                    })
        
        return suggestions[:8]  # Limit to 8 suggestions
    
    async def create_agent_with_claude(self, name: str, description: str) -> Dict[str, Any]:
        """Create an agent using Claude Code's /agent command."""
        try:
            # Ensure the local agents directory exists
            self.local_agents_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a simple prompt that Claude will flesh out
            agent_prompt = f"Create an agent named '{name}' that {description}"
            
            # Use Claude Code's /agent command to create the agent
            # This will create the agent file in .claude/agents/
            process = await asyncio.create_subprocess_exec(
                'claude',
                '--no-interactive',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir)
            )
            
            # Send the /agent command
            command = f"/agent {name}\n{description}\n"
            stdout, stderr = await process.communicate(command.encode())
            
            # Wait a moment for file creation
            await asyncio.sleep(1)
            
            # Reload agents to pick up the new one
            self.reload_agents()
            
            # Check if the agent was created
            agent = self.get_agent(name)
            if agent:
                return {
                    "success": True,
                    "agent": agent.to_dict(),
                    "message": f"Agent '{name}' created successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to create agent: {stderr.decode() if stderr else 'Unknown error'}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating agent: {str(e)}"
            }
    
    def delete_agent(self, name: str) -> Dict[str, Any]:
        """Delete an agent file."""
        agent = self.get_agent(name)
        if not agent:
            return {
                "success": False,
                "message": f"Agent '{name}' not found"
            }
        
        if not agent.file_path or not agent.file_path.exists():
            return {
                "success": False,
                "message": f"Agent file not found"
            }
        
        try:
            # Only allow deleting local agents
            if not agent.is_local:
                return {
                    "success": False,
                    "message": "Cannot delete global agents. Only local agents can be deleted."
                }
            
            # Delete the file
            agent.file_path.unlink()
            
            # Reload agents
            self.reload_agents()
            
            return {
                "success": True,
                "message": f"Agent '{name}' deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting agent: {str(e)}"
            }
    
    def update_agent(self, name: str, new_content: str) -> Dict[str, Any]:
        """Update an agent's content."""
        agent = self.get_agent(name)
        if not agent:
            return {
                "success": False,
                "message": f"Agent '{name}' not found"
            }
        
        if not agent.is_local:
            return {
                "success": False,
                "message": "Cannot edit global agents. Only local agents can be modified."
            }
        
        try:
            # Write the new content
            agent.file_path.write_text(new_content)
            
            # Reload agents
            self.reload_agents()
            
            return {
                "success": True,
                "message": f"Agent '{name}' updated successfully",
                "agent": self.get_agent(name).to_dict()
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating agent: {str(e)}"
            }