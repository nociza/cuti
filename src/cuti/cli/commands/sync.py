"""
CLI commands for syncing usage data.
"""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
from pathlib import Path

from ...services.usage_sync_service import UsageSyncManager
from ...services.container_usage_sync import get_container_sync, sync_now as container_sync_now
from ...services.global_data_manager import GlobalDataManager

app = typer.Typer(help="Sync usage data between container and host")
console = Console()


@app.command()
def now(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output")
):
    """Manually trigger usage data sync."""
    
    # Check if we're in a container
    import os
    is_container = os.environ.get("CUTI_IN_CONTAINER") == "true"
    
    if is_container:
        console.print("[cyan]Running container usage sync...[/cyan]")
        records = container_sync_now()
        
        if records > 0:
            console.print(f"✅ Synced {records} usage records from container to host")
        else:
            console.print("ℹ️  No new usage records to sync")
    else:
        console.print("[cyan]Running host usage sync...[/cyan]")
        records = UsageSyncManager.sync_now()
        
        if records > 0:
            console.print(f"✅ Imported {records} new usage records")
        else:
            console.print("ℹ️  No new usage records found")
    
    if verbose:
        # Show sync status
        status = UsageSyncManager.get_status()
        console.print("\n[bold]Sync Status:[/bold]")
        console.print(f"  Last sync: {status.get('last_sync', 'Never')}")
        console.print(f"  Total syncs: {status.get('sync_count', 0)}")
        console.print(f"  Errors: {status.get('error_count', 0)}")


@app.command()
def status():
    """Show usage sync service status."""
    
    # Get sync status
    status = UsageSyncManager.get_status()
    
    # Create status table
    table = Table(title="Usage Sync Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Service Running", "✅ Yes" if status['running'] else "❌ No")
    table.add_row("Tracking Enabled", "✅ Yes" if status['tracking_enabled'] else "❌ No")
    table.add_row("Last Sync", status.get('last_sync', 'Never'))
    table.add_row("Total Syncs", str(status.get('sync_count', 0)))
    table.add_row("Error Count", str(status.get('error_count', 0)))
    table.add_row("Sync Interval", f"{status.get('sync_interval', 300)} seconds")
    
    console.print(table)
    
    # Check container sync if in container
    import os
    if os.environ.get("CUTI_IN_CONTAINER") == "true":
        console.print("\n[bold]Container Sync:[/bold]")
        sync = get_container_sync()
        if sync.should_run():
            console.print("  ✅ Container sync available")
            if sync._last_sync:
                console.print(f"  Last sync: {sync._last_sync.isoformat()}")
            console.print(f"  Sync count: {sync._sync_count}")
        else:
            console.print("  ℹ️  Container sync not needed")


@app.command()
def start():
    """Start the background usage sync service."""
    
    import os
    is_container = os.environ.get("CUTI_IN_CONTAINER") == "true"
    
    if is_container:
        console.print("[cyan]Starting container usage sync service...[/cyan]")
        sync = get_container_sync()
        sync.start_background_sync()
        console.print("✅ Container usage sync service started")
    else:
        console.print("[cyan]Starting host usage sync service...[/cyan]")
        UsageSyncManager.start_service()
        console.print("✅ Host usage sync service started")


@app.command()
def stop():
    """Stop the background usage sync service."""
    
    import os
    is_container = os.environ.get("CUTI_IN_CONTAINER") == "true"
    
    if is_container:
        console.print("[cyan]Stopping container usage sync service...[/cyan]")
        sync = get_container_sync()
        sync.stop_background_sync()
        console.print("✅ Container usage sync service stopped")
    else:
        console.print("[cyan]Stopping host usage sync service...[/cyan]")
        UsageSyncManager.stop_service()
        console.print("✅ Host usage sync service stopped")


@app.command()
def stats():
    """Show usage statistics from the global database."""
    
    manager = GlobalDataManager()
    
    # Get usage statistics
    stats = manager.get_usage_stats(days=30)
    
    if not stats:
        console.print("ℹ️  No usage data available")
        return
    
    # Create statistics table
    table = Table(title="Usage Statistics (Last 30 Days)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Tokens", f"{stats.get('total_tokens', 0):,}")
    table.add_row("Input Tokens", f"{stats.get('input_tokens', 0):,}")
    table.add_row("Output Tokens", f"{stats.get('output_tokens', 0):,}")
    table.add_row("Cache Read Tokens", f"{stats.get('cache_read_tokens', 0):,}")
    table.add_row("Cache Creation Tokens", f"{stats.get('cache_creation_tokens', 0):,}")
    table.add_row("Total Cost", f"${stats.get('total_cost', 0):.4f}")
    table.add_row("Total Requests", str(stats.get('request_count', 0)))
    
    console.print(table)
    
    # Show breakdown by model if available
    if 'by_model' in stats and stats['by_model']:
        console.print("\n[bold]Usage by Model:[/bold]")
        model_table = Table()
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Requests", style="yellow")
        model_table.add_column("Tokens", style="green")
        model_table.add_column("Cost", style="magenta")
        
        for model, data in stats['by_model'].items():
            model_table.add_row(
                model,
                str(data.get('requests', 0)),
                f"{data.get('tokens', 0):,}",
                f"${data.get('cost', 0):.4f}"
            )
        
        console.print(model_table)


if __name__ == "__main__":
    app()