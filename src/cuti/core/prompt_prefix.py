"""Prompt prefix management for cuti."""

import json
from pathlib import Path
from typing import Dict, Optional, List
from pydantic import BaseModel


class PromptPrefix(BaseModel):
    """Model for a prompt prefix configuration."""
    name: str
    description: str
    prompt: str
    tools: List[str]
    is_template: bool = False
    is_active: bool = False


class PromptPrefixManager:
    """Manages prompt prefixes and templates."""
    
    # Built-in templates
    TEMPLATES = [
        {
            "name": "Software Engineer",
            "description": "Professional software engineering assistant",
            "prompt": "You are an expert software engineer. Write clean, efficient, well-tested code following best practices.",
            "tools": [
                "Use version control (git) for all changes",
                "Write comprehensive tests for new features", 
                "Follow existing code style and conventions",
                "Document complex logic with clear comments",
                "Consider performance and scalability"
            ]
        },
        {
            "name": "Code Reviewer",
            "description": "Thorough code review and quality assurance",
            "prompt": "You are a senior code reviewer. Analyze code for bugs, security issues, and improvements.",
            "tools": [
                "Check for potential bugs and edge cases",
                "Identify security vulnerabilities",
                "Suggest performance optimizations",
                "Ensure code follows best practices",
                "Verify test coverage is adequate"
            ]
        },
        {
            "name": "DevOps Engineer",
            "description": "Infrastructure and deployment specialist",
            "prompt": "You are a DevOps expert. Focus on automation, CI/CD, monitoring, and infrastructure as code.",
            "tools": [
                "Automate repetitive tasks with scripts",
                "Set up CI/CD pipelines",
                "Configure monitoring and alerting",
                "Use containerization (Docker/Kubernetes)",
                "Apply infrastructure as code principles"
            ]
        },
        {
            "name": "Data Scientist",
            "description": "Data analysis and machine learning expert",
            "prompt": "You are a data scientist. Analyze data, build models, and provide insights.",
            "tools": [
                "Perform exploratory data analysis",
                "Build and evaluate ML models",
                "Create clear visualizations",
                "Document findings and methodology",
                "Use appropriate statistical methods"
            ]
        },
        {
            "name": "Debugger",
            "description": "Expert at finding and fixing bugs",
            "prompt": "You are a debugging specialist. Systematically identify and resolve issues.",
            "tools": [
                "Reproduce issues consistently",
                "Use debugging tools and logs",
                "Add diagnostic output",
                "Test fixes thoroughly",
                "Document root cause and solution"
            ]
        },
        {
            "name": "Minimal",
            "description": "Simple, no-frills assistant",
            "prompt": "Be concise and direct. Focus on solving the task efficiently.",
            "tools": [
                "Get to the point quickly",
                "Avoid unnecessary explanations",
                "Focus on the requested task"
            ]
        }
    ]
    
    def __init__(self, config_dir: Path = None):
        """Initialize the prompt prefix manager."""
        self.config_dir = config_dir or Path.home() / ".cuti"
        self.config_dir.mkdir(exist_ok=True)
        self.prefix_file = self.config_dir / "prompt_prefix.json"
        self.custom_prefixes_file = self.config_dir / "custom_prefixes.json"
        self._ensure_files()
    
    def _ensure_files(self):
        """Ensure prefix files exist."""
        if not self.prefix_file.exists():
            # Create default prefix file with no active prefix
            self.save_active_prefix(None)
        
        if not self.custom_prefixes_file.exists():
            # Create empty custom prefixes file
            with open(self.custom_prefixes_file, 'w') as f:
                json.dump([], f)
    
    def get_templates(self) -> List[Dict]:
        """Get all available templates."""
        return self.TEMPLATES
    
    def get_custom_prefixes(self) -> List[Dict]:
        """Get all custom prefixes."""
        try:
            with open(self.custom_prefixes_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def save_custom_prefix(self, prefix: Dict) -> bool:
        """Save a custom prefix."""
        try:
            prefixes = self.get_custom_prefixes()
            
            # Check if prefix with same name exists
            existing_index = next((i for i, p in enumerate(prefixes) if p['name'] == prefix['name']), None)
            
            if existing_index is not None:
                # Update existing
                prefixes[existing_index] = prefix
            else:
                # Add new
                prefixes.append(prefix)
            
            with open(self.custom_prefixes_file, 'w') as f:
                json.dump(prefixes, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving custom prefix: {e}")
            return False
    
    def delete_custom_prefix(self, name: str) -> bool:
        """Delete a custom prefix."""
        try:
            prefixes = self.get_custom_prefixes()
            prefixes = [p for p in prefixes if p['name'] != name]
            
            with open(self.custom_prefixes_file, 'w') as f:
                json.dump(prefixes, f, indent=2)
            
            # If this was the active prefix, clear it
            active = self.get_active_prefix()
            if active and active.get('name') == name:
                self.save_active_prefix(None)
            
            return True
        except:
            return False
    
    def get_active_prefix(self) -> Optional[Dict]:
        """Get the currently active prefix."""
        try:
            with open(self.prefix_file, 'r') as f:
                data = json.load(f)
                return data.get('active_prefix')
        except:
            return None
    
    def save_active_prefix(self, prefix: Optional[Dict]) -> bool:
        """Save the active prefix."""
        try:
            data = {
                'active_prefix': prefix,
                'enabled': prefix is not None
            }
            
            with open(self.prefix_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except:
            return False
    
    def format_prefix_for_chat(self, prefix: Dict) -> str:
        """Format a prefix for use in chat."""
        if not prefix:
            return ""
        
        lines = [prefix['prompt']]
        
        if prefix.get('tools'):
            lines.append("\nKey guidelines:")
            for tool in prefix['tools']:
                lines.append(f"- {tool}")
        
        return "\n".join(lines)
    
    def get_all_prefixes(self) -> Dict:
        """Get all templates and custom prefixes."""
        return {
            'templates': self.get_templates(),
            'custom': self.get_custom_prefixes(),
            'active': self.get_active_prefix()
        }