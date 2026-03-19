"""Summary endpoints for the redesigned cuti dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Request

from ...core.models import PromptStatus
from ...services.provider_host import ProviderHostService
from ...services.providers import ProviderManager
from ...services.todo_service import TodoService
from .tools import AVAILABLE_TOOLS, check_tool_installed, load_tools_config

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _serialize_prompt(prompt: Any) -> Dict[str, Any]:
    return {
        "id": prompt.id,
        "content": prompt.content,
        "status": prompt.status.value,
        "priority": prompt.priority,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "working_directory": prompt.working_directory,
    }


def _queue_summary(request: Request) -> Dict[str, Any]:
    queue_manager = request.app.state.queue_manager
    if not queue_manager:
        return {
            "available": False,
            "queue_running": False,
            "total_prompts": 0,
            "status_counts": {status.value: 0 for status in PromptStatus},
            "recent_prompts": [],
            "detail": "Queue manager unavailable because the primary CLI could not be initialized.",
        }

    state = queue_manager.get_status()
    stats = state.get_stats()
    prompts = sorted(state.prompts, key=lambda item: item.created_at, reverse=True)
    return {
        "available": True,
        "queue_running": bool(getattr(request.app.state, "queue_running", False)),
        "total_prompts": stats.get("total_prompts", 0),
        "status_counts": stats.get("status_counts", {}),
        "total_processed": stats.get("total_processed", 0),
        "failed_count": stats.get("failed_count", 0),
        "rate_limited_count": stats.get("rate_limited_count", 0),
        "last_processed": stats.get("last_processed"),
        "recent_prompts": [_serialize_prompt(prompt) for prompt in prompts[:6]],
        "detail": "Queue processor is active." if getattr(request.app.state, "queue_running", False) else "Queue processor is initialized but not currently running.",
    }


def _todo_summary(request: Request) -> Dict[str, Any]:
    todo_service = TodoService(str(request.app.state.storage_dir))
    master_list = todo_service.get_master_list()
    if not master_list:
        return {
            "available": True,
            "statistics": {
                "total": 0,
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "blocked": 0,
                "cancelled": 0,
                "completion_percentage": 0,
            },
            "top_items": [],
        }

    status_rank = {
        "in_progress": 0,
        "pending": 1,
        "blocked": 2,
        "completed": 3,
        "cancelled": 4,
    }
    top_items = sorted(
        (todo.to_dict() for todo in master_list.todos),
        key=lambda item: (
            status_rank.get(item.get("status", "pending"), 9),
            -int(item.get("priority", 0)),
            item.get("updated_at") or "",
        ),
    )
    return {
        "available": True,
        "statistics": master_list.get_progress(),
        "top_items": top_items[:8],
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
        "missing_enabled": missing_enabled[:5],
    }


def _agents_summary(request: Request) -> Dict[str, Any]:
    manager = request.app.state.claude_code_agent_manager
    manager.reload_agents()
    agents = [agent.to_dict() for agent in manager.list_agents()]
    local_agents = [agent for agent in agents if agent.get("is_local")]
    builtin_agents = [agent for agent in agents if agent.get("is_builtin")]

    orchestration = request.app.state.orchestration_manager
    claude_md_path = getattr(orchestration, "claude_md_path", Path(request.app.state.working_directory) / "CLAUDE.md")

    return {
        "total_agents": len(agents),
        "local_agents": len(local_agents),
        "builtin_agents": len(builtin_agents),
        "gemini_available": bool(manager.gemini_available),
        "sample_agents": agents[:8],
        "claude_md_path": str(claude_md_path),
        "claude_md_exists": Path(claude_md_path).exists(),
    }


def _provider_summary(request: Request) -> Dict[str, Any]:
    service = ProviderHostService(working_directory=str(request.app.state.working_directory))
    manager = service.provider_manager
    statuses = [status.to_dict() for status in service.list_statuses()]
    return {
        "primary_provider": manager.primary_provider(),
        "selected_providers": manager.selected_providers(),
        "items": statuses,
    }


def _workspace_summary(request: Request) -> Dict[str, Any]:
    working_directory = Path(request.app.state.working_directory)
    instruction_files = [
        {
            "name": name,
            "exists": (working_directory / name).exists(),
            "path": str(working_directory / name),
        }
        for name in ("CLAUDE.md", "AGENTS.md", "SOUL.md", "TOOLS.md", "GOAL.md")
    ]
    provider_manager = ProviderManager()
    return {
        "name": working_directory.name,
        "path": str(working_directory),
        "storage_dir": str(request.app.state.storage_dir),
        "selected_instruction_files": provider_manager.provider_instruction_files(),
        "instruction_files": instruction_files,
    }


@router.get("/summary")
async def dashboard_summary(request: Request) -> Dict[str, Any]:
    """Return the control-room summary used by the redesigned web UI."""

    providers = _provider_summary(request)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": _workspace_summary(request),
        "providers": providers,
        "queue": _queue_summary(request),
        "todos": _todo_summary(request),
        "tools": _tools_summary(),
        "agents": _agents_summary(request),
        "quickstart": {
            "container": "cuti container",
            "providers": [
                f"cuti providers auth {provider} --login"
                for provider in providers["selected_providers"]
            ],
            "refresh": [
                f"cuti providers update {provider}"
                for provider in providers["selected_providers"]
            ],
        },
    }
