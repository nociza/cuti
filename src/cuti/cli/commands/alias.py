"""
Alias-related CLI commands.
"""

import json
from typing import Optional, List

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from ...services.aliases import PromptAliasManager

alias_app = typer.Typer(help="Manage prompt aliases")
console = Console()


def get_alias_manager(storage_dir: str) -> PromptAliasManager:
    """Get alias manager instance."""
    return PromptAliasManager(storage_dir)


@alias_app.command("create")
def create_alias(
    name: str = typer.Argument(..., help="Alias name"),
    prompt: str = typer.Argument(..., help="Prompt content"),
    description: str = typer.Option("", "-d", "--description", help="Alias description"),
    working_dir: str = typer.Option(".", "-w", "--working-dir", help="Working directory"),
    context_files: List[str] = typer.Option([], "-f", "--context-files", help="Context files"),
    storage_dir: str = typer.Option("~/.cuti", help="Storage directory"),
):
    """Create a new prompt alias."""
    alias_manager = get_alias_manager(storage_dir)
    success = alias_manager.create_alias(name, prompt, description, working_dir, context_files)
    
    if success:
        rprint(f"[green]✓[/green] Created alias [bold]{name}[/bold]")
    else:
        rprint(f"[red]✗[/red] Failed to create alias (may already exist)")
        raise typer.Exit(1)


@alias_app.command("list")
def list_aliases(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    storage_dir: str = typer.Option("~/.cuti", help="Storage directory"),
):
    """List all aliases."""
    alias_manager = get_alias_manager(storage_dir)
    aliases = alias_manager.list_aliases()
    
    if not aliases:
        rprint("[yellow]No aliases found[/yellow]")
        return

    if json_output:
        print(json.dumps(aliases, indent=2, default=str))
    else:
        table = Table(title=f"Found {len(aliases)} aliases")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="yellow")
        table.add_column("Content", style="green", max_width=50)
        table.add_column("Working Dir", style="blue")
        
        for alias in aliases:
            content_preview = alias['content'][:50] + "..." if len(alias['content']) > 50 else alias['content']
            table.add_row(
                alias['name'],
                alias.get('description', ''),
                content_preview,
                alias.get('working_directory', '.')
            )
        
        console.print(table)


@alias_app.command("delete")
def delete_alias(
    name: str = typer.Argument(..., help="Alias name to delete"),
    storage_dir: str = typer.Option("~/.cuti", help="Storage directory"),
):
    """Delete an alias."""
    alias_manager = get_alias_manager(storage_dir)
    success = alias_manager.delete_alias(name)
    
    if success:
        rprint(f"[green]✓[/green] Deleted alias [bold]{name}[/bold]")
    else:
        rprint(f"[red]✗[/red] Alias [bold]{name}[/bold] not found")
        raise typer.Exit(1)


@alias_app.command("show")
def show_alias(
    name: str = typer.Argument(..., help="Alias name to show"),
    storage_dir: str = typer.Option("~/.cuti", help="Storage directory"),
):
    """Show alias details."""
    alias_manager = get_alias_manager(storage_dir)
    alias = alias_manager.get_alias(name)
    
    if not alias:
        rprint(f"[red]✗[/red] Alias [bold]{name}[/bold] not found")
        raise typer.Exit(1)

    rprint(f"[bold]Alias:[/bold] {alias['name']}")
    if alias.get('description'):
        rprint(f"[bold]Description:[/bold] {alias['description']}")
    rprint(f"[bold]Working Directory:[/bold] {alias.get('working_directory', '.')}")
    if alias.get('context_files'):
        rprint(f"[bold]Context Files:[/bold] {', '.join(alias['context_files'])}")
    rprint(f"[bold]Content:[/bold]\n{alias['content']}")


@alias_app.command("update")
def update_alias(
    name: str = typer.Argument(..., help="Alias name to update"),
    prompt: Optional[str] = typer.Option(None, "-p", "--prompt", help="New prompt content"),
    description: Optional[str] = typer.Option(None, "-d", "--description", help="New description"),
    working_dir: Optional[str] = typer.Option(None, "-w", "--working-dir", help="New working directory"),
    storage_dir: str = typer.Option("~/.cuti", help="Storage directory"),
):
    """Update an existing alias."""
    alias_manager = get_alias_manager(storage_dir)
    
    # Get existing alias
    existing_alias = alias_manager.get_alias(name)
    if not existing_alias:
        rprint(f"[red]✗[/red] Alias [bold]{name}[/bold] not found")
        raise typer.Exit(1)
    
    # Update fields that were provided
    updated_content = prompt if prompt is not None else existing_alias['content']
    updated_description = description if description is not None else existing_alias.get('description', '')
    updated_working_dir = working_dir if working_dir is not None else existing_alias.get('working_directory', '.')
    updated_context_files = existing_alias.get('context_files', [])
    
    # Delete old alias and create new one
    alias_manager.delete_alias(name)
    success = alias_manager.create_alias(
        name, updated_content, updated_description, 
        updated_working_dir, updated_context_files
    )
    
    if success:
        rprint(f"[green]✓[/green] Updated alias [bold]{name}[/bold]")
    else:
        rprint(f"[red]✗[/red] Failed to update alias [bold]{name}[/bold]")
        raise typer.Exit(1)