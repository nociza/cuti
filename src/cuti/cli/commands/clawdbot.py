"""Run Clawdbot commands inside the cuti dev container."""

from __future__ import annotations

import json
import os
import socket
import shlex
import subprocess
import textwrap
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from ...services.clawdbot_instance import ClawdbotInstance, ClawdbotInstanceManager
from ...services.devcontainer import DevContainerService, is_running_in_container

app = typer.Typer(help="Manage the optional Clawdbot assistant from the host CLI")
console = Console()

_CLAWDBOT_CONFIG_PATH = Path.home() / ".cuti" / "clawdbot" / "config" / "clawdbot.json"
_DEFAULT_GATEWAY_PORT = 18789


def _load_clawdbot_config() -> dict:
    """Return the parsed Clawdbot config if it exists, otherwise {}."""

    try:
        return json.loads(_CLAWDBOT_CONFIG_PATH.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _read_clawdbot_version() -> Optional[str]:
    """Return the last known Clawdbot version from config (if available)."""

    data = _load_clawdbot_config()
    meta = data.get("meta") or {}
    version = meta.get("lastTouchedVersion")
    return version if isinstance(version, str) and version else None


def _coerce_port(value: object) -> Optional[int]:
    """Return value as an int port (1-65535) if possible."""

    try:
        port = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if 0 < port < 65536:
        return port
    return None


def _get_configured_gateway_port() -> Optional[int]:
    """Pull a stored gateway port out of clawdbot.json if present."""

    data = _load_clawdbot_config()
    candidate_paths = [
        ("gateway", "port"),
        ("session", "gateway", "port"),
        ("gatewayPort",),
        ("gateway_port",),
    ]

    for path in candidate_paths:
        cursor: object = data
        for key in path:
            if not isinstance(cursor, dict):
                break
            cursor = cursor.get(key)
        else:
            port = _coerce_port(cursor)
            if port is not None:
                return port
    return None


def _is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if the host+port appears free."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _scan_for_open_port(start: int, attempts: int = 32) -> Optional[int]:
    """Return the first open port starting at `start` within `attempts`."""

    for offset in range(max(1, attempts)):
        port = start + offset
        if _is_port_available(port):
            return port
    # Fall back to an ephemeral suggestion
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        port = sock.getsockname()[1]
    return port if _is_port_available(port) else None


def _auto_select_gateway_port(explicit: Optional[int]) -> int:
    """Pick a port using CLI input, env, config, or a free fallback."""

    env_value = os.environ.get("CUTI_CLAWDBOT_PORT")
    env_port = _coerce_port(env_value) if env_value else None
    config_port = _get_configured_gateway_port()

    candidates: List[tuple[str, Optional[int]]] = [
        ("command line", explicit),
        ("CUTI_CLAWDBOT_PORT", env_port),
        ("clawdbot config", config_port),
        ("default", _DEFAULT_GATEWAY_PORT),
    ]

    for source, port in candidates:
        if port is None:
            continue
        if _is_port_available(port):
            if source != "command line":
                console.print(
                    f"[dim]Using {source} gateway port: {port}[/dim]"
                )
            return port
        console.print(
            f"[yellow]⚠️  {source.title()} port {port} is busy; searching for another...[/yellow]"
        )

    fallback = _scan_for_open_port(_DEFAULT_GATEWAY_PORT)
    if fallback is None:
        console.print(
            "[red]Unable to find an open port; use --port to specify one manually.[/red]"
        )
        raise typer.Exit(1)
    console.print(
        f"[dim]Auto-selected fallback port {fallback} for Clawdbot gateway[/dim]"
    )
    return fallback


# ------------------------------------------------------------------
# Instance Management Helpers
# ------------------------------------------------------------------


def _check_running_instances(
    manager: ClawdbotInstanceManager, target_port: int
) -> Optional[ClawdbotInstance]:
    """Check for running instances, preferring the one on target_port."""
    running = manager.detect_running_instances()
    if not running:
        return None

    # First check if there's one on the target port
    for instance in running:
        if instance.port == target_port:
            return instance

    # Otherwise return the first running instance
    return running[0]


def _warn_concurrent_instance(
    existing: ClawdbotInstance, current_workspace: Path
) -> bool:
    """Display warning about concurrent instance. Returns True to continue."""
    existing_path = Path(existing.workspace_path)

    console.print()
    console.print("=" * 60, style="yellow bold")
    console.print("WARNING: Another Clawdbot instance detected!", style="yellow bold")
    console.print("=" * 60, style="yellow bold")
    console.print()

    console.print("[bold]Running instance:[/bold]")
    console.print(f"  Port: {existing.port}")
    console.print(f"  Workspace: {existing.workspace_path}")
    console.print(f"  Started: {existing.started_at}")
    console.print()

    console.print("[bold]Current workspace:[/bold]")
    console.print(f"  {current_workspace}")
    console.print()

    if existing_path.resolve() != current_workspace.resolve():
        console.print(
            "Starting a new instance from a different workspace may cause",
            style="yellow",
        )
        console.print(
            "configuration conflicts. This feature is under active development.",
            style="yellow",
        )
        console.print()

    return Confirm.ask("Continue anyway?", default=False)


def _setup_workspace_config(workspace_path: Path) -> str:
    """Setup workspace config before starting. Returns workspace slug."""
    console.print("[dim]Configuring workspace...[/dim]")

    manager = ClawdbotInstanceManager()
    workspace_slug = manager.generate_workspace_slug(workspace_path)

    # Update clawdbot.json to set workspace = /workspace
    if manager.update_workspace_config():
        console.print(f"[dim]Project: {workspace_path.name}[/dim]")
        console.print("[dim]Clawdbot agents will work in: /workspace[/dim]")
    else:
        console.print("[yellow]Warning: Could not update workspace config[/yellow]")

    return workspace_slug


def _should_auto_build_ui(args: List[str]) -> bool:
    """Return True if the command requires the Control UI assets."""

    if not args:
        return False
    return args[0] == "gateway"


def _control_ui_bootstrap_script(version: Optional[str]) -> str:
    """Shell snippet that builds the Control UI once per container session."""

    expected = version or "unknown"
    # Store sentinel in Clawdbot config dir (persists across sessions)
    clawdbot_config = "/home/cuti/.clawdbot"
    sentinel = f"{clawdbot_config}/.control-ui-built"

    script = f"""
    ensure_clawdbot_control_ui() {{
        local config_dir={shlex.quote(clawdbot_config)}
        local sentinel={shlex.quote(sentinel)}
        local desired={shlex.quote(expected)}
        local need_build=0

        if [ ! -d "$config_dir" ]; then
            mkdir -p "$config_dir" 2>/dev/null || true
        fi

        if [ ! -f "$sentinel" ]; then
            need_build=1
        else
            local recorded
            recorded=$(cat "$sentinel" 2>/dev/null || echo "")
            if [ "$recorded" != "$desired" ]; then
                need_build=1
            fi
        fi

        if [ $need_build -eq 0 ]; then
            return
        fi

        local package_dir
        package_dir=$(cuti_locate_clawdbot_package)
        if [ -z "$package_dir" ]; then
            echo "⚠️  Unable to locate Clawdbot CLI install to build Control UI"
            return
        fi

        echo "🛠️  Preparing Clawdbot Control UI (pnpm ui:build)..."
        if cd "$package_dir" && pnpm ui:build; then
            mkdir -p "$(dirname "$sentinel")" 2>/dev/null || true
            printf "%s" "$desired" > "$sentinel"
            echo "✅ Clawdbot Control UI assets ready"
        else
            echo "⚠️  Failed to build Clawdbot Control UI assets - gateway health checks may fail"
        fi
    }}

    cuti_locate_clawdbot_package() {{
        local npm_root
        if command -v npm >/dev/null 2>&1; then
            npm_root=$(npm root -g 2>/dev/null || echo "")
            if [ -n "$npm_root" ] && [ -f "$npm_root/clawdbot/package.json" ]; then
                echo "$npm_root/clawdbot"
                return
            fi
        fi

        for candidate in \
            "/usr/local/lib/node_modules/clawdbot" \
            "/usr/lib/node_modules/clawdbot" \
            "/opt/homebrew/lib/node_modules/clawdbot"; do
            if [ -n "$candidate" ] && [ -f "$candidate/package.json" ]; then
                echo "$candidate"
                return
            fi
        done

        echo ""
    }}

    ensure_clawdbot_control_ui
    """

    return textwrap.dedent(script).strip()


def _maybe_wrap_with_ui_bootstrap(args: List[str], command: str) -> str:
    """Prepend the Control UI bootstrap snippet when the gateway runs."""

    final_command = command

    if args and args[0] == "gateway":
        final_command = _wrap_gateway_signals(final_command)

    if not _should_auto_build_ui(args):
        return final_command

    script = _control_ui_bootstrap_script(_read_clawdbot_version())
    if not script:
        return final_command

    return f"{script}\n{final_command}"


def _command_requires_tty(args: List[str]) -> bool:
    if not args:
        return False
    first = args[0]
    if first in {"config", "onboard", "channels", "configure"}:
        return True
    return False


def _wrap_gateway_signals(command: str) -> str:
    """Ensure ctrl+c (and TERM) stops the gateway gracefully before exiting."""

    wrapper = f"""
    cuti_run_gateway_foreground() {{
        local _cuti_gateway_pid

        cuti_shutdown_gateway() {{
            if [ -n "$_cuti_gateway_pid" ] \\
               && kill -0 "$_cuti_gateway_pid" >/dev/null 2>&1; then
                echo "🧹 Gracefully stopping Clawdbot gateway (PID $_cuti_gateway_pid)..."
                kill -INT "$_cuti_gateway_pid" >/dev/null 2>&1 \\
                    || kill -TERM "$_cuti_gateway_pid" >/dev/null 2>&1
            fi
        }}

        trap 'cuti_shutdown_gateway' INT TERM
        {command} &
        _cuti_gateway_pid=$!
        wait "$_cuti_gateway_pid"
        local exit_code=$?
        trap - INT TERM
        return $exit_code
    }}

    cuti_run_gateway_foreground
    """

    return textwrap.dedent(wrapper).strip()


def _prepare_service(skip_colima: bool) -> DevContainerService:
    """Prepare the dev container runtime (Colima/Docker) if needed."""

    service = DevContainerService()
    console.print("[cyan]Checking container dependencies...[/cyan]")
    if not service.ensure_dependencies():
        console.print("[red]Container dependencies not available[/red]")
        raise typer.Exit(1)

    service.colima_available = service._check_colima()
    service.docker_available = service._check_docker()

    if not service.docker_available:
        if service.colima_available and not skip_colima:
            console.print("[cyan]Docker not running, will start Colima...[/cyan]")
            console.print("[dim]This may take a minute on first start[/dim]")
            if not service.setup_colima():
                console.print("[red]Failed to start Colima automatically[/red]")
                console.print("Start Docker Desktop or rerun with --skip-colima.")
                raise typer.Exit(1)
            service.docker_available = service._check_docker()
        else:
            console.print("[red]Docker is not available[/red]")
            raise typer.Exit(1)

    # Ensure the addon is enabled so the build includes Clawdbot
    service._is_clawdbot_enabled()
    return service


def _run_clawdbot(
    args: List[str],
    *,
    rebuild: bool = False,
    skip_colima: bool = False,
) -> None:
    """Run a Clawdbot CLI command (host or container).

    Args:
        args: Arguments to pass to clawdbot CLI
        rebuild: Force rebuild of the container image
        skip_colima: Skip starting Colima automatically
    """

    base_command = shlex.join(["clawdbot", *args])
    wrapped_command = _maybe_wrap_with_ui_bootstrap(args, base_command)
    requires_tty = _command_requires_tty(args)

    if is_running_in_container():
        if wrapped_command == base_command:
            process = subprocess.run(["clawdbot", *args])
        else:
            process = subprocess.run(["/bin/zsh", "-lc", wrapped_command])
        if process.returncode != 0:
            raise typer.Exit(process.returncode)
        return

    service = _prepare_service(skip_colima)
    exit_code = service.run_in_container(
        wrapped_command,
        rebuild=rebuild,
        interactive=requires_tty,
        mount_docker_socket=False,
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command()
def onboard(
    install_daemon: bool = typer.Option(True, "--install-daemon/--no-install-daemon", help="Install background service"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild of the container image"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip starting Colima automatically"),
) -> None:
    """Run the Clawdbot onboarding wizard inside the dev container."""

    args = ["onboard"]
    if install_daemon:
        args.append("--install-daemon")
    _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)


@app.command()
def gateway(
    port: int = typer.Option(18789, "--port", help="Gateway port"),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Mirror verbose logs"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild before starting"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima auto-start"),
    extra_args: List[str] = typer.Argument(
        [],
        help="Additional arguments forwarded to `clawdbot gateway`",
        metavar="[EXTRA...]",
    ),
) -> None:
    """Start the Clawdbot gateway (streams logs until interrupted)."""

    args = ["gateway", "--port", str(port)]
    if verbose:
        args.append("--verbose")
    if extra_args:
        args.extend(extra_args)
    _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)


