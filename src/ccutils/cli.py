#!/usr/bin/env python3
"""
ccutils - Modern CLI with Typer and prompt aliases.
"""

from typing import Optional, List
from datetime import datetime
import json
import sys

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from .queue_manager import QueueManager
from .models import QueuedPrompt, PromptStatus
from .aliases import PromptAliasManager
from .history import PromptHistoryManager

app = typer.Typer(
    name="claude-queue",
    help="Production-ready ccutils system with aliases and monitoring",
    rich_markup_mode="rich",
)

console = Console()

# Global state
_manager: Optional[QueueManager] = None
_alias_manager: Optional[PromptAliasManager] = None
_history_manager: Optional[PromptHistoryManager] = None


def get_manager(
    storage_dir: str = "~/.claude-queue",
    claude_command: str = "claude",
    check_interval: int = 30,
    timeout: int = 3600,
) -> QueueManager:
    """Get or create queue manager instance."""
    global _manager
    if _manager is None:
        _manager = QueueManager(
            storage_dir=storage_dir,
            claude_command=claude_command,
            check_interval=check_interval,
            timeout=timeout,
        )
    return _manager


def get_alias_manager(storage_dir: str = "~/.claude-queue") -> PromptAliasManager:
    """Get or create alias manager instance."""
    global _alias_manager
    if _alias_manager is None:
        _alias_manager = PromptAliasManager(storage_dir)
    return _alias_manager


def get_history_manager(storage_dir: str = "~/.claude-queue") -> PromptHistoryManager:
    """Get or create history manager instance."""
    global _history_manager
    if _history_manager is None:
        _history_manager = PromptHistoryManager(storage_dir)
    return _history_manager


