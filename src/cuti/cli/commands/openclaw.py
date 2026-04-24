"""Turnkey OpenClaw container commands."""

from __future__ import annotations

import shlex
from contextvars import ContextVar
from typing import List, Optional

import typer
from rich.console import Console

from ...services.provider_host import ProviderHostService

app = typer.Typer(
    help="Run OpenClaw inside the cuti Qt container with provider state and dependencies wired automatically.",
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()
_OPENCLAW_GLOBAL_ARGS: ContextVar[tuple[str, ...]] = ContextVar(
    "openclaw_global_args", default=()
)

_FORWARD_CONTEXT = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}


def _collect_forwarded(ctx: typer.Context, args: Optional[List[str]]) -> List[str]:
    """Merge positional args and unknown option args captured by Typer."""

    return [*(args or []), *ctx.args]


def _current_global_args() -> List[str]:
    """Return root OpenClaw flags captured by the Typer callback."""

    return list(_OPENCLAW_GLOBAL_ARGS.get())


def _uses_isolated_openclaw_profile() -> bool:
    """Return True when root flags select a non-default OpenClaw state tree."""

    global_args = _OPENCLAW_GLOBAL_ARGS.get()
    return "--dev" in global_args or "--profile" in global_args


@app.callback()
def main(
    ctx: typer.Context,
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Forward OpenClaw's dev profile flag and shifted default ports.",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        help="Forward OpenClaw's named profile flag.",
    ),
    container: Optional[str] = typer.Option(
        None,
        "--container",
        help="Forward OpenClaw's named container target flag.",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Forward OpenClaw's no-color output flag.",
    ),
    update: bool = typer.Option(
        False,
        "--update",
        help="Run `openclaw update` inside the Qt container.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        "-v",
        help="Print the OpenClaw CLI version from inside the Qt container.",
    ),
) -> None:
    """Capture OpenClaw root flags before dispatching to a command wrapper."""

    global_args: List[str] = []
    if dev:
        global_args.append("--dev")
    if profile:
        global_args.extend(["--profile", profile])
    if container:
        global_args.extend(["--container", container])
    if no_color:
        global_args.append("--no-color")
    _OPENCLAW_GLOBAL_ARGS.set(tuple(global_args))

    if version:
        _run_openclaw(["--version"])
        raise typer.Exit()

    if update:
        _run_openclaw(["update"], interactive=True)
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


def _run_openclaw(
    args: List[str],
    *,
    rebuild: bool = False,
    interactive: bool = False,
    mount_docker_socket: bool = True,
) -> None:
    """Run an OpenClaw command in the provider-aware cloud container."""

    service = ProviderHostService()
    forwarded_args = [*_current_global_args(), *args]
    exit_code = service.run_provider_command(
        "openclaw",
        forwarded_args,
        rebuild=rebuild,
        interactive=interactive,
        mount_docker_socket=mount_docker_socket,
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)


def _run_openclaw_shell(
    command: str,
    *,
    rebuild: bool = False,
    interactive: bool = False,
    mount_docker_socket: bool = True,
) -> None:
    """Run a composed OpenClaw shell command in the provider-aware container."""

    service = ProviderHostService()
    exit_code = service.run_provider_shell_command(
        "openclaw",
        command,
        rebuild=rebuild,
        interactive=interactive,
        mount_docker_socket=mount_docker_socket,
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)


def _openclaw_command(args: List[str]) -> str:
    return shlex.join(["openclaw", *_current_global_args(), *args])


def _openclaw_setup_state() -> str:
    return ProviderHostService().get_status("openclaw").setup_state


def _gateway_args(
    *,
    port: Optional[int],
    bind: Optional[str],
    allow_unconfigured: bool,
    dev: bool,
    verbose: bool,
    extra_args: Optional[List[str]] = None,
) -> List[str]:
    args = ["gateway"]
    if port is not None:
        args.extend(["--port", str(port)])
    if bind:
        args.extend(["--bind", bind])
    if allow_unconfigured:
        args.append("--allow-unconfigured")
    if dev:
        args.append("--dev")
    if verbose:
        args.append("--verbose")
    if extra_args:
        args.extend(extra_args)
    return args


