"""Tests for the Claude CLI update command install scope behavior."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Any

from cuti.cli.commands import claude_account


@dataclass
class _CompletedProcess:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _setup_update_mocks(monkeypatch, tmp_path, *, in_container: bool) -> list[list[str]]:
    calls: list[list[str]] = []

    monkeypatch.setenv("HOME", str(tmp_path))
    if in_container:
        monkeypatch.setenv("CUTI_IN_CONTAINER", "true")
    else:
        monkeypatch.delenv("CUTI_IN_CONTAINER", raising=False)

    def _fake_which(cmd: str) -> str | None:
        mapping = {
            "npm-original": "/usr/local/bin/npm-original",
            "npm": "/usr/bin/npm",
            "sudo": "/usr/bin/sudo",
            "claude": "/usr/local/bin/claude",
        }
        return mapping.get(cmd)

    def _fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> _CompletedProcess:
        calls.append(cmd)

        if "view" in cmd:
            return _CompletedProcess(stdout="1.2.3\n")

        if len(cmd) >= 2 and cmd[1] == "list":
            return _CompletedProcess(
                stdout='{"dependencies":{"@anthropic-ai/claude-code":{"version":"1.2.2"}}}'
            )

        if "--version" in cmd:
            return _CompletedProcess(stdout="1.2.3\n")

        return _CompletedProcess()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setattr("shutil.which", _fake_which)
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    return calls


def test_update_defaults_to_shared_cuti_prefix(monkeypatch, tmp_path) -> None:
    calls = _setup_update_mocks(monkeypatch, tmp_path, in_container=False)

    claude_account.update_claude_cli(
        version=None,
        beta=False,
        force=False,
        system=False,
        dry_run=False,
        yes=True,
    )

    install_cmds = [cmd for cmd in calls if "install" in cmd]
    assert len(install_cmds) == 1
    install_cmd = install_cmds[0]

    expected_prefix = str(tmp_path / ".cuti" / "claude-cli")
    assert "--prefix" in install_cmd
    assert expected_prefix in install_cmd
    assert "sudo" not in install_cmd


def test_update_inside_container_uses_shared_prefix_not_system(monkeypatch, tmp_path) -> None:
    calls = _setup_update_mocks(monkeypatch, tmp_path, in_container=True)

    claude_account.update_claude_cli(
        version=None,
        beta=False,
        force=False,
        system=False,
        dry_run=False,
        yes=True,
    )

    install_cmds = [cmd for cmd in calls if "install" in cmd]
    assert len(install_cmds) == 1
    install_cmd = install_cmds[0]

    expected_prefix = str(tmp_path / ".cuti" / "claude-cli")
    assert "--prefix" in install_cmd
    assert expected_prefix in install_cmd
    assert "sudo" not in install_cmd


def test_update_shared_scope_does_not_validate_shell_claude(monkeypatch, tmp_path) -> None:
    calls = _setup_update_mocks(monkeypatch, tmp_path, in_container=False)

    claude_account.update_claude_cli(
        version=None,
        beta=False,
        force=False,
        system=False,
        dry_run=False,
        yes=True,
    )

    assert ["claude", "--version"] not in calls


def test_update_system_scope_omits_prefix_and_uses_sudo(monkeypatch, tmp_path) -> None:
    calls = _setup_update_mocks(monkeypatch, tmp_path, in_container=False)
    monkeypatch.setattr(os, "geteuid", lambda: 1000)

    claude_account.update_claude_cli(
        version=None,
        beta=False,
        force=False,
        system=True,
        dry_run=False,
        yes=True,
    )

    install_cmds = [cmd for cmd in calls if "install" in cmd]
    assert len(install_cmds) == 1
    install_cmd = install_cmds[0]

    assert install_cmd[0] == "sudo"
    assert "--prefix" not in install_cmd
