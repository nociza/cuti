"""Prompt prefix management for cuti."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..utils.constants import PROMPT_PREFIXES_DIR


class PromptPrefix(BaseModel):
    """Model for a prompt prefix configuration."""
    name: str
    description: str
    prompt: str
    tools: list[str]
    is_template: bool = False
    is_active: bool = False


class PromptPrefixManager:
    """Manages prompt prefixes and templates."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the prompt prefix manager."""
        self.config_dir = config_dir or Path.home() / ".cuti"
        self.config_dir.mkdir(exist_ok=True)
        self.prefix_file = self.config_dir / "prompt_prefix.json"
        self.custom_prefixes_file = self.config_dir / "custom_prefixes.json"

        # Path to templates directory
        self.templates_dir = PROMPT_PREFIXES_DIR

        self._ensure_files()

    def _ensure_files(self) -> None:
        """Ensure prefix files exist."""
        if not self.prefix_file.exists():
            # Create default prefix file with no active prefix
            self.save_active_prefix(None)

        if not self.custom_prefixes_file.exists():
            # Create empty custom prefixes file
            with open(self.custom_prefixes_file, 'w') as f:
                json.dump([], f)

    def get_templates(self) -> list[dict[str, Any]]:
        """Get all available templates by loading from JSON files."""
        templates = []

        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob("*.json"):
                try:
                    with open(template_file) as f:
                        template = json.load(f)
                        template['is_template'] = True
                        templates.append(template)
                except Exception as e:
                    print(f"Error loading template {template_file}: {e}")

        # Sort templates by name for consistency
        templates.sort(key=lambda x: x.get('name', ''))

        return templates

    def get_custom_prefixes(self) -> list[dict[str, Any]]:
        """Get all custom prefixes."""
        try:
            with open(self.custom_prefixes_file) as f:
                return json.load(f)
        except Exception:
            return []

    def save_custom_prefix(self, prefix: dict[str, Any]) -> bool:
        """Save a custom prefix."""
        try:
            prefixes = self.get_custom_prefixes()

            # Check if prefix with same name exists
            existing_index = next((i for i, p in enumerate(prefixes) if p['name'] == prefix['name']), None)

            if existing_index is not None:
                # Update existing
                prefixes[existing_index] = prefix
            else:
                # Add new
                prefixes.append(prefix)

            with open(self.custom_prefixes_file, 'w') as f:
                json.dump(prefixes, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving custom prefix: {e}")
            return False

    def delete_custom_prefix(self, name: str) -> bool:
        """Delete a custom prefix."""
        try:
            prefixes = self.get_custom_prefixes()
            prefixes = [p for p in prefixes if p['name'] != name]

            with open(self.custom_prefixes_file, 'w') as f:
                json.dump(prefixes, f, indent=2)

            # If this was the active prefix, clear it
            active = self.get_active_prefix()
            if active and active.get('name') == name:
                self.save_active_prefix(None)

            return True
        except Exception:
            return False

    def get_active_prefix(self) -> dict[str, Any] | None:
        """Get the currently active prefix."""
        try:
            with open(self.prefix_file) as f:
                data = json.load(f)
                return data.get('active_prefix')
        except Exception:
            return None

    def save_active_prefix(self, prefix: dict[str, Any] | None) -> bool:
        """Save the active prefix."""
        try:
            data = {
                'active_prefix': prefix,
                'enabled': prefix is not None
            }

            with open(self.prefix_file, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception:
            return False

    def format_prefix_for_chat(self, prefix: dict[str, Any]) -> str:
        """Format a prefix for use in chat."""
        if not prefix:
            return ""

        lines = [prefix['prompt']]

        if prefix.get('tools'):
            lines.append("\nKey guidelines:")
            for tool in prefix['tools']:
                lines.append(f"- {tool}")

        return "\n".join(lines)

    def get_all_prefixes(self) -> dict[str, Any]:
        """Get all templates and custom prefixes."""
        return {
            'templates': self.get_templates(),
            'custom': self.get_custom_prefixes(),
            'active': self.get_active_prefix()
        }