@app.command()
def onboard(
    install_daemon: bool = typer.Option(
        True,
        "--install-daemon/--no-install-daemon",
        help="Install or refresh OpenClaw's gateway service during onboarding.",
    ),
    doctor: bool = typer.Option(
        True,
        "--doctor/--no-doctor",
        help="Run `openclaw doctor --non-interactive` after onboarding.",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
    extra_args: Optional[List[str]] = typer.Argument(
        None,
        help="Additional arguments forwarded to `openclaw onboard`.",
        metavar="[EXTRA...]",
    ),
) -> None:
    """Run OpenClaw onboarding in the Qt container."""

    args = ["onboard"]
    if install_daemon:
        args.append("--install-daemon")
    if extra_args:
        args.extend(extra_args)

    if doctor:
        command = f"{_openclaw_command(args)} && {_openclaw_command(['doctor', '--non-interactive'])}"
        _run_openclaw_shell(command, rebuild=rebuild, interactive=True)
        return

    _run_openclaw(args, rebuild=rebuild, interactive=True)


@app.command()
def doctor(
    repair: bool = typer.Option(
        False,
        "--repair/--no-repair",
        help="Allow OpenClaw to apply safe repairs.",
    ),
    non_interactive: bool = typer.Option(
        True,
        "--non-interactive/--interactive",
        help="Run without prompts by default.",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Run OpenClaw doctor in the Qt container."""

    args = ["doctor"]
    if repair:
        args.append("--repair")
    if non_interactive:
        args.append("--non-interactive")
    _run_openclaw(args, rebuild=rebuild, interactive=not non_interactive)


@app.command(context_settings=_FORWARD_CONTEXT)
def gateway(
    ctx: typer.Context,
    port: Optional[int] = typer.Option(None, "--port", help="Gateway port."),
    bind: Optional[str] = typer.Option(None, "--bind", help="Gateway bind mode."),
    allow_unconfigured: bool = typer.Option(
        False,
        "--allow-unconfigured",
        help="Allow foreground gateway start before local gateway config exists.",
    ),
    dev: bool = typer.Option(False, "--dev", help="Ask OpenClaw to create dev config/workspace if missing."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Enable verbose gateway logs."),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
    extra_args: Optional[List[str]] = typer.Argument(
        None,
        help="Additional arguments forwarded to `openclaw gateway`.",
        metavar="[EXTRA...]",
    ),
) -> None:
    """Run the OpenClaw gateway in the foreground."""

    args = _gateway_args(
        port=port,
        bind=bind,
        allow_unconfigured=allow_unconfigured,
        dev=dev,
        verbose=verbose,
        extra_args=_collect_forwarded(ctx, extra_args),
    )
    _run_openclaw(args, rebuild=rebuild, interactive=True)


@app.command()
def up(
    port: Optional[int] = typer.Option(None, "--port", help="Gateway port."),
    bind: Optional[str] = typer.Option(None, "--bind", help="Gateway bind mode."),
    configure: bool = typer.Option(
        True,
        "--configure/--no-configure",
        help="Run onboarding first when no OpenClaw setup is detected.",
    ),
    doctor_first: bool = typer.Option(
        True,
        "--doctor/--no-doctor",
        help="Run `openclaw doctor --non-interactive` before starting the gateway.",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Bring OpenClaw up: onboard if needed, check health, then start the gateway."""

    if configure and (
        _uses_isolated_openclaw_profile() or _openclaw_setup_state() == "missing"
    ):
        command = (
            f"{_openclaw_command(['onboard', '--install-daemon'])} "
            f"&& {_openclaw_command(['doctor', '--non-interactive'])}"
        )
        _run_openclaw_shell(command, rebuild=rebuild, interactive=True)

    if doctor_first:
        _run_openclaw(["doctor", "--non-interactive"], rebuild=rebuild)

    _run_openclaw(
        _gateway_args(
            port=port,
            bind=bind,
            allow_unconfigured=False,
            dev=False,
            verbose=True,
        ),
        rebuild=rebuild,
        interactive=True,
    )


@app.command("channels-login")
def channels_login(
    channel: Optional[str] = typer.Option(None, "--channel", "-c", help="Channel identifier, for example whatsapp."),
    account: Optional[str] = typer.Option(None, "--account", help="Account id for multi-account setups."),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Run `openclaw channels login` for QR or browser-based channel auth."""

    args = ["channels", "login"]
    if channel:
        args.extend(["--channel", channel])
    if account:
        args.extend(["--account", account])
    _run_openclaw(args, rebuild=rebuild, interactive=True)


@app.command(context_settings=_FORWARD_CONTEXT)
def channels(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(
        None,
        help="Arguments forwarded to `openclaw channels`.",
        metavar="[ARGS...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Run any OpenClaw channels command."""

    _run_openclaw(["channels", *_collect_forwarded(ctx, args)], rebuild=rebuild)


@app.command(context_settings=_FORWARD_CONTEXT)
def browser(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(
        None,
        help="Arguments forwarded to `openclaw browser`.",
        metavar="[ARGS...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Run OpenClaw browser automation commands."""

    _run_openclaw(["browser", *_collect_forwarded(ctx, args)], rebuild=rebuild)


@app.command(context_settings=_FORWARD_CONTEXT)
def plugins(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(
        None,
        help="Arguments forwarded to `openclaw plugins`.",
        metavar="[ARGS...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Install and manage OpenClaw plugins in the persisted container state."""

    _run_openclaw(["plugins", *_collect_forwarded(ctx, args)], rebuild=rebuild)


@app.command("voice-setup")
def voice_setup(
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Install and enable the official OpenClaw voice-call plugin."""

    command = (
        f"{_openclaw_command(['plugins', 'install', '@openclaw/voice-call'])} "
        f"|| {_openclaw_command(['plugins', 'enable', 'voice-call'])} "
        "|| true; "
        f"{_openclaw_command(['plugins', 'enable', 'voice-call'])} || true; "
        f"{_openclaw_command(['doctor', '--repair', '--non-interactive'])} || true"
    )
    _run_openclaw_shell(command, rebuild=rebuild)


@app.command(context_settings=_FORWARD_CONTEXT)
def voicecall(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(
        None,
        help="Arguments forwarded to `openclaw voicecall`.",
        metavar="[ARGS...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Run OpenClaw voice-call commands."""

    _run_openclaw(["voicecall", *_collect_forwarded(ctx, args)], rebuild=rebuild)


@app.command(context_settings=_FORWARD_CONTEXT)
def voice(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(
        None,
        help="Arguments forwarded to `openclaw voicecall`.",
        metavar="[ARGS...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Alias for OpenClaw voice-call commands."""

    voicecall(ctx, args=args, rebuild=rebuild)


def _make_forward_command(
    command_name: str,
    *,
    help_text: str,
    interactive_default: bool = False,
):
    def forwarded(
        ctx: typer.Context,
        args: Optional[List[str]] = typer.Argument(
            None,
            help=f"Arguments forwarded to `openclaw {command_name}`.",
            metavar="[ARGS...]",
        ),
        rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
        interactive: bool = typer.Option(
            interactive_default,
            "--interactive/--no-interactive",
            help="Allocate a TTY for prompts, login flows, QR output, or terminal UIs.",
        ),
        no_docker_socket: bool = typer.Option(
            False,
            "--no-docker-socket",
            help="Do not mount the host Docker socket into the Qt container.",
        ),
    ) -> None:
        _run_openclaw(
            [command_name, *_collect_forwarded(ctx, args)],
            rebuild=rebuild,
            interactive=interactive,
            mount_docker_socket=not no_docker_socket,
        )

    forwarded.__name__ = f"{command_name.replace('-', '_')}_command"
    forwarded.__doc__ = help_text
    return forwarded


# Mirrors OpenClaw's source-defined command descriptor surface. Plugin-added
# command roots can still be reached through `qt-openclaw run <command> ...`.
_SOURCE_BACKED_FORWARD_COMMANDS = [
    ("setup", "Initialize OpenClaw local config and workspace.", True),
    ("configure", "Run OpenClaw's interactive configuration flow.", True),
    ("config", "Read, write, validate, or locate OpenClaw config.", False),
    ("backup", "Create and verify OpenClaw state backups.", False),
    ("reset", "Reset OpenClaw local config/state inside the persisted state mount.", True),
    ("uninstall", "Uninstall OpenClaw gateway service and local data.", True),
    ("message", "Send, read, and manage messages across OpenClaw channels.", False),
    ("agent", "Run one OpenClaw agent turn via the gateway.", True),
    ("agents", "Manage OpenClaw agents, bindings, auth, and routing.", False),
    ("status", "Show OpenClaw gateway, channel, session, and usage status.", False),
    ("health", "Fetch health from the running OpenClaw gateway.", False),
    ("sessions", "List and inspect stored OpenClaw conversation sessions.", False),
    ("tasks", "Inspect and manage OpenClaw durable task and flow state.", False),
    ("flows", "OpenClaw flow shortcut; current flow commands live under `tasks flow`.", False),
    ("acp", "Run OpenClaw Agent Control Protocol tools.", False),
    ("mcp", "Run OpenClaw MCP server and configuration commands.", False),
    ("daemon", "Run OpenClaw gateway service commands.", False),
    ("logs", "Tail OpenClaw gateway logs.", True),
    ("system", "Inspect OpenClaw system events, heartbeat, and presence.", False),
    ("models", "Discover, authenticate, scan, and configure OpenClaw model providers.", True),
    ("infer", "Run OpenClaw provider-backed inference commands.", False),
    ("capability", "Run OpenClaw provider-backed inference commands via fallback alias.", False),
    ("approvals", "Manage OpenClaw exec approval policy and allowlists.", False),
    ("exec-policy", "Show or sync requested OpenClaw exec policy.", False),
    ("nodes", "Manage gateway-owned node pairing and node commands.", False),
    ("devices", "Manage OpenClaw device pairing and token rotation.", True),
    ("node", "Run and manage the OpenClaw headless node host service.", True),
    ("sandbox", "Manage OpenClaw sandbox runtimes for isolated agent execution.", False),
    ("tui", "Open the OpenClaw terminal UI connected to the gateway.", True),
    ("terminal", "Open the OpenClaw local terminal UI.", True),
    ("chat", "Open the OpenClaw local chat terminal UI.", True),
    ("cron", "Manage OpenClaw scheduled jobs.", False),
    ("dns", "Run OpenClaw DNS helpers for wide-area discovery.", False),
    ("docs", "Search OpenClaw documentation.", False),
    ("proxy", "Run or inspect the OpenClaw debug proxy.", True),
    ("hooks", "Manage OpenClaw internal agent hooks.", False),
    ("webhooks", "Manage OpenClaw webhook integrations.", True),
    ("qr", "Generate OpenClaw mobile pairing QR/setup codes.", True),
    ("pairing", "Approve OpenClaw secure DM pairing requests.", True),
    ("directory", "Look up contact and group IDs for supported chat channels.", False),
    ("security", "Run OpenClaw security tools and local config audits.", False),
    ("secrets", "Manage OpenClaw secrets reload, audit, configure, and apply flows.", True),
    ("skills", "List and inspect OpenClaw skills.", False),
    ("update", "Update OpenClaw and inspect update channel status.", True),
    ("completion", "Generate OpenClaw shell completion scripts.", False),
    ("memory", "Run OpenClaw memory status, indexing, search, and promotion commands.", False),
    ("wiki", "Run OpenClaw wiki ingestion, compile, lint, search, and bridge commands.", False),
]


for _command_name, _help_text, _interactive_default in _SOURCE_BACKED_FORWARD_COMMANDS:
    if _command_name in {
        "channels",
        "browser",
        "plugins",
        "voicecall",
        "dashboard",
        "gateway",
        "doctor",
    }:
        continue
    app.command(name=_command_name, context_settings=_FORWARD_CONTEXT, help=_help_text)(
        _make_forward_command(
            _command_name,
            help_text=_help_text,
            interactive_default=_interactive_default,
        )
    )


@app.command(context_settings=_FORWARD_CONTEXT)
def dashboard(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(
        None,
        help="Arguments forwarded to `openclaw dashboard`.",
        metavar="[ARGS...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
) -> None:
    """Open or print the OpenClaw dashboard URL."""

    _run_openclaw(["dashboard", *_collect_forwarded(ctx, args)], rebuild=rebuild, interactive=True)


@app.command(context_settings=_FORWARD_CONTEXT)
def run(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(
        None,
        help="Arguments forwarded directly to the OpenClaw CLI.",
        metavar="[ARGS...]",
    ),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the container image first."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Allocate a TTY."),
) -> None:
    """Run any OpenClaw CLI command inside the Qt container."""

    forwarded = _collect_forwarded(ctx, args)
    _run_openclaw(forwarded, rebuild=rebuild, interactive=interactive)
