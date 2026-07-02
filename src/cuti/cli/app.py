"""
Main CLI application using Typer.
"""

from importlib.metadata import version
from pathlib import Path

import typer
from rich.console import Console

from ..services.aliases import PromptAliasManager
from ..services.history import PromptHistoryManager
from ..services.queue_service import QueueManager
from .commands.agent import agent_app
from .commands.alias import alias_app
from .commands.queue import add_prompt, queue_app, show_status, start_queue
from .commands.todo import app as todo_app

# Version information - dynamically imported from package
__version__ = version("cuti")

devcontainer_app: typer.Typer | None = None
try:
    from .commands.devcontainer import app as _devcontainer_app
except ImportError:
    pass
else:
    devcontainer_app = _devcontainer_app

container_app: typer.Typer | None = None
try:
    from .commands.container import app as _container_app
except ImportError:
    pass
else:
    container_app = _container_app

tools_app: typer.Typer | None = None
try:
    from .commands.tools import app as _tools_app
except ImportError:
    pass
else:
    tools_app = _tools_app

settings_app: typer.Typer | None = None
try:
    from .commands.settings import app as _settings_app
except ImportError:
    pass
else:
    settings_app = _settings_app

favorites_app: typer.Typer | None = None
try:
    from .commands.favorites import app as _favorites_app
except ImportError:
    pass
else:
    favorites_app = _favorites_app

sync_app: typer.Typer | None = None
try:
    from .commands.sync import app as _sync_app
except ImportError:
    pass
else:
    sync_app = _sync_app

claude_app: typer.Typer | None = None
try:
    from .commands.claude_account import app as _claude_app
except ImportError:
    pass
else:
    claude_app = _claude_app

providers_app: typer.Typer | None = None
try:
    from .commands.providers import app as _providers_app
except ImportError:
    pass
else:
    providers_app = _providers_app

openclaw_app: typer.Typer | None = None
try:
    from .commands.openclaw import app as _openclaw_app
except ImportError:
    pass
else:
    openclaw_app = _openclaw_app

history_app: typer.Typer | None = None
try:
    from .commands.history import history_app as _history_app
except ImportError:
    pass
else:
    history_app = _history_app

