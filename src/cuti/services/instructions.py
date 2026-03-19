"""Helpers for updating provider instruction files inside the workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .providers import ProviderManager

DEFAULT_INSTRUCTION_FILES: Sequence[str] = ("CLAUDE.md", "AGENTS.md", "TOOLS.md")
TOOLS_SECTION_HEADER = "## Available CLI Tools"


def _build_tools_section(tools: List[Dict[str, Any]]) -> str:
    content = f"\n{TOOLS_SECTION_HEADER}\n\n"
    content += "The following CLI tools are available in the development environment:\n\n"

    enabled_tools = [tool for tool in tools if tool.get("enabled") and tool.get("installed")]
    if enabled_tools:
        for tool in enabled_tools:
            content += f"### {tool['display_name']}\n"
            content += f"{tool['description']}\n\n"
            content += f"{tool['usage_instructions']}\n\n"
    else:
        content += "*No additional CLI tools are currently enabled.*\n\n"

    return content


def update_instruction_files_with_tools(
    tools: List[Dict[str, Any]],
    *,
    workspace: Path = Path("/workspace"),
    instruction_files: Optional[Iterable[str]] = None,
    provider_storage_dir: Optional[Path] = None,
) -> List[Path]:
    """Update any existing provider instruction files with the enabled tool list."""

    updated_paths: List[Path] = []
    tools_content = _build_tools_section(tools)
    resolved_files: List[str] = []
    seen = set()

    if instruction_files is not None:
        for filename in instruction_files:
            if filename not in seen:
                seen.add(filename)
                resolved_files.append(filename)
    else:
        provider_files = ProviderManager(storage_dir=provider_storage_dir).provider_instruction_files()
        for filename in provider_files:
            if filename not in seen:
                seen.add(filename)
                resolved_files.append(filename)

        # Keep existing standard instruction files updated even if the current
        # provider selection changes, so workspaces do not drift.
        for filename in DEFAULT_INSTRUCTION_FILES:
            if (workspace / filename).exists() and filename not in seen:
                seen.add(filename)
                resolved_files.append(filename)

    for filename in resolved_files:
        path = workspace / filename
        if not path.exists():
            continue

        content = path.read_text()
        section_start = content.find(TOOLS_SECTION_HEADER)
        section_end = content.find("\n## ", section_start + 1) if section_start != -1 else -1

        if section_start != -1:
            if section_end != -1:
                new_content = content[:section_start] + tools_content + content[section_end:]
            else:
                new_content = content[:section_start] + tools_content
        else:
            last_section = content.rfind("\n# ")
            if last_section != -1:
                new_content = content[:last_section] + "\n" + tools_content + content[last_section:]
            else:
                new_content = content + "\n" + tools_content

        path.write_text(new_content)
        updated_paths.append(path)

    return updated_paths