@app.command()
def start(
    port: Optional[int] = typer.Option(
        None,
        "--port",
        help="Preferred gateway port; defaults to config/env/first available",
    ),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Mirror verbose logs"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild before starting"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima auto-start"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip concurrent instance warning"),
    extra_args: List[str] = typer.Argument(
        [],
        help="Additional arguments forwarded to `clawdbot gateway`",
        metavar="[EXTRA...]",
    ),
) -> None:
    """Start the gateway after auto-selecting a usable host port."""

    current_workspace = Path.cwd().resolve()
    manager = ClawdbotInstanceManager()

    # 1. Setup workspace configuration BEFORE port selection
    workspace_slug = _setup_workspace_config(current_workspace)

    # 2. Auto-select port
    chosen_port = _auto_select_gateway_port(port)

    # 3. Check for running instances (unless --force)
    if not force:
        existing = _check_running_instances(manager, chosen_port)
        if existing:
            if not _warn_concurrent_instance(existing, current_workspace):
                console.print("[dim]Aborted.[/dim]")
                raise typer.Exit(0)
            # User wants to continue; find a different port if needed
            if existing.port == chosen_port:
                console.print(
                    f"[yellow]Note: Another instance is running on port {chosen_port} "
                    f"from {Path(existing.workspace_path).name}[/yellow]"
                )
                fallback = _scan_for_open_port(chosen_port + 1)
                if fallback:
                    chosen_port = fallback
                    console.print(f"[dim]Switching to port {chosen_port}[/dim]")
    else:
        # With --force, just note if there's another instance
        existing = _check_running_instances(manager, chosen_port)
        if existing and existing.port == chosen_port:
            console.print(
                f"[yellow]Note: Another instance is running on port {chosen_port} "
                f"from {Path(existing.workspace_path).name}[/yellow]"
            )
            fallback = _scan_for_open_port(chosen_port + 1)
            if fallback:
                chosen_port = fallback
                console.print(f"[dim]Switching to port {chosen_port}[/dim]")

    # 4. Register instance before starting
    instance_id = manager.register_instance(
        port=chosen_port,
        workspace_path=current_workspace,
        workspace_slug=workspace_slug,
        pid=os.getpid(),
    )

    console.print(f"[cyan]Launching Clawdbot gateway on port {chosen_port}[/cyan]")
    console.print(f"[dim]Control UI: http://127.0.0.1:{chosen_port}/[/dim]")

    try:
        # 5. Run gateway
        args = ["gateway", "--port", str(chosen_port)]
        if verbose:
            args.append("--verbose")
        if extra_args:
            args.extend(extra_args)
        _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)
    finally:
        # 6. Cleanup on exit
        manager.unregister_instance(instance_id)


