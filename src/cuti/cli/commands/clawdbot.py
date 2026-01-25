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


def _should_auto_build_ui(args: List[str]) -> bool:
    """Return True if the command requires the Control UI assets."""

    if not args:
        return False
    return args[0] == "gateway"


def _control_ui_bootstrap_script(version: Optional[str]) -> str:
    """Shell snippet that builds the Control UI once per workspace."""

    expected = version or "unknown"
    workspace = "/home/cuti/clawd"
    sentinel = f"{workspace}/.cuti-control-ui-built"

    script = f"""
    ensure_clawdbot_control_ui() {{
        local workspace={shlex.quote(workspace)}
        local sentinel={shlex.quote(sentinel)}
        local desired={shlex.quote(expected)}
        local need_build=0

        if [ ! -d "$workspace" ]; then
            echo "⚠️  Clawdbot workspace missing at $workspace"
            return
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
        local resolved
        resolved=$(node -p "try {{ require.resolve('clawdbot/package.json') }} catch (err) {{ '' }}" 2>/dev/null || echo "")
        if [ -n "$resolved" ] && [ -f "$resolved" ]; then
            dirname "$resolved"
            return
        fi

        local npm_root
        if command -v npm >/dev/null 2>&1; then
            npm_root=$(npm root -g 2>/dev/null || echo "")
        fi

        for candidate in \
            "$npm_root/clawdbot" \
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
    """Run a Clawdbot CLI command (host or container)."""

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
    extra_args: List[str] = typer.Argument(
        [],
        help="Additional arguments forwarded to `clawdbot gateway`",
        metavar="[EXTRA...]",
    ),
) -> None:
    """Start the gateway after auto-selecting a usable host port."""

    chosen_port = _auto_select_gateway_port(port)
    console.print(f"[cyan]Launching Clawdbot gateway on port {chosen_port}[/cyan]")
    console.print(f"[dim]Control UI: http://127.0.0.1:{chosen_port}/[/dim]")

    args = ["gateway", "--port", str(chosen_port)]
    if verbose:
        args.append("--verbose")
    if extra_args:
        args.extend(extra_args)
    _run_clawdbot(args, rebuild=rebuild, skip_colima=skip_colima)


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
