"""
Container management commands for cuti.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

app = typer.Typer(help="Container management commands")
console = Console()


def get_container_info() -> Dict[str, List[Dict]]:
    """Get information about all cuti-dev containers grouped by workspace."""
    try:
        # Get all containers using cuti-dev-universal image
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=cuti-dev-universal", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        
        containers_by_workspace = defaultdict(list)
        
        # Parse each container's JSON
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                container = json.loads(line)
                container_id = container.get('ID', '')[:12]
                
                # Get detailed inspect info for mount paths
                inspect_result = subprocess.run(
                    ["docker", "inspect", container_id],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if inspect_result.returncode == 0:
                    inspect_data = json.loads(inspect_result.stdout)[0]
                    
                    # Find the workspace mount
                    workspace_path = None
                    for mount in inspect_data.get('Mounts', []):
                        if mount.get('Destination') == '/workspace':
                            workspace_path = mount.get('Source')
                            break
                    
                    if workspace_path:
                        # Extract project name from path
                        project_name = Path(workspace_path).name
                        
                        container_info = {
                            'id': container_id,
                            'name': container.get('Names', 'unknown'),
                            'status': container.get('Status', 'unknown'),
                            'created': container.get('CreatedAt', 'unknown'),
                            'workspace_path': workspace_path
                        }
                        
                        containers_by_workspace[workspace_path].append(container_info)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                console.print(f"[yellow]Warning: Could not parse container info: {e}[/yellow]")
                continue
        
        return dict(containers_by_workspace)
        
    except subprocess.TimeoutExpired:
        console.print("[red]Error: Docker command timed out[/red]")
        return {}
    except FileNotFoundError:
        console.print("[red]Error: Docker not found[/red]")
        return {}
    except Exception as e:
        console.print(f"[red]Error getting container info: {e}[/red]")
        return {}


@app.command()
def start(
    command: Optional[str] = typer.Argument(None, help="Command to run in container"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild the container image"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima auto-setup")
):
    """Start a new container for the current workspace."""
    from ...services.devcontainer import DevContainerService, is_running_in_container
    
    if is_running_in_container():
        console.print("[yellow]Already running in a container![/yellow]")
        if command:
            import subprocess
            subprocess.run(command, shell=True)
        return
    
    service = DevContainerService()
    
    # Ensure dependencies are installed on macOS
    console.print("[cyan]Checking container dependencies...[/cyan]")
    if not service.ensure_dependencies():
        console.print("[red]Container dependencies not available[/red]")
        raise typer.Exit(1)
    
    # Re-check availability after potential installation
    service.colima_available = service._check_colima()
    service.docker_available = service._check_docker()
    
    # Check Docker availability
    if not service.docker_available:
        if service.colima_available and not skip_colima:
            console.print("[cyan]Docker not running, will start Colima...[/cyan]")
            console.print("[dim]This may take 1-2 minutes on first start[/dim]")
            if not service.setup_colima():
                console.print("[red]Failed to start Colima automatically[/red]")
                console.print("\n[yellow]Please try one of these options:[/yellow]")
                console.print("1. Start Colima manually: [cyan]colima start[/cyan]")
                console.print("2. Start Docker Desktop")
                console.print("3. Run with --skip-colima flag if Docker is running")
                raise typer.Exit(1)
        else:
            console.print("[red]Docker is not available[/red]")
            if not service.colima_available:
                console.print("Install Colima: [cyan]brew install colima[/cyan]")
            console.print("Or start Docker Desktop")
            raise typer.Exit(1)
    
    # Run in container
    console.print("[green]Starting dev container...[/green]")
    exit_code = service.run_in_container(command, rebuild=rebuild)
    
    if exit_code != 0:
        console.print(f"[red]Container exited with code {exit_code}[/red]")
        raise typer.Exit(exit_code)


@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Show status of all cuti containers grouped by workspace."""
    
    containers = get_container_info()
    
    if json_output:
        import json as json_lib
        console.print(json_lib.dumps(containers, indent=2))
        return
    
    if not containers:
        console.print("[yellow]No cuti containers are currently running[/yellow]")
        return
    
    # Create summary panel
    total_containers = sum(len(c) for c in containers.values())
    total_workspaces = len(containers)
    
    summary = Panel(
        f"[bold cyan]Container Summary[/bold cyan]\n"
        f"Total Containers: [green]{total_containers}[/green]\n"
        f"Total Workspaces: [green]{total_workspaces}[/green]",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(summary)
    console.print()
    
    # Create table for each workspace
    for workspace_path, container_list in sorted(containers.items()):
        # Create a table for this workspace
        table = Table(
            title=f"[bold]{Path(workspace_path).name}[/bold]",
            caption=f"[dim]{workspace_path}[/dim]",
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold magenta",
            title_style="bold blue"
        )
        
        table.add_column("Container ID", style="cyan", width=14)
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        
        if verbose:
            table.add_column("Created", style="dim")
        
        # Add rows for each container
        for container in container_list:
            if verbose:
                table.add_row(
                    container['id'],
                    container['name'],
                    container['status'],
                    container['created']
                )
            else:
                table.add_row(
                    container['id'],
                    container['name'],
                    container['status']
                )
        
        console.print(table)
        console.print()
    
    # Add helpful commands
    console.print("[dim]Commands:[/dim]")
    console.print("[dim]• Stop a container: docker stop <container-id>[/dim]")
    console.print("[dim]• Enter a container: docker exec -it <container-id> /bin/zsh[/dim]")
    console.print("[dim]• Stop all: docker stop $(docker ps -q --filter 'ancestor=cuti-dev-universal')[/dim]")


@app.command()
def stop(
    container_id: Optional[str] = typer.Argument(None, help="Container ID to stop (or current if inside container)"),
    all: bool = typer.Option(False, "--all", "-a", help="Stop all cuti containers"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Stop running cuti containers."""
    
    if all:
        containers = get_container_info()
        
        if not containers:
            console.print("[yellow]No cuti containers are currently running[/yellow]")
            return
        
        total_containers = sum(len(c) for c in containers.values())
        
        if not force:
            console.print(f"[yellow]This will stop {total_containers} container(s) across {len(containers)} workspace(s)[/yellow]")
            if not typer.confirm("Continue?"):
                raise typer.Abort()
        
        console.print("[cyan]Stopping all cuti containers...[/cyan]")
        
        # Get all container IDs
        all_ids = []
        for container_list in containers.values():
            all_ids.extend([c['id'] for c in container_list])
        
        # Stop all containers
        result = subprocess.run(
            ["docker", "stop"] + all_ids,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print(f"[green]✅ Successfully stopped {total_containers} container(s)[/green]")
        else:
            console.print(f"[red]❌ Error stopping containers: {result.stderr}[/red]")
            raise typer.Exit(1)
    else:
        # Stop specific container or current if inside one
        from ...services.devcontainer import is_running_in_container
        
        if not container_id and is_running_in_container():
            # Get current container ID
            import os
            container_id = os.environ.get('HOSTNAME', '')[:12]
            if container_id:
                console.print(f"[cyan]Stopping current container {container_id}...[/cyan]")
        
        if not container_id:
            console.print("[red]No container ID specified[/red]")
            console.print("Usage: cuti container stop <container-id>")
            console.print("       cuti container stop --all")
            raise typer.Exit(1)
        
        result = subprocess.run(
            ["docker", "stop", container_id],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print(f"[green]✅ Stopped container {container_id}[/green]")
        else:
            console.print(f"[red]❌ Error stopping container: {result.stderr}[/red]")
            raise typer.Exit(1)


@app.command()
def enter(
    container_id: Optional[str] = typer.Argument(None, help="Container ID to enter"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Enter container for specific workspace")
):
    """Enter an existing cuti container."""
    
    containers = get_container_info()
    
    if not containers:
        console.print("[yellow]No cuti containers are currently running[/yellow]")
        return
    
    target_id = None
    
    if workspace:
        # Find container for specified workspace
        for ws_path, container_list in containers.items():
            if workspace in ws_path or Path(ws_path).name == workspace:
                if container_list:
                    target_id = container_list[0]['id']
                    break
        
        if not target_id:
            console.print(f"[red]No container found for workspace: {workspace}[/red]")
            raise typer.Exit(1)
    elif container_id:
        target_id = container_id
    else:
        # If only one container running, use it
        all_containers = []
        for container_list in containers.values():
            all_containers.extend(container_list)
        
        if len(all_containers) == 1:
            target_id = all_containers[0]['id']
        else:
            # Show available containers and let user choose
            console.print("[yellow]Multiple containers running. Please specify one:[/yellow]")
            for ws_path, container_list in containers.items():
                for container in container_list:
                    console.print(f"  {container['id']} - {Path(ws_path).name}")
            raise typer.Exit(1)
    
    # Enter the container
    console.print(f"[cyan]Entering container {target_id}...[/cyan]")
    import os
    os.system(f"docker exec -it {target_id} /bin/zsh")


@app.command()
def cleanup(
    days: int = typer.Option(7, "--days", "-d", help="Remove containers older than N days"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Clean up old stopped cuti containers."""
    
    # Get all stopped containers
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", "ancestor=cuti-dev-universal", 
         "--filter", "status=exited", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 or not result.stdout.strip():
        console.print("[yellow]No stopped cuti containers found[/yellow]")
        return
    
    to_remove = []
    for line in result.stdout.strip().split('\n'):
        try:
            container = json.loads(line)
            to_remove.append(container['ID'][:12])
        except:
            continue
    
    if not to_remove:
        console.print("[yellow]No stopped containers to clean up[/yellow]")
        return
    
    if not force:
        console.print(f"[yellow]This will remove {len(to_remove)} stopped container(s)[/yellow]")
        if not typer.confirm("Continue?"):
            raise typer.Abort()
    
    result = subprocess.run(
        ["docker", "rm"] + to_remove,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        console.print(f"[green]✅ Removed {len(to_remove)} stopped container(s)[/green]")
    else:
        console.print(f"[red]❌ Error removing containers: {result.stderr}[/red]")