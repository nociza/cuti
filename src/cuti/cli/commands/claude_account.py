"""
CLI commands for managing Claude accounts.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from pathlib import Path

from ...services.claude_account_manager import ClaudeAccountManager

app = typer.Typer(
    name="claude",
    help="Manage Claude accounts for container usage"
)

console = Console()


@app.command("list")
def list_accounts(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    backups: bool = typer.Option(False, "--backups", help="Include auto-generated backup accounts")
):
    """List all saved Claude accounts."""
    manager = ClaudeAccountManager()
    accounts = manager.list_accounts(include_backups=backups)
    backup_count = manager.count_backup_accounts()
    
    if not accounts:
        console.print("[yellow]No Claude accounts found.[/yellow]")
        console.print("\n[dim]Create a new account with:[/dim]")
        console.print("  1. [cyan]cuti claude new[/cyan]")
        console.print("  2. [cyan]claude login[/cyan] (inside container)")
        console.print("  3. [cyan]cuti claude save -n \"default\"[/cyan]")
        return
    
    table = Table(title="Claude Accounts", box=box.ROUNDED, show_header=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("Created", style="dim")
    table.add_column("Last Used", style="dim")
    table.add_column("Status", style="yellow")
    
    for account in accounts:
        status = "🟢 Active" if account["is_active"] else ""
        if not account["has_credentials"]:
            status = "⚠️  No Credentials"
        
        created = account["created"]
        if created != "unknown":
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created)
                created = dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        
        last_used = account["last_used"]
        if last_used != "never":
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_used)
                last_used = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        
        table.add_row(
            account["name"],
            account["type"],
            created,
            last_used,
            status
        )
    
    console.print(table)
    
    # Show note about hidden backups
    if not backups and backup_count > 0:
        console.print(f"\n[dim]Note: {backup_count} backup account(s) hidden. Use --backups to show them.[/dim]")
    
    # Show active account info
    active = manager.get_active_account()
    if active:
        console.print(f"\n[green]Active Account:[/green] {active}")
    else:
        console.print("\n[yellow]No active account[/yellow]")
        console.print("[dim]Use 'cuti claude use <account>' to activate an account[/dim]")


@app.command("use")
def use_account(
    account: str = typer.Argument(..., help="Account name to use")
):
    """Switch to a different Claude account."""
    manager = ClaudeAccountManager()
    
    try:
        manager.use_account(account)
        console.print(f"[green]✓[/green] Switched to account: [cyan]{account}[/cyan]")
        console.print("\n[dim]The credentials are now active in your container.[/dim]")
        console.print("[dim]Start a container with:[/dim] [cyan]cuti container[/cyan]")
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to switch account: {str(e)}")
        raise typer.Exit(1)


@app.command("save")
def save_account(
    name: str = typer.Option(..., "--name", "-n", help="Name for the account"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing account")
):
    """Save current credentials as a named account."""
    manager = ClaudeAccountManager()
    
    # Check if account already exists
    existing = manager.get_account_info(name)
    if existing and not force:
        console.print(f"[yellow]⚠[/yellow]  Account '{name}' already exists.")
        console.print("[dim]Use --force to overwrite[/dim]")
        raise typer.Exit(1)
    
    try:
        manager.save_account(name)
        action = "Updated" if existing else "Saved"
        console.print(f"[green]✓[/green] {action} account: [cyan]{name}[/cyan]")
        console.print("\n[dim]The current credentials have been saved.[/dim]")
        console.print(f"[dim]Switch to this account anytime with:[/dim] [cyan]cuti claude use \"{name}\"[/cyan]")
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to save account: {str(e)}")
        raise typer.Exit(1)


@app.command("new")
def new_account():
    """Prepare to create a new Claude account."""
    manager = ClaudeAccountManager()
    
    console.print("[cyan]Preparing to create a new Claude account...[/cyan]")
    
    try:
        had_backup = manager.new_account()
        
        if had_backup:
            console.print("\n[green]✓[/green] Current credentials backed up automatically")
        
        console.print("[green]✓[/green] Cleared all credential and session files")
        console.print("\n[green]✓[/green] Ready for new account authentication")
        
        console.print("\n[yellow]⚠️  Important:[/yellow]")
        console.print("  • If you have running containers, exit them first")
        console.print("  • Start a fresh container to avoid cached credentials")
        
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Exit any running containers (type [cyan]exit[/cyan])")
        console.print("  2. Start a fresh container: [cyan]cuti container[/cyan]")
        console.print("  3. Inside the container, login: [cyan]claude login[/cyan]")
        console.print("  4. Follow the browser authentication flow")
        console.print("  5. Exit and save: [cyan]cuti claude save -n \"Account Name\"[/cyan]")
        console.print("\n[dim]Your previous credentials (if any) have been safely backed up.[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to prepare new account: {str(e)}")
        raise typer.Exit(1)


@app.command("delete")
def delete_account(
    account: str = typer.Argument(..., help="Account name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Delete a saved Claude account."""
    manager = ClaudeAccountManager()
    
    # Check if account exists
    info = manager.get_account_info(account)
    if not info:
        console.print(f"[red]✗[/red] Account '{account}' not found")
        raise typer.Exit(1)
    
    # Confirm deletion
    if not force:
        console.print(f"[yellow]⚠[/yellow]  About to delete account: [cyan]{account}[/cyan]")
        if info["is_active"]:
            console.print("[red]This is the currently active account![/red]")
        
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[dim]Deletion cancelled[/dim]")
            return
    
    try:
        manager.delete_account(account)
        console.print(f"[green]✓[/green] Deleted account: [cyan]{account}[/cyan]")
        
        if info["is_active"]:
            console.print("\n[yellow]Note:[/yellow] This was your active account.")
            console.print("[dim]Use 'cuti claude use <account>' to activate another account[/dim]")
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to delete account: {str(e)}")
        raise typer.Exit(1)


