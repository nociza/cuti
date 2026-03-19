"""Tests for Claude update delegation into the provider workflow."""

from __future__ import annotations

import click
import pytest

from cuti.cli.commands import claude_account


def test_claude_update_delegates_to_provider_host_service(monkeypatch) -> None:
    calls: list[tuple[str, bool]] = []

    class _FakeProviderHostService:
        def run_update(self, provider: str, *, rebuild: bool = False) -> int:
            calls.append((provider, rebuild))
            return 0

    monkeypatch.setattr("cuti.services.provider_host.ProviderHostService", _FakeProviderHostService)

    claude_account.update_claude_cli(rebuild=True)

    assert calls == [("claude", True)]


def test_claude_update_raises_on_nonzero_exit(monkeypatch) -> None:
    class _FakeProviderHostService:
        def run_update(self, provider: str, *, rebuild: bool = False) -> int:
            return 7

    monkeypatch.setattr("cuti.services.provider_host.ProviderHostService", _FakeProviderHostService)

    with pytest.raises(click.exceptions.Exit) as exc_info:
        claude_account.update_claude_cli(rebuild=False)

    assert exc_info.value.exit_code == 7
