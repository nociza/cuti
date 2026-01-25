"""Addon management for optional cuti integrations (e.g. Clawdbot)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:  # Rich is an optional dependency in a few environments
    from rich.console import Console
    from rich.prompt import Confirm

    _RICH_AVAILABLE = True
    _console: Optional[Console] = Console()
except Exception:  # pragma: no cover - rich may be missing in minimal envs
    _RICH_AVAILABLE = False
    _console = None


@dataclass
class AddonMetadata:
    """Metadata for a known addon."""

    name: str
    title: str
    description: str
    default_enabled: bool = True


KNOWN_ADDONS: Dict[str, AddonMetadata] = {
    "clawdbot": AddonMetadata(
        name="clawdbot",
        title="Clawdbot personal assistant",
        description="Installs the Clawdbot CLI inside the cuti container so you can run the gateway and connect messaging channels.",
        default_enabled=True,
    )
}


class AddonManager:
    """Manage addon enablement preferences stored under ~/.cuti/addons.json."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir or Path.home() / ".cuti")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.storage_dir / "addons.json"
        self._addons: Dict[str, Dict[str, object]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self.config_path.exists():
            try:
                self._addons = json.loads(self.config_path.read_text())
            except json.JSONDecodeError:
                # Corrupt file, start fresh but keep backup for inspection
                backup_path = self.config_path.with_suffix(".bak")
                self.config_path.rename(backup_path)
                self._addons = {}
        else:
            self._addons = {}

    def _save(self) -> None:
        self.config_path.write_text(json.dumps(self._addons, indent=2))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def known_addons(self) -> Dict[str, AddonMetadata]:
        return KNOWN_ADDONS

    def get_state(self, addon: str) -> Dict[str, object]:
        return self._addons.get(addon, {}).copy()

    def set_enabled(self, addon: str, enabled: bool, source: str = "manual") -> None:
        state = self._addons.get(addon, {})
        state.update(
            {
                "enabled": bool(enabled),
                "updated_at": datetime.utcnow().isoformat(),
                "source": source,
            }
        )
        self._addons[addon] = state
        self._save()

    def is_enabled(self, addon: str) -> Optional[bool]:
        state = self._addons.get(addon)
        if state is None:
            return None
        return bool(state.get("enabled")) if "enabled" in state else None

    # Prompt ----------------------------------------------------------------
    def ensure_enabled(self, addon: str, *, prompt: Optional[str] = None, default_enabled: Optional[bool] = None) -> bool:
        """Ensure an addon has an enablement decision, prompting the user if needed.

        Args:
            addon: The addon identifier (e.g. "clawdbot").
            prompt: Custom prompt string.
            default_enabled: Optional default. If omitted, the metadata default is used.
        """

        existing = self.is_enabled(addon)
        if existing is not None:
            return existing

        meta = KNOWN_ADDONS.get(addon)
        default = default_enabled if default_enabled is not None else (meta.default_enabled if meta else True)
        message = prompt or (meta.description if meta else f"Enable addon '{addon}'?")

        choice = default
        if sys.stdin.isatty():
            question = f"{meta.title if meta else addon}: install now?"
            if _RICH_AVAILABLE:
                choice = Confirm.ask(f"{question}\n{message}", default=default)
            else:  # Fallback to plain input
                suffix = "[Y/n]" if default else "[y/N]"
                response = input(f"{question}\n{message} {suffix} ").strip().lower()
                if response in {"y", "yes"}:
                    choice = True
                elif response in {"n", "no"}:
                    choice = False
        else:
            if _console:
                _console.print(
                    f"[cyan]Using default {'enabled' if default else 'disabled'} for addon '{addon}' (non-interactive).[/cyan]"
                )

        state = {
            "enabled": bool(choice),
            "prompted_at": datetime.utcnow().isoformat(),
            "default": default,
        }
        self._addons[addon] = state
        self._save()
        return bool(choice)


def is_clawdbot_enabled(manager: Optional[AddonManager] = None, *, prompt: bool = True) -> bool:
    """Helper to check the Clawdbot addon flag, prompting if desired."""

    manager = manager or AddonManager()
    state = manager.is_enabled("clawdbot")
    if state is not None or not prompt:
        return bool(state) if state is not None else False
    return manager.ensure_enabled("clawdbot")

