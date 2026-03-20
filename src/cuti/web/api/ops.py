"""Read-only operations summary for the cuti web console."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from ...core.models import PromptStatus
from ...services.instructions import TOOLS_SECTION_HEADER
from ...services.provider_host import ProviderHostService
from ...services.providers import ProviderManager
from ...services.tool_catalog import AVAILABLE_TOOLS, check_tool_installed, load_tools_config

router = APIRouter(prefix="/api/ops", tags=["ops"])

INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md", "SOUL.md", "TOOLS.md", "GOAL.md")
PROVIDER_INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md", "SOUL.md", "TOOLS.md")
SEVERITY_ORDER = {"critical": 0, "warning": 1, "note": 2}


def _isoformat(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)



def _serialize_queue_prompt(prompt: Any) -> Dict[str, Any]:
    return {
        "id": prompt.id,
        "content": prompt.content,
        "status": prompt.status.value,
        "priority": prompt.priority,
        "created_at": _isoformat(prompt.created_at),
        "working_directory": prompt.working_directory,
        "context_files": list(prompt.context_files or []),
    }



def _serialize_history_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "content": entry.get("content", ""),
        "working_directory": entry.get("working_directory"),
        "timestamp": _isoformat(entry.get("timestamp")),
        "success": entry.get("success"),
        "context_files": list(entry.get("context_files") or []),
        "output_preview": entry.get("output_preview"),
    }



def _queue_summary(request: Request) -> Dict[str, Any]:
    queue_manager = request.app.state.queue_manager
    detail = "The ops console is passive. Use the CLI or container session to process queued prompts."
    status_counts = {status.value: 0 for status in PromptStatus}

    if not queue_manager:
        warning = getattr(request.app.state, "queue_warning", None)
        if warning:
            detail = f"{detail} Queue inspection is unavailable: {warning}"
        return {
            "available": False,
            "processor_mode": "passive",
            "total_prompts": 0,
            "status_counts": status_counts,
            "total_processed": 0,
            "failed_count": 0,
            "rate_limited_count": 0,
            "last_processed": None,
            "current_rate_limit": {"is_rate_limited": False, "reset_time": None},
            "recent_prompts": [],
            "detail": detail,
        }

    state = queue_manager.get_status()
    stats = state.get_stats()
    prompts = sorted(state.prompts, key=lambda item: item.created_at, reverse=True)
    return {
        "available": True,
        "processor_mode": "passive",
        "total_prompts": stats.get("total_prompts", 0),
        "status_counts": stats.get("status_counts", status_counts),
        "total_processed": stats.get("total_processed", 0),
        "failed_count": stats.get("failed_count", 0),
        "rate_limited_count": stats.get("rate_limited_count", 0),
        "last_processed": stats.get("last_processed"),
        "current_rate_limit": stats.get(
            "current_rate_limit",
            {"is_rate_limited": False, "reset_time": None},
        ),
        "recent_prompts": [_serialize_queue_prompt(prompt) for prompt in prompts[:6]],
        "detail": detail,
    }



def _history_summary(request: Request) -> Dict[str, Any]:
    history_manager = request.app.state.history_manager
    history = [_serialize_history_entry(entry) for entry in history_manager.get_history(limit=8)]
    stats = history_manager.get_history_stats() or {}
    return {
        "recent": history,
        "stats": {
            "total_prompts": stats.get("total_prompts", 0),
            "successful_prompts": stats.get("successful_prompts", 0),
            "failed_prompts": stats.get("failed_prompts", 0),
            "success_rate": stats.get("success_rate", 0),
            "latest_prompt": stats.get("latest_prompt"),
        },
    }



def _session_summary(request: Request) -> Dict[str, Any]:
    logs_reader = request.app.state.claude_logs_reader
    current_session_id = logs_reader.get_current_session_id()
    sessions = logs_reader.get_all_sessions()[:6]
    current_stats = logs_reader.get_statistics(current_session_id) if current_session_id else {}
    return {
        "project_name": logs_reader.project_name,
        "current_session_id": current_session_id,
        "current_stats": current_stats or None,
        "recent_sessions": sessions,
    }



def _provider_summary(request: Request) -> Dict[str, Any]:
    service = ProviderHostService(working_directory=str(request.app.state.working_directory))
    manager = service.provider_manager
    statuses = [status.to_dict() for status in service.list_statuses()]
    return {
        "primary_provider": manager.primary_provider(),
        "selected_providers": manager.selected_providers(),
        "ready_count": sum(1 for status in statuses if status["setup_state"] == "ready"),
        "selected_count": sum(1 for status in statuses if status["enabled"]),
        "items": statuses,
    }



def _tools_summary() -> Dict[str, Any]:
    config = load_tools_config()
    enabled = set(config.get("enabled_tools", []))
    auto_install = set(config.get("auto_install", []))
    items: List[Dict[str, Any]] = []
    installed_count = 0

    for tool in AVAILABLE_TOOLS:
        installed = check_tool_installed(tool["check_command"])
        if installed:
            installed_count += 1
        items.append(
            {
                "name": tool["name"],
                "display_name": tool["display_name"],
                "category": tool["category"],
                "enabled": tool["name"] in enabled,
                "auto_install": tool["name"] in auto_install,
                "installed": installed,
            }
        )

    missing_enabled = [item for item in items if item["enabled"] and not item["installed"]]
    return {
        "total_count": len(items),
        "enabled_count": len(enabled),
        "installed_count": installed_count,
        "auto_install_count": len(auto_install),
        "items": items,
        "missing_enabled": missing_enabled[:6],
    }



def _workspace_summary(request: Request, selected_instruction_files: List[str], tools_enabled: bool) -> Dict[str, Any]:
    working_directory = Path(request.app.state.working_directory)
    files: List[Dict[str, Any]] = []
    missing_selected_files: List[str] = []
    stale_files: List[str] = []
    missing_tools_sections: List[str] = []

    for name in INSTRUCTION_FILES:
        path = working_directory / name
        exists = path.exists()
        selected = name in selected_instruction_files
        content = ""
        if exists:
            try:
                content = path.read_text()
            except Exception:
                content = ""

        has_tools_section = TOOLS_SECTION_HEADER in content if exists else False
        if selected and not exists:
            missing_selected_files.append(name)
        if exists and name in PROVIDER_INSTRUCTION_FILES and not selected:
            stale_files.append(name)
        if tools_enabled and exists and selected and not has_tools_section:
            missing_tools_sections.append(name)

        files.append(
            {
                "name": name,
                "path": str(path),
                "exists": exists,
                "selected": selected,
                "has_tools_section": has_tools_section,
            }
        )

    return {
        "name": working_directory.name,
        "path": str(working_directory),
        "storage_dir": str(request.app.state.storage_dir),
        "selected_instruction_files": selected_instruction_files,
        "instruction_files": files,
        "drift": {
            "missing_selected_files": missing_selected_files,
            "stale_files": stale_files,
            "missing_tools_sections": missing_tools_sections,
        },
    }



def _action_item(
    severity: str,
    title: str,
    detail: str,
    *,
    command: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "severity": severity,
        "title": title,
        "detail": detail,
        "command": command,
        "source": source,
    }



def _attention_items(
    providers: Dict[str, Any],
    queue: Dict[str, Any],
    history: Dict[str, Any],
    tools: Dict[str, Any],
    workspace: Dict[str, Any],
    sessions: Dict[str, Any],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    if not providers["selected_providers"]:
        items.append(
            _action_item(
                "critical",
                "No providers selected",
                "Select at least one provider before rebuilding the container.",
                command="cuti providers enable claude",
                source="providers",
            )
        )

    for status in providers["items"]:
        if status["enabled"] and status["setup_state"] != "ready":
            items.append(
                _action_item(
                    "warning",
                    f"{status['title']} needs setup",
                    status["detail"],
                    command=f"cuti providers auth {status['provider']} --login",
                    source="providers",
                )
            )

    if queue["current_rate_limit"].get("is_rate_limited"):
        reset_time = queue["current_rate_limit"].get("reset_time") or "unknown time"
        items.append(
            _action_item(
                "warning",
                "Queue is rate limited",
                f"Claude reported a rate limit. Next reset: {reset_time}.",
                source="queue",
            )
        )

    for tool in tools["missing_enabled"][:3]:
        items.append(
            _action_item(
                "warning",
                f"{tool['display_name']} is enabled but not installed",
                "Install the tool from the terminal so workspace instructions match reality.",
                command=f"cuti tools install {tool['name']} --enable",
                source="tools",
            )
        )

    if workspace["drift"]["missing_selected_files"]:
        missing = ", ".join(workspace["drift"]["missing_selected_files"])
        items.append(
            _action_item(
                "note",
                "Selected instruction files are missing",
                f"Expected provider files are missing from the workspace: {missing}.",
                source="workspace",
            )
        )

    if workspace["drift"]["stale_files"]:
        stale = ", ".join(workspace["drift"]["stale_files"])
        items.append(
            _action_item(
                "note",
                "Workspace instruction surface has stale files",
                f"These provider files exist but are not selected by the current provider set: {stale}.",
                source="workspace",
            )
        )

    if workspace["drift"]["missing_tools_sections"]:
        missing = ", ".join(workspace["drift"]["missing_tools_sections"])
        items.append(
            _action_item(
                "note",
                "Tool instructions are missing from selected files",
                f"Enabled tools are not documented in: {missing}.",
                source="workspace",
            )
        )

    if not sessions["recent_sessions"] and "claude" in providers["selected_providers"]:
        items.append(
            _action_item(
                "note",
                "No Claude session logs detected yet",
                "Session history will appear here after Claude has been used in this workspace.",
                source="sessions",
            )
        )

    if queue["available"] and queue["total_prompts"] and not history["recent"]:
        items.append(
            _action_item(
                "note",
                "Queued work has not produced history yet",
                "The queue has prompts, but there is no recent prompt history recorded for this workspace.",
                command="cuti start",
                source="history",
            )
        )

    if not items:
        items.append(
            _action_item(
                "note",
                "No immediate drift detected",
                "Providers, tools, and workspace instruction files look aligned.",
                source="summary",
            )
        )

    items.sort(key=lambda item: SEVERITY_ORDER.get(item["severity"], 9))
    return items[:8]



def _recommended_commands(attention_items: List[Dict[str, Any]]) -> List[str]:
    commands: List[str] = []
    for candidate in [item.get("command") for item in attention_items] + [
        "cuti providers doctor",
        "cuti start",
        "cuti container",
    ]:
        if candidate and candidate not in commands:
            commands.append(candidate)
    return commands[:6]


@router.get("/summary")
async def ops_summary(request: Request) -> Dict[str, Any]:
    """Return the passive operations summary used by the web console."""

    providers = _provider_summary(request)
    queue = _queue_summary(request)
    history = _history_summary(request)
    tools = _tools_summary()
    workspace = _workspace_summary(
        request,
        selected_instruction_files=providers["selected_providers"]
        and ProviderManager().provider_instruction_files(providers["selected_providers"])
        or [],
        tools_enabled=tools["enabled_count"] > 0,
    )
    sessions = _session_summary(request)
    attention_items = _attention_items(providers, queue, history, tools, workspace, sessions)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "providers": providers,
        "queue": queue,
        "history": history,
        "tools": tools,
        "workspace": workspace,
        "sessions": sessions,
        "attention_items": attention_items,
        "recommended_commands": _recommended_commands(attention_items),
    }
