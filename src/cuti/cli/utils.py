"""
CLI utility functions.
"""

from typing import Any

from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def test_connection(manager: Any) -> bool:
    """Test Claude Code connection with progress indicator."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task(description="Testing Claude Code connection...", total=None)
        is_working, message = manager.claude_interface.test_connection()

    if is_working:
        rprint(f"[green]✓[/green] {message}")
        return True
    else:
        rprint(f"[red]✗[/red] {message}")
        return False


def format_prompt_status(status_value: str) -> str:
    """Format prompt status with emoji."""
    status_emojis = {
        "queued": "⏳",
        "executing": "▶️",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "🚫",
        "rate_limited": "⚠️"
    }
    emoji = status_emojis.get(status_value, "❓")
    return f"{emoji} {status_value}"


def confirm_action(message: str) -> bool:
    """Ask for user confirmation."""
    import typer
    return typer.confirm(message)


def print_error(message: str) -> None:
    """Print error message with consistent formatting."""
    rprint(f"[red]✗[/red] {message}")


def print_success(message: str) -> None:
    """Print success message with consistent formatting."""
    rprint(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print warning message with consistent formatting."""
    rprint(f"[yellow]⚠[/yellow] {message}")
