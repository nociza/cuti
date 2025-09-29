"""
CLI Tools management commands for cuti.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="CLI tools management commands")
console = Console()


# Predefined tools list (same as in web API)
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
    },
    {
        "name": "playwright",
        "display_name": "Playwright",
        "description": "Browser automation and testing framework for headless browser testing",
        "install_command": "sudo pip install playwright && sudo playwright install chromium && sudo apt-get update && sudo apt-get install -y libnspr4 libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2",
        "check_command": "playwright --version",
        "usage_instructions": "Use `playwright` for browser automation and testing. Example: Create a Python script using `from playwright.async_api import async_playwright` to automate browser tasks.",
        "category": "Testing"
    },
    {
        "name": "cypress",
        "display_name": "Cypress",
        "description": "JavaScript end-to-end testing framework",
        "install_command": "sudo npm install -g cypress && sudo apt-get update && sudo apt-get install -y libgtk2.0-0 libgtk-3-0 libgbm-dev libnotify-dev libgconf-2-4 libnss3 libxss1 libasound2 libxtst6 xauth xvfb",
        "check_command": "cypress --version",
        "usage_instructions": "Use `cypress` for E2E testing. Run `cypress open` to launch the test runner.",
        "category": "Testing"
    },
    {
        "name": "k6",
        "display_name": "k6",
        "description": "Modern load testing tool",
        "install_command": "sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 && echo 'deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main' | sudo tee /etc/apt/sources.list.d/k6.list && sudo apt-get update && sudo apt-get install k6",
        "check_command": "k6 version",
        "usage_instructions": "Use `k6` for load testing. Example: `k6 run script.js`",
        "category": "Testing"
    }
]


def get_tools_config_path() -> Path:
    """Get the path to the tools configuration file."""
    config_dir = Path.home() / ".cuti"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "tools_config.json"


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
        console.print(f"[yellow]Warning: Could not update CLAUDE.md: {e}[/yellow]")


@app.command("list")
def list_tools(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    installed: Optional[bool] = typer.Option(None, "--installed", help="Show only installed tools"),
    enabled: Optional[bool] = typer.Option(None, "--enabled", help="Show only enabled tools")
):
    """List available CLI tools and their status."""
    config = load_tools_config()
    
    # Create categories dict for grouping
    categories = {}
    for tool_def in AVAILABLE_TOOLS:
        tool = tool_def.copy()
        tool["enabled"] = tool["name"] in config.get("enabled_tools", [])
        tool["auto_install"] = tool["name"] in config.get("auto_install", [])
        tool["installed"] = check_tool_installed(tool["check_command"])
        
        # Apply filters
        if category and tool["category"].lower() != category.lower():
            continue
        if installed is not None and tool["installed"] != installed:
            continue
        if enabled is not None and tool["enabled"] != enabled:
            continue
        
        # Group by category
        if tool["category"] not in categories:
            categories[tool["category"]] = []
        categories[tool["category"]].append(tool)
    
    if not categories:
        console.print("[yellow]No tools match the specified filters[/yellow]")
        return
    
    # Display tools by category
    for cat_name, tools in sorted(categories.items()):
        # Create table for this category
        table = Table(
            title=f"[bold cyan]{cat_name}[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Tool", style="cyan", width=15)
        table.add_column("Description", style="white", width=45)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Enabled", justify="center", width=10)
        table.add_column("Auto", justify="center", width=8)
        
        for tool in tools:
            status = "[green]✓ Installed[/green]" if tool["installed"] else "[dim]Not installed[/dim]"
            enabled_mark = "[green]✓[/green]" if tool["enabled"] else "[dim]-[/dim]"
            auto_mark = "[blue]✓[/blue]" if tool["auto_install"] else "[dim]-[/dim]"
            
            table.add_row(
                tool["display_name"],
                tool["description"],
                status,
                enabled_mark,
                auto_mark
            )
        
        console.print(table)
        console.print()
    
    # Show legend
    console.print("[dim]Legend: Enabled = Tool is enabled | Auto = Auto-install on container start[/dim]")


@app.command("install")
def install_tool(
    tool_name: str = typer.Argument(..., help="Name of the tool to install"),
    enable: bool = typer.Option(True, "--enable/--no-enable", help="Enable the tool after installation"),
    auto: bool = typer.Option(False, "--auto", help="Auto-install on container start")
):
    """Install a CLI tool in the container."""
    # Find the tool
    tool = None
    for t in AVAILABLE_TOOLS:
        if t["name"] == tool_name or t["display_name"].lower() == tool_name.lower():
            tool = t
            break
    
    if not tool:
        console.print(f"[red]Tool '{tool_name}' not found[/red]")
        console.print("[yellow]Use 'cuti tools list' to see available tools[/yellow]")
        raise typer.Exit(1)
    
    # Check if already installed
    if check_tool_installed(tool["check_command"]):
        console.print(f"[green]✓ {tool['display_name']} is already installed[/green]")
        
        # Update configuration if needed
        if enable or auto:
            config = load_tools_config()
            enabled_tools = set(config.get("enabled_tools", []))
            auto_install_tools = set(config.get("auto_install", []))
            
            if enable:
                enabled_tools.add(tool["name"])
            if auto:
                auto_install_tools.add(tool["name"])
            
            config["enabled_tools"] = list(enabled_tools)
            config["auto_install"] = list(auto_install_tools)
            save_tools_config(config)
            
            console.print(f"[green]✓ {tool['display_name']} configuration updated[/green]")
        return
    
    console.print(f"[cyan]Installing {tool['display_name']}...[/cyan]")
    
    # Show progress spinner
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Installing {tool['display_name']}...", total=None)
        
        try:
            import os
            # Run installation command
            install_cmd = tool["install_command"]
            
            # Handle sudo commands properly
            if "sudo" in install_cmd:
                install_cmd = install_cmd.replace("sudo ", "")
                cmd_list = ["sudo", "-E", "bash", "-c", install_cmd]
                result = subprocess.run(
                    cmd_list,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
                )
            else:
                result = subprocess.run(
                    install_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
                )
            
            progress.update(task, completed=True)
            
            if result.returncode == 0:
                console.print(f"[green]✓ {tool['display_name']} installed successfully![/green]")
                
                # Update configuration
                config = load_tools_config()
                enabled_tools = set(config.get("enabled_tools", []))
                auto_install_tools = set(config.get("auto_install", []))
                
                if enable:
                    enabled_tools.add(tool["name"])
                if auto:
                    auto_install_tools.add(tool["name"])
                
                config["enabled_tools"] = list(enabled_tools)
                config["auto_install"] = list(auto_install_tools)
                save_tools_config(config)
                
                # Update CLAUDE.md
                all_tools = []
                for t in AVAILABLE_TOOLS:
                    t_copy = t.copy()
                    t_copy["enabled"] = t["name"] in enabled_tools
                    t_copy["installed"] = check_tool_installed(t["check_command"])
                    all_tools.append(t_copy)
                update_claude_md(all_tools)
                
                console.print(f"\n[cyan]Usage:[/cyan] {tool['usage_instructions']}")
            else:
                console.print(f"[red]✗ Installation failed[/red]")
                if result.stderr:
                    console.print(f"[dim]Error: {result.stderr}[/dim]")
                raise typer.Exit(1)
                
        except subprocess.TimeoutExpired:
            progress.update(task, completed=True)
            console.print("[red]✗ Installation timed out[/red]")
            raise typer.Exit(1)
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]✗ Installation failed: {e}[/red]")
            raise typer.Exit(1)


@app.command("enable")
def enable_tool(
    tool_name: str = typer.Argument(..., help="Name of the tool to enable"),
    auto: bool = typer.Option(False, "--auto", help="Also enable auto-install")
):
    """Enable a CLI tool (mark it as available for use)."""
    # Find the tool
    tool = None
    for t in AVAILABLE_TOOLS:
        if t["name"] == tool_name or t["display_name"].lower() == tool_name.lower():
            tool = t
            break
    
    if not tool:
        console.print(f"[red]Tool '{tool_name}' not found[/red]")
        raise typer.Exit(1)
    
    # Check if installed
    if not check_tool_installed(tool["check_command"]):
        console.print(f"[yellow]⚠ {tool['display_name']} is not installed[/yellow]")
        if typer.confirm("Install it now?"):
            install_tool(tool_name, enable=True, auto=auto)
            return
        else:
            raise typer.Exit(1)
    
    # Update configuration
    config = load_tools_config()
    enabled_tools = set(config.get("enabled_tools", []))
    auto_install_tools = set(config.get("auto_install", []))
    
    enabled_tools.add(tool["name"])
    if auto:
        auto_install_tools.add(tool["name"])
    
    config["enabled_tools"] = list(enabled_tools)
    config["auto_install"] = list(auto_install_tools)
    save_tools_config(config)
    
    console.print(f"[green]✓ {tool['display_name']} enabled[/green]")
    if auto:
        console.print(f"[green]✓ Auto-install enabled for {tool['display_name']}[/green]")
    
    # Update CLAUDE.md
    all_tools = []
    for t in AVAILABLE_TOOLS:
        t_copy = t.copy()
        t_copy["enabled"] = t["name"] in enabled_tools
        t_copy["installed"] = check_tool_installed(t["check_command"])
        all_tools.append(t_copy)
    update_claude_md(all_tools)


@app.command("disable")
def disable_tool(
    tool_name: str = typer.Argument(..., help="Name of the tool to disable")
):
    """Disable a CLI tool (unmark it from available tools)."""
    # Find the tool
    tool = None
    for t in AVAILABLE_TOOLS:
        if t["name"] == tool_name or t["display_name"].lower() == tool_name.lower():
            tool = t
            break
    
    if not tool:
        console.print(f"[red]Tool '{tool_name}' not found[/red]")
        raise typer.Exit(1)
    
    # Update configuration
    config = load_tools_config()
    enabled_tools = set(config.get("enabled_tools", []))
    auto_install_tools = set(config.get("auto_install", []))
    
    enabled_tools.discard(tool["name"])
    auto_install_tools.discard(tool["name"])
    
    config["enabled_tools"] = list(enabled_tools)
    config["auto_install"] = list(auto_install_tools)
    save_tools_config(config)
    
    console.print(f"[green]✓ {tool['display_name']} disabled[/green]")
    
    # Update CLAUDE.md
    all_tools = []
    for t in AVAILABLE_TOOLS:
        t_copy = t.copy()
        t_copy["enabled"] = t["name"] in enabled_tools
        t_copy["installed"] = check_tool_installed(t["check_command"])
        all_tools.append(t_copy)
    update_claude_md(all_tools)


@app.command("info")
def tool_info(
    tool_name: str = typer.Argument(..., help="Name of the tool to show info for")
):
    """Show detailed information about a tool."""
    # Find the tool
    tool = None
    for t in AVAILABLE_TOOLS:
        if t["name"] == tool_name or t["display_name"].lower() == tool_name.lower():
            tool = t
            break
    
    if not tool:
        console.print(f"[red]Tool '{tool_name}' not found[/red]")
        raise typer.Exit(1)
    
    # Check status
    config = load_tools_config()
    is_installed = check_tool_installed(tool["check_command"])
    is_enabled = tool["name"] in config.get("enabled_tools", [])
    is_auto = tool["name"] in config.get("auto_install", [])
    
    # Create info panel
    info_text = f"""[bold cyan]{tool['display_name']}[/bold cyan]
    
