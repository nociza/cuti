"""Tests for persistent Claude CLI wiring in dev containers."""

from __future__ import annotations

from pathlib import Path

from cuti.services.devcontainer import DevContainerService


class _RunResult:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


def test_generate_dockerfile_prefers_shared_claude_install(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path)
    dockerfile = service._generate_dockerfile("general")

    assert "/home/cuti/.cuti/claude-cli/lib/node_modules/@anthropic-ai/claude-code/cli.js" in dockerfile
    assert 'echo "Claude CLI not found. Run: cuti claude update" >&2' in dockerfile


def test_run_in_container_sets_shared_claude_bin_first_in_path(monkeypatch, tmp_path: Path) -> None:
    service = DevContainerService(tmp_path)
    service.is_macos = False

    captured_args = {}

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(service, "_build_container_image", lambda image_name, rebuild: True)
    monkeypatch.setattr(service, "_setup_claude_host_config", lambda: tmp_path / "claude-linux")
    monkeypatch.setattr(service, "_is_clawdbot_enabled", lambda: False)

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr("cuti.services.devcontainer.subprocess.run", _fake_subprocess_run)

    exit_code = service.run_in_container(command="echo ok", rebuild=False)

    assert exit_code == 0
    docker_args = captured_args["args"]
    assert "--env" in docker_args
    assert any(
        arg.startswith(
            "PATH=/home/cuti/.cuti/claude-cli/bin:/home/cuti/.local/bin:/usr/local/bin:"
        )
        for arg in docker_args
    )
