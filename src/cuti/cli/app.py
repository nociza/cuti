"""
Main CLI application using Typer.
"""

from typing import Optional

import typer
from rich.console import Console

from ..services.queue_service import QueueManager
from ..services.aliases import PromptAliasManager
from ..services.history import PromptHistoryManager
from .commands.queue import queue_app
from .commands.alias import alias_app
from .commands.agent import agent_app

app = typer.Typer(
    name="cuti",
    help="Production-ready AI command queue and orchestration system",
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


# Add sub-applications
app.add_typer(queue_app, name="queue", help="Queue management commands")
app.add_typer(alias_app, name="alias", help="Alias management commands")  
app.add_typer(agent_app, name="agent", help="Agent system commands")

# Add top-level commands for convenience
from .commands.queue import start_queue, add_prompt, show_status

app.command("start")(start_queue)
app.command("add")(add_prompt)
app.command("status")(show_status)


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    storage_dir: str = typer.Option("~/.claude-queue", "--storage-dir", help="Storage directory"),
    working_directory: Optional[str] = typer.Option(None, "--working-dir", "-w", help="Working directory"),
):
    """Start the web interface."""
    import sys
    import os
    from pathlib import Path
    
    # Set environment variables for the web app
    if working_directory:
        os.environ["CUTI_WORKING_DIR"] = str(Path(working_directory).resolve())
    
    # Import and run the web app
    from ..web.app import main as web_main
    
    # Override sys.argv for the web main function
    sys.argv = [
        "cuti-web",
        "--host", host,
        "--port", str(port),
        "--storage-dir", storage_dir,
    ]
    
    if working_directory:
        sys.argv.extend(["--working-directory", working_directory])
    
    try:
        web_main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Web interface stopped[/yellow]")
        sys.exit(0)