"""
DevContainer CLI commands for cuti.
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...services.devcontainer import DevContainerService, is_running_in_container

app = typer.Typer(help="DevContainer management commands")
console = Console()


@app.command()
def init(
    project_type: str = typer.Option(None, "--type", "-t", help="Project type (python, javascript, fullstack, etc.)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force regeneration of existing devcontainer"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima setup even if available")
):
    """Initialize a dev container for the current project."""
    
    working_dir = Path.cwd()
    service = DevContainerService(working_dir)
    
    # Check if already in container
    if is_running_in_container():
        console.print("[yellow]⚠️  Already running in a container![/yellow]")
        return
    
    # Check if devcontainer exists
    if (working_dir / ".devcontainer").exists() and not force:
        console.print("[yellow]⚠️  Dev container already exists. Use --force to regenerate.[/yellow]")
        return
    
    console.print(Panel.fit(
        f"[bold cyan]Initializing Dev Container[/bold cyan]\n"
        f"Project: {working_dir.name}\n"
        f"Type: {project_type or 'auto-detect'}"
    ))
    
    # Check Docker first
    if service.docker_available:
        console.print("[green]✅ Docker is already running[/green]")
    elif service.colima_available and not skip_colima:
        console.print("[cyan]🐳 Docker not running, will use Colima[/cyan]")
        if not service.setup_colima():
            console.print("[red]❌ Failed to setup Colima[/red]")
            console.print("[yellow]Try starting Docker Desktop or Colima manually[/yellow]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]⚠️  Docker not available[/yellow]")
        console.print("Please start Docker Desktop or install Colima:")
        console.print("  brew install colima && colima start")
        raise typer.Exit(1)
    
    # Generate devcontainer
    if service.generate_devcontainer(project_type):
        console.print("[green]✅ Dev container initialized successfully![/green]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Run: [cyan]cuti devcontainer start[/cyan]")
        console.print("2. Or open in VS Code and use 'Reopen in Container'")
    else:
        console.print("[red]❌ Failed to initialize dev container[/red]")
        raise typer.Exit(1)


@app.command()
def start(
    command: str = typer.Argument(None, help="Command to run in container"),
    build: bool = typer.Option(True, "--build/--no-build", help="Build the container image"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima setup")
):
    """Start the dev container and optionally run a command."""
    
    working_dir = Path.cwd()
    service = DevContainerService(working_dir)
    
    # Check if already in container
    if is_running_in_container():
        console.print("[yellow]⚠️  Already running in a container![/yellow]")
        if command:
            import subprocess
            subprocess.run(command, shell=True)
        return
    
    # Check if devcontainer exists - for the start command, we need devcontainer files
    if not (working_dir / ".devcontainer").exists():
        console.print("[yellow]⚠️  No dev container found. Run 'cuti devcontainer init' first.[/yellow]")
        raise typer.Exit(1)
    
    # Check Docker availability
    if not service.docker_available:
        if service.colima_available and not skip_colima:
            console.print("[cyan]🐳 Docker not running, starting Colima...[/cyan]")
            if not service.setup_colima():
                console.print("[red]❌ Failed to start Colima[/red]")
                console.print("[yellow]Troubleshooting:[/yellow]")
                console.print("1. Try: colima stop -f && colima start")
                console.print("2. Or start Docker Desktop")
                console.print("3. Or use --skip-colima flag")
                raise typer.Exit(1)
        else:
            console.print("[red]❌ Docker is not running[/red]")
            console.print("Please start Docker Desktop or Colima first:")
            console.print("  colima start")
            console.print("  # or open Docker Desktop")
            raise typer.Exit(1)
    
    console.print(Panel.fit(
        f"[bold cyan]Starting Dev Container[/bold cyan]\n"
        f"Project: {working_dir.name}\n"
        f"Command: {command or 'interactive shell'}"
    ))
    
    # Run in container
    exit_code = service.run_in_container(command)
    
    if exit_code != 0:
        console.print(f"[red]❌ Container exited with code {exit_code}[/red]")
        raise typer.Exit(exit_code)


@app.command()
def stop():
    """Stop any running dev containers for this project."""
    
    working_dir = Path.cwd()
    container_name = f"cuti-dev-{working_dir.name}"
    
    import subprocess
    result = subprocess.run(
        ["docker", "stop", container_name],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        console.print(f"[green]✅ Stopped container {container_name}[/green]")
    else:
        console.print(f"[yellow]⚠️  No running container found[/yellow]")


@app.command()
def clean(
    all_containers: bool = typer.Option(False, "--all", "-a", help="Clean ALL Docker containers and images"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Clean up dev container files and images."""
    
    import subprocess
    
    if all_containers:
        console.print("[bold red]⚠️  This will remove:[/bold red]")
        console.print("  • ALL Docker containers (running and stopped)")
        console.print("  • ALL Docker images")
        console.print("  • ALL Docker volumes")
        console.print("  • ALL Docker build cache")
        
        if not force and not typer.confirm("Continue?"):
            raise typer.Abort()
        
        console.print("[cyan]🧹 Cleaning all Docker resources...[/cyan]")
        
        # Stop all containers
        subprocess.run(["docker", "stop", "$(docker ps -aq)"], shell=True, capture_output=True, text=True)
        
        # Remove all containers
        subprocess.run(["docker", "rm", "$(docker ps -aq)"], shell=True, capture_output=True, text=True)
        
        # Remove all images
        subprocess.run(["docker", "rmi", "$(docker images -q)"], shell=True, capture_output=True, text=True)
        
        # System prune everything
        result = subprocess.run(
            ["docker", "system", "prune", "-a", "-f", "--volumes"],
            capture_output=True,
            text=True
        )
        
        if "Total reclaimed space:" in result.stdout:
            # Extract the reclaimed space
            for line in result.stdout.split('\n'):
                if "Total reclaimed space:" in line:
                    console.print(f"[green]✅ {line.strip()}[/green]")
        
        # Show final status
        df_result = subprocess.run(["docker", "system", "df"], capture_output=True, text=True)
        console.print("\n[bold]Docker disk usage after cleanup:[/bold]")
        console.print(df_result.stdout)
        
        console.print("[green]✅ All Docker resources cleaned![/green]")
    else:
        working_dir = Path.cwd()
        service = DevContainerService(working_dir)
        
        console.print("[yellow]⚠️  This will remove:[/yellow]")
        console.print("  • .devcontainer directory")
        console.print(f"  • Docker image: cuti-dev-{working_dir.name}")
        
        if not force and not typer.confirm("Continue?"):
            raise typer.Abort()
            
        if service.clean():
            console.print("[green]✅ Cleaned up dev container resources[/green]")
        else:
            console.print("[red]❌ Failed to clean up[/red]")
            raise typer.Exit(1)


