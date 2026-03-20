from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from cuti.core.models import QueueState, QueuedPrompt
from cuti.web.api.ops import router as ops_router
from cuti.web.routes import main_router


class _QueueManagerStub:
    def __init__(self, state: QueueState):
        self._state = state

    def get_status(self) -> QueueState:
        return self._state


class _HistoryManagerStub:
    def get_history(self, limit: int = 8):
        return [
            {
                "content": "Audit provider readiness",
                "working_directory": "/workspace",
                "timestamp": datetime(2025, 3, 14, 12, 0, 0),
                "success": True,
                "context_files": ["README.md"],
                "output_preview": None,
            }
        ]

    def get_history_stats(self):
        return {
            "total_prompts": 3,
            "successful_prompts": 2,
            "failed_prompts": 1,
            "success_rate": 2 / 3,
            "latest_prompt": "2025-03-14T12:00:00",
        }


class _ClaudeLogsReaderStub:
    project_name = "workspace"

    def get_current_session_id(self):
        return "session-1234567890"

    def get_all_sessions(self):
        return [
            {
                "session_id": "session-1234567890",
                "start_time": "2025-03-14T11:00:00",
                "last_activity": "2025-03-14T12:00:00",
                "prompt_count": 4,
                "file_size": 128,
            }
        ]

    def get_statistics(self, session_id=None):
        return {
            "session_id": session_id or "session-1234567890",
            "total_prompts": 4,
            "total_responses": 4,
            "total_tokens": 1200,
            "todos_count": 0,
            "todos_completed": 0,
            "todos_pending": 0,
            "todos_in_progress": 0,
        }


def _build_app(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("cuti.web.api.ops.check_tool_installed", lambda _cmd: False)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "CLAUDE.md").write_text("# Claude\n")

    app = FastAPI()
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "src" / "cuti" / "web" / "static")),
        name="static",
    )
    app.state.templates = Jinja2Templates(
        directory=str(Path(__file__).resolve().parents[1] / "src" / "cuti" / "web" / "templates")
    )
    app.state.working_directory = workspace
    app.state.storage_dir = tmp_path / ".cuti-workspace"
    app.state.queue_warning = None
    app.state.queue_manager = _QueueManagerStub(
        QueueState(prompts=[QueuedPrompt(content="Ship the ops console", working_directory=str(workspace), priority=1)])
    )
    app.state.history_manager = _HistoryManagerStub()
    app.state.claude_logs_reader = _ClaudeLogsReaderStub()

    app.include_router(ops_router)
    app.include_router(main_router)
    return TestClient(app)


def test_ops_summary_exposes_attention_history_and_workspace_drift(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/api/ops/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers"]["primary_provider"] == "claude"
    assert payload["queue"]["total_prompts"] == 1
    assert payload["history"]["stats"]["total_prompts"] == 3
    assert payload["sessions"]["current_session_id"] == "session-1234567890"
    assert payload["workspace"]["instruction_files"][0]["name"] == "CLAUDE.md"
    assert "cuti providers doctor" in payload["recommended_commands"]
    assert payload["attention_items"]


def test_ops_route_renders_workspace_ops_console(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "Workspace Ops Console" in response.text
    assert "Action queue" in response.text
    assert "Suggested commands" in response.text


def test_legacy_routes_redirect_to_root(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/tasks", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/"
