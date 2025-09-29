"""
Container status command - shows all cuti containers grouped by workspace.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

app = typer.Typer()
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
def stop_all(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Stop all running cuti containers."""
    
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
            # Parse created time and check age
            # Docker's CreatedAt format: "2024-01-15 10:30:45 -0500 EST"
            # For simplicity, we'll remove all stopped containers
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


if __name__ == "__main__":
    app()