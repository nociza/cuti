from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from cuti.core.models import QueueState, QueuedPrompt
from cuti.web.api.dashboard import router as dashboard_router
from cuti.web.api.providers import router as providers_router
from cuti.web.routes import main_router


class _QueueManagerStub:
    def __init__(self, state: QueueState):
        self._state = state

    def get_status(self) -> QueueState:
        return self._state


class _AgentStub:
    def __init__(self, name: str, *, is_local: bool, is_builtin: bool, agent_type: str = "claude"):
        self.name = name
        self.is_local = is_local
        self.is_builtin = is_builtin
        self.agent_type = agent_type

    def to_dict(self):
        return {
            "name": self.name,
            "description": f"Agent {self.name}",
            "capabilities": ["testing"],
            "tools": ["bash"],
            "is_local": self.is_local,
            "is_builtin": self.is_builtin,
            "agent_type": self.agent_type,
        }


class _AgentManagerStub:
    gemini_available = False

    def reload_agents(self) -> None:
        return None

    def list_agents(self):
        return [
            _AgentStub("reviewer", is_local=True, is_builtin=False),
            _AgentStub("planner", is_local=False, is_builtin=True),
        ]


class _OrchestrationStub:
    def __init__(self, claude_md_path: Path):
        self.claude_md_path = claude_md_path


def _build_app(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("cuti.web.api.dashboard.check_tool_installed", lambda _cmd: False)

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
    app.state.storage_dir = str(tmp_path / ".cuti-workspace")
    app.state.queue_running = True
    app.state.queue_manager = _QueueManagerStub(
        QueueState(prompts=[QueuedPrompt(content="Ship the redesign", working_directory=str(workspace), priority=1)])
    )
    app.state.claude_code_agent_manager = _AgentManagerStub()
    app.state.orchestration_manager = _OrchestrationStub(workspace / "CLAUDE.md")

    app.include_router(dashboard_router)
    app.include_router(providers_router)
    app.include_router(main_router)
    return TestClient(app)


def test_dashboard_summary_exposes_provider_queue_and_workspace_data(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers"]["primary_provider"] == "claude"
    assert payload["queue"]["total_prompts"] == 1
    assert payload["workspace"]["instruction_files"][0]["name"] == "CLAUDE.md"
    assert payload["agents"]["total_agents"] == 2


def test_provider_selection_api_updates_enabled_state(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.put("/api/providers/codex/selection", json={"enabled": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert "codex" in payload["selected_providers"]

    listing = client.get("/api/providers")
    assert listing.status_code == 200
    assert "codex" in listing.json()["selected_providers"]


def test_dashboard_route_renders_new_control_room(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "Workspace Control Room" in response.text
    assert "Queue a prompt" in response.text


def test_legacy_todos_route_redirects_to_tasks(tmp_path: Path, monkeypatch) -> None:
    client = _build_app(tmp_path, monkeypatch)

    response = client.get("/todos", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/tasks"
