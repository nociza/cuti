"""CLI commands for managing optional addons like Clawdbot."""

import typer
from rich.console import Console

from ...services.addons import AddonManager, KNOWN_ADDONS

console = Console()
app = typer.Typer(help="Manage optional addons (Clawdbot and more).")


def _validate_addon(name: str) -> str:
    if name not in KNOWN_ADDONS:
        available = ", ".join(sorted(KNOWN_ADDONS))
        raise typer.BadParameter(f"Unknown addon '{name}'. Available addons: {available}")
    return name


@app.command("list")
def list_addons() -> None:
    """List known addons and their enabled state."""

    manager = AddonManager()
    rows = []
    for name, meta in KNOWN_ADDONS.items():
        state = manager.get_state(name)
        enabled = state.get("enabled")
        rows.append(
            {
                "name": name,
                "title": meta.title,
                "enabled": "yes" if enabled else "no" if enabled is not None else "not set",
                "description": meta.description,
            }
        )

    for row in rows:
        console.print(f"[bold]{row['title']}[/bold] ({row['name']}) - {row['enabled']}")
        console.print(f"  {row['description']}")


@app.command()
def enable(name: str = typer.Argument(..., callback=_validate_addon)) -> None:
    """Enable an addon (installs on the next container build)."""

    manager = AddonManager()
    manager.set_enabled(name, True)
    console.print(f"[green]Addon '{name}' enabled.[/green]")


@app.command()
def disable(name: str = typer.Argument(..., callback=_validate_addon)) -> None:
    """Disable an addon (skips installation)."""

    manager = AddonManager()
    manager.set_enabled(name, False)
    console.print(f"[yellow]Addon '{name}' disabled.[/yellow]")


@app.command()
def status(name: str = typer.Argument("clawdbot", callback=_validate_addon)) -> None:
    """Show detailed state for an addon."""

    manager = AddonManager()
    state = manager.get_state(name)
    if not state:
        console.print(f"[cyan]Addon '{name}' has no stored preferences yet (will use defaults).[/cyan]")
        return
    console.print(
        f"""[bold]{name}[/bold] state:
  enabled: {state.get('enabled')}
  prompted_at: {state.get('prompted_at')}
  updated_at: {state.get('updated_at')}
  source: {state.get('source')}"""
    )
