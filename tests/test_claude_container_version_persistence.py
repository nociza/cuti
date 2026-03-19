"""Tests for provider wiring in dev containers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cuti.services.devcontainer import DevContainerService


class _RunResult:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


def test_generate_dockerfile_uses_provider_installers(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    dockerfile = service._generate_dockerfile("general")

    assert "curl -fsSL https://claude.ai/install.sh | bash -s --" in dockerfile
    assert "https://github.com/openai/codex/releases/latest/download/install.sh" in dockerfile
    assert "curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path" in dockerfile
    assert "npm-original install -g openclaw@latest" in dockerfile
    assert 'OPENCODE_CLI="/home/cuti/.opencode/bin/opencode"' in dockerfile
    assert "@anthropic-ai/claude-code" not in dockerfile


def test_prepare_cloud_provider_mounts_includes_selected_provider_dirs(monkeypatch, tmp_path: Path) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.provider_manager.set_enabled("codex", True)
    service.provider_manager.set_enabled("opencode", True)
    service.provider_manager.set_enabled("openclaw", True)
    service._selected_providers_cache = None

    monkeypatch.setattr(service, "_setup_claude_host_config", lambda: tmp_path / "claude-linux")
    monkeypatch.setattr(service, "_prepare_agents_storage", lambda: tmp_path / ".agents")
    monkeypatch.setattr(service, "_prepare_codex_storage", lambda: tmp_path / ".codex")
    monkeypatch.setattr(
        service,
        "_prepare_opencode_storage",
        lambda: (tmp_path / ".opencode", tmp_path / ".config" / "opencode", tmp_path / ".local" / "share" / "opencode"),
    )
    monkeypatch.setattr(service, "_prepare_openclaw_storage", lambda: tmp_path / ".openclaw")

    linux_claude_dir, mount_args = service._prepare_cloud_provider_mounts()

    assert linux_claude_dir == tmp_path / "claude-linux"
    assert f"{tmp_path / '.codex'}:/home/cuti/.codex:rw" in mount_args
    assert f"{tmp_path / '.opencode'}:/home/cuti/.opencode:rw" in mount_args
    assert f"{tmp_path / '.config' / 'opencode'}:/home/cuti/.config/opencode:rw" in mount_args
    assert f"{tmp_path / '.local' / 'share' / 'opencode'}:/home/cuti/.local/share/opencode:rw" in mount_args
    assert f"{tmp_path / '.openclaw'}:/home/cuti/.openclaw:rw" in mount_args
    assert f"{tmp_path / '.agents'}:/home/cuti/.agents:rw" in mount_args


def test_run_in_container_sets_provider_envs(monkeypatch, tmp_path: Path) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    service.provider_manager.set_enabled("codex", True)
    service.provider_manager.set_enabled("opencode", True)
    service._selected_providers_cache = None

    captured_args = {}

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(service, "_build_container_image", lambda image_name, rebuild: True)
    monkeypatch.setattr(service, "_prepare_cloud_provider_mounts", lambda: (tmp_path / "claude-linux", []))

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr("cuti.services.devcontainer.subprocess.run", _fake_subprocess_run)

    exit_code = service.run_in_container(command="echo ok", rebuild=False)

    assert exit_code == 0
    docker_args = captured_args["args"]
    assert "CUTI_AGENT_PROVIDERS=claude,codex,opencode" in docker_args
    assert "CUTI_PRIMARY_AGENT_PROVIDER=claude" in docker_args
    assert any(arg.startswith("PATH=/home/cuti/.opencode/bin:/home/cuti/.local/bin:") for arg in docker_args)


def test_run_in_container_init_script_handles_runtime_provider_installs(monkeypatch, tmp_path: Path) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    service.provider_manager.set_enabled("codex", True)
    service.provider_manager.set_enabled("opencode", True)
    service.provider_manager.set_enabled("openclaw", True)
    service._selected_providers_cache = None

    captured_args = {}

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(service, "_build_container_image", lambda image_name, rebuild: True)
    monkeypatch.setattr(service, "_prepare_cloud_provider_mounts", lambda: (tmp_path / "claude-linux", []))

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr("cuti.services.devcontainer.subprocess.run", _fake_subprocess_run)

    exit_code = service.run_in_container(command="codex --version && opencode --version && openclaw --version", rebuild=False)

    assert exit_code == 0
    full_command = captured_args["args"][-1]
    assert 'export PATH="/home/cuti/.opencode/bin:/home/cuti/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"' in full_command
    assert "cuti_provider_selected codex" in full_command
    assert "cuti_provider_selected opencode" in full_command
    assert "cuti_provider_selected openclaw" in full_command
    assert "hash -r 2>/dev/null || true" in full_command


def test_build_container_image_places_no_cache_before_context(monkeypatch, tmp_path: Path) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    commands: list[list[str]] = []

    monkeypatch.setattr(service, "_generate_dockerfile", lambda project_type: "FROM python:3.11-bullseye\n")

    def _fake_run_command(cmd, timeout=30, show_output=False):
        commands.append(cmd)
        if cmd[:2] == ["docker", "images"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(service, "_run_command", _fake_run_command)

    assert service._build_container_image("cuti-test-image", rebuild=True) is True

    build_cmd = next(cmd for cmd in commands if cmd[:2] == ["docker", "build"])
    assert build_cmd[-2] == "--no-cache"
