"""Tests for provider metadata and defaults."""

from __future__ import annotations

import pytest

from cuti.services.providers import KNOWN_PROVIDERS, ProviderManager


def test_known_providers_default_to_claude_only(tmp_path) -> None:
    manager = ProviderManager(storage_dir=tmp_path)

    assert manager.selected_providers() == ["claude"]
    assert manager.primary_provider() == "claude"
    assert KNOWN_PROVIDERS["claude"].default_enabled is True
    assert KNOWN_PROVIDERS["codex"].default_enabled is False
    assert KNOWN_PROVIDERS["openclaw"].default_enabled is False
    assert KNOWN_PROVIDERS["hermes"].default_enabled is False
    assert KNOWN_PROVIDERS["opencode"].default_enabled is False


def test_provider_instruction_files_follow_enabled_selection(tmp_path) -> None:
    manager = ProviderManager(storage_dir=tmp_path)

    manager.set_enabled("codex", True)
    manager.set_enabled("openclaw", True)

    assert manager.provider_instruction_files() == [
        "CLAUDE.md",
        "AGENTS.md",
        "SOUL.md",
        "TOOLS.md",
    ]


def test_hermes_instruction_files_include_project_context_files(tmp_path) -> None:
    manager = ProviderManager(storage_dir=tmp_path)

    manager.set_enabled("claude", False)
    manager.set_enabled("hermes", True)

    assert manager.provider_instruction_files() == [
        ".hermes.md",
        "HERMES.md",
        "AGENTS.md",
        "CLAUDE.md",
    ]


def test_unknown_provider_raises_clean_error(tmp_path) -> None:
    manager = ProviderManager(storage_dir=tmp_path)

    with pytest.raises(ValueError, match="Unknown provider 'clawdbot'"):
        manager.get_metadata("clawdbot")
