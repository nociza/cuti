"""
Tools management API endpoints.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/tools", tags=["tools"])


class Tool(BaseModel):
    """Tool configuration model."""
    name: str
    display_name: str
    description: str
    install_command: str
    check_command: str
    usage_instructions: str
    category: str
    enabled: bool = False
    installed: bool = False
    auto_install: bool = False


class ToolToggleRequest(BaseModel):
    """Request to toggle a tool."""
    name: str
    enabled: bool
    auto_install: Optional[bool] = False


# Predefined tools list
AVAILABLE_TOOLS = [
    {
        "name": "ast-grep",
        "display_name": "AST Grep",
        "description": "Structural search and replace tool for code",
        "install_command": "sudo npm install --global --force @ast-grep/cli",
        "check_command": "ast-grep --version",
        "usage_instructions": "Use `ast-grep` to search code by AST patterns. Example: `ast-grep --pattern 'console.log($$$)'`",
        "category": "Code Analysis"
    },
    {
        "name": "ripgrep",
        "display_name": "Ripgrep (rg)",
        "description": "Fast recursive grep with smart defaults",
        "install_command": "sudo apt-get update && sudo apt-get install -y ripgrep",
        "check_command": "rg --version",
        "usage_instructions": "Use `rg` for fast text search. Example: `rg 'pattern' --type python`",
        "category": "Search"
    },
    {
        "name": "fd",
        "display_name": "fd",
        "description": "Fast and user-friendly alternative to find",
        "install_command": "sudo apt-get update && sudo apt-get install -y fd-find && sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd",
        "check_command": "fd --version || fdfind --version",
        "usage_instructions": "Use `fd` to find files and directories. Example: `fd '.*\\.py$'`",
        "category": "File Management"
    },
    {
        "name": "jq",
        "display_name": "jq",
        "description": "Command-line JSON processor",
        "install_command": "sudo apt-get update && sudo apt-get install -y jq",
        "check_command": "jq --version",
        "usage_instructions": "Use `jq` to process JSON data. Example: `cat data.json | jq '.items[]'`",
        "category": "Data Processing"
    },
    {
        "name": "tree",
        "display_name": "Tree",
        "description": "Display directory structure as a tree",
        "install_command": "sudo apt-get update && sudo apt-get install -y tree",
        "check_command": "tree --version",
        "usage_instructions": "Use `tree` to visualize directory structure. Example: `tree -L 2`",
        "category": "File Management"
    },
    {
        "name": "bat",
        "display_name": "Bat",
        "description": "Cat clone with syntax highlighting",
        "install_command": "sudo apt-get update && sudo apt-get install -y bat",
        "check_command": "batcat --version",
        "usage_instructions": "Use `bat` to view files with syntax highlighting. Example: `bat file.py`",
        "category": "File Viewing"
    },
    {
        "name": "httpie",
        "display_name": "HTTPie",
        "description": "Modern command-line HTTP client",
        "install_command": "sudo pip install httpie",
        "check_command": "http --version",
        "usage_instructions": "Use `http` for HTTP requests. Example: `http GET api.example.com/users`",
        "category": "Network"
    },
    {
        "name": "gh",
        "display_name": "GitHub CLI",
        "description": "GitHub's official command line tool",
        "install_command": "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && echo 'deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && sudo apt update && sudo apt install gh -y",
        "check_command": "gh --version",
        "usage_instructions": "Use `gh` for GitHub operations. Example: `gh pr create --title 'New feature'`",
        "category": "Version Control"
    },
    {
        "name": "tokei",
        "display_name": "Tokei",
        "description": "Count lines of code quickly",
        "install_command": "sudo cargo install tokei --root /usr/local",
        "check_command": "tokei --version",
        "usage_instructions": "Use `tokei` to count lines of code. Example: `tokei --exclude '*.min.js'`",
        "category": "Code Analysis"
    },
    {
        "name": "lazygit",
        "display_name": "LazyGit",
        "description": "Terminal UI for git commands",
        "install_command": "LAZYGIT_VERSION=$(curl -s 'https://api.github.com/repos/jesseduffield/lazygit/releases/latest' | grep -Po '\"tag_name\": \"v\\K[0-9.]+') && curl -Lo lazygit.tar.gz \"https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz\" && sudo tar xf lazygit.tar.gz -C /usr/local/bin lazygit && rm lazygit.tar.gz",
        "check_command": "lazygit --version",
        "usage_instructions": "Use `lazygit` for interactive git operations. Just run `lazygit` in a git repository.",
        "category": "Version Control"
    },
    {
        "name": "tldr",
        "display_name": "TLDR Pages",
        "description": "Simplified man pages with practical examples",
        "install_command": "sudo pip install tldr",
        "check_command": "tldr --version",
        "usage_instructions": "Use `tldr` for quick command examples. Example: `tldr tar`",
        "category": "Documentation"
    },
    {
        "name": "ncdu",
        "display_name": "NCurses Disk Usage",
        "description": "Interactive disk usage analyzer",
        "install_command": "sudo apt-get update && sudo apt-get install -y ncdu",
        "check_command": "ncdu --version",
        "usage_instructions": "Use `ncdu` to analyze disk usage. Example: `ncdu /workspace`",
        "category": "System"
    }
]


def get_tools_config_path() -> Path:
    """Get the path to the tools configuration file."""
    config_dir = Path.home() / ".cuti"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "tools_config.json"


def get_container_tools_path() -> Path:
    """Get the path to the container tools setup file."""
    return Path("/workspace/.cuti/container_tools.sh")


def load_tools_config() -> Dict[str, Any]:
    """Load tools configuration from file."""
    config_path = get_tools_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"enabled_tools": [], "auto_install": []}


def save_tools_config(config: Dict[str, Any]):
    """Save tools configuration to file."""
    config_path = get_tools_config_path()
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def check_tool_installed(check_command: str) -> bool:
    """Check if a tool is installed by running its check command."""
    try:
        result = subprocess.run(
            check_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def update_claude_md(tools: List[Dict[str, Any]]):
    """Update CLAUDE.md with enabled tools information."""
    claude_md_path = Path("/workspace/CLAUDE.md")
    
    if not claude_md_path.exists():
        return
    
    try:
        with open(claude_md_path, 'r') as f:
            content = f.read()
        
        # Find or create tools section
        tools_section_start = content.find("## Available CLI Tools")
        tools_section_end = content.find("\n## ", tools_section_start + 1) if tools_section_start != -1 else -1
        
        # Build new tools section
        tools_content = "\n## Available CLI Tools\n\n"
        tools_content += "The following CLI tools are available in the development environment:\n\n"
        
        enabled_tools = [t for t in tools if t.get('enabled') and t.get('installed')]
        
        if enabled_tools:
            for tool in enabled_tools:
                tools_content += f"### {tool['display_name']}\n"
                tools_content += f"{tool['description']}\n\n"
                tools_content += f"{tool['usage_instructions']}\n\n"
        else:
            tools_content += "*No additional CLI tools are currently enabled.*\n\n"
        
        # Replace or append tools section
        if tools_section_start != -1:
            if tools_section_end != -1:
                new_content = content[:tools_section_start] + tools_content + content[tools_section_end:]
            else:
                new_content = content[:tools_section_start] + tools_content
        else:
            # Append before the last section or at the end
            last_section = content.rfind("\n# ")
            if last_section != -1:
                new_content = content[:last_section] + "\n" + tools_content + content[last_section:]
            else:
                new_content = content + "\n" + tools_content
        
        with open(claude_md_path, 'w') as f:
            f.write(new_content)
            
    except Exception as e:
        print(f"Error updating CLAUDE.md: {e}")


def update_container_setup(tools: List[Dict[str, Any]]):
    """Update container setup script with auto-install tools."""
    setup_path = get_container_tools_path()
    setup_path.parent.mkdir(parents=True, exist_ok=True)
    
    auto_install_tools = [t for t in tools if t.get('auto_install')]
    
    script_content = "#!/bin/bash\n"
    script_content += "# Auto-generated container tools setup\n"
    script_content += "# This file is managed by the tools management system\n\n"
    
    if auto_install_tools:
        script_content += "echo 'Installing additional CLI tools...'\n\n"
        for tool in auto_install_tools:
            script_content += f"# Install {tool['display_name']}\n"
            script_content += f"echo 'Installing {tool['display_name']}...'\n"
            script_content += f"if ! {tool['check_command']} &>/dev/null; then\n"
            script_content += f"  {tool['install_command']}\n"
            script_content += f"else\n"
            script_content += f"  echo '{tool['display_name']} already installed'\n"
            script_content += f"fi\n\n"
    else:
        script_content += "# No tools configured for auto-installation\n"
    
    with open(setup_path, 'w') as f:
        f.write(script_content)
    
    # Make script executable
    setup_path.chmod(0o755)


@router.get("/list")
async def list_tools(request: Request) -> List[Dict[str, Any]]:
    """List all available tools with their status."""
    config = load_tools_config()
    tools = []
    
    for tool_def in AVAILABLE_TOOLS:
        tool = tool_def.copy()
        tool["enabled"] = tool["name"] in config.get("enabled_tools", [])
        tool["auto_install"] = tool["name"] in config.get("auto_install", [])
        tool["installed"] = check_tool_installed(tool["check_command"])
        tools.append(tool)
    
    return tools


@router.post("/toggle")
async def toggle_tool(request: Request, toggle_request: ToolToggleRequest) -> Dict[str, Any]:
    """Toggle a tool on or off."""
    config = load_tools_config()
    enabled_tools = set(config.get("enabled_tools", []))
    auto_install = set(config.get("auto_install", []))
    
    # Find the tool
    tool = None
    for t in AVAILABLE_TOOLS:
        if t["name"] == toggle_request.name:
            tool = t.copy()
            break
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Check if tool is installed
    tool["installed"] = check_tool_installed(tool["check_command"])
    
    # Update enabled status
    if toggle_request.enabled:
        enabled_tools.add(toggle_request.name)
        if not tool["installed"]:
            # Tool needs to be installed
            return {
                "success": False,
                "needs_install": True,
                "tool": tool
            }
    else:
        enabled_tools.discard(toggle_request.name)
    
    # Update auto-install status
    if toggle_request.auto_install:
        auto_install.add(toggle_request.name)
    else:
        auto_install.discard(toggle_request.name)
    
    # Save configuration
    config["enabled_tools"] = list(enabled_tools)
    config["auto_install"] = list(auto_install)
    save_tools_config(config)
    
    # Update CLAUDE.md
    tools = await list_tools(request)
    update_claude_md(tools)
    
    # Update container setup if needed
    if toggle_request.auto_install:
        update_container_setup(tools)
    
    return {
        "success": True,
        "tool": tool,
        "enabled": toggle_request.enabled
    }


@router.post("/install")
async def install_tool(request: Request, tool_name: str, auto_install: bool = False) -> Dict[str, Any]:
    """Install a tool in the container."""
    # Find the tool
    tool = None
    for t in AVAILABLE_TOOLS:
        if t["name"] == tool_name:
            tool = t
            break
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    try:
        # Get the install command
        install_cmd = tool["install_command"]
        
        # For all commands that need sudo (which is most of them), we need to ensure
        # the subprocess runs with proper privileges
        # We'll use sudo -S and pass it through stdin to avoid issues
        if "sudo" in install_cmd:
            # Remove any existing sudo from the command since we'll add it at the subprocess level
            install_cmd = install_cmd.replace("sudo ", "")
            # Use sudo with -E to preserve environment
            cmd_list = ["sudo", "-E", "bash", "-c", install_cmd]
            # Run with sudo
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"}  # Non-interactive for apt
            )
        else:
            # Run without sudo for commands that don't need it
            result = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"}  # Non-interactive for apt
            )
        
        if result.returncode == 0:
            # Update configuration
            config = load_tools_config()
            enabled_tools = set(config.get("enabled_tools", []))
            auto_install_tools = set(config.get("auto_install", []))
            
            enabled_tools.add(tool_name)
            if auto_install:
                auto_install_tools.add(tool_name)
            
            config["enabled_tools"] = list(enabled_tools)
            config["auto_install"] = list(auto_install_tools)
            save_tools_config(config)
            
            # Update CLAUDE.md and container setup
            tools = await list_tools(request)
            update_claude_md(tools)
            if auto_install:
                update_container_setup(tools)
            
            return {
                "success": True,
                "message": f"{tool['display_name']} installed successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Installation failed: {result.stderr}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Installation timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/check/{tool_name}")
async def check_tool(tool_name: str) -> Dict[str, Any]:
    """Check if a specific tool is installed."""
    for tool in AVAILABLE_TOOLS:
        if tool["name"] == tool_name:
            installed = check_tool_installed(tool["check_command"])
            return {
                "name": tool_name,
                "installed": installed
            }
    
    raise HTTPException(status_code=404, detail="Tool not found")