@app.command("info")
def account_info(
    account: str = typer.Argument(..., help="Account name to show info for")
):
    """Show detailed information about an account."""
    manager = ClaudeAccountManager()
    
    info = manager.get_account_info(account)
    if not info:
        console.print(f"[red]✗[/red] Account '{account}' not found")
        raise typer.Exit(1)
    
    # Format info as a panel
    content = []
    content.append(f"[bold]Name:[/bold] {info['name']}")
    content.append(f"[bold]Type:[/bold] {info.get('type', 'unknown')}")
    content.append(f"[bold]Created:[/bold] {info['created']}")
    content.append(f"[bold]Last Used:[/bold] {info['last_used']}")
    content.append(f"[bold]Has Credentials:[/bold] {'Yes' if info['has_credentials'] else 'No'}")
    content.append(f"[bold]Active:[/bold] {'Yes' if info['is_active'] else 'No'}")
    
    if info.get("subscription_type"):
        content.append(f"[bold]Subscription:[/bold] {info['subscription_type']}")
    if info.get("email"):
        content.append(f"[bold]Email:[/bold] {info['email']}")
    
    content.append(f"\n[dim]Path: {info['path']}[/dim]")
    
    panel = Panel(
        "\n".join(content),
        title=f"Account: {account}",
        border_style="cyan"
    )
    console.print(panel)


@app.command("current")
def current_account():
    """Show the currently active account."""
    manager = ClaudeAccountManager()
    
    active = manager.get_active_account()
    if not active:
        console.print("[yellow]No active account[/yellow]")
        console.print("\n[dim]Available commands:[/dim]")
        console.print("  • [cyan]cuti claude list[/cyan] - View all accounts")
        console.print("  • [cyan]cuti claude use <account>[/cyan] - Activate an account")
        console.print("  • [cyan]cuti claude new[/cyan] - Create a new account")
        return
    
    console.print(f"[green]Active Account:[/green] [cyan]{active}[/cyan]")
    
    # Show detailed info
    info = manager.get_account_info(active)
    if info:
        console.print(f"[dim]Type:[/dim] {info.get('type', 'unknown')}")
        console.print(f"[dim]Last Used:[/dim] {info['last_used']}")

