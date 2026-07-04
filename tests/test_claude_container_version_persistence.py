"""Tests for provider wiring in dev containers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cuti.services.devcontainer import (
    DevContainerService,
    get_claude_command,
    get_claude_permission_mode,
)


class _RunResult:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


def test_generate_dockerfile_uses_provider_installers(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    dockerfile = service._generate_dockerfile("general")

    assert "curl -fsSL https://claude.ai/install.sh | bash -s --" in dockerfile
    assert (
        "https://github.com/openai/codex/releases/latest/download/install.sh"
        in dockerfile
    )
    assert (
        "curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path"
        in dockerfile
    )
    assert "https://openclaw.ai/install-cli.sh" in dockerfile
    assert (
        "npm-original install -g --prefix \"$OPENCLAW_PREFIX\" openclaw@latest"
        in dockerfile
    )
    assert 'export npm_config_prefix="$OPENCLAW_PREFIX"' in dockerfile
    assert (
        "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh"
        in dockerfile
    )
    assert "/usr/local/bin/cuti-update-hermes" in dockerfile
    assert 'OPENCODE_CLI="/home/cuti/.opencode/bin/opencode"' in dockerfile
    assert (
        'HERMES_CLI="${HERMES_CLI:-$HERMES_HOME/hermes-agent/venv/bin/hermes}"'
        in dockerfile
    )
    assert "Claude provider is not selected for this container mode" in dockerfile
    assert 'CUTI_CLAUDE_PERMISSION_MODE="${CUTI_CLAUDE_PERMISSION_MODE:-auto}"' in dockerfile
    assert '--permission-mode "$CUTI_CLAUDE_PERMISSION_MODE"' in dockerfile
    assert 'alias claude="claude --dangerously-skip-permissions"' not in dockerfile
    assert "RUN HOME=/home/cuti /usr/local/bin/cuti-install-claude" not in dockerfile
    assert "@anthropic-ai/claude-code" not in dockerfile


def test_claude_permission_mode_defaults_to_auto(monkeypatch) -> None:
    monkeypatch.delenv("CUTI_CLAUDE_PERMISSION_MODE", raising=False)

    assert get_claude_permission_mode() == "auto"


def test_claude_permission_mode_normalizes_legacy_alias(monkeypatch) -> None:
    monkeypatch.setenv("CUTI_CLAUDE_PERMISSION_MODE", "bypass")

    assert get_claude_permission_mode() == "bypassPermissions"


def test_prepare_cloud_provider_mounts_includes_selected_provider_dirs(
    monkeypatch, tmp_path: Path
) -> None:
    service = DevContainerService(
        tmp_path,
        provider_storage_dir=tmp_path / ".cuti",
        container_mode=DevContainerService.CONTAINER_MODE_OPENCLAW,
    )
    service.provider_manager.set_enabled("claude", True)
    service.provider_manager.set_enabled("codex", True)
    service.provider_manager.set_enabled("opencode", True)
    service.provider_manager.set_enabled("openclaw", True)
    service.provider_manager.set_enabled("hermes", True)
    service._selected_providers_cache = None

    monkeypatch.setattr(
        service, "_setup_claude_host_config", lambda: tmp_path / "claude-linux"
    )
    monkeypatch.setattr(
        service, "_prepare_agents_storage", lambda: tmp_path / ".agents"
    )
    monkeypatch.setattr(service, "_prepare_codex_storage", lambda: tmp_path / ".codex")
    monkeypatch.setattr(
        service,
        "_prepare_opencode_storage",
        lambda: (
            tmp_path / ".opencode",
            tmp_path / ".config" / "opencode",
            tmp_path / ".local" / "share" / "opencode",
        ),
    )
    monkeypatch.setattr(
        service, "_prepare_openclaw_storage", lambda: tmp_path / ".openclaw"
    )
    monkeypatch.setattr(
        service, "_prepare_hermes_storage", lambda: tmp_path / ".hermes"
    )

    linux_claude_dir, mount_args = service._prepare_cloud_provider_mounts()

    assert linux_claude_dir == tmp_path / "claude-linux"
    assert (
        f"{tmp_path / '.cuti' / 'provider-runtimes'}:/home/cuti/.cuti-providers:rw"
        in mount_args
    )
    assert f"{tmp_path / '.codex'}:/home/cuti/.codex:rw" in mount_args
    assert f"{tmp_path / '.opencode'}:/home/cuti/.opencode:rw" in mount_args
    assert (
        f"{tmp_path / '.config' / 'opencode'}:/home/cuti/.config/opencode:rw"
        in mount_args
    )
    assert (
        f"{tmp_path / '.local' / 'share' / 'opencode'}:/home/cuti/.local/share/opencode:rw"
        in mount_args
    )
    assert f"{tmp_path / '.openclaw'}:/home/cuti/.openclaw:rw" in mount_args
    assert f"{tmp_path / '.hermes'}:/home/cuti/.hermes:rw" in mount_args
    assert f"{tmp_path / '.agents'}:/home/cuti/.agents:rw" in mount_args


def test_provider_runtime_permissions_keep_version_binaries_executable(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "provider-runtimes"
    version_binary = (
        runtime_dir / "claude" / ".local" / "share" / "claude" / "versions" / "2.1.112"
    )
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
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )
    monkeypatch.setattr(
        service,
        "_prepare_cloud_provider_mounts",
        lambda: (tmp_path / "claude-linux", []),
    )

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr(
        "cuti.services.devcontainer.subprocess.run", _fake_subprocess_run
    )

    exit_code = service.run_in_container(command="echo ok", rebuild=False)

    assert exit_code == 0
    docker_args = captured_args["args"]
    assert "CUTI_AGENT_PROVIDERS=claude,codex,opencode" in docker_args
    assert "CUTI_PRIMARY_AGENT_PROVIDER=claude" in docker_args
    assert "CUTI_CONTAINER_MODE=claude-code" in docker_args
    assert "CUTI_CLAUDE_AUTO_UPDATE=true" in docker_args
    assert "CUTI_CLAUDE_PERMISSION_MODE=auto" in docker_args
    assert "CLAUDE_CODE_ENABLE_AUTO_MODE=1" in docker_args
    assert "CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true" not in docker_args
    assert "CUTI_ENFORCE_SELECTED_PROVIDERS=true" in docker_args
    assert "CODEX_INSTALL_DIR=/home/cuti/.cuti-providers/codex/bin" in docker_args
    assert "OPENCLAW_PREFIX=/home/cuti/.cuti-providers/openclaw" in docker_args
    assert "NPM_CONFIG_PREFIX=/home/cuti/.cuti-providers/openclaw" in docker_args
    assert "npm_config_prefix=/home/cuti/.cuti-providers/openclaw" in docker_args
    assert any(
        arg.startswith(
            "PATH=/home/cuti/.cuti-providers/claude/.local/bin:/home/cuti/.cuti-providers/codex/bin:/home/cuti/.opencode/bin:"
        )
        for arg in docker_args
    )
    assert any(
        arg.startswith(
            "CUTI_CONTAINER_PATH=/home/cuti/.cuti-providers/claude/.local/bin:/home/cuti/.cuti-providers/codex/bin:/home/cuti/.opencode/bin:"
        )
        for arg in docker_args
    )
    assert "HERMES_HOME=/home/cuti/.hermes" in docker_args


def test_run_in_container_allows_claude_permission_override(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CUTI_CLAUDE_PERMISSION_MODE", "accept-edits")
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    captured_args = {}

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )
    monkeypatch.setattr(
        service,
        "_prepare_cloud_provider_mounts",
        lambda: (tmp_path / "claude-linux", []),
    )

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr(
        "cuti.services.devcontainer.subprocess.run", _fake_subprocess_run
    )

    exit_code = service.run_in_container(command="echo ok", rebuild=False)

    assert exit_code == 0
    docker_args = captured_args["args"]
    assert "CUTI_CLAUDE_PERMISSION_MODE=acceptEdits" in docker_args
    assert "CLAUDE_CODE_ENABLE_AUTO_MODE=1" not in docker_args


def test_get_claude_command_uses_configured_permission_mode(monkeypatch) -> None:
    monkeypatch.setenv("CUTI_IN_CONTAINER", "true")
    monkeypatch.setenv("CUTI_CLAUDE_PERMISSION_MODE", "plan")

    assert get_claude_command("inspect") == [
        "claude",
        "--permission-mode",
        "plan",
        "inspect",
    ]


def test_run_in_container_init_script_handles_runtime_provider_installs(
    monkeypatch, tmp_path: Path
) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    service.provider_manager.set_enabled("codex", True)
    service.provider_manager.set_enabled("opencode", True)
    service.provider_manager.set_enabled("openclaw", True)
    service.provider_manager.set_enabled("hermes", True)
    service._selected_providers_cache = None

    captured_args = {}

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )
    monkeypatch.setattr(
        service,
        "_prepare_cloud_provider_mounts",
        lambda: (tmp_path / "claude-linux", []),
    )

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr(
        "cuti.services.devcontainer.subprocess.run", _fake_subprocess_run
    )

    exit_code = service.run_in_container(
        command="codex --version && opencode --version && openclaw --version && hermes version",
        rebuild=False,
    )

    assert exit_code == 0
    full_command = captured_args["args"][-1]
    assert "Updating Claude Code in persistent provider runtime" in full_command
    assert "export HOME=/home/cuti/.cuti-providers/claude" in full_command
    assert "Claude Code is up to date for subsequent containers" in full_command
    assert 'export PATH="${CUTI_CONTAINER_PATH}:$PATH"' in full_command
    assert "ensure_provider_runtime_shell_path" in full_command
    assert "cuti-provider-runtime-path" in full_command
    assert "cuti_provider_selected codex" in full_command
    assert "cuti_provider_selected opencode" in full_command
    assert "cuti_provider_selected openclaw" in full_command
    assert "OPENCLAW_PREFIX=/home/cuti/.cuti-providers/openclaw" in full_command
    assert 'export npm_config_prefix="$OPENCLAW_PREFIX"' in full_command
    assert "openclaw doctor --non-interactive" in full_command
    assert "cuti_provider_selected hermes" in full_command
    assert "cuti-install-hermes" in full_command
    assert "cuti_restore_hermes_profile_wrappers" in full_command
    assert 'exec hermes -p $PROFILE_NAME "\\$@"' in full_command
    assert "hash -r 2>/dev/null || true" in full_command


def test_openclaw_container_mode_uses_flagged_mode_and_explicit_addons(
    monkeypatch, tmp_path: Path
) -> None:
    service = DevContainerService(
        tmp_path,
        provider_storage_dir=tmp_path / ".cuti",
        container_mode=DevContainerService.CONTAINER_MODE_OPENCLAW,
    )
    service.is_macos = False
    service.provider_manager.set_enabled("codex", True)
    service.provider_manager.set_enabled("claude", True)
    service._selected_providers_cache = None

    captured_args = {}

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )
    monkeypatch.setattr(
        service,
        "_prepare_cloud_provider_mounts",
        lambda: (tmp_path / "claude-linux", []),
    )

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr(
        "cuti.services.devcontainer.subprocess.run", _fake_subprocess_run
    )

    exit_code = service.run_in_container(command="openclaw --version", rebuild=False)

    assert exit_code == 0
    docker_args = captured_args["args"]
    assert "CUTI_CONTAINER_MODE=openclaw" in docker_args
    assert "CUTI_AGENT_PROVIDERS=openclaw,claude,codex" in docker_args
    assert "CUTI_PRIMARY_AGENT_PROVIDER=openclaw" in docker_args
    assert "CUTI_CLAUDE_AUTO_UPDATE=false" in docker_args
    assert "CUTI_ENFORCE_SELECTED_PROVIDERS=true" in docker_args
    assert "cuti.container_mode=openclaw" in docker_args
    assert any(
        arg.startswith(
            "CUTI_CONTAINER_PATH=/home/cuti/.cuti-providers/claude/.local/bin:/home/cuti/.cuti-providers/codex/bin:/home/cuti/.cuti-providers/openclaw/bin:"
        )
        for arg in docker_args
    )


def test_openclaw_container_mode_does_not_expose_default_claude_path(
    monkeypatch, tmp_path: Path
) -> None:
    service = DevContainerService(
        tmp_path,
        provider_storage_dir=tmp_path / ".cuti",
        container_mode=DevContainerService.CONTAINER_MODE_OPENCLAW,
    )
    service.is_macos = False
    captured_args = {}

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )
    monkeypatch.setattr(
        service,
        "_prepare_cloud_provider_mounts",
        lambda: (None, []),
    )

    def _fake_subprocess_run(args):
        captured_args["args"] = args
        return _RunResult(0)

    monkeypatch.setattr(
        "cuti.services.devcontainer.subprocess.run", _fake_subprocess_run
    )

    exit_code = service.run_in_container(command="openclaw --version", rebuild=False)

    assert exit_code == 0
    docker_args = captured_args["args"]
    container_path = next(
        arg.removeprefix("CUTI_CONTAINER_PATH=")
        for arg in docker_args
        if arg.startswith("CUTI_CONTAINER_PATH=")
    )
    assert "/home/cuti/.cuti-providers/openclaw/bin" in container_path
    assert "/home/cuti/.cuti-providers/claude/.local/bin" not in container_path
    assert "/home/cuti/.cuti-providers/codex/bin" not in container_path


def test_run_provider_update_updates_persistent_runtime_and_active_containers(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    commands: list[list[str]] = []

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )

    def _fake_run_command(cmd, timeout=30, show_output=False):
        commands.append(cmd)
        if (
            cmd[:2] == ["docker", "ps"]
            and f"label=cuti.runtime_profile={service.RUNTIME_PROFILE_CLOUD}" in cmd
        ):
            return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")
        if cmd[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(service, "_run_command", _fake_run_command)

    exit_code = service.run_provider_update(
        "claude", "/usr/local/bin/cuti-install-claude"
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Updating claude target 1/2: persistent runtime" in output
    assert "Updating claude target 2/2: active container 1/1 (abc123)" in output
    assert (
        "Updated claude in 2 target(s): persistent runtime and 1 active cuti "
        "container(s)."
    ) in output
    docker_run = next(cmd for cmd in commands if cmd[:2] == ["docker", "run"])
    assert (
        f"{tmp_path / '.cuti' / 'provider-runtimes'}:/home/cuti/.cuti-providers:rw"
        in docker_run
    )
    assert docker_run[-4:] == [
        service.IMAGE_NAME,
        "/usr/bin/zsh",
        "-lc",
        docker_run[-1],
    ]
    assert "export HOME=/home/cuti/.cuti-providers/claude" in docker_run[-1]
    assert (
        "export XDG_DATA_HOME=/home/cuti/.cuti-providers/claude/.local/share"
        in docker_run[-1]
    )
    assert (
        "export XDG_STATE_HOME=/home/cuti/.cuti-providers/claude/.local/state"
        in docker_run[-1]
    )
    assert (
        "export XDG_CACHE_HOME=/home/cuti/.cuti-providers/claude/.cache"
        in docker_run[-1]
    )
    assert "/usr/local/bin/cuti-install-claude" in docker_run[-1]
    assert "curl -fsSL https://claude.ai/install.sh | bash" in docker_run[-1]

    docker_exec = next(cmd for cmd in commands if cmd[:2] == ["docker", "exec"])
    assert docker_exec[2] == "abc123"
    assert "export HOME=/home/cuti" in docker_exec[-1]
    assert "export HOME=/home/cuti/.cuti-providers/claude" not in docker_exec[-1]
    assert "curl -fsSL https://claude.ai/install.sh | bash" in docker_exec[-1]


def test_run_provider_update_configures_hermes_home(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    service.provider_manager.set_enabled("hermes", True)
    service._selected_providers_cache = None
    commands: list[list[str]] = []

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )

    def _fake_run_command(cmd, timeout=30, show_output=False):
        commands.append(cmd)
        if cmd[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(service, "_run_command", _fake_run_command)

    exit_code = service.run_provider_update(
        "hermes", "/usr/local/bin/cuti-update-hermes"
    )

    assert exit_code == 0
    docker_run = next(cmd for cmd in commands if cmd[:2] == ["docker", "run"])
    assert f"{tmp_path / '.hermes'}:/home/cuti/.hermes:rw" in docker_run
    assert "export HERMES_HOME=/home/cuti/.hermes" in docker_run[-1]
    assert "export HERMES_INSTALL_DIR=/home/cuti/.hermes/hermes-agent" in docker_run[-1]
    assert "/usr/local/bin/cuti-update-hermes" in docker_run[-1]
    assert "hermes update" in docker_run[-1]


def test_run_provider_update_configures_openclaw_persistent_runtime(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    service.is_macos = False
    service.provider_manager.set_enabled("openclaw", True)
    service._selected_providers_cache = None
    commands: list[list[str]] = []

    monkeypatch.setattr(service, "_check_tool_available", lambda name: True)
    monkeypatch.setattr(
        service, "_build_container_image", lambda image_name, rebuild: True
    )

    def _fake_run_command(cmd, timeout=30, show_output=False):
        commands.append(cmd)
        if cmd[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(service, "_run_command", _fake_run_command)

    exit_code = service.run_provider_update(
        "openclaw", "/usr/local/bin/cuti-install-openclaw"
    )

    assert exit_code == 0
    docker_run = next(cmd for cmd in commands if cmd[:2] == ["docker", "run"])
    assert f"{tmp_path / '.openclaw'}:/home/cuti/.openclaw:rw" in docker_run
    assert (
        f"{tmp_path / '.cuti' / 'provider-runtimes'}:/home/cuti/.cuti-providers:rw"
        in docker_run
    )
    assert "export OPENCLAW_STATE_DIR=/home/cuti/.openclaw" in docker_run[-1]
    assert (
        "export OPENCLAW_CONFIG_PATH=/home/cuti/.openclaw/openclaw.json"
        in docker_run[-1]
    )
    assert (
        "export OPENCLAW_PREFIX=/home/cuti/.cuti-providers/openclaw" in docker_run[-1]
    )
    assert (
        "export npm_config_prefix=/home/cuti/.cuti-providers/openclaw" in docker_run[-1]
    )
    assert "/usr/local/bin/cuti-install-openclaw" in docker_run[-1]
    assert "openclaw doctor --non-interactive" in docker_run[-1]


def test_build_container_image_places_no_cache_before_context(
    monkeypatch, tmp_path: Path
) -> None:
    service = DevContainerService(tmp_path, provider_storage_dir=tmp_path / ".cuti")
    commands: list[list[str]] = []

    monkeypatch.setattr(
        service,
        "_generate_dockerfile",
        lambda project_type: "FROM python:3.11-bullseye\n",
    )

    def _fake_run_command(cmd, timeout=30, show_output=False):
        commands.append(cmd)
        if cmd[:2] == ["docker", "images"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(service, "_run_command", _fake_run_command)

    assert service._build_container_image("cuti-test-image", rebuild=True) is True

    build_cmd = next(cmd for cmd in commands if cmd[:2] == ["docker", "build"])
    assert build_cmd[-2] == "--no-cache"
