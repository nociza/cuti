"""Claude Code history browser commands."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from ...services.claude_history import (
    ClaudeHistoryService,
    SessionSummary,
)

history_app = typer.Typer(help="Inspect Claude Code chat history and resume sessions")
console = Console()


def _workspace_path_override(workspace: Optional[str]) -> Path:
    return Path(workspace).expanduser().resolve() if workspace else Path.cwd().resolve()


def _resolve_session_identifier(identifier: str, sessions: List[SessionSummary]) -> SessionSummary:
    if not sessions:
        raise typer.BadParameter("No Claude sessions available")

    identifier = identifier.strip().lower()
    if identifier in {"latest", "last", ""}:
        return sessions[0]

    if identifier.isdigit():
        idx = int(identifier) - 1
        if 0 <= idx < len(sessions):
            return sessions[idx]
        raise typer.BadParameter(f"Index {identifier} is out of range (total sessions: {len(sessions)})")

    matches = [session for session in sessions if session.session_id.lower().startswith(identifier)]
    if not matches:
        raise typer.BadParameter(f"No session with id/prefix '{identifier}' found")
    if len(matches) > 1:
        ids = ", ".join(s.session_id[:8] for s in matches[:5])
        raise typer.BadParameter(
            f"Identifier '{identifier}' is ambiguous (matches: {ids}{'...' if len(matches) > 5 else ''})"
        )
    return matches[0]


def _format_timestamp(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


@history_app.command("list")
def list_sessions(
    limit: int = typer.Option(10, help="Number of sessions to show"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace path (defaults to cwd)"),
    all_workspaces: bool = typer.Option(False, "--all", help="Show sessions for every recorded workspace"),
):
    """Display Claude sessions for the current workspace."""

    service = ClaudeHistoryService(_workspace_path_override(workspace))
    sessions = service.list_sessions(limit=limit, include_all_workspaces=all_workspaces)

    if not sessions:
        console.print("[yellow]No Claude sessions found for this workspace yet.[/yellow]")
        return

    table = Table(title="Claude Sessions")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Session", style="magenta")
    table.add_column("Last Activity", style="green")
    table.add_column("Turns", justify="right", style="cyan")
    table.add_column("Last Prompt", style="white")

    for idx, summary in enumerate(sessions, start=1):
        turns = f"{summary.user_turns}/{summary.assistant_turns}"
        table.add_row(
            str(idx),
            summary.session_id,
            _format_timestamp(summary.updated_at),
            turns,
            (summary.last_user_prompt[:80] + "…") if len(summary.last_user_prompt) > 80 else summary.last_user_prompt,
        )

    console.print(table)


@history_app.command("show")
def show_session(
    session: str = typer.Argument("latest", help="Session id, numeric index, or 'latest'"),
    limit: int = typer.Option(40, help="Number of messages to display"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace path (defaults to cwd)"),
    all_workspaces: bool = typer.Option(False, "--all", help="Search across every recorded workspace"),
):
    """Show the last few messages from a Claude session."""

    service = ClaudeHistoryService(_workspace_path_override(workspace))
    sessions = service.list_sessions(limit=max(limit, 50), include_all_workspaces=all_workspaces)
    if not sessions:
        console.print("[yellow]No Claude sessions available to display.[/yellow]")
        raise typer.Exit(code=1)

    summary = _resolve_session_identifier(session, sessions)
    messages = service.load_session(summary, limit=limit)
    console.print(f"[bold]Session:[/bold] {summary.session_id}")
    if summary.workspace_path:
        console.print(f"[bold]Workspace:[/bold] {summary.workspace_path}")
    console.print(f"[bold]Messages shown:[/bold] {len(messages)} (latest first)")
    console.print()

    for message in messages:
        timestamp = message.timestamp.isoformat(sep=" ") if message.timestamp else "-"
        role = "USER" if message.role == "user" else message.role.upper()
        console.print(f"[cyan]{timestamp}[/cyan] [bold]{role}[/bold]")
        console.print(f"{message.text}\n")


@history_app.command("resume")
def resume_session(
    session: str = typer.Argument("latest", help="Session id, numeric index, or 'latest'"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace path (defaults to cwd)"),
    all_workspaces: bool = typer.Option(False, "--all", help="Search across every recorded workspace"),
):
    """Resume a Claude session using the official CLI."""

    if not shutil.which("claude"):
        console.print("[red]The 'claude' CLI is not available in this environment.[/red]")
        raise typer.Exit(code=1)

    service = ClaudeHistoryService(_workspace_path_override(workspace))
    sessions = service.list_sessions(limit=50, include_all_workspaces=all_workspaces)
    if not sessions:
        console.print("[yellow]No sessions found to resume.[/yellow]")
        raise typer.Exit(code=1)

    summary = _resolve_session_identifier(session, sessions)
    console.print(
        f"[dim]Launching:[/dim] claude --resume {summary.session_id} (last active {_format_timestamp(summary.updated_at)})"
    )
    result = subprocess.run([
        "claude",
        "--resume",
        summary.session_id,
    ], check=False, cwd=str(service.workspace_path))
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