@app.command()
def config(
    extra_args: List[str] = typer.Argument(
        [],
        help="Arguments forwarded directly to `clawdbot config`",
        metavar="[EXTRA...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild before running"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima auto-start"),
) -> None:
    """Show or edit Clawdbot config via the upstream CLI."""

    args = ["config"]
    if extra_args:
        args.extend(extra_args)
    _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)


@app.command("channels-login")
def channels_login(
    channel: Optional[str] = typer.Option(None, "--channel", "-c", help="Channel identifier (e.g. whatsapp)"),
    account: Optional[str] = typer.Option(None, "--account", help="Account id for multi-account setups"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild before running"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima auto-start"),
) -> None:
    """Launch `clawdbot channels login` to link messaging channels (WhatsApp, etc.)."""

    args = ["channels", "login"]
    if channel:
        args.extend(["--channel", channel])
    if account:
        args.extend(["--account", account])
    _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)


@app.command()
def send(
    to: str = typer.Option(..., "--to", help="Target phone/user id"),
    message: str = typer.Option(..., "--message", help="Message text"),
    media: Optional[str] = typer.Option(None, "--media", help="Optional media path or URL"),
    gateway_session: Optional[str] = typer.Option(None, "--session", help="Session id to route through"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild before running"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima auto-start"),
) -> None:
    """Send a one-off message via the running gateway (good for smoke tests)."""

    args = [
        "message",
        "send",
        "--target",
        to,
        "--message",
        message,
    ]
    if media:
        args.extend(["--media", media])
    if gateway_session:
        args.extend(["--session", gateway_session])
    _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)


