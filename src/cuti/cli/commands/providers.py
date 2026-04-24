"""CLI commands for managing agent providers in cuti containers."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...services.provider_host import ProviderHostService, ProviderHostStatus
from ...services.providers import ProviderManager

console = Console()
app = typer.Typer(help="Manage agent providers from the host CLI.")


def _validate_provider(name: str) -> str:
    try:
        return ProviderManager().get_metadata(name).name
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _setup_state_label(status: ProviderHostStatus) -> str:
    if status.setup_state == "ready":
        return "ready"
    if status.setup_state == "partial":
        return "partial"
    return "needs setup"


def _provider_label(status: ProviderHostStatus) -> str:
    label = f"{status.title} ({status.provider})"
    if status.experimental:
        return f"{label} [experimental]"
    return label


def _selection_label(status: ProviderHostStatus) -> str:
    enabled_label = "enabled" if status.enabled else "disabled"
    if not status.explicit:
        enabled_label = f"{enabled_label} (default)"
    if status.experimental:
        enabled_label = f"{enabled_label}; experimental"
    return enabled_label


def _print_provider_panel(status: ProviderHostStatus) -> None:
    state_paths = "\n".join(f"  - {path}" for path in status.state_paths) or "  - none"
    existing_paths = (
        "\n".join(f"  - {path}" for path in status.existing_state_paths)
        or "  - none detected"
    )

    lines = [
        f"[bold]selection:[/bold] {_selection_label(status)}",
        f"[bold]setup state:[/bold] {_setup_state_label(status)}",
        f"[bold]detail:[/bold] {status.detail}",
        f"[bold]release track:[/bold] {'experimental' if status.experimental else 'standard'}",
        f"[bold]container command:[/bold] {', '.join(status.commands) or '(none)'}",
        f"[bold]host command:[/bold] {status.host_command_path or 'not installed on host'}",
        f"[bold]setup flow:[/bold] {status.setup_hint or 'n/a'}",
        f"[bold]setup command:[/bold] {status.setup_command or 'n/a'}",
        f"[bold]update flow:[/bold] {status.update_hint or 'n/a'}",
        f"[bold]update command:[/bold] {status.update_command or 'n/a'}",
    ]
    if status.experimental_note:
        lines.extend(
            [
                f"[bold]experimental note:[/bold] {status.experimental_note}",
            ]
        )
    lines.extend(
        [
            "[bold]state paths:[/bold]",
            state_paths,
            "[bold]existing paths:[/bold]",
            existing_paths,
            f"[bold]host actions:[/bold] cuti providers auth {status.provider} --login",
            f"                cuti providers update {status.provider}",
        ]
    )
    console.print(
        Panel("\n".join(lines), title=_provider_label(status), border_style="cyan")
    )


@app.command("list")
def list_providers(
    enabled_only: bool = typer.Option(
        False, "--enabled-only", help="Show only enabled providers"
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON"),
) -> None:
    """List known providers with host-side setup status."""

    service = ProviderHostService()
    statuses = service.list_statuses(enabled_only=enabled_only)
    if json_output:
        console.print(json.dumps([status.to_dict() for status in statuses], indent=2))
        return

    table = Table(title="Agent Providers", show_header=True)
    table.add_column("Provider", style="cyan")
    table.add_column("Track", style="magenta")
    table.add_column("Selected", style="green")
    table.add_column("Setup", style="yellow")
    table.add_column("Host CLI", style="dim")
    table.add_column("Summary")

    for status in statuses:
        table.add_row(
            _provider_label(status),
            "experimental" if status.experimental else "standard",
            _selection_label(status),
            _setup_state_label(status),
            status.host_command_path or "container-managed",
            status.detail,
        )

    console.print(table)
    console.print("[dim]Use `cuti providers status <provider>` for full details.[/dim]")


@app.command()
def enable(name: str = typer.Argument(..., callback=_validate_provider)) -> None:
    """Enable a provider for future container runs."""

    manager = ProviderManager()
    canonical = manager.get_metadata(name).name
    meta = manager.get_metadata(canonical)
    manager.set_enabled(canonical, True)
    message = f"Provider '{canonical}' enabled."
    if meta.experimental:
        message = f"{message} This integration is experimental."
    console.print(f"[green]{message}[/green]")


@app.command()
def disable(name: str = typer.Argument(..., callback=_validate_provider)) -> None:
    """Disable a provider for future container runs."""

    manager = ProviderManager()
    canonical = manager.get_metadata(name).name
    manager.set_enabled(canonical, False)
    console.print(f"[yellow]Provider '{canonical}' disabled.[/yellow]")


@app.command()
def status(
    name: str = typer.Argument("claude", callback=_validate_provider),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON"),
) -> None:
    """Show detailed host/container status for one provider."""

    service = ProviderHostService()
    provider_status = service.get_status(name)
    if json_output:
        console.print(json.dumps(provider_status.to_dict(), indent=2))
        return
    _print_provider_panel(provider_status)


@app.command()
def doctor(
    enabled_only: bool = typer.Option(
        False, "--enabled-only", help="Check only enabled providers"
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON"),
) -> None:
    """Run a host-side provider readiness check."""

    service = ProviderHostService()
    statuses = service.list_statuses(enabled_only=enabled_only)
    if json_output:
        console.print(json.dumps([status.to_dict() for status in statuses], indent=2))
        return

    table = Table(title="Provider Doctor", show_header=True)
    table.add_column("Provider", style="cyan")
    table.add_column("Selected", style="green")
    table.add_column("Setup", style="yellow")
    table.add_column("Fix")

    for status in statuses:
        fix = "none"
        if status.setup_state != "ready":
            fix = f"cuti providers auth {status.provider} --login"
        table.add_row(
            status.provider,
            "yes" if status.enabled else "no",
            _setup_state_label(status),
            fix,
        )

    console.print(table)
    console.print(
        "[dim]Run `cuti providers status <provider>` for path and setup details.[/dim]"
    )


@app.command()
def auth(
    name: str = typer.Argument("claude", callback=_validate_provider),
    login: bool = typer.Option(
        False,
        "--login",
        help="Run the provider's interactive setup flow inside the container",
    ),
    rebuild: bool = typer.Option(
        False, "--rebuild", help="Rebuild the container image first"
    ),
) -> None:
    """Show or run provider authentication/onboarding from the host."""

    service = ProviderHostService()
    provider_status = service.get_status(name)
    _print_provider_panel(provider_status)
    if not login:
        console.print(
            f"[dim]Run `cuti providers auth {provider_status.provider} --login` to start setup inside the container.[/dim]"
        )
        return

    changed = service.ensure_enabled(provider_status.provider)
    if changed:
        console.print(
            f"[yellow]Enabled provider '{provider_status.provider}' for this setup flow.[/yellow]"
        )

    exit_code = service.run_setup(provider_status.provider, rebuild=rebuild)
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command()
def update(
    name: str = typer.Argument(
        None, help="Provider name (default: all enabled providers)"
    ),
    rebuild: bool = typer.Option(
        False, "--rebuild", help="Rebuild the container image first"
    ),
) -> None:
    """Update one provider, or all enabled providers, from the host."""

    service = ProviderHostService()
    if name:
        targets = [_validate_provider(name)]
    else:
        targets = [
            status.provider for status in service.list_statuses(enabled_only=True)
        ]
        if not targets:
            console.print(
                "[yellow]No enabled providers selected. Enable one with `cuti providers enable <name>` first.[/yellow]"
            )
            raise typer.Exit(1)

    for provider in targets:
        status_info = service.get_status(provider)
        console.print(f"[cyan]Updating {status_info.title} ({provider})...[/cyan]")
        changed = service.ensure_enabled(provider)
        if changed:
            console.print(
                f"[yellow]Enabled provider '{provider}' for this update flow.[/yellow]"
            )
        exit_code = service.run_update(provider, rebuild=rebuild)
        if exit_code != 0:
            raise typer.Exit(exit_code)
