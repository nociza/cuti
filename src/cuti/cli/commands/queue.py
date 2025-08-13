"""
Queue-related CLI commands.
"""

import json
import os
from datetime import datetime
from typing import Optional, List

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...core.models import QueuedPrompt
from ...services.queue_service import QueueManager
from ...services.aliases import PromptAliasManager
from ...services.history import PromptHistoryManager
from ...services.todo_service import TodoService
from ...core.todo_models import TodoStatus

queue_app = typer.Typer(help="Queue management commands")
console = Console()


def get_managers(storage_dir: str):
    """Get manager instances."""
    manager = QueueManager(storage_dir)
    alias_manager = PromptAliasManager(storage_dir)
    history_manager = PromptHistoryManager(storage_dir)
    return manager, alias_manager, history_manager


@queue_app.command("start")
def start_queue(
    storage_dir: str = typer.Option(".cuti", help="Storage directory"),
    claude_command: str = typer.Option("claude", help="Claude CLI command"),
    check_interval: int = typer.Option(30, help="Check interval in seconds"),
    timeout: int = typer.Option(3600, help="Command timeout in seconds"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """Start the queue processor."""
    manager = QueueManager(storage_dir, claude_command, check_interval, timeout)
    
    def status_callback(state):
        if verbose:
            stats = state.get_stats()
            rprint(f"[blue]Queue status:[/blue] {stats['status_counts']}")

    try:
        manager.start(callback=status_callback if verbose else None)
    except KeyboardInterrupt:
        rprint("\n[yellow]Queue processor stopped by user[/yellow]")


@queue_app.command("add")
def add_prompt(
    prompt: str = typer.Argument(..., help="The prompt text or alias name"),
    priority: int = typer.Option(0, "-p", "--priority", help="Priority (lower = higher)"),
    working_dir: Optional[str] = typer.Option(None, "-d", "--working-dir", help="Working directory (default: current)"),
    context_files: List[str] = typer.Option([], "-f", "--context-files", help="Context files"),
    max_retries: int = typer.Option(3, "-r", "--max-retries", help="Maximum retry attempts"),
    estimated_tokens: Optional[int] = typer.Option(None, "-t", "--estimated-tokens", help="Estimated tokens"),
    storage_dir: str = typer.Option(".cuti", help="Storage directory"),
):
    """Add a prompt to the queue (supports aliases)."""
    # Use current directory if not specified
    if working_dir is None:
        working_dir = os.getcwd()
    
    manager, alias_manager, history_manager = get_managers(storage_dir)
    
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


@queue_app.command("template")
def create_template(
    filename: str = typer.Argument(..., help="Template filename"),
    priority: int = typer.Option(0, "-p", "--priority", help="Default priority"),
    storage_dir: str = typer.Option(".cuti", help="Storage directory"),
):
    """Create a prompt template file."""
    manager, _, _ = get_managers(storage_dir)
    file_path = manager.create_prompt_template(filename, priority)
    rprint(f"[green]✓[/green] Created template: [bold]{file_path}[/bold]")
    rprint("Edit the file and it will be automatically picked up")


@queue_app.command("status")
def show_status(
    detailed: bool = typer.Option(False, "-d", "--detailed", help="Show detailed info"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    storage_dir: str = typer.Option(".cuti", help="Storage directory"),
):
    """Show queue status."""
    manager, _, _ = get_managers(storage_dir)
    state = manager.get_status()
    stats = state.get_stats()

    if json_output:
        print(json.dumps(stats, indent=2))
        return

    # Create a nice table
    table = Table(title="cuti Status")
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
    
    # Show detailed prompt list if requested
    if detailed:
        rprint(f"\n[bold]Active prompts:[/bold]")
        for prompt in state.prompts:
            status_emoji = {
                "queued": "⏳",
                "executing": "▶️",
                "completed": "✅", 
                "failed": "❌",
                "cancelled": "🚫",
                "rate_limited": "⚠️"
            }.get(prompt.status.value, "❓")
            
            rprint(f"  {status_emoji} [bold]{prompt.id}[/bold] ({prompt.status.value})")
            rprint(f"    Priority: {prompt.priority} | Retries: {prompt.retry_count}/{prompt.max_retries}")
            rprint(f"    Content: {prompt.content[:100]}...")
            if prompt.working_directory != ".":
                rprint(f"    Dir: {prompt.working_directory}")
            rprint()


@queue_app.command("remove")
def remove_prompt(
    prompt_id: str = typer.Argument(..., help="Prompt ID to remove"),
    storage_dir: str = typer.Option(".cuti", help="Storage directory"),
):
    """Remove/cancel a prompt from the queue."""
    manager, _, _ = get_managers(storage_dir)
    
    success = manager.remove_prompt(prompt_id)
    if success:
        rprint(f"[green]✓[/green] Cancelled prompt [bold]{prompt_id}[/bold]")
    else:
        rprint(f"[red]✗[/red] Failed to cancel prompt {prompt_id}")
        raise typer.Exit(1)


@queue_app.command("list")
def list_prompts(
    status_filter: Optional[str] = typer.Option(None, "-s", "--status", help="Filter by status"),
    storage_dir: str = typer.Option(".cuti", help="Storage directory"),
):
    """List all prompts in the queue."""
    manager, _, _ = get_managers(storage_dir)
    state = manager.get_status()
    
    # Filter prompts if status specified
    if status_filter:
        filtered_prompts = [p for p in state.prompts if p.status.value == status_filter]
    else:
        filtered_prompts = state.prompts
    
    if not filtered_prompts:
        filter_msg = f" with status '{status_filter}'" if status_filter else ""
        rprint(f"[yellow]No prompts found{filter_msg}[/yellow]")
        return
    
    table = Table(title="Prompt Queue")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Priority", style="blue")
    table.add_column("Content", style="white", max_width=50)
    table.add_column("Created", style="green")
    
    for prompt in sorted(filtered_prompts, key=lambda p: p.priority):
        status_emoji = {
            "queued": "⏳",
            "executing": "▶️",
            "completed": "✅",
            "failed": "❌", 
            "cancelled": "🚫",
            "rate_limited": "⚠️"
        }.get(prompt.status.value, "❓")
        
        content = prompt.content[:47] + "..." if len(prompt.content) > 50 else prompt.content
        created = prompt.created_at.strftime('%m/%d %H:%M')
        
        table.add_row(
            prompt.id,
            f"{status_emoji} {prompt.status.value}",
            str(prompt.priority),
            content,
            created
        )
    
    console.print(table)


@queue_app.command("from-todo")
def add_from_todo(
    todo_id: Optional[str] = typer.Argument(None, help="Todo ID to convert to prompt"),
    all_pending: bool = typer.Option(False, "--all-pending", help="Add all pending todos"),
    priority: int = typer.Option(0, "-p", "--priority", help="Priority for prompts"),
    storage_dir: str = typer.Option(".cuti", help="Storage directory"),  # Changed default
):
    """Create queue prompts from todo items."""
    manager, _, _ = get_managers(storage_dir)
    todo_service = TodoService(storage_dir)
    
    todos_to_process = []
    
    if all_pending:
        # Get all pending todos
        todos_to_process = todo_service.get_todos_by_status(TodoStatus.PENDING)
        if not todos_to_process:
            rprint("[yellow]No pending todos found[/yellow]")
            return
    elif todo_id:
        # Get specific todo
        todo = todo_service.get_todo(todo_id)
        if not todo:
            rprint(f"[red]Todo {todo_id} not found[/red]")
            raise typer.Exit(1)
        todos_to_process = [todo]
    else:
        rprint("[yellow]Specify a todo ID or use --all-pending[/yellow]")
        raise typer.Exit(1)
    
    # Create prompts from todos
    added_count = 0
    for todo in todos_to_process:
        # Create a prompt that asks Claude to work on this todo
        prompt_content = f"Work on this task: {todo.content}"
        
        # Add context if todo has metadata
        if todo.metadata.get("context"):
            prompt_content += f"\n\nContext: {todo.metadata['context']}"
        
        # QueuedPrompt doesn't have a metadata field by default, just add the info to content
        queued_prompt = QueuedPrompt(
            content=prompt_content,
            priority=priority
        )
        
        if manager.add_prompt(queued_prompt):
            # Mark todo as in progress
            todo_service.update_todo(todo.id, {'status': TodoStatus.IN_PROGRESS})
            added_count += 1
            rprint(f"[green]✓[/green] Added prompt for todo: {todo.id[:8]}... {todo.content[:50]}")
        else:
            rprint(f"[red]✗[/red] Failed to add prompt for todo: {todo.id}")
    
    if added_count > 0:
        rprint(f"\n[green]Added {added_count} prompt(s) to queue from todos[/green]")