app = typer.Typer(
    name="cuti",
    help="Provider-aware AI development runtime and read-only ops console",
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"cuti version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """
    cuti - Provider-aware AI development runtime and read-only ops console

    Use --help with any command for more information.
    """
    pass


# Global state
_manager: QueueManager | None = None
_alias_manager: PromptAliasManager | None = None
_history_manager: PromptHistoryManager | None = None


def get_manager(
    storage_dir: str = "~/.cuti",
    claude_command: str = "claude",
    check_interval: int = 30,
    timeout: int = 3600,
) -> QueueManager:
    """Get or create legacy queue manager instance."""
    global _manager
    if _manager is None:
        _manager = QueueManager(
            storage_dir=storage_dir,
            claude_command=claude_command,
            check_interval=check_interval,
            timeout=timeout,
        )
    return _manager


def get_alias_manager(storage_dir: str = "~/.cuti") -> PromptAliasManager:
    """Get or create alias manager instance."""
    global _alias_manager
    if _alias_manager is None:
        _alias_manager = PromptAliasManager(storage_dir)
    return _alias_manager


def get_history_manager(storage_dir: str = "~/.cuti") -> PromptHistoryManager:
    """Get or create history manager instance."""
    global _history_manager
    if _history_manager is None:
        _history_manager = PromptHistoryManager(storage_dir)
    return _history_manager


# Version command
@app.command(name="version")
def show_version() -> None:
    """Show version information."""
    console.print(f"cuti version {__version__}")


# Add sub-applications
app.add_typer(queue_app, name="queue", help="Legacy Claude queue commands")
app.add_typer(alias_app, name="alias", help="Alias management commands")
app.add_typer(agent_app, name="agent", help="Experimental local agent library commands")
app.add_typer(todo_app, name="todo", help="Legacy todo helper commands")
if devcontainer_app:
    app.add_typer(devcontainer_app, name="devcontainer", help="DevContainer management")
if container_app:
    app.add_typer(
        container_app, name="containers", help="Container management commands"
    )
if tools_app:
    app.add_typer(tools_app, name="tools", help="CLI tools management")
if settings_app:
    app.add_typer(settings_app, name="settings", help="Global settings management")
if favorites_app:
    app.add_typer(favorites_app, name="favorites", help="Favorite prompts management")

# Add sync commands if available
if sync_app:
    app.add_typer(sync_app, name="sync", help="Sync usage data")

# Add claude account commands if available
if claude_app:
    app.add_typer(claude_app, name="claude", help="Manage Claude accounts and API keys")
if providers_app:
    app.add_typer(
        providers_app,
        name="providers",
        help="Manage provider selection, setup, status, and updates",
    )
if openclaw_app:
    app.add_typer(
        openclaw_app, name="openclaw", help="Run OpenClaw inside the Qt container"
    )
if history_app:
    app.add_typer(
        history_app,
        name="history",
        help="Browse Claude chat history and resume sessions",
    )

app.command("start")(start_queue)
app.command("add")(add_prompt)
app.command("status")(show_status)


@app.command()
def container(
    init: bool = typer.Option(False, "--init", help="Initialize devcontainer"),
    rebuild: bool = typer.Option(
        False, "--rebuild", help="Force rebuild the container image"
    ),
    command: str | None = typer.Argument(
        None, help="Command to run in container (or 'start' for interactive shell)"
    ),
    skip_colima: bool = typer.Option(
        False, "--skip-colima", help="Skip Colima auto-setup"
    ),
    status: bool = typer.Option(
        False, "--status", help="Show status of all containers"
    ),
    openclaw_mode: bool = typer.Option(
        False,
        "--openclaw",
        "--claw",
        help="Start in OpenClaw mode instead of the default Claude Code mode",
    ),
) -> None:
    """Run cuti in a dev container with automatic setup."""
    from ..services.devcontainer import DevContainerService, is_running_in_container

    # Handle status flag
    if status:
        from .commands.container import status as show_container_status

        show_container_status(verbose=False, json_output=False)
        return

    # Handle 'start' as a special case - treat it as no command (interactive mode)
    if command == "start":
        command = None

    if is_running_in_container():
        console.print("[yellow]Already running in a container![/yellow]")
        if command:
            import subprocess

            subprocess.run(command, shell=True)
        return

    container_mode = (
        DevContainerService.CONTAINER_MODE_OPENCLAW
        if openclaw_mode
        else DevContainerService.CONTAINER_MODE_CLAUDE
    )
    service = DevContainerService(container_mode=container_mode)

    # Ensure dependencies are installed on macOS
    console.print("[cyan]Checking container dependencies...[/cyan]")
    if not service.ensure_dependencies():
        console.print("[red]Container dependencies not available[/red]")
        raise typer.Exit(1)

    # Re-check availability after potential installation
    service.colima_available = service._check_colima()
    service.docker_available = service._check_docker()

    # The container command should work without creating any local devcontainer files
    # Skip devcontainer initialization entirely - use embedded minimal container
    if init:
        console.print("[cyan]Initializing dev container configuration...[/cyan]")
        if not service.generate_devcontainer():
            console.print("[red]Failed to initialize dev container[/red]")
            raise typer.Exit(1)

    # Check Docker availability
    if not service.docker_available:
        if service.colima_available and not skip_colima:
            console.print("[cyan]Docker not running, will start Colima...[/cyan]")
            console.print("[dim]This may take 1-2 minutes on first start[/dim]")
            if not service.setup_colima():
                console.print("[red]Failed to start Colima automatically[/red]")
                console.print("\n[yellow]Please try one of these options:[/yellow]")
                console.print("1. Start Colima manually: [cyan]colima start[/cyan]")
                console.print("2. Start Docker Desktop")
                console.print("3. Run with --skip-colima flag if Docker is running")
                raise typer.Exit(1)
        else:
            console.print("[red]Docker is not available[/red]")
            if not service.colima_available:
                console.print("Install Colima: [cyan]brew install colima[/cyan]")
            console.print("Or start Docker Desktop")
            raise typer.Exit(1)

    # Run in container
    mode_label = "OpenClaw" if openclaw_mode else "Claude Code"
    console.print(f"[green]Starting dev container in {mode_label} mode...[/green]")
    # If no command provided, just start an interactive shell
    exit_code = service.run_in_container(command, rebuild=rebuild)

    if exit_code != 0:
        console.print(f"[red]Container exited with code {exit_code}[/red]")
        raise typer.Exit(exit_code)


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    storage_dir: str = typer.Option(
        "~/.cuti", "--storage-dir", help="Storage directory"
    ),
    working_directory: str | None = typer.Option(
        None, "--working-dir", "-w", help="Working directory"
    ),
) -> None:
    """Start the read-only ops console."""
    import os
    import sys

    # Set environment variables for the web app
    if working_directory:
        os.environ["CUTI_WORKING_DIR"] = str(Path(working_directory).resolve())

    # Import and run the web app
    from ..web.app import main as web_main

    # Override sys.argv for the web main function
    sys.argv = [
        "cuti-web",
        "--host",
        host,
        "--port",
        str(port),
        "--storage-dir",
        storage_dir,
    ]

    if working_directory:
        sys.argv.extend(["--working-directory", working_directory])

    try:
        web_main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Web interface stopped[/yellow]")
        sys.exit(0)
