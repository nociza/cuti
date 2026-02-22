"""Security checklist validation tests for container runtime profiles."""

from pathlib import Path

from cuti.services.devcontainer import DevContainerService


def _base_sandbox_args(tmp_path: Path) -> list[str]:
    workspace = tmp_path / "workspace"
    config = tmp_path / "claw-config"
    clawd = tmp_path / "claw-workspace"
    workspace.mkdir()
    config.mkdir()
    clawd.mkdir()

    return [
        "docker",
        "run",
        "--rm",
        "--init",
        "-v",
        f"{workspace}:/workspace:rw",
        "-v",
        f"{config}:/home/cuti/.clawdbot:rw",
        "-v",
        f"{clawd}:/home/cuti/clawd:rw",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--security-opt",
        "seccomp=/tmp/kuyuchi-clawdbot-seccomp.json",
        "--pids-limit",
        "256",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev",
        "--tmpfs",
        "/run:rw,nosuid,nodev",
    ]


def test_clawdbot_sandbox_profile_checklist_accepts_valid_args(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path)
    args = _base_sandbox_args(tmp_path)

    errors = service._validate_runtime_profile_args(
        DevContainerService.RUNTIME_PROFILE_CLAWDBOT_SANDBOX,
        args,
    )

    assert errors == []


def test_clawdbot_sandbox_profile_rejects_host_network(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path)
    args = _base_sandbox_args(tmp_path) + ["--network", "host"]

    errors = service._validate_runtime_profile_args(
        DevContainerService.RUNTIME_PROFILE_CLAWDBOT_SANDBOX,
        args,
    )

    assert any("forbidden network mode 'host'" in error for error in errors)


def test_clawdbot_sandbox_profile_rejects_forbidden_mount(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path)
    args = _base_sandbox_args(tmp_path) + [
        "-v",
        f"{tmp_path / 'cuti'}:/home/cuti/.cuti-shared:rw",
    ]

    errors = service._validate_runtime_profile_args(
        DevContainerService.RUNTIME_PROFILE_CLAWDBOT_SANDBOX,
        args,
    )

    assert any("forbidden mount target '/home/cuti/.cuti-shared'" in error for error in errors)


def test_clawdbot_sandbox_profile_rejects_unapproved_mount_target(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path)
    args = _base_sandbox_args(tmp_path) + [
        "-v",
        f"{tmp_path / 'claude'}:/home/cuti/.claude-linux:rw",
    ]

    errors = service._validate_runtime_profile_args(
        DevContainerService.RUNTIME_PROFILE_CLAWDBOT_SANDBOX,
        args,
    )

    assert any("not allowed for profile 'clawdbot_sandbox'" in error for error in errors)


def test_clawdbot_sandbox_profile_requires_seccomp_security_opt(tmp_path: Path) -> None:
    service = DevContainerService(tmp_path)
    args = _base_sandbox_args(tmp_path)
    args = service._remove_flag_value_pair(args, "--security-opt", "seccomp=/tmp/kuyuchi-clawdbot-seccomp.json")

    errors = service._validate_runtime_profile_args(
        DevContainerService.RUNTIME_PROFILE_CLAWDBOT_SANDBOX,
        args,
    )

    assert any("missing required --security-opt value with prefix 'seccomp='" in error for error in errors)
