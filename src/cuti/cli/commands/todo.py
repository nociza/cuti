"""
CLI commands for todo list management.
"""

from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from ...services.todo_service import TodoService
from ...core.todo_models import TodoItem, TodoList, TodoStatus, TodoPriority

app = typer.Typer(help="Todo list management commands")
console = Console()


def get_service(storage_dir: str = ".cuti") -> TodoService:
    """Get todo service instance."""
    return TodoService(storage_dir)


@app.command("add")
def add_todo(
    content: str = typer.Argument(..., help="Todo content"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority: low, medium, high, critical"),
    list_name: Optional[str] = typer.Option(None, "--list", "-l", help="Add to specific list"),
    storage_dir: str = typer.Option(".cuti", "--storage-dir", help="Storage directory"),
):
    """Add a new todo item."""
    service = get_service(storage_dir)
    
    try:
        priority_enum = TodoPriority[priority.upper()]
    except KeyError:
        console.print(f"[red]Invalid priority: {priority}[/red]")
        raise typer.Exit(1)
    
    todo = TodoItem(
        content=content,
        priority=priority_enum,
        created_by="user"
    )
    
    # Get the target list
    if list_name:
        # Find list by name
        # For now, we'll add to master list
        target_list = service.get_master_list()
    else:
        # Add to master list by default
        target_list = service.get_master_list()
    
    if not target_list:
        console.print("[red]No todo list found[/red]")
        raise typer.Exit(1)
    
    target_list.add_todo(todo)
    service.save_list(target_list)
    
    console.print(f"[green]✓[/green] Added todo: {todo.id}")
    console.print(f"  Content: {content}")
    console.print(f"  Priority: {priority}")


@app.command("list")
def list_todos(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    list_name: Optional[str] = typer.Option(None, "--list", "-l", help="Show specific list"),
    all_lists: bool = typer.Option(False, "--all", "-a", help="Show all lists"),
    storage_dir: str = typer.Option(".cuti", "--storage-dir", help="Storage directory"),
):
    """List todo items."""
    service = get_service(storage_dir)
    
    if all_lists:
        # Show all sessions and lists
        session = service.get_active_session()
        if session:
            console.print(Panel(f"[bold]Active Session: {session.name}[/bold]", box=box.ROUNDED))
            
            # Show master list
            if session.master_list:
                _display_list(session.master_list, is_master=True)
            
            # Show sub-lists
            for sub_list in session.sub_lists:
                _display_list(sub_list, is_master=False)
        else:
            # Just show master list
            master_list = service.get_master_list()
            if master_list:
                _display_list(master_list, is_master=True)
    else:
        # Show specific list or master
        if list_name:
            # TODO: Implement finding list by name
            target_list = service.get_master_list()
        else:
            target_list = service.get_master_list()
        
        if target_list:
            # Filter by status if specified
            if status:
                try:
                    status_enum = TodoStatus(status.lower())
                    todos = [t for t in target_list.todos if t.status == status_enum]
                except ValueError:
                    console.print(f"[red]Invalid status: {status}[/red]")
                    raise typer.Exit(1)
            else:
                todos = target_list.todos
            
            _display_todos(todos, target_list.name)
        else:
            console.print("[yellow]No todos found[/yellow]")


def _display_list(todo_list: TodoList, is_master: bool = False):
    """Display a todo list."""
    title = f"{'[bold cyan]Master List:[/bold cyan]' if is_master else '[bold]List:[/bold]'} {todo_list.name}"
    
    progress = todo_list.get_progress()
    subtitle = f"Total: {progress['total']} | Completed: {progress['completed']} ({progress['completion_percentage']}%)"
    
    console.print(Panel(title, subtitle=subtitle, box=box.ROUNDED))
    
    if todo_list.todos:
        _display_todos(todo_list.todos, None)
    else:
        console.print("[dim]No todos in this list[/dim]")
    console.print()


def _display_todos(todos, list_name: Optional[str]):
    """Display todos in a table."""
    if not todos:
        console.print("[yellow]No todos to display[/yellow]")
        return
    
    table = Table(title=list_name if list_name else None, box=box.SIMPLE)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Priority", style="yellow")
    table.add_column("Content", style="white")
    table.add_column("Created", style="dim")
    
    for todo in todos:
        status_icon = {
            TodoStatus.PENDING: "⏳",
            TodoStatus.IN_PROGRESS: "🔄",
            TodoStatus.COMPLETED: "✅",
            TodoStatus.BLOCKED: "🚫",
            TodoStatus.CANCELLED: "❌"
        }.get(todo.status, "❓")
        
        priority_color = {
            TodoPriority.LOW: "dim",
            TodoPriority.MEDIUM: "yellow",
            TodoPriority.HIGH: "red",
            TodoPriority.CRITICAL: "bold red"
        }.get(todo.priority, "white")
        
        table.add_row(
            todo.id,
            f"{status_icon} {todo.status.value}",
            f"[{priority_color}]{todo.priority.name}[/{priority_color}]",
            todo.content[:50] + "..." if len(todo.content) > 50 else todo.content,
            todo.created_at.strftime("%Y-%m-%d %H:%M") if todo.created_at else ""
        )
    
    console.print(table)


@app.command("update")
def update_todo(
    todo_id: str = typer.Argument(..., help="Todo ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New priority"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="New content"),
    storage_dir: str = typer.Option(".cuti", "--storage-dir", help="Storage directory"),
):
    """Update a todo item."""
    service = get_service(storage_dir)
    
    updates = {}
    
    if status:
        try:
            updates['status'] = TodoStatus(status.lower())
        except ValueError:
            console.print(f"[red]Invalid status: {status}[/red]")
            raise typer.Exit(1)
    
    if priority:
        try:
            updates['priority'] = TodoPriority[priority.upper()]
        except KeyError:
            console.print(f"[red]Invalid priority: {priority}[/red]")
            raise typer.Exit(1)
    
    if content:
        updates['content'] = content
    
    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(1)
    
    if service.update_todo(todo_id, updates):
        console.print(f"[green]✓[/green] Updated todo: {todo_id}")
        
        # Show updated todo
        todo = service.get_todo(todo_id)
        if todo:
            console.print(f"  Status: {todo.status.value}")
            console.print(f"  Priority: {todo.priority.name}")
            console.print(f"  Content: {todo.content}")
    else:
        console.print(f"[red]Failed to update todo: {todo_id}[/red]")
        raise typer.Exit(1)


@app.command("complete")
def complete_todo(
    todo_id: str = typer.Argument(..., help="Todo ID to mark as completed"),
    storage_dir: str = typer.Option(".cuti", "--storage-dir", help="Storage directory"),
):
    """Mark a todo as completed."""
    service = get_service(storage_dir)
    
    if service.update_todo(todo_id, {'status': TodoStatus.COMPLETED}):
        console.print(f"[green]✓[/green] Marked todo {todo_id} as completed")
    else:
        console.print(f"[red]Failed to complete todo: {todo_id}[/red]")
        raise typer.Exit(1)


@app.command("progress")
def show_progress(
    session: bool = typer.Option(False, "--session", "-s", help="Show session progress"),
    storage_dir: str = typer.Option(".cuti", "--storage-dir", help="Storage directory"),
):
    """Show todo progress statistics."""
    service = get_service(storage_dir)
    
    if session:
        active_session = service.get_active_session()
        if active_session:
            progress = active_session.get_overall_progress()
            
            console.print(Panel(f"[bold]Session: {active_session.name}[/bold]", box=box.DOUBLE))
            
            # Overall stats
            table = Table(box=box.SIMPLE)
            table.add_column("Status", style="cyan")
            table.add_column("Count", style="yellow")
            table.add_column("Percentage", style="green")
            
            total = progress['total']
            for status in ['pending', 'in_progress', 'completed', 'blocked', 'cancelled']:
                count = progress[status]
                pct = (count / total * 100) if total > 0 else 0
                table.add_row(
                    status.replace('_', ' ').title(),
                    str(count),
                    f"{pct:.1f}%"
                )
            
            console.print(table)
            console.print(f"\n[bold]Overall Completion: {progress['completion_percentage']}%[/bold]")
        else:
            console.print("[yellow]No active session[/yellow]")
    else:
        master_list = service.get_master_list()
        if master_list:
            progress = master_list.get_progress()
            
            console.print(Panel("[bold]Master Todo List Progress[/bold]", box=box.DOUBLE))
            
            # Progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress_bar:
                task = progress_bar.add_task(
                    f"[cyan]Completion: {progress['completion_percentage']}%",
                    total=progress['total']
                )
                progress_bar.update(task, completed=progress['completed'])
            
            # Stats table
            table = Table(box=box.SIMPLE)
            table.add_column("Status", style="cyan")
            table.add_column("Count", style="yellow")
            
            for status in ['pending', 'in_progress', 'completed', 'blocked', 'cancelled']:
                if progress[status] > 0:
                    table.add_row(
                        status.replace('_', ' ').title(),
                        str(progress[status])
                    )
            
            console.print(table)
        else:
            console.print("[yellow]No todos found[/yellow]")


@app.command("session")
def manage_session(
    new: Optional[str] = typer.Option(None, "--new", "-n", help="Create new session with name"),
    show: bool = typer.Option(False, "--show", "-s", help="Show active session"),
    storage_dir: str = typer.Option(".cuti", "--storage-dir", help="Storage directory"),
):
    """Manage todo sessions."""
    service = get_service(storage_dir)
    
    if new:
        session = service.create_session(new)
        console.print(f"[green]✓[/green] Created new session: {session.name}")
        console.print(f"  ID: {session.id}")
        console.print(f"  Master list attached: {session.master_list is not None}")
    elif show:
        session = service.get_active_session()
        if session:
            console.print(Panel(f"[bold]Active Session: {session.name}[/bold]", box=box.DOUBLE))
            console.print(f"  ID: {session.id}")
            console.print(f"  Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}")
            console.print(f"  Sub-lists: {len(session.sub_lists)}")
            
            progress = session.get_overall_progress()
            console.print(f"  Total todos: {progress['total']}")
            console.print(f"  Completion: {progress['completion_percentage']}%")
        else:
            console.print("[yellow]No active session[/yellow]")
    else:
        console.print("[yellow]Specify --new <name> to create a session or --show to view[/yellow]")