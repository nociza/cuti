"""
CLI commands for managing favorite prompts.
"""

import os
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...services.global_data_manager import GlobalDataManager

console = Console()
app = typer.Typer(help="Manage favorite prompts")


favorites = app


@app.command(name="list")
def list_favorites(
    project: str | None = typer.Option(None, "--project", help="Filter by project path"),
    tags: str | None = typer.Option(None, "--tags", help="Filter by tags (comma-separated)"),
    limit: int = typer.Option(20, "--limit", help="Maximum number to show"),
) -> None:
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


@app.command()
def show(favorite_id: str = typer.Argument(..., help="Favorite prompt ID")) -> None:
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


@app.command()
def add(
    title: str = typer.Argument(..., help="Favorite prompt title"),
    content: str | None = typer.Option(None, "--content", help="Prompt content (or read from stdin)"),
    file: Path | None = typer.Option(None, "--file", exists=True, dir_okay=False, help="Read content from file"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    project: str | None = typer.Option(None, "--project", help="Associated project path"),
) -> None:
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


@app.command()
def remove(favorite_id: str = typer.Argument(..., help="Favorite prompt ID")) -> None:
    """Remove a favorite prompt."""
    if typer.confirm(f"Remove favorite '{favorite_id}'?"):
        # We need to add a remove method to GlobalDataManager
        # For now, we'll mark it as a TODO
        console.print("[yellow]Remove functionality to be implemented[/yellow]")


@app.command()
def use(favorite_id: str = typer.Argument(..., help="Favorite prompt ID")) -> None:
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
        import pyperclip  # type: ignore[import-not-found]
        pyperclip.copy(favorite.content)
        console.print("[green]✓[/green] Copied to clipboard and marked as used")
    except ImportError:
        console.print("[green]✓[/green] Marked as used")
        console.print("\n[bold]Content:[/bold]")
        console.print(Panel(favorite.content, border_style="dim"))


@app.command()
def search(
    project: bool = typer.Option(False, "--project/--all", help="Search in current project only"),
    tags: str | None = typer.Option(None, "--tags", help="Filter by tags (comma-separated)"),
) -> None:
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
        choice = typer.prompt("Enter number", type=int)
        if 1 <= choice <= len(favorites):
            selected = favorites[choice - 1]

            # Show and use the selected favorite
            console.print(f"\n[green]Selected:[/green] {selected.title}")
            console.print(Panel(selected.content, border_style="dim"))

            if typer.confirm("Use this prompt?"):
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
