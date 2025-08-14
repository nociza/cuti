"""
CLI commands for managing global settings and data.
"""

import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from ...services.global_data_manager import GlobalDataManager, GlobalSettings
from ...services.usage_sync_service import UsageSyncManager

console = Console()


@click.group()
def settings():
    """Manage global cuti settings and data."""
    pass


@settings.command()
def show():
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


@settings.command()
@click.option('--tracking/--no-tracking', help='Enable/disable usage tracking')
@click.option('--privacy/--no-privacy', help='Enable/disable privacy mode')
@click.option('--favorites/--no-favorites', help='Enable/disable favorite prompts')
@click.option('--cleanup-days', type=int, help='Days to keep data')
@click.option('--max-storage', type=int, help='Max storage in MB')
@click.option('--plan', type=click.Choice(['pro', 'max5', 'max20']), help='Claude plan')
@click.option('--theme', type=click.Choice(['light', 'dark', 'auto']), help='UI theme')
@click.option('--notifications/--no-notifications', help='Enable/disable notifications')
def update(**kwargs):
    """Update global settings."""
    manager = GlobalDataManager()
    settings = manager.settings
    updated = False
    
    # Update settings based on provided options
    if kwargs.get('tracking') is not None:
        settings.usage_tracking_enabled = kwargs['tracking']
        updated = True
    
    if kwargs.get('privacy') is not None:
        settings.privacy_mode = kwargs['privacy']
        updated = True
    
    if kwargs.get('favorites') is not None:
        settings.favorite_prompts_enabled = kwargs['favorites']
        updated = True
    
    if kwargs.get('cleanup_days'):
        settings.auto_cleanup_days = kwargs['cleanup_days']
        updated = True
    
    if kwargs.get('max_storage'):
        settings.max_storage_mb = kwargs['max_storage']
        updated = True
    
    if kwargs.get('plan'):
        settings.claude_plan = kwargs['plan']
        updated = True
    
    if kwargs.get('theme'):
        settings.theme = kwargs['theme']
        updated = True
    
    if kwargs.get('notifications') is not None:
        settings.notifications_enabled = kwargs['notifications']
        updated = True
    
    if updated:
        manager.save_settings(settings)
        console.print("[green]✓[/green] Settings updated successfully")
    else:
        console.print("[yellow]No settings changed[/yellow]")


@settings.command()
def reset():
    """Reset settings to defaults."""
    if click.confirm("Reset all settings to defaults?"):
        manager = GlobalDataManager()
        manager.save_settings(GlobalSettings())
        console.print("[green]✓[/green] Settings reset to defaults")


@settings.command()
def cleanup():
    """Clean up old usage data."""
    manager = GlobalDataManager()
    
    if click.confirm(f"Delete data older than {manager.settings.auto_cleanup_days} days?"):
        manager.cleanup_old_data()
        console.print("[green]✓[/green] Old data cleaned up")
        
        # Show updated storage info
        storage_info = manager.get_storage_info()
        console.print(f"Storage now: {storage_info['total_size_mb']} MB")


@settings.command()
def backup():
    """Create a backup of global data."""
    manager = GlobalDataManager()
    backup_path = manager.backup_database()
    
    if backup_path:
        console.print(f"[green]✓[/green] Backup created: {backup_path}")
    else:
        console.print("[red]✗[/red] Backup failed")


@settings.command()
@click.argument('output_path', type=click.Path())
@click.option('--format', type=click.Choice(['json', 'csv']), default='json')
def export(output_path, format):
    """Export all global data."""
    manager = GlobalDataManager()
    
    if manager.export_data(output_path, format):
        console.print(f"[green]✓[/green] Data exported to: {output_path}")
    else:
        console.print("[red]✗[/red] Export failed")


@settings.command()
def sync():
    """Sync usage data from Claude logs."""
    console.print("Syncing usage data from Claude logs...")
    
    imported = UsageSyncManager.sync_now()
    
    if imported > 0:
        console.print(f"[green]✓[/green] Imported {imported} new usage records")
    elif imported == 0:
        console.print("[yellow]No new usage data found[/yellow]")
    else:
        console.print("[red]✗[/red] Sync failed")


@settings.command()
def sync_status():
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


@settings.command()
def start_sync():
    """Start the background sync service."""
    UsageSyncManager.start_service()
    console.print("[green]✓[/green] Sync service started")


@settings.command()
def stop_sync():
    """Stop the background sync service."""
    UsageSyncManager.stop_service()
    console.print("[green]✓[/green] Sync service stopped")