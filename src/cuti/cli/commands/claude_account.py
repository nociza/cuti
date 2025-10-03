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
        
        # Check if account has API keys and generate env script
        env_vars = manager.get_env_vars(account)
        if env_vars:
            script_file = manager.save_env_script(account)
            console.print(f"\n[yellow]📝 API Key Environment Variables:[/yellow]")
            console.print(f"  To use API keys, run: [cyan]source {script_file}[/cyan]")
            console.print(f"  Or use: [cyan]cuti claude env {account}[/cyan]")
            console.print("\n[dim]Set variables:[/dim]")
            for key in env_vars.keys():
                console.print(f"  • [cyan]{key}[/cyan]")
        
        console.print("\n[dim]OAuth credentials active in containers.[/dim]")
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


@app.command("add-api-key")
def add_api_key(
    account: str = typer.Argument(..., help="Account name"),
    api_key: str = typer.Option(..., "--api-key", "-k", help="API key or bearer token"),
    provider: str = typer.Option("anthropic", "--provider", "-p", help="Provider: anthropic or bedrock"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region (for Bedrock)"),
    access_key: str = typer.Option(None, "--access-key", help="AWS access key ID (Bedrock with access keys)"),
    secret_key: str = typer.Option(None, "--secret-key", help="AWS secret access key (Bedrock with access keys)"),
    use_bearer: bool = typer.Option(True, "--bearer/--access-keys", help="Use bearer token (default) or access keys for Bedrock")
):
    """Add API key credentials to an account.
    
    For Bedrock, you can use either:
    - Bearer token (recommended): Just --api-key and --region
    - Access keys: --api-key, --region, --access-key, --secret-key with --access-keys flag
    """
    manager = ClaudeAccountManager()
    
    # Validate provider
    if provider not in ["anthropic", "bedrock"]:
        console.print(f"[red]✗[/red] Invalid provider: {provider}")
        console.print("[dim]Valid providers: anthropic, bedrock[/dim]")
        raise typer.Exit(1)
    
    # Convert provider to credential type
    cred_type = "anthropic_api" if provider == "anthropic" else "bedrock_api"
    
    try:
        if provider == "bedrock":
            if use_bearer:
                # Bearer token mode (Option D - preferred)
                manager.save_api_key(
                    account,
                    api_key,
                    provider=cred_type,
                    region=region or "us-east-1",
                    use_bearer_token=True
                )
                console.print(f"[green]✓[/green] Added Bedrock bearer token to account: [cyan]{account}[/cyan]")
                console.print(f"[dim]Region:[/dim] {region or 'us-east-1'}")
            else:
                # Access keys mode (Option B)
                if not all([region, access_key, secret_key]):
                    console.print("[red]✗[/red] Access keys mode requires --region, --access-key, and --secret-key")
                    raise typer.Exit(1)
                
                manager.save_api_key(
                    account,
                    api_key,
                    provider=cred_type,
                    region=region,
                    access_key_id=access_key,
                    secret_access_key=secret_key,
                    use_bearer_token=False
                )
                console.print(f"[green]✓[/green] Added Bedrock access keys to account: [cyan]{account}[/cyan]")
                console.print(f"[dim]Region:[/dim] {region}")
        else:
            manager.save_api_key(account, api_key, provider=cred_type)
            console.print(f"[green]✓[/green] Added {provider} API key to account: [cyan]{account}[/cyan]")
        
        console.print(f"\n[dim]API key stored securely with 600 permissions[/dim]")
        console.print(f"[dim]To use: [cyan]cuti claude env {account}[/cyan][/dim]")
        
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to save API key: {str(e)}")
        raise typer.Exit(1)


@app.command("show-api-key")
def show_api_key(
    account: str = typer.Argument(..., help="Account name"),
    provider: str = typer.Option("anthropic", "--provider", "-p", help="Provider: anthropic or bedrock"),
    show_secret: bool = typer.Option(False, "--show-secret", help="Show full API key (default: masked)")
):
    """Show API key for an account."""
    manager = ClaudeAccountManager()
    
    api_key_info = manager.get_api_key(account, provider)
    
    if not api_key_info:
        console.print(f"[yellow]⚠[/yellow]  No {provider} API key found for account: {account}")
        console.print(f"\n[dim]Add one with:[/dim] [cyan]cuti claude add-api-key {account} --api-key YOUR_KEY --provider {provider}[/cyan]")
        return
    
    # Create display panel
    content = []
    content.append(f"[bold]Provider:[/bold] {api_key_info.get('provider', provider)}")
    content.append(f"[bold]Created:[/bold] {api_key_info.get('created', 'unknown')}")
    
    if provider == "anthropic":
        api_key = api_key_info.get("api_key", "")
        if show_secret:
            content.append(f"[bold]API Key:[/bold] {api_key}")
        else:
            masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            content.append(f"[bold]API Key:[/bold] {masked}")
    elif provider == "bedrock":
        auth_method = api_key_info.get('auth_method', 'bearer_token')
        content.append(f"[bold]Auth Method:[/bold] {auth_method}")
        content.append(f"[bold]Region:[/bold] {api_key_info.get('region', 'unknown')}")
        
        if auth_method == "bearer_token":
            bearer_token = api_key_info.get("bearer_token", "")
            if show_secret:
                content.append(f"[bold]Bearer Token:[/bold] {bearer_token}")
            else:
                masked = bearer_token[:12] + "..." + bearer_token[-6:] if len(bearer_token) > 18 else "***"
                content.append(f"[bold]Bearer Token:[/bold] {masked}")
        else:
            access_key = api_key_info.get("access_key_id", "")
            secret_key = api_key_info.get("secret_access_key", "")
            
            if show_secret:
                content.append(f"[bold]Access Key ID:[/bold] {access_key}")
                content.append(f"[bold]Secret Access Key:[/bold] {secret_key}")
            else:
                masked_access = access_key[:8] + "..." if len(access_key) > 8 else "***"
                content.append(f"[bold]Access Key ID:[/bold] {masked_access}")
                content.append(f"[bold]Secret Access Key:[/bold] ***")
    
    if not show_secret:
        content.append(f"\n[dim]Use --show-secret to reveal full credentials[/dim]")
    
    panel = Panel(
        "\n".join(content),
        title=f"{provider.capitalize()} API Key - {account}",
        border_style="cyan"
    )
    console.print(panel)


@app.command("list-api-keys")
def list_api_keys_cmd(
    account: str = typer.Argument(..., help="Account name")
):
    """List all API key providers for an account."""
    manager = ClaudeAccountManager()
    
    providers = manager.list_api_keys(account)
    
    if not providers:
        console.print(f"[yellow]No API keys found for account: {account}[/yellow]")
        console.print("\n[dim]Add an API key with:[/dim]")
        console.print(f"  [cyan]cuti claude add-api-key {account} --api-key YOUR_KEY --provider anthropic[/cyan]")
        return
    
    console.print(f"[green]API Keys for account:[/green] [cyan]{account}[/cyan]\n")
    
    for provider in providers:
        api_key_info = manager.get_api_key(account, provider)
        if api_key_info:
            created = api_key_info.get("created", "unknown")
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created)
                created = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
            
            console.print(f"  • [cyan]{provider}[/cyan] - Added: {created}")


