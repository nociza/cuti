"""Tests for provider-aware instruction file updates."""

from __future__ import annotations

from cuti.services.instructions import TOOLS_SECTION_HEADER, update_instruction_files_with_tools
from cuti.services.providers import ProviderManager


def _enabled_tool() -> list[dict[str, object]]:
    return [
        {
            "display_name": "jq",
            "description": "JSON processor",
            "usage_instructions": "Use `jq` for JSON inspection.",
            "enabled": True,
            "installed": True,
        }
    ]


def test_instruction_updates_include_provider_specific_files(tmp_path) -> None:
    provider_storage = tmp_path / ".cuti"
    manager = ProviderManager(storage_dir=provider_storage)
    manager.set_enabled("openclaw", True)

    soul_md = tmp_path / "SOUL.md"
    soul_md.write_text("# OpenClaw\n")

    updated = update_instruction_files_with_tools(
        _enabled_tool(),
        workspace=tmp_path,
        provider_storage_dir=provider_storage,
    )

    assert soul_md in updated
    assert TOOLS_SECTION_HEADER in soul_md.read_text()


def test_instruction_updates_keep_existing_standard_files_in_sync(tmp_path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    agents_md = tmp_path / "AGENTS.md"
    claude_md.write_text("# Claude\n")
    agents_md.write_text("# Agents\n")

    updated = update_instruction_files_with_tools(_enabled_tool(), workspace=tmp_path, provider_storage_dir=tmp_path / ".cuti")

    assert claude_md in updated
    assert agents_md in updated
    assert TOOLS_SECTION_HEADER in claude_md.read_text()
    assert TOOLS_SECTION_HEADER in agents_md.read_text()
