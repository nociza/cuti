"""
CLI Tools management commands for cuti.
"""

import os
import subprocess
from typing import Dict, Any, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...services.instructions import update_instruction_files_with_tools
from ...services.tool_catalog import (
    AVAILABLE_TOOLS,
    check_tool_installed,
    load_tools_config,
    save_tools_config,
)

app = typer.Typer(help="CLI tools management commands")
console = Console()


def update_claude_md(tools: List[Dict[str, Any]]):
    """Update provider instruction files with enabled tools information."""

    try:
        update_instruction_files_with_tools(tools)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not update instruction files: {e}[/yellow]")


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
    auto: bool = typer.Option(False, "--auto", help="Auto-install on container start"),
    scope: str = typer.Option("container", "--scope", "-s", help="Installation scope: workspace|container|system")
):
    """Install a CLI tool with specified scope (workspace, container, or system)."""
    # Import workspace tools manager
    from ...services.workspace_tools import WorkspaceToolsManager
    
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
    
    # Handle workspace-specific installation
    if scope == "workspace":
        manager = WorkspaceToolsManager()
        console.print(f"[cyan]Installing {tool['display_name']} for workspace: {manager.workspace_path}[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Installing {tool['display_name']} to workspace...", total=None)
            
            result = manager.install_tool_for_workspace(tool["name"], tool, scope="workspace")
            progress.update(task, completed=True)
            
            if result["success"]:
                console.print(f"[green]✓ {result['message']}[/green]")
                console.print(f"[cyan]Tool available in: {manager.workspace_tools_bin}[/cyan]")
                
                # Automatically activate workspace tools
                activation_script = manager.activate_workspace_tools()
                
                # Update current process environment
                env = manager.get_environment()
                for key, value in env.items():
                    os.environ[key] = value
                
                console.print(f"[green]✓ Workspace tools activated for current session[/green]")
                console.print(f"[yellow]For new shells, run: eval $(cuti tools activate)[/yellow]")
            else:
                console.print(f"[red]✗ {result['message']}[/red]")
                raise typer.Exit(1)
        return
    elif scope not in ["container", "system"]:
        console.print(f"[red]Invalid scope: {scope}. Use workspace, container, or system[/red]")
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


@app.command("activate")
def activate_tools(
    setup: bool = typer.Option(False, "--setup", help="Setup automatic activation in shell")
):
    """Activate workspace tools in current shell environment."""
    from ...services.workspace_tools import WorkspaceToolsManager
    
    if setup:
        # Setup automatic activation
        setup_auto_activation()
        return
    
    manager = WorkspaceToolsManager()
    activation_script = manager.activate_workspace_tools()
    
    # Output the source command for the shell to execute
    # This allows: eval $(cuti tools activate)
    print(f"source {activation_script}")


def setup_auto_activation():
    """Setup automatic workspace tools activation in shell initialization files."""
    import shutil
    
    # Copy auto-activation script to a known location
    auto_activate_source = Path(__file__).parent.parent.parent / "shell" / "auto_activate.sh"
    auto_activate_dest = Path.home() / ".cuti" / "auto_activate.sh"
    
    if auto_activate_source.exists():
        auto_activate_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(auto_activate_source, auto_activate_dest)
        auto_activate_dest.chmod(0o755)
    else:
        console.print("[red]Auto-activation script not found[/red]")
        return
    
    # Add to shell initialization files
    activation_line = f"\n# Cuti workspace tools auto-activation\n[ -f {auto_activate_dest} ] && source {auto_activate_dest}\n"
    
    shells_updated = []
    for shell_rc in [Path.home() / ".bashrc", Path.home() / ".zshrc"]:
        if shell_rc.exists():
            content = shell_rc.read_text()
            if str(auto_activate_dest) not in content:
                shell_rc.write_text(content + activation_line)
                shells_updated.append(shell_rc.name)
    
    if shells_updated:
        console.print(f"[green]✓ Auto-activation setup complete![/green]")
        console.print(f"[cyan]Updated: {', '.join(shells_updated)}[/cyan]")
        console.print("[yellow]Restart your shell or run:[/yellow]")
        console.print(f"  source {auto_activate_dest}")
    else:
        console.print("[yellow]Auto-activation already configured[/yellow]")


@app.command("workspace")
def workspace_tools():
    """Show workspace-specific tools configuration and status."""
    from ...services.workspace_tools import WorkspaceToolsManager
    
    manager = WorkspaceToolsManager()
    
    # Show workspace tools status
    tools_info = manager.list_workspace_tools()
    
    # Create panel for workspace info
    workspace_text = f"""[bold cyan]Workspace Tools Configuration[/bold cyan]
    
[yellow]Workspace:[/yellow] {tools_info['workspace']}
[yellow]Inherit Container Tools:[/yellow] {'Yes' if tools_info['inherit_container'] else 'No'}
[yellow]Inherit System Tools:[/yellow] {'Yes' if tools_info['inherit_system'] else 'No'}
"""
    
    panel = Panel(workspace_text, box=box.ROUNDED, padding=(1, 2))
    console.print(panel)
    
    # Show workspace-specific tools
    if tools_info['workspace_tools']:
        table = Table(
            title="[bold]Workspace-Specific Tools[/bold]",
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Tool", style="cyan")
        table.add_column("Available", justify="center")
        table.add_column("Path", style="dim")
        
        for tool_name, tool_data in tools_info['workspace_tools'].items():
            available = "[green]✓[/green]" if tool_data.get('available') else "[red]✗[/red]"
            path = tool_data.get('path', 'N/A')
            table.add_row(tool_name, available, path)
        
        console.print(table)
    else:
        console.print("[yellow]No workspace-specific tools installed[/yellow]")
    
    # Show tool paths
    if tools_info['tool_paths']:
        console.print("\n[cyan]Tool Paths (in order):[/cyan]")
        for path in tools_info['tool_paths']:
            console.print(f"  • {path}")
    
    console.print("\n[dim]Tip: Use --scope workspace when installing to add tools only to this workspace[/dim]")


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
