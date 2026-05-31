"""
CLI utility functions.
"""

from rich import print as rprint
from rich.console import Console

console = Console()


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