@app.command()
def status():
    """Show dev container status."""
    
    working_dir = Path.cwd()
    service = DevContainerService(working_dir)
    
    table = Table(title="Dev Container Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    # Check if in container
    in_container = is_running_in_container()
    table.add_row(
        "Running in Container",
        "✅ Yes" if in_container else "❌ No"
    )
    
    # Check devcontainer files
    devcontainer_exists = (working_dir / ".devcontainer").exists()
    table.add_row(
        "DevContainer Config",
        "✅ Exists" if devcontainer_exists else "❌ Not found"
    )
    
    # Check Colima
    table.add_row(
        "Colima",
        "✅ Available" if service.colima_available else "❌ Not installed"
    )
    
    # Check Docker
    table.add_row(
        "Docker",
        "✅ Running" if service.docker_available else "❌ Not running"
    )
    
    # Check for running container
    import subprocess
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name=cuti-dev-{working_dir.name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )
    
    container_running = working_dir.name in result.stdout
    table.add_row(
        "Container Running",
        "✅ Yes" if container_running else "❌ No"
    )
    
    console.print(table)
    
    if in_container:
        console.print("\n[green]🚀 You are currently inside the dev container![/green]")
        console.print("[dim]Claude commands will use --dangerously-skip-permissions[/dim]")


@app.command("devcontainer-init")
def devcontainer_init():
    """Initialize the container environment (called automatically)."""
    
    if not is_running_in_container():
        console.print("[red]❌ This command should only run inside a container[/red]")
        raise typer.Exit(1)
    
    console.print("[cyan]🔧 Initializing container environment...[/cyan]")
    
    import subprocess
    import os
    
    # Ensure .cuti directory exists
    cuti_dir = Path.cwd() / ".cuti"
    cuti_dir.mkdir(exist_ok=True)
    
    # Initialize Python environment if needed
    if Path("pyproject.toml").exists() or Path("requirements.txt").exists():
        if not Path(".venv").exists():
            console.print("[cyan]📦 Creating Python virtual environment...[/cyan]")
            subprocess.run(["python", "-m", "venv", ".venv"])
        
        if Path("pyproject.toml").exists() and shutil.which("uv"):
            console.print("[cyan]📦 Installing dependencies with uv...[/cyan]")
            subprocess.run(["uv", "sync"])
        elif Path("requirements.txt").exists():
            console.print("[cyan]📦 Installing requirements.txt...[/cyan]")
            subprocess.run([".venv/bin/pip", "install", "-r", "requirements.txt"])
    
    # Install Node dependencies if needed
    if Path("package.json").exists():
        if Path("yarn.lock").exists():
            console.print("[cyan]📦 Installing dependencies with yarn...[/cyan]")
            subprocess.run(["yarn", "install"])
        elif Path("pnpm-lock.yaml").exists():
            console.print("[cyan]📦 Installing dependencies with pnpm...[/cyan]")
            subprocess.run(["pnpm", "install"])
        else:
            console.print("[cyan]📦 Installing dependencies with npm...[/cyan]")
            subprocess.run(["npm", "install"])
    
    console.print("[green]✅ Container environment initialized![/green]")


# Export for CLI
import shutil  # Import here to avoid issues if not used