[yellow]Description:[/yellow] {tool['description']}
[yellow]Category:[/yellow] {tool['category']}
[yellow]Status:[/yellow] {"[green]Installed[/green]" if is_installed else "[red]Not installed[/red]"}
[yellow]Enabled:[/yellow] {"[green]Yes[/green]" if is_enabled else "[dim]No[/dim]"}
[yellow]Auto-install:[/yellow] {"[green]Yes[/green]" if is_auto else "[dim]No[/dim]"}

[yellow]Check command:[/yellow]
  [dim]{tool['check_command']}[/dim]

[yellow]Usage instructions:[/yellow]
  {tool['usage_instructions']}
"""
    
    panel = Panel(info_text, box=box.ROUNDED, padding=(1, 2))
    console.print(panel)
    
    if not is_installed:
        console.print("\n[cyan]To install this tool, run:[/cyan]")
        console.print(f"  cuti tools install {tool['name']}")


@app.command("check")
def check_tools():
    """Check which tools are installed and their versions."""
    console.print("[cyan]Checking installed tools...[/cyan]\n")
    
    installed_count = 0
    total_count = len(AVAILABLE_TOOLS)
    
    for tool in AVAILABLE_TOOLS:
        is_installed = check_tool_installed(tool["check_command"])
        if is_installed:
            installed_count += 1
            # Try to get version info
            try:
                result = subprocess.run(
                    tool["check_command"],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                version_info = result.stdout.strip().split('\n')[0] if result.stdout else "installed"
                console.print(f"[green]✓[/green] {tool['display_name']}: {version_info}")
            except:
                console.print(f"[green]✓[/green] {tool['display_name']}: installed")
        else:
            console.print(f"[dim]✗[/dim] {tool['display_name']}: not installed")
    
    console.print(f"\n[cyan]Summary:[/cyan] {installed_count}/{total_count} tools installed")


if __name__ == "__main__":
    app()