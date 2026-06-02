"""
Main CLI application using Typer.
"""

from importlib.metadata import version as _pkg_version

import typer
from rich.console import Console

try:
    __version__ = _pkg_version("cuti")
except Exception:  # pragma: no cover - metadata always present once installed
    __version__ = "0.0.0"

# First-party command groups are imported unconditionally so that a genuine
# breakage surfaces loudly instead of silently dropping a command.
from .commands.claude_account import app as claude_app
from .commands.container import app as container_app
from .commands.devcontainer import app as devcontainer_app
from .commands.favorites import favorites as favorites_app
from .commands.history import history_app
from .commands.openclaw import app as openclaw_app
from .commands.providers import app as providers_app
from .commands.settings import settings as settings_app
from .commands.sync import app as sync_app
from .commands.tools import app as tools_app

app = typer.Typer(
    name="cuti",
    help="An instant, containerized Claude Code dev environment — plus provider, "
    "account, history, and usage tooling.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"cuti version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """
    [bold]cuti[/bold] — an instant, containerized Claude Code dev environment.

    Get started: [cyan]cuti container[/cyan] launches a ready-to-use Claude Code
    workspace in Docker. Run [cyan]cuti --help[/cyan] to see everything else.
    """
    pass


# Version command
@app.command(name="version")
def show_version():
    """Show version information."""
    console.print(f"cuti version {__version__}")


# --- Containers -----------------------------------------------------------
app.add_typer(
    container_app,
    name="containers",
    help="Manage running dev containers (status, stop, enter, cleanup).",
    rich_help_panel="Containers",
)
app.add_typer(
    devcontainer_app,
    name="devcontainer",
    help="Generate and manage .devcontainer configuration.",
    rich_help_panel="Containers",
)

# --- Providers & accounts --------------------------------------------------
app.add_typer(
    providers_app,
    name="providers",
    help="Manage provider selection, setup, status, and updates.",
    rich_help_panel="Providers & accounts",
)
app.add_typer(
    claude_app,
    name="claude",
    help="Manage Claude accounts and API keys.",
    rich_help_panel="Providers & accounts",
)
app.add_typer(
    openclaw_app,
    name="openclaw",
    help="Run OpenClaw inside the cuti container.",
    rich_help_panel="Providers & accounts",
)

# --- Insight & tooling -----------------------------------------------------
app.add_typer(
    history_app,
    name="history",
    help="Browse Claude chat history and resume sessions.",
    rich_help_panel="Insight & tooling",
)
app.add_typer(
    sync_app,
    name="sync",
    help="Sync and inspect Claude usage data.",
    rich_help_panel="Insight & tooling",
)
app.add_typer(
    tools_app,
    name="tools",
    help="Manage workspace CLI tools.",
    rich_help_panel="Insight & tooling",
)

# settings / favorites are Click groups — convert them to Typer apps.
settings_typer = typer.Typer()
for cmd in settings_app.commands.values():
    settings_typer.command()(cmd.callback)
app.add_typer(
    settings_typer,
    name="settings",
    help="Global settings management.",
    rich_help_panel="Insight & tooling",
)

favorites_typer = typer.Typer()
for cmd in favorites_app.commands.values():
    favorites_typer.command()(cmd.callback)
app.add_typer(
    favorites_typer,
    name="favorites",
    help="Favorite prompts management.",
    rich_help_panel="Insight & tooling",
)


@app.command(rich_help_panel="Getting started")
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
    docker_socket: bool = typer.Option(
        False,
        "--docker-socket",
        help="Mount the host Docker socket for Docker-in-Docker. Off by default: "
        "the socket is root-equivalent on the host, so only enable it when you "
        "trust the workload and explicitly need Docker inside the container.",
    ),
):
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
    if docker_socket:
        console.print(
            "[yellow]⚠ Mounting the host Docker socket — this grants the container "
            "root-equivalent access to the host.[/yellow]"
        )
    # If no command provided, just start an interactive shell
    exit_code = service.run_in_container(
        command, rebuild=rebuild, mount_docker_socket=docker_socket
    )

    if exit_code != 0:
        console.print(f"[red]Container exited with code {exit_code}[/red]")
        raise typer.Exit(exit_code)


@app.command(rich_help_panel="Getting started")
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    storage_dir: str = typer.Option(
        "~/.cuti", "--storage-dir", help="Storage directory"
    ),
    working_directory: str | None = typer.Option(
        None, "--working-dir", "-w", help="Working directory"
    ),
):
    """Start the read-only ops console."""
    import os
    import sys
    from pathlib import Path

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