@app.command("delete-api-key")
def delete_api_key_cmd(
    account: str = typer.Argument(..., help="Account name"),
    provider: str = typer.Option(..., "--provider", "-p", help="Provider: anthropic or bedrock"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Delete an API key from an account."""
    manager = ClaudeAccountManager()
    
    # Check if API key exists
    api_key_info = manager.get_api_key(account, provider)
    if not api_key_info:
        console.print(f"[yellow]⚠[/yellow]  No {provider} API key found for account: {account}")
        return
    
    # Confirm deletion
    if not force:
        console.print(f"[yellow]⚠[/yellow]  About to delete {provider} API key from account: [cyan]{account}[/cyan]")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[dim]Deletion cancelled[/dim]")
            return
    
    try:
        if manager.delete_api_key(account, provider):
            console.print(f"[green]✓[/green] Deleted {provider} API key from account: [cyan]{account}[/cyan]")
        else:
            console.print(f"[red]✗[/red] Failed to delete API key")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to delete API key: {str(e)}")
        raise typer.Exit(1)


@app.command("env")
def show_env(
    account: str = typer.Argument(None, help="Account name (default: active account)"),
    export: bool = typer.Option(False, "--export", "-e", help="Print export commands"),
    save: bool = typer.Option(False, "--save", "-s", help="Save to env.sh file"),
    unset: bool = typer.Option(False, "--unset", "-u", help="Show unset commands instead")
):
    """Show environment variables for API keys.
    
    Usage:
      cuti claude env                    # Show vars for active account
      cuti claude env my-account         # Show vars for specific account
      cuti claude env my-account --export  # Print export commands
      cuti claude env --unset            # Show unset commands
      
    To apply:
      eval $(cuti claude env my-account --export)
      # Or
      source ~/.cuti/claude-accounts/my-account/env.sh
    """
    manager = ClaudeAccountManager()
    
    # Handle unset mode
    if unset:
        console.print("[yellow]Unset commands for all Claude API variables:[/yellow]\n")
        for var in manager.get_env_vars_to_unset():
            console.print(f"unset {var}")
        console.print(f"\n[dim]To apply: [cyan]eval $(cuti claude env --unset)[/cyan][/dim]")
        return
    
    # Get account name
    if not account:
        account = manager.get_active_account()
        if not account:
            console.print("[yellow]No active account[/yellow]")
            console.print("[dim]Specify an account: [cyan]cuti claude env <account>[/cyan][/dim]")
            raise typer.Exit(1)
    
    # Get environment variables
    env_vars = manager.get_env_vars(account)
    
    if not env_vars:
        console.print(f"[yellow]No API keys configured for account:[/yellow] {account}")
        console.print(f"\n[dim]Add an API key with:[/dim] [cyan]cuti claude add-api-key {account} ...[/cyan]")
        return
    
    # Export mode - just print commands
    if export:
        for key, value in env_vars.items():
            console.print(f'export {key}="{value}"')
        return
    
    # Save mode - save to file
    if save:
        script_file = manager.save_env_script(account)
        if script_file:
            console.print(f"[green]✓[/green] Saved environment script to: [cyan]{script_file}[/cyan]")
            console.print(f"\n[dim]To use:[/dim] [cyan]source {script_file}[/cyan]")
        else:
            console.print("[yellow]No API keys to save[/yellow]")
        return
    
    # Default mode - show variables nicely
    console.print(f"[green]Environment variables for account:[/green] [cyan]{account}[/cyan]\n")
    
    table = Table(show_header=True, box=box.SIMPLE)
    table.add_column("Variable", style="cyan")
    table.add_column("Value", style="dim")
    
    for key, value in env_vars.items():
        # Mask sensitive values
        if "KEY" in key or "SECRET" in key or "TOKEN" in key:
            if len(value) > 20:
                masked = value[:8] + "..." + value[-6:]
            else:
                masked = "***"
            table.add_row(key, masked)
        else:
            table.add_row(key, value)
    
    console.print(table)
    
    # Show usage instructions
    console.print(f"\n[yellow]To apply these variables:[/yellow]")
    console.print(f"  [cyan]eval $(cuti claude env {account} --export)[/cyan]")
    console.print(f"\n[yellow]Or save to file and source:[/yellow]")
    console.print(f"  [cyan]cuti claude env {account} --save[/cyan]")
    console.print(f"  [cyan]source ~/.cuti/claude-accounts/{account}/env.sh[/cyan]")
    console.print(f"\n[yellow]To unset all variables:[/yellow]")
    console.print(f"  [cyan]eval $(cuti claude env --unset)[/cyan]")

