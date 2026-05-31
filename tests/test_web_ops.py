from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from cuti.web.api.ops import router as ops_router
from cuti.web.routes import main_router


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
        StaticFiles(
            directory=str(
                Path(__file__).resolve().parents[1] / "src" / "cuti" / "web" / "static"
            )
        ),
        name="static",
    )
    app.state.templates = Jinja2Templates(
        directory=str(
            Path(__file__).resolve().parents[1] / "src" / "cuti" / "web" / "templates"
        )
    )
    app.state.working_directory = workspace
    app.state.storage_dir = tmp_path / ".cuti-workspace"
    app.state.claude_logs_reader = _ClaudeLogsReaderStub()

    app.include_router(ops_router)
    app.include_router(main_router)
    return TestClient(app)


def test_ops_summary_exposes_providers_sessions_and_workspace_drift(
    tmp_path: Path, monkeypatch
) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/api/ops/summary")

    assert response.status_code == 200
    payload = response.json()
    # Obsolete queue/prompt-history surfaces must not reappear.
    assert "queue" not in payload
    assert "history" not in payload
    assert payload["providers"]["primary_provider"] == "claude"
    assert payload["sessions"]["current_session_id"] == "session-1234567890"
    assert payload["workspace"]["instruction_files"][0]["name"] == "CLAUDE.md"
    assert "cuti providers doctor" in payload["recommended_commands"]
    assert payload["attention_items"]


def test_ops_route_renders_workspace_ops_console(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "Workspace Ops Console" in response.text
    # "Action queue" is the attention-list header, not the removed prompt queue.
    assert "Action queue" in response.text
    assert "Suggested commands" in response.text