@app.command()
def start(
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
    claude_command: str = typer.Option("claude", help="Claude CLI command"),
    check_interval: int = typer.Option(30, help="Check interval in seconds"),
    timeout: int = typer.Option(3600, help="Command timeout in seconds"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """Start the queue processor."""
    manager = get_manager(storage_dir, claude_command, check_interval, timeout)
    
    def status_callback(state):
        if verbose:
            stats = state.get_stats()
            rprint(f"[blue]Queue status:[/blue] {stats['status_counts']}")

    try:
        manager.start(callback=status_callback if verbose else None)
    except KeyboardInterrupt:
        rprint("\n[yellow]Queue processor stopped by user[/yellow]")


@app.command()
def add(
    prompt: str = typer.Argument(..., help="The prompt text or alias name"),
    priority: int = typer.Option(0, "-p", "--priority", help="Priority (lower = higher)"),
    working_dir: str = typer.Option(".", "-d", "--working-dir", help="Working directory"),
    context_files: List[str] = typer.Option([], "-f", "--context-files", help="Context files"),
    max_retries: int = typer.Option(3, "-r", "--max-retries", help="Maximum retry attempts"),
    estimated_tokens: Optional[int] = typer.Option(None, "-t", "--estimated-tokens", help="Estimated tokens"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Add a prompt to the queue (supports aliases)."""
    manager = get_manager(storage_dir)
    alias_manager = get_alias_manager(storage_dir)
    history_manager = get_history_manager(storage_dir)
    
    # Check if this is an alias
    resolved_prompt = alias_manager.resolve_alias(prompt, working_dir)
    if resolved_prompt != prompt:
        rprint(f"[green]Using alias:[/green] {prompt} -> {resolved_prompt[:80]}...")
        actual_prompt = resolved_prompt
    else:
        actual_prompt = prompt
    
    # Store in history
    history_manager.add_prompt_to_history(actual_prompt, working_dir, context_files)
    
    queued_prompt = QueuedPrompt(
        content=actual_prompt,
        working_directory=working_dir,
        priority=priority,
        context_files=context_files,
        max_retries=max_retries,
        estimated_tokens=estimated_tokens,
    )

    success = manager.add_prompt(queued_prompt)
    if success:
        rprint(f"[green]✓[/green] Added prompt [bold]{queued_prompt.id}[/bold] to queue")
    else:
        rprint("[red]✗ Failed to add prompt[/red]")
        raise typer.Exit(1)


@app.command()
def template(
    filename: str = typer.Argument(..., help="Template filename"),
    priority: int = typer.Option(0, "-p", "--priority", help="Default priority"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Create a prompt template file."""
    manager = get_manager(storage_dir)
    file_path = manager.create_prompt_template(filename, priority)
    rprint(f"[green]✓[/green] Created template: [bold]{file_path}[/bold]")
    rprint("Edit the file and it will be automatically picked up")


@app.command()
def status(
    detailed: bool = typer.Option(False, "-d", "--detailed", help="Show detailed info"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Show queue status."""
    manager = get_manager(storage_dir)
    state = manager.get_status()
    stats = state.get_stats()

    if json_output:
        print(json.dumps(stats, indent=2))
        return

    # Create a nice table
    table = Table(title="ccutils Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total prompts", str(stats['total_prompts']))
    table.add_row("Total processed", str(stats['total_processed']))
    table.add_row("Failed count", str(stats['failed_count']))
    table.add_row("Rate limited count", str(stats['rate_limited_count']))
    
    if stats["last_processed"]:
        last_processed = datetime.fromisoformat(stats["last_processed"])
        table.add_row("Last processed", last_processed.strftime('%Y-%m-%d %H:%M:%S'))
    
    console.print(table)
    
    # Status breakdown
    if any(count > 0 for count in stats["status_counts"].values()):
        rprint("\n[bold]Status breakdown:[/bold]")
        for status, count in stats["status_counts"].items():
            if count > 0:
                emoji = {
                    "queued": "⏳",
                    "executing": "▶️", 
                    "completed": "✅",
                    "failed": "❌",
                    "cancelled": "🚫",
                    "rate_limited": "⚠️"
                }.get(status, "❓")
                rprint(f"  {emoji} {status}: {count}")
    
    if detailed and state.prompts:
        rprint("\n[bold]Prompt Details:[/bold]")
        prompt_table = Table()
        prompt_table.add_column("ID", style="cyan")
        prompt_table.add_column("Status", style="yellow")
        prompt_table.add_column("Priority", style="red")
        prompt_table.add_column("Content", style="green")
        
        for prompt in sorted(state.prompts, key=lambda p: p.priority):
            status_emoji = {
                PromptStatus.QUEUED: "⏳",
                PromptStatus.EXECUTING: "▶️",
                PromptStatus.COMPLETED: "✅", 
                PromptStatus.FAILED: "❌",
                PromptStatus.CANCELLED: "🚫",
                PromptStatus.RATE_LIMITED: "⚠️"
            }.get(prompt.status, "❓")
            
            content_preview = prompt.content[:60] + "..." if len(prompt.content) > 60 else prompt.content
            prompt_table.add_row(
                prompt.id,
                f"{status_emoji} {prompt.status.value}",
                str(prompt.priority),
                content_preview
            )
        
        console.print(prompt_table)


@app.command()
def cancel(
    prompt_id: str = typer.Argument(..., help="Prompt ID to cancel"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Cancel a prompt."""
    manager = get_manager(storage_dir)
    success = manager.remove_prompt(prompt_id)
    if success:
        rprint(f"[green]✓[/green] Cancelled prompt [bold]{prompt_id}[/bold]")
    else:
        rprint(f"[red]✗[/red] Failed to cancel prompt [bold]{prompt_id}[/bold]")
        raise typer.Exit(1)


@app.command()
def list_prompts(
    status_filter: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """List prompts."""
    manager = get_manager(storage_dir)
    state = manager.get_status()
    prompts = state.prompts

    if status_filter:
        try:
            status_enum = PromptStatus(status_filter)
            prompts = [p for p in prompts if p.status == status_enum]
        except ValueError:
            rprint(f"[red]Invalid status:[/red] {status_filter}")
            raise typer.Exit(1)

    if not prompts:
        rprint("[yellow]No prompts found[/yellow]")
        return

    if json_output:
        prompt_data = []
        for prompt in prompts:
            prompt_data.append({
                "id": prompt.id,
                "content": prompt.content,
                "status": prompt.status.value,
                "priority": prompt.priority,
                "working_directory": prompt.working_directory,
                "created_at": prompt.created_at.isoformat(),
                "retry_count": prompt.retry_count,
                "max_retries": prompt.max_retries,
            })
        print(json.dumps(prompt_data, indent=2))
    else:
        table = Table(title=f"Found {len(prompts)} prompts")
        table.add_column("ID", style="cyan") 
        table.add_column("Status", style="yellow")
        table.add_column("Priority", style="red")
        table.add_column("Content", style="green")
        table.add_column("Created", style="blue")
        
        for prompt in sorted(prompts, key=lambda p: p.priority):
            status_emoji = {
                PromptStatus.QUEUED: "⏳",
                PromptStatus.EXECUTING: "▶️",
                PromptStatus.COMPLETED: "✅",
                PromptStatus.FAILED: "❌", 
                PromptStatus.CANCELLED: "🚫",
                PromptStatus.RATE_LIMITED: "⚠️"
            }.get(prompt.status, "❓")
            
            content_preview = prompt.content[:50] + "..." if len(prompt.content) > 50 else prompt.content
            table.add_row(
                prompt.id,
                f"{status_emoji} {prompt.status.value}",
                str(prompt.priority),
                content_preview,
                prompt.created_at.strftime('%m-%d %H:%M')
            )
        
        console.print(table)


@app.command()
def test(
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
    claude_command: str = typer.Option("claude", help="Claude CLI command"),
):
    """Test Claude Code connection."""
    manager = get_manager(storage_dir, claude_command)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task(description="Testing Claude Code connection...", total=None)
        is_working, message = manager.claude_interface.test_connection()
    
    if is_working:
        rprint(f"[green]✓[/green] {message}")
    else:
        rprint(f"[red]✗[/red] {message}")
        raise typer.Exit(1)


# Alias management commands
alias_app = typer.Typer(help="Manage prompt aliases")
app.add_typer(alias_app, name="alias")


@alias_app.command("create")
def create_alias(
    name: str = typer.Argument(..., help="Alias name"),
    prompt: str = typer.Argument(..., help="Prompt content"),
    description: str = typer.Option("", help="Alias description"),
    working_dir: str = typer.Option(".", help="Default working directory"),
    context_files: List[str] = typer.Option([], help="Default context files"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Create a new prompt alias."""
    alias_manager = get_alias_manager(storage_dir)
    success = alias_manager.create_alias(name, prompt, description, working_dir, context_files)
    
    if success:
        rprint(f"[green]✓[/green] Created alias [bold]{name}[/bold]")
    else:
        rprint(f"[red]✗[/red] Failed to create alias (may already exist)")
        raise typer.Exit(1)


@alias_app.command("list")
def list_aliases(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """List all aliases."""
    alias_manager = get_alias_manager(storage_dir)
    aliases = alias_manager.list_aliases()
    
    if not aliases:
        rprint("[yellow]No aliases found[/yellow]")
        return
    
    if json_output:
        print(json.dumps(aliases, indent=2, default=str))
    else:
        table = Table(title="Prompt Aliases")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Content Preview", style="yellow")
        table.add_column("Working Dir", style="blue")
        
        for alias in aliases:
            content_preview = alias['content'][:50] + "..." if len(alias['content']) > 50 else alias['content']
            table.add_row(
                alias['name'],
                alias.get('description', ''),
                content_preview,
                alias.get('working_directory', '.')
            )
        
        console.print(table)


@alias_app.command("delete") 
def delete_alias(
    name: str = typer.Argument(..., help="Alias name to delete"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Delete an alias."""
    alias_manager = get_alias_manager(storage_dir)
    success = alias_manager.delete_alias(name)
    
    if success:
        rprint(f"[green]✓[/green] Deleted alias [bold]{name}[/bold]")
    else:
        rprint(f"[red]✗[/red] Alias [bold]{name}[/bold] not found")
        raise typer.Exit(1)


@alias_app.command("show")
def show_alias(
    name: str = typer.Argument(..., help="Alias name to show"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Show alias details."""
    alias_manager = get_alias_manager(storage_dir)
    alias = alias_manager.get_alias(name)
    
    if not alias:
        rprint(f"[red]✗[/red] Alias [bold]{name}[/bold] not found")
        raise typer.Exit(1)
    
    rprint(f"[bold]Alias:[/bold] {alias['name']}")
    if alias.get('description'):
        rprint(f"[bold]Description:[/bold] {alias['description']}")
    rprint(f"[bold]Working Directory:[/bold] {alias.get('working_directory', '.')}")
    if alias.get('context_files'):
        rprint(f"[bold]Context Files:[/bold] {', '.join(alias['context_files'])}")
    rprint(f"[bold]Content:[/bold]\n{alias['content']}")


# History commands
history_app = typer.Typer(help="Manage prompt history")
app.add_typer(history_app, name="history")


@history_app.command("list")
def list_history(
    limit: int = typer.Option(20, help="Number of entries to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """List prompt history."""
    history_manager = get_history_manager(storage_dir)
    history = history_manager.get_history(limit)
    
    if not history:
        rprint("[yellow]No history found[/yellow]")
        return
    
    if json_output:
        print(json.dumps(history, indent=2, default=str))
    else:
        table = Table(title=f"Recent Prompts (last {len(history)})")
        table.add_column("Date", style="blue")
        table.add_column("Content Preview", style="green") 
        table.add_column("Working Dir", style="yellow")
        
        for entry in history:
            content_preview = entry['content'][:60] + "..." if len(entry['content']) > 60 else entry['content']
            table.add_row(
                entry['timestamp'].strftime('%m-%d %H:%M'),
                content_preview,
                entry['working_directory']
            )
        
        console.print(table)


@history_app.command("search")
def search_history(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, help="Number of results"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Search prompt history."""
    history_manager = get_history_manager(storage_dir)
    results = history_manager.search_history(query, limit)
    
    if not results:
        rprint(f"[yellow]No results found for:[/yellow] {query}")
        return
    
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Date", style="blue")
    table.add_column("Content Preview", style="green")
    table.add_column("Working Dir", style="yellow")
    
    for entry in results:
        content_preview = entry['content'][:60] + "..." if len(entry['content']) > 60 else entry['content']
        table.add_row(
            entry['timestamp'].strftime('%m-%d %H:%M'),
            content_preview, 
            entry['working_directory']
        )
    
    console.print(table)


@history_app.command("clear")
def clear_history(
    confirm: bool = typer.Option(False, "--yes", help="Skip confirmation"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Clear prompt history."""
    if not confirm:
        confirm = typer.confirm("Are you sure you want to clear all history?")
        if not confirm:
            rprint("[yellow]Cancelled[/yellow]")
            return
    
    history_manager = get_history_manager(storage_dir)
    success = history_manager.clear_history()
    
    if success:
        rprint("[green]✓[/green] History cleared")
    else:
        rprint("[red]✗[/red] Failed to clear history")
        raise typer.Exit(1)


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    storage_dir: str = typer.Option("~/.claude-queue", help="Storage directory"),
):
    """Start the web interface."""
    try:
        import uvicorn
        from .web.main import create_app
        
        app_instance = create_app(storage_dir)
        rprint(f"[green]🚀 Starting web interface at http://{host}:{port}[/green]")
        uvicorn.run(app_instance, host=host, port=port, log_level="info")
    except ImportError:
        rprint("[red]Web dependencies not installed. Run: uv add 'fastapi[all]'[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()