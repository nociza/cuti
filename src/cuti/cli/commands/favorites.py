"""
CLI commands for managing favorite prompts.
"""

import click
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.syntax import Syntax

from ...services.global_data_manager import GlobalDataManager

console = Console()


@click.group()
def favorites():
    """Manage favorite prompts."""
    pass


@favorites.command()
@click.option('--project', help='Filter by project path')
@click.option('--tags', help='Filter by tags (comma-separated)')
@click.option('--limit', type=int, default=20, help='Maximum number to show')
def list(project, tags, limit):
    """List favorite prompts."""
    manager = GlobalDataManager()
    
    if not manager.settings.favorite_prompts_enabled:
        console.print("[yellow]Favorite prompts are disabled in settings[/yellow]")
        return
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else None
    
    # Get favorites
    favorites = manager.get_favorite_prompts(
        project_path=project,
        tags=tag_list
    )[:limit]
    
    if not favorites:
        console.print("[yellow]No favorite prompts found[/yellow]")
        return
    
    table = Table(title="Favorite Prompts", box=box.ROUNDED)
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Title", style="green")
    table.add_column("Project", style="yellow")
    table.add_column("Tags", style="magenta")
    table.add_column("Uses", style="blue", justify="right")
    table.add_column("Last Used", style="dim")
    
    for fav in favorites:
        project_name = Path(fav.project_path).name if fav.project_path else "Global"
        tags_str = ", ".join(fav.tags) if fav.tags else ""
        last_used = fav.last_used.strftime("%Y-%m-%d") if fav.last_used else "Never"
        
        table.add_row(
            fav.id,
            fav.title[:40] + "..." if len(fav.title) > 40 else fav.title,
            project_name,
            tags_str,
            str(fav.use_count),
            last_used
        )
    
    console.print(table)


@favorites.command()
@click.argument('favorite_id')
def show(favorite_id):
    """Show details of a favorite prompt."""
    manager = GlobalDataManager()
    
    favorites = manager.get_favorite_prompts()
    favorite = next((f for f in favorites if f.id == favorite_id), None)
    
    if not favorite:
        console.print(f"[red]Favorite '{favorite_id}' not found[/red]")
        return
    
    # Show details
    console.print(Panel(
        f"[cyan]Title:[/cyan] {favorite.title}\n"
        f"[cyan]Project:[/cyan] {favorite.project_path}\n"
        f"[cyan]Tags:[/cyan] {', '.join(favorite.tags) if favorite.tags else 'None'}\n"
        f"[cyan]Created:[/cyan] {favorite.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"[cyan]Last Used:[/cyan] {favorite.last_used.strftime('%Y-%m-%d %H:%M') if favorite.last_used else 'Never'}\n"
        f"[cyan]Use Count:[/cyan] {favorite.use_count}",
        title=f"Favorite: {favorite.id}",
        border_style="cyan"
    ))
    
    # Show content
    console.print("\n[bold]Content:[/bold]")
    console.print(Panel(favorite.content, border_style="dim"))


@favorites.command()
@click.argument('title')
@click.option('--content', help='Prompt content (or read from stdin)')
@click.option('--file', type=click.Path(exists=True), help='Read content from file')
@click.option('--tags', help='Comma-separated tags')
@click.option('--project', help='Associated project path')
def add(title, content, file, tags, project):
    """Add a new favorite prompt."""
    manager = GlobalDataManager()
    
    if not manager.settings.favorite_prompts_enabled:
        console.print("[red]Favorite prompts are disabled in settings[/red]")
        return
    
    # Get content
    if file:
        content = Path(file).read_text()
    elif not content:
        console.print("Enter prompt content (Ctrl+D to finish):")
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            content = "\n".join(lines)
    
    if not content:
        console.print("[red]No content provided[/red]")
        return
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else []
    
    # Add favorite
    favorite_id = manager.add_favorite_prompt(
        title=title,
        content=content,
        tags=tag_list,
        project_path=project or os.getcwd()
    )
    
    console.print(f"[green]✓[/green] Added favorite prompt: {favorite_id}")


@favorites.command()
@click.argument('favorite_id')
def remove(favorite_id):
    """Remove a favorite prompt."""
    manager = GlobalDataManager()
    
    if click.confirm(f"Remove favorite '{favorite_id}'?"):
        # We need to add a remove method to GlobalDataManager
        # For now, we'll mark it as a TODO
        console.print("[yellow]Remove functionality to be implemented[/yellow]")


@favorites.command()
@click.argument('favorite_id')
def use(favorite_id):
    """Use a favorite prompt (mark as used and copy to clipboard)."""
    manager = GlobalDataManager()
    
    favorites = manager.get_favorite_prompts()
    favorite = next((f for f in favorites if f.id == favorite_id), None)
    
    if not favorite:
        console.print(f"[red]Favorite '{favorite_id}' not found[/red]")
        return
    
    # Mark as used
    manager.use_favorite_prompt(favorite_id)
    
    # Try to copy to clipboard
    try:
        import pyperclip
        pyperclip.copy(favorite.content)
        console.print(f"[green]✓[/green] Copied to clipboard and marked as used")
    except ImportError:
        console.print(f"[green]✓[/green] Marked as used")
        console.print("\n[bold]Content:[/bold]")
        console.print(Panel(favorite.content, border_style="dim"))


@favorites.command()
@click.option('--project/--all', default=False, help='Search in current project only')
@click.option('--tags', help='Filter by tags (comma-separated)')
def search(project, tags):
    """Search favorite prompts interactively."""
    manager = GlobalDataManager()
    
    if not manager.settings.favorite_prompts_enabled:
        console.print("[yellow]Favorite prompts are disabled in settings[/yellow]")
        return
    
    # Get favorites
    project_path = os.getcwd() if project else None
    tag_list = [t.strip() for t in tags.split(',')] if tags else None
    
    favorites = manager.get_favorite_prompts(
        project_path=project_path,
        tags=tag_list
    )
    
    if not favorites:
        console.print("[yellow]No favorite prompts found[/yellow]")
        return
    
    # Interactive selection
    console.print("[cyan]Select a favorite prompt:[/cyan]")
    for i, fav in enumerate(favorites[:10], 1):
        console.print(f"{i}. {fav.title} [dim]({fav.use_count} uses)[/dim]")
    
    try:
        choice = click.prompt("Enter number", type=int)
        if 1 <= choice <= len(favorites):
            selected = favorites[choice - 1]
            
            # Show and use the selected favorite
            console.print(f"\n[green]Selected:[/green] {selected.title}")
            console.print(Panel(selected.content, border_style="dim"))
            
            if click.confirm("Use this prompt?"):
                manager.use_favorite_prompt(selected.id)
                try:
                    import pyperclip
                    pyperclip.copy(selected.content)
                    console.print("[green]✓[/green] Copied to clipboard")
                except ImportError:
                    pass
        else:
            console.print("[red]Invalid selection[/red]")
    except (ValueError, EOFError):
        console.print("[yellow]Cancelled[/yellow]")