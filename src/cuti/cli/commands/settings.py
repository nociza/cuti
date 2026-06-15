"""
CLI commands for managing global settings and data.
"""

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...services.global_data_manager import GlobalDataManager, GlobalSettings
from ...services.usage_sync_service import UsageSyncManager

console = Console()
app = typer.Typer(help="Manage global cuti settings and data")


settings = app


@app.command()
def show() -> None:
    """Show current global settings."""
    manager = GlobalDataManager()
    settings = manager.settings

    table = Table(title="Global Settings", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")
    table.add_column("Description", style="dim")

    table.add_row(
        "Usage Tracking",
        "✓ Enabled" if settings.usage_tracking_enabled else "✗ Disabled",
        "Track Claude Code usage statistics"
    )
    table.add_row(
        "Privacy Mode",
        "✓ Enabled" if settings.privacy_mode else "✗ Disabled",
        "Don't store prompt content"
    )
    table.add_row(
        "Favorite Prompts",
        "✓ Enabled" if settings.favorite_prompts_enabled else "✗ Disabled",
        "Save favorite prompts for reuse"
    )
    table.add_row(
        "Auto Cleanup",
        f"{settings.auto_cleanup_days} days",
        "Delete data older than N days"
    )
    table.add_row(
        "Max Storage",
        f"{settings.max_storage_mb} MB",
        "Maximum storage for global data"
    )
    table.add_row(
        "Claude Plan",
        settings.claude_plan.upper(),
        "Your Claude subscription plan"
    )
    table.add_row(
        "Theme",
        settings.theme.capitalize(),
        "UI theme preference"
    )
    table.add_row(
        "Notifications",
        "✓ Enabled" if settings.notifications_enabled else "✗ Disabled",
        "Show notifications"
    )

    console.print(table)

    # Show storage info
    storage_info = manager.get_storage_info()
    storage_panel = Panel(
        f"Storage: {storage_info['total_size_mb']} MB / {storage_info['max_storage_mb']} MB "
        f"({storage_info['usage_percentage']}%)\n"
        f"Files: {storage_info['file_count']}\n"
        f"Database: {storage_info['database_size_mb']} MB",
        title="Storage Usage",
        border_style="dim"
    )
    console.print(storage_panel)


@app.command()
def update(
    tracking: bool | None = typer.Option(None, "--tracking/--no-tracking", help="Enable/disable usage tracking"),
    privacy: bool | None = typer.Option(None, "--privacy/--no-privacy", help="Enable/disable privacy mode"),
    favorites: bool | None = typer.Option(None, "--favorites/--no-favorites", help="Enable/disable favorite prompts"),
    cleanup_days: int | None = typer.Option(None, "--cleanup-days", help="Days to keep data"),
    max_storage: int | None = typer.Option(None, "--max-storage", help="Max storage in MB"),
    plan: str | None = typer.Option(None, "--plan", help="Claude plan: pro, max5, or max20"),
    theme: str | None = typer.Option(None, "--theme", help="UI theme: light, dark, or auto"),
    notifications: bool | None = typer.Option(
        None, "--notifications/--no-notifications", help="Enable/disable notifications"
    ),
) -> None:
    """Update global settings."""
    manager = GlobalDataManager()
    settings = manager.settings
    updated = False

    # Update settings based on provided options
    if tracking is not None:
        settings.usage_tracking_enabled = tracking
        updated = True

    if privacy is not None:
        settings.privacy_mode = privacy
        updated = True

    if favorites is not None:
        settings.favorite_prompts_enabled = favorites
        updated = True

    if cleanup_days is not None:
        settings.auto_cleanup_days = cleanup_days
        updated = True

    if max_storage is not None:
        settings.max_storage_mb = max_storage
        updated = True

    if plan is not None:
        if plan not in {"pro", "max5", "max20"}:
            console.print("[red]Plan must be one of: pro, max5, max20[/red]")
            raise typer.Exit(1)
        settings.claude_plan = plan
        updated = True

    if theme is not None:
        if theme not in {"light", "dark", "auto"}:
            console.print("[red]Theme must be one of: light, dark, auto[/red]")
            raise typer.Exit(1)
        settings.theme = theme
        updated = True

    if notifications is not None:
        settings.notifications_enabled = notifications
        updated = True

    if updated:
        manager.save_settings(settings)
        console.print("[green]✓[/green] Settings updated successfully")
    else:
        console.print("[yellow]No settings changed[/yellow]")


@app.command()
def reset() -> None:
    """Reset settings to defaults."""
    if typer.confirm("Reset all settings to defaults?"):
        manager = GlobalDataManager()
        manager.save_settings(GlobalSettings())
        console.print("[green]✓[/green] Settings reset to defaults")


@app.command()
def cleanup() -> None:
    """Clean up old usage data."""
    manager = GlobalDataManager()

    if typer.confirm(f"Delete data older than {manager.settings.auto_cleanup_days} days?"):
        manager.cleanup_old_data()
        console.print("[green]✓[/green] Old data cleaned up")

        # Show updated storage info
        storage_info = manager.get_storage_info()
        console.print(f"Storage now: {storage_info['total_size_mb']} MB")


@app.command()
def backup() -> None:
    """Create a backup of global data."""
    manager = GlobalDataManager()
    backup_path = manager.backup_database()

    if backup_path:
        console.print(f"[green]✓[/green] Backup created: {backup_path}")
    else:
        console.print("[red]✗[/red] Backup failed")


@app.command()
def export(
    output_path: str = typer.Argument(..., help="Output file path"),
    export_format: str = typer.Option("json", "--format", help="Export format: json or csv"),
) -> None:
    """Export all global data."""
    manager = GlobalDataManager()

    if export_format not in {"json", "csv"}:
        console.print("[red]Format must be one of: json, csv[/red]")
        raise typer.Exit(1)

    if manager.export_data(output_path, export_format):
        console.print(f"[green]✓[/green] Data exported to: {output_path}")
    else:
        console.print("[red]✗[/red] Export failed")


@app.command()
def sync() -> None:
    """Sync usage data from Claude logs."""
    console.print("Syncing usage data from Claude logs...")

    imported = UsageSyncManager.sync_now()

    if imported > 0:
        console.print(f"[green]✓[/green] Imported {imported} new usage records")
    elif imported == 0:
        console.print("[yellow]No new usage data found[/yellow]")
    else:
        console.print("[red]✗[/red] Sync failed")


@app.command()
def sync_status() -> None:
    """Show sync service status."""
    status = UsageSyncManager.get_status()

    table = Table(title="Sync Service Status", box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Status", "🟢 Running" if status['running'] else "🔴 Stopped")
    table.add_row("Last Sync", status['last_sync'] or "Never")
    table.add_row("Sync Count", str(status['sync_count']))
    table.add_row("Error Count", str(status['error_count']))
    table.add_row("Sync Interval", f"{status['sync_interval']} seconds")
    table.add_row("Tracking Enabled", "Yes" if status['tracking_enabled'] else "No")

    console.print(table)


@app.command()
def start_sync() -> None:
    """Start the background sync service."""
    UsageSyncManager.start_service()
    console.print("[green]✓[/green] Sync service started")


@app.command()
def stop_sync() -> None:
    """Stop the background sync service."""
    UsageSyncManager.stop_service()
    console.print("[green]✓[/green] Sync service stopped")
