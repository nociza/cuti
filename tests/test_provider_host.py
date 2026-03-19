"""Tests for host-side provider setup and update workflows."""

from __future__ import annotations

from pathlib import Path

from cuti.services.claude_account_manager import ClaudeAccountManager
from cuti.services.provider_host import ProviderHostService


def test_claude_status_reports_ready_when_active_account_exists(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    storage_dir = tmp_path / ".cuti"
    manager = ClaudeAccountManager(storage_dir=str(storage_dir))
    creds_path = storage_dir / "claude-linux" / ".credentials.json"
    creds_path.write_text('{"claudeAiOauth": {"accessToken": "token"}}')
    manager.save_account("main")
    manager.use_account("main")

    service = ProviderHostService(provider_storage_dir=storage_dir)
    status = service.get_status("claude")

    assert status.setup_state == "ready"
    assert "main" in status.detail


def test_codex_status_uses_auth_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".codex").mkdir(parents=True)
    (tmp_path / ".codex" / "auth.json").write_text('{"session": "ok"}')

    service = ProviderHostService(provider_storage_dir=tmp_path / ".cuti")
    status = service.get_status("codex")

    assert status.setup_state == "ready"
    assert "auth" in status.detail.lower()


def test_run_setup_enables_provider_and_invokes_container(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    calls: list[dict[str, object]] = []

    class _FakeDevContainerService:
        def __init__(self, working_directory=None, provider_storage_dir=None):
            calls.append(
                {
                    "working_directory": working_directory,
                    "provider_storage_dir": provider_storage_dir,
                }
            )

        def run_in_container(self, command=None, rebuild=False, interactive=False, **kwargs):
            calls.append(
                {
                    "command": command,
                    "rebuild": rebuild,
                    "interactive": interactive,
                }
            )
            return 0

    monkeypatch.setattr("cuti.services.provider_host.DevContainerService", _FakeDevContainerService)

    service = ProviderHostService(str(tmp_path), provider_storage_dir=tmp_path / ".cuti")
    assert service.provider_manager.is_enabled("codex") is False

    exit_code = service.run_setup("codex", rebuild=True)

    assert exit_code == 0
    assert service.provider_manager.is_enabled("codex") is True
    assert calls[-1]["command"] == "codex"
    assert calls[-1]["interactive"] is True
    assert calls[-1]["rebuild"] is True


def test_run_update_uses_provider_installer(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    calls: list[dict[str, object]] = []

    class _FakeDevContainerService:
        def __init__(self, working_directory=None, provider_storage_dir=None):
            pass

        def run_in_container(self, command=None, rebuild=False, interactive=False, **kwargs):
            calls.append(
                {
                    "command": command,
                    "rebuild": rebuild,
                    "interactive": interactive,
                }
            )
            return 0

    monkeypatch.setattr("cuti.services.provider_host.DevContainerService", _FakeDevContainerService)

    service = ProviderHostService(provider_storage_dir=tmp_path / ".cuti")
    exit_code = service.run_update("claude", rebuild=False)

    assert exit_code == 0
    assert calls == [
        {
            "command": "/usr/local/bin/cuti-install-claude",
            "rebuild": False,
            "interactive": False,
        }
    ]
