"""Utilities for inspecting Claude Code conversation history."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp strings from Claude logs."""

    if not value:
        return None
    # Claude log timestamps end with Z (UTC)
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _content_to_text(content) -> str:
    """Flatten Claude message content into human readable text."""

    if isinstance(content, str):
        return content
    parts: List[str] = []
    if isinstance(content, list):
        for chunk in content:
            if not isinstance(chunk, dict):
                continue
            ctype = chunk.get("type")
            if ctype == "text":
                parts.append(chunk.get("text", ""))
            elif ctype == "tool_use":
                tool_name = chunk.get("name", "tool")
                tool_id = chunk.get("id", "")
                parts.append(f"[tool:{tool_name} {tool_id}] {json.dumps(chunk.get('input', {}))}")
            elif ctype == "tool_result":
                tool_id = chunk.get("tool_use_id", "")
                if "content" in chunk:
                    parts.append(f"[tool-result {tool_id}] {_content_to_text(chunk['content'])}")
                else:
                    parts.append(f"[tool-result {tool_id}]")
    return "\n".join(part for part in parts if part).strip()


@dataclass
class SessionSummary:
    """Lightweight metadata for a Claude session log."""

    session_id: str
    file_path: Path
    workspace_path: Optional[str]
    started_at: datetime
    updated_at: datetime
    user_turns: int
    assistant_turns: int
    last_user_prompt: str


@dataclass
class SessionMessage:
    """Individual message inside a session transcript."""

    role: str
    timestamp: Optional[datetime]
    text: str


class ClaudeHistoryService:
    """Loads and summarizes Claude Code JSONL conversation logs."""

    def __init__(self, workspace_path: Optional[Path] = None) -> None:
        self.workspace_path = Path(workspace_path or Path.cwd()).resolve()
        self._project_dirs = self._discover_project_dirs()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_sessions(
        self,
        *,
        limit: int = 20,
        include_all_workspaces: bool = False,
    ) -> List[SessionSummary]:
        """Return the most recent session summaries."""

        session_files = self._collect_session_files(include_all_workspaces)
        summaries: List[SessionSummary] = []
        for file_path in session_files:
            summary = self._summarize_session(file_path)
            if summary:
                summaries.append(summary)

        summaries.sort(key=lambda item: item.updated_at, reverse=True)
        return summaries[:limit]

    def load_session(self, summary: SessionSummary, *, limit: Optional[int] = None) -> List[SessionMessage]:
        """Return ordered transcript for ``summary`` (optionally truncated)."""

        messages: List[SessionMessage] = []
        try:
            with summary.file_path.open() as handle:
                for raw_line in handle:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        record = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    entry_type = record.get("type")
                    if entry_type not in {"user", "assistant", "system"}:
                        continue
                    text = _content_to_text(record.get("message", {}).get("content"))
                    if not text and entry_type != "system":
                        continue
                    timestamp = _parse_timestamp(record.get("timestamp"))
                    messages.append(SessionMessage(role=entry_type, timestamp=timestamp, text=text))
        except FileNotFoundError:
            return []

        if limit is not None:
            return messages[-limit:]
        return messages

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _discover_project_dirs(self) -> List[Path]:
        """Return existing Claude projects directories to inspect."""

        candidates: List[Path] = []
        env_dir = os.getenv("CLAUDE_CONFIG_DIR")
        if env_dir:
            candidates.append(Path(env_dir).expanduser())
        candidates.append(Path.home() / ".cuti" / "claude-linux")
        candidates.append(Path.home() / ".claude")

        project_dirs: List[Path] = []
        seen: set[Path] = set()
        for root in candidates:
            projects = root / "projects"
            try:
                resolved = projects.resolve()
            except FileNotFoundError:
                continue
            if resolved in seen or not projects.exists():
                continue
            seen.add(resolved)
            project_dirs.append(projects)
        return project_dirs

    def _collect_session_files(self, include_all: bool) -> List[Path]:
        """Return candidate JSONL files for the current workspace."""

        files: List[Path] = []
        target_slug = self._workspace_slug(self.workspace_path)
        for projects_dir in self._project_dirs:
            if not projects_dir.exists():
                continue
            dirs: Iterable[Path]
            if include_all:
                dirs = [child for child in projects_dir.iterdir() if child.is_dir()]
            else:
                dirs = [
                    child
                    for child in projects_dir.iterdir()
                    if child.is_dir()
                    and (child.name == target_slug or child.name.startswith(f"{target_slug}-"))
                ]
                if not dirs:
                    # Fallback to direct slug match on sanitized /workspace, useful when running on host
                    dirs = [child for child in projects_dir.iterdir() if child.is_dir() and child.name.endswith(target_slug)]
            for directory in dirs:
                for path in directory.glob("*.jsonl"):
                    files.append(path)

        if files or include_all:
            return files

        # Final fallback: scan every JSONL file across all projects when we couldn't
        # find a directory for the current workspace slug.
        for projects_dir in self._project_dirs:
            for directory in projects_dir.iterdir():
                if directory.is_dir():
                    files.extend(directory.glob("*.jsonl"))
        return files

    def _summarize_session(self, file_path: Path) -> Optional[SessionSummary]:
        session_id = file_path.stem
        workspace_path: Optional[str] = None
        started_at: Optional[datetime] = None
        updated_at: Optional[datetime] = None
        user_turns = 0
        assistant_turns = 0
        last_prompt = ""

        try:
            with file_path.open() as handle:
                for raw_line in handle:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        record = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    session_id = record.get("sessionId", session_id)
                    workspace_path = record.get("cwd", workspace_path)
                    timestamp = _parse_timestamp(record.get("timestamp"))
                    if timestamp:
                        if not started_at:
                            started_at = timestamp
                        updated_at = timestamp
                    entry_type = record.get("type")
                    if entry_type == "user":
                        user_turns += 1
                        text = _content_to_text(record.get("message", {}).get("content"))
                        if text:
                            last_prompt = text.strip()
                    elif entry_type == "assistant":
                        assistant_turns += 1
        except FileNotFoundError:
            return None

        if not started_at:
            started_at = datetime.fromtimestamp(file_path.stat().st_mtime)
        if not updated_at:
            updated_at = started_at

        return SessionSummary(
            session_id=session_id,
            file_path=file_path,
            workspace_path=workspace_path,
            started_at=started_at,
            updated_at=updated_at,
            user_turns=user_turns,
            assistant_turns=assistant_turns,
            last_user_prompt=last_prompt,
        )

    @staticmethod
    def _workspace_slug(path: Path) -> str:
        """Mimic Claude's directory name strategy for workspace logs."""

        normalized = str(path)
        normalized = normalized.replace("\\", "-")
        normalized = normalized.replace("/", "-")
        normalized = normalized.replace(":", "")
        normalized = re.sub(r"\s+", "-", normalized)
        normalized = re.sub(r"-+", "-", normalized)
        if not normalized.startswith("-"):
            normalized = f"-{normalized}"
        return normalized


def claude_available() -> bool:
    """Return True when the ``claude`` CLI is discoverable."""

    return subprocess.call(["which", "claude"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

