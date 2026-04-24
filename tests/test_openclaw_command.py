"""Tests for the dedicated OpenClaw container command surface."""

from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from cuti.cli.commands.openclaw import app


def test_openclaw_onboard_runs_container_shell_with_doctor(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeProviderHostService:
        def run_provider_shell_command(
            self,
            provider,
            command,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append(
                {
                    "provider": provider,
                    "command": command,
                    "rebuild": rebuild,
                    "interactive": interactive,
                    "mount_docker_socket": mount_docker_socket,
                }
            )
            return 0

    monkeypatch.setattr(
        "cuti.cli.commands.openclaw.ProviderHostService", _FakeProviderHostService
    )

    result = CliRunner().invoke(app, ["onboard", "--no-install-daemon", "--rebuild"])

    assert result.exit_code == 0
    assert calls == [
        {
            "provider": "openclaw",
            "command": "openclaw onboard && openclaw doctor --non-interactive",
            "rebuild": True,
            "interactive": True,
            "mount_docker_socket": True,
        }
    ]


def test_openclaw_channels_login_forwards_to_provider_command(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeProviderHostService:
        def run_provider_command(
            self,
            provider,
            args,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append(
                {
                    "provider": provider,
                    "args": args,
                    "rebuild": rebuild,
                    "interactive": interactive,
                    "mount_docker_socket": mount_docker_socket,
                }
            )
            return 0

    monkeypatch.setattr(
        "cuti.cli.commands.openclaw.ProviderHostService", _FakeProviderHostService
    )

    result = CliRunner().invoke(
        app,
        ["channels-login", "--channel", "whatsapp", "--account", "main"],
    )

    assert result.exit_code == 0
    assert calls == [
        {
            "provider": "openclaw",
            "args": ["channels", "login", "--channel", "whatsapp", "--account", "main"],
            "rebuild": False,
            "interactive": True,
            "mount_docker_socket": True,
        }
    ]


def test_openclaw_browser_forwards_unknown_options(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _FakeProviderHostService:
        def run_provider_command(
            self,
            provider,
            args,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append(args)
            return 0

    monkeypatch.setattr(
        "cuti.cli.commands.openclaw.ProviderHostService", _FakeProviderHostService
    )

    result = CliRunner().invoke(
        app,
        ["browser", "--browser-profile", "openclaw", "start"],
    )

    assert result.exit_code == 0
    assert calls == [["browser", "--browser-profile", "openclaw", "start"]]


def test_openclaw_source_backed_command_forwards_with_root_profile(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeProviderHostService:
        def run_provider_command(
            self,
            provider,
            args,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append(
                {
                    "provider": provider,
                    "args": args,
                    "rebuild": rebuild,
                    "interactive": interactive,
                    "mount_docker_socket": mount_docker_socket,
                }
            )
            return 0

    monkeypatch.setattr(
        "cuti.cli.commands.openclaw.ProviderHostService", _FakeProviderHostService
    )

    result = CliRunner().invoke(
        app,
        ["--profile", "work", "models", "--no-interactive", "status", "--json"],
    )

    assert result.exit_code == 0
    assert calls == [
        {
            "provider": "openclaw",
            "args": ["--profile", "work", "models", "status", "--json"],
            "rebuild": False,
            "interactive": False,
            "mount_docker_socket": True,
        }
    ]


def test_openclaw_run_remains_future_plugin_escape_hatch(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _FakeProviderHostService:
        def run_provider_command(
            self,
            provider,
            args,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append(args)
            return 0

    monkeypatch.setattr(
        "cuti.cli.commands.openclaw.ProviderHostService", _FakeProviderHostService
    )

    result = CliRunner().invoke(
        app,
        ["run", "future-plugin", "do-thing", "--flag", "value"],
    )

    assert result.exit_code == 0
    assert calls == [["future-plugin", "do-thing", "--flag", "value"]]


def test_openclaw_root_version_forwards_to_installed_cli(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _FakeProviderHostService:
        def run_provider_command(
            self,
            provider,
            args,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append(args)
            return 0

    monkeypatch.setattr(
        "cuti.cli.commands.openclaw.ProviderHostService", _FakeProviderHostService
    )

    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert calls == [["--version"]]


def test_openclaw_up_onboards_when_state_missing(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeProviderHostService:
        def get_status(self, provider):
            assert provider == "openclaw"
            return SimpleNamespace(setup_state="missing")

        def run_provider_shell_command(
            self,
            provider,
            command,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append({"kind": "shell", "command": command, "interactive": interactive})
            return 0

        def run_provider_command(
            self,
            provider,
            args,
            rebuild=False,
            interactive=False,
            mount_docker_socket=True,
        ):
            calls.append({"kind": "command", "args": args, "interactive": interactive})
            return 0

    monkeypatch.setattr(
        "cuti.cli.commands.openclaw.ProviderHostService", _FakeProviderHostService
    )

    result = CliRunner().invoke(app, ["up", "--port", "18888"])

    assert result.exit_code == 0
    assert calls == [
        {
            "kind": "shell",
            "command": "openclaw onboard --install-daemon && openclaw doctor --non-interactive",
            "interactive": True,
        },
        {
            "kind": "command",
            "args": ["doctor", "--non-interactive"],
            "interactive": False,
        },
        {
            "kind": "command",
            "args": ["gateway", "--port", "18888", "--verbose"],
            "interactive": True,
        },
    ]
