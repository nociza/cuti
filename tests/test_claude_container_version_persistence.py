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
    assert f"{tmp_path / '.cuti' / 'provider-runtimes'}:/home/cuti/.cuti-providers:rw" in mount_args
    assert f"{tmp_path / '.codex'}:/home/cuti/.codex:rw" in mount_args
    assert f"{tmp_path / '.opencode'}:/home/cuti/.opencode:rw" in mount_args
    assert f"{tmp_path / '.config' / 'opencode'}:/home/cuti/.config/opencode:rw" in mount_args
    assert f"{tmp_path / '.local' / 'share' / 'opencode'}:/home/cuti/.local/share/opencode:rw" in mount_args
    assert f"{tmp_path / '.openclaw'}:/home/cuti/.openclaw:rw" in mount_args
    assert f"{tmp_path / '.agents'}:/home/cuti/.agents:rw" in mount_args


def test_provider_runtime_permissions_keep_version_binaries_executable(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "provider-runtimes"
    version_binary = runtime_dir / "claude" / ".local" / "share" / "claude" / "versions" / "2.1.112"
    data_file = runtime_dir / "claude" / ".cache" / "claude" / "metadata.json"
    version_binary.parent.mkdir(parents=True)
    data_file.parent.mkdir(parents=True)
    version_binary.write_text("binary")
    data_file.write_text("{}")

    DevContainerService._make_tree_container_writable(runtime_dir)

    assert version_binary.stat().st_mode & 0o111
    assert not data_file.stat().st_mode & 0o111


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
    assert "CODEX_INSTALL_DIR=/home/cuti/.cuti-providers/codex/bin" in docker_args
    assert any(arg.startswith("PATH=/home/cuti/.cuti-providers/claude/.local/bin:/home/cuti/.cuti-providers/codex/bin:") for arg in docker_args)


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
    assert 'export PATH="/home/cuti/.cuti-providers/claude/.local/bin:/home/cuti/.cuti-providers/codex/bin:/home/cuti/.opencode/bin:/home/cuti/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"' in full_command
    assert "ensure_provider_runtime_shell_path" in full_command
    assert "cuti-provider-runtime-path" in full_command
    assert "cuti_provider_selected codex" in full_command
    assert "cuti_provider_selected opencode" in full_command
    assert "cuti_provider_selected openclaw" in full_command
    assert "hash -r 2>/dev/null || true" in full_command


def test_run_provider_update_updates_persistent_runtime_and_active_containers(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    commands: list[list[str]] = []

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(service, "_build_container_image", lambda image_name, rebuild: True)

    def _fake_run_command(cmd, timeout=30, show_output=False):
        commands.append(cmd)
        if cmd[:2] == ["docker", "ps"] and f"label=cuti.runtime_profile={service.RUNTIME_PROFILE_CLOUD}" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")
        if cmd[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(service, "_run_command", _fake_run_command)

    exit_code = service.run_provider_update("claude", "/usr/local/bin/cuti-install-claude")

    assert exit_code == 0
    docker_run = next(cmd for cmd in commands if cmd[:2] == ["docker", "run"])
    assert f"{tmp_path / '.cuti' / 'provider-runtimes'}:/home/cuti/.cuti-providers:rw" in docker_run
    assert docker_run[-4:] == [
        service.IMAGE_NAME,
        "/usr/bin/zsh",
        "-lc",
        docker_run[-1],
    ]
    assert "export HOME=/home/cuti/.cuti-providers/claude" in docker_run[-1]
    assert "export XDG_DATA_HOME=/home/cuti/.cuti-providers/claude/.local/share" in docker_run[-1]
    assert "export XDG_STATE_HOME=/home/cuti/.cuti-providers/claude/.local/state" in docker_run[-1]
    assert "export XDG_CACHE_HOME=/home/cuti/.cuti-providers/claude/.cache" in docker_run[-1]
    assert "/usr/local/bin/cuti-install-claude" in docker_run[-1]
    assert "curl -fsSL https://claude.ai/install.sh | bash" in docker_run[-1]

    docker_exec = next(cmd for cmd in commands if cmd[:2] == ["docker", "exec"])
    assert docker_exec[2] == "abc123"
    assert "export HOME=/home/cuti" in docker_exec[-1]
    assert "export HOME=/home/cuti/.cuti-providers/claude" not in docker_exec[-1]
    assert "curl -fsSL https://claude.ai/install.sh | bash" in docker_exec[-1]


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
