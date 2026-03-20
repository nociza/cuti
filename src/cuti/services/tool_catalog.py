"""Shared tool catalog and configuration helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

AVAILABLE_TOOLS: List[Dict[str, str]] = [
    {
        "name": "ast-grep",
        "display_name": "AST Grep",
        "description": "Structural search and replace tool for code",
        "install_command": "sudo npm install --global --force @ast-grep/cli",
        "check_command": "ast-grep --version",
        "usage_instructions": "Use `ast-grep` to search code by AST patterns. Example: `ast-grep --pattern 'console.log($$$)'`",
        "category": "Code Analysis",
    },
    {
        "name": "ripgrep",
        "display_name": "Ripgrep (rg)",
        "description": "Fast recursive grep with smart defaults",
        "install_command": "sudo apt-get update && sudo apt-get install -y ripgrep",
        "check_command": "rg --version",
        "usage_instructions": "Use `rg` for fast text search. Example: `rg 'pattern' --type python`",
        "category": "Search",
    },
    {
        "name": "fd",
        "display_name": "fd",
        "description": "Fast and user-friendly alternative to find",
        "install_command": "sudo apt-get update && sudo apt-get install -y fd-find && sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd",
        "check_command": "fd --version || fdfind --version",
        "usage_instructions": "Use `fd` to find files and directories. Example: `fd '.*\\.py$'`",
        "category": "File Management",
    },
    {
        "name": "jq",
        "display_name": "jq",
        "description": "Command-line JSON processor",
        "install_command": "sudo apt-get update && sudo apt-get install -y jq",
        "check_command": "jq --version",
        "usage_instructions": "Use `jq` to process JSON data. Example: `cat data.json | jq '.items[]'`",
        "category": "Data Processing",
    },
    {
        "name": "tree",
        "display_name": "Tree",
        "description": "Display directory structure as a tree",
        "install_command": "sudo apt-get update && sudo apt-get install -y tree",
        "check_command": "tree --version",
        "usage_instructions": "Use `tree` to visualize directory structure. Example: `tree -L 2`",
        "category": "File Management",
    },
    {
        "name": "bat",
        "display_name": "Bat",
        "description": "Cat clone with syntax highlighting",
        "install_command": "sudo apt-get update && sudo apt-get install -y bat",
        "check_command": "batcat --version",
        "usage_instructions": "Use `bat` to view files with syntax highlighting. Example: `bat file.py`",
        "category": "File Viewing",
    },
    {
        "name": "httpie",
        "display_name": "HTTPie",
        "description": "Modern command-line HTTP client",
        "install_command": "sudo pip install httpie",
        "check_command": "http --version",
        "usage_instructions": "Use `http` for HTTP requests. Example: `http GET api.example.com/users`",
        "category": "Network",
    },
    {
        "name": "gh",
        "display_name": "GitHub CLI",
        "description": "GitHub's official command line tool",
        "install_command": "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && echo 'deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && sudo apt update && sudo apt install gh -y",
        "check_command": "gh --version",
        "usage_instructions": "Use `gh` for GitHub operations. Example: `gh pr create --title 'New feature'`",
        "category": "Version Control",
    },
    {
        "name": "tokei",
        "display_name": "Tokei",
        "description": "Count lines of code quickly",
        "install_command": "sudo cargo install tokei --root /usr/local",
        "check_command": "tokei --version",
        "usage_instructions": "Use `tokei` to count lines of code. Example: `tokei --exclude '*.min.js'`",
        "category": "Code Analysis",
    },
    {
        "name": "lazygit",
        "display_name": "LazyGit",
        "description": "Terminal UI for git commands",
        "install_command": "LAZYGIT_VERSION=$(curl -s 'https://api.github.com/repos/jesseduffield/lazygit/releases/latest' | grep -Po '\"tag_name\": \"v\\K[0-9.]+') && curl -Lo lazygit.tar.gz \"https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz\" && sudo tar xf lazygit.tar.gz -C /usr/local/bin lazygit && rm lazygit.tar.gz",
        "check_command": "lazygit --version",
        "usage_instructions": "Use `lazygit` for interactive git operations. Just run `lazygit` in a git repository.",
        "category": "Version Control",
    },
    {
        "name": "tldr",
        "display_name": "TLDR Pages",
        "description": "Simplified man pages with practical examples",
        "install_command": "sudo pip install tldr",
        "check_command": "tldr --version",
        "usage_instructions": "Use `tldr` for quick command examples. Example: `tldr tar`",
        "category": "Documentation",
    },
    {
        "name": "ncdu",
        "display_name": "NCurses Disk Usage",
        "description": "Interactive disk usage analyzer",
        "install_command": "sudo apt-get update && sudo apt-get install -y ncdu",
        "check_command": "ncdu --version",
        "usage_instructions": "Use `ncdu` to analyze disk usage. Example: `ncdu /workspace`",
        "category": "System",
    },
    {
        "name": "playwright",
        "display_name": "Playwright",
        "description": "Browser automation and testing framework for headless browser testing",
        "install_command": "sudo pip install playwright && sudo playwright install chromium && sudo apt-get update && sudo apt-get install -y libnspr4 libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2",
        "check_command": "playwright --version",
        "usage_instructions": "Use `playwright` for browser automation and testing. Example: Create a Python script using `from playwright.async_api import async_playwright` to automate browser tasks.",
        "category": "Testing",
    },
    {
        "name": "cypress",
        "display_name": "Cypress",
        "description": "JavaScript end-to-end testing framework",
        "install_command": "sudo npm install -g cypress && sudo apt-get update && sudo apt-get install -y libgtk2.0-0 libgtk-3-0 libgbm-dev libnotify-dev libgconf-2-4 libnss3 libxss1 libasound2 libxtst6 xauth xvfb",
        "check_command": "cypress --version",
        "usage_instructions": "Use `cypress` for E2E testing. Run `cypress open` to launch the test runner.",
        "category": "Testing",
    },
    {
        "name": "k6",
        "display_name": "k6",
        "description": "Modern load testing tool",
        "install_command": "sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 && echo 'deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main' | sudo tee /etc/apt/sources.list.d/k6.list && sudo apt-get update && sudo apt-get install k6",
        "check_command": "k6 version",
        "usage_instructions": "Use `k6` for load testing. Example: `k6 run script.js`",
        "category": "Testing",
    },
]


def get_tools_config_path() -> Path:
    """Return the tools configuration path under ~/.cuti."""

    config_dir = Path.home() / ".cuti"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "tools_config.json"



def load_tools_config() -> Dict[str, Any]:
    """Load persisted tool selection state."""

    config_path = get_tools_config_path()
    if config_path.exists():
        try:
            with config_path.open("r") as handle:
                return json.load(handle)
        except Exception:
            pass
    return {"enabled_tools": [], "auto_install": []}



def save_tools_config(config: Dict[str, Any]) -> None:
    """Persist tool selection state."""

    config_path = get_tools_config_path()
    with config_path.open("w") as handle:
        json.dump(config, handle, indent=2)



def check_tool_installed(check_command: str) -> bool:
    """Check whether a tool is installed by running its version command."""

    try:
        result = subprocess.run(
            check_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False