@app.command()
def run(
    args: List[str] = typer.Argument(..., help="Arguments forwarded directly to the Clawdbot CLI"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild before running"),
    skip_colima: bool = typer.Option(False, "--skip-colima", help="Skip Colima auto-start"),
) -> None:
    """Run any Clawdbot CLI command inside the container (escape hatch)."""

    _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)


@app.command("status")
def status() -> None:
    """Show status of running Clawdbot instances."""
    manager = ClawdbotInstanceManager()
    instances = manager.detect_running_instances()

    if not instances:
        console.print("[dim]No running Clawdbot instances detected.[/dim]")
        return

    table = Table(title="Running Clawdbot Instances")
    table.add_column("Instance", style="cyan")
    table.add_column("Port", style="green")
    table.add_column("Workspace", style="blue")
    table.add_column("Started", style="dim")
    table.add_column("PID", style="dim")

    for instance in instances:
        workspace_name = Path(instance.workspace_path).name
        table.add_row(
            instance.instance_id,
            str(instance.port),
            workspace_name,
            instance.started_at[:19] if instance.started_at else "-",
            str(instance.pid) if instance.pid else "-",
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Control UI: http://127.0.0.1:{instances[0].port}/[/dim]")


@app.command("cleanup")
def cleanup() -> None:
    """Remove stale instance entries from tracking file."""
    manager = ClawdbotInstanceManager()

    # Count instances before cleanup
    state_before = manager._state.get("instances", {})
    count_before = len(state_before)

    # Force cleanup
    manager._cleanup_stale_instances()

    # Count after
    state_after = manager._state.get("instances", {})
    count_after = len(state_after)

    removed = count_before - count_after
    if removed > 0:
        console.print(f"[green]Cleaned up {removed} stale instance(s).[/green]")
    else:
        console.print("[dim]No stale instances found.[/dim]")

    if count_after > 0:
        console.print(f"[dim]{count_after} active instance(s) remain tracked.[/dim]")
