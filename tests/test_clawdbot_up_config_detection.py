"""Behavior tests for `cuti clawdbot up` config detection heuristics."""

import json
from pathlib import Path

from cuti.cli.commands import clawdbot


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def test_needs_initial_configuration_when_config_missing(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config" / "clawdbot.json"
    monkeypatch.setattr(clawdbot, "_CLAWDBOT_CONFIG_PATH", config_path)

    assert clawdbot._needs_initial_configuration() is True


def test_needs_initial_configuration_false_when_credentials_exist(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config" / "clawdbot.json"
    creds_file = config_path.parent / "credentials" / "whatsapp" / "acct" / "session.json"
    creds_file.parent.mkdir(parents=True, exist_ok=True)
    creds_file.write_text("{}")
    monkeypatch.setattr(clawdbot, "_CLAWDBOT_CONFIG_PATH", config_path)

    assert clawdbot._needs_initial_configuration() is False


def test_needs_initial_configuration_true_for_workspace_bootstrap_only(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config" / "clawdbot.json"
    _write_json(
        config_path,
        {"agents": {"defaults": {"workspace": "/workspace"}}},
    )
    monkeypatch.setattr(clawdbot, "_CLAWDBOT_CONFIG_PATH", config_path)

    assert clawdbot._needs_initial_configuration() is True


def test_needs_initial_configuration_false_for_meaningful_config(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config" / "clawdbot.json"
    _write_json(
        config_path,
        {
            "agents": {"defaults": {"workspace": "/workspace"}},
            "channels": {"whatsapp": {"enabled": True}},
        },
    )
    monkeypatch.setattr(clawdbot, "_CLAWDBOT_CONFIG_PATH", config_path)

    assert clawdbot._needs_initial_configuration() is False


def test_up_runs_configure_then_start(monkeypatch) -> None:
    calls = []

    def _fake_ensure(*, rebuild: bool, skip_colima: bool) -> None:
        calls.append(("ensure", rebuild, skip_colima))

    def _fake_start(**kwargs) -> None:
        calls.append(("start", kwargs))

    monkeypatch.setattr(clawdbot, "_ensure_clawdbot_configuration", _fake_ensure)
    monkeypatch.setattr(clawdbot, "start", _fake_start)

    clawdbot.up(
        port=19000,
        verbose=False,
        rebuild=True,
        skip_colima=True,
        force=True,
        configure=True,
        extra_args=["--foo", "bar"],
    )

    assert calls[0] == ("ensure", True, True)
    assert calls[1][0] == "start"
    assert calls[1][1]["port"] == 19000
    assert calls[1][1]["extra_args"] == ["--foo", "bar"]
    assert calls[1][1]["force"] is True


def test_up_skips_configure_when_disabled(monkeypatch) -> None:
    calls = []

    def _fake_ensure(*, rebuild: bool, skip_colima: bool) -> None:
        calls.append(("ensure", rebuild, skip_colima))

    def _fake_start(**kwargs) -> None:
        calls.append(("start", kwargs))

    monkeypatch.setattr(clawdbot, "_ensure_clawdbot_configuration", _fake_ensure)
    monkeypatch.setattr(clawdbot, "start", _fake_start)

    clawdbot.up(
        port=None,
        verbose=True,
        rebuild=False,
        skip_colima=False,
        force=False,
        configure=False,
        extra_args=None,
    )

    assert calls == [
        (
            "start",
            {
                "port": None,
                "verbose": True,
                "rebuild": False,
                "skip_colima": False,
                "force": False,
                "extra_args": None,
            },
        )
    ]
