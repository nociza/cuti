"""Agent provider selection and metadata for cuti containers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class ProviderMetadata:
    """Metadata for a known agent provider."""

    name: str
    title: str
    description: str
    experimental: bool = False
    experimental_note: str = ""
    default_enabled: bool = False
    instruction_files: Tuple[str, ...] = ()
    commands: Tuple[str, ...] = ()
    setup_command: Optional[str] = None
    setup_hint: str = ""
    update_command: Optional[str] = None
    update_hint: str = ""


KNOWN_PROVIDERS: Dict[str, ProviderMetadata] = {
    "claude": ProviderMetadata(
        name="claude",
        title="Anthropic Claude Code",
        description="Anthropic's Claude Code CLI, with Linux-specific auth storage handled by cuti for container use.",
        default_enabled=True,
        instruction_files=("CLAUDE.md",),
        commands=("claude",),
        setup_command="claude login",
        setup_hint="Authenticate Claude Code inside the cuti container and persist Linux credentials under ~/.cuti/claude-linux.",
        update_command="/usr/local/bin/cuti-install-claude",
        update_hint="Refresh Claude Code inside the cuti container using the official native installer path.",
    ),
    "codex": ProviderMetadata(
        name="codex",
        title="OpenAI Codex CLI",
        description="OpenAI's Codex CLI, with persisted auth and skills mounted into the cuti container.",
        instruction_files=("AGENTS.md",),
        commands=("codex",),
        setup_command="codex",
        setup_hint="Start Codex interactively in the cuti container and complete ChatGPT sign-in or provide OPENAI_API_KEY.",
        update_command="/usr/local/bin/cuti-install-codex",
        update_hint="Refresh Codex inside the cuti container using the official standalone installer.",
    ),
    "openclaw": ProviderMetadata(
        name="openclaw",
        title="OpenClaw",
        description="OpenClaw's personal agent/gateway runtime, with persisted state and workspace prompt files wired into the container.",
        instruction_files=(
            "AGENTS.md",
            "SOUL.md",
            "TOOLS.md",
            "IDENTITY.md",
            "USER.md",
            "HEARTBEAT.md",
            "BOOTSTRAP.md",
            "MEMORY.md",
        ),
        commands=("openclaw",),
        setup_command="openclaw onboard --install-daemon",
        setup_hint="Run OpenClaw onboarding in the cuti container to initialize credentials, daemon state, and workspace prompts.",
        update_command="/usr/local/bin/cuti-install-openclaw",
        update_hint="Refresh OpenClaw in cuti's persistent provider runtime, then run OpenClaw doctor checks.",
    ),
    "hermes": ProviderMetadata(
        name="hermes",
        title="Hermes Agent",
        description="Experimental cuti integration for Nous Research's Hermes Agent, with persisted HERMES_HOME state, profile-aware updates, and OpenClaw migration support.",
        experimental=True,
        experimental_note="Hermes is still evolving quickly upstream. cuti follows Hermes' native setup and update lifecycle and may adjust as upstream profile and gateway features change.",
        instruction_files=(".hermes.md", "HERMES.md", "AGENTS.md", "CLAUDE.md"),
        commands=("hermes",),
        setup_command="hermes setup",
        setup_hint="Run the Hermes setup wizard in the cuti container. It can detect OpenClaw state for migration, and `hermes model` remains the upstream path for later provider/model changes.",
        update_command="/usr/local/bin/cuti-update-hermes",
        update_hint="Run Hermes' native update flow inside the cuti container. This follows the upstream `hermes update` path: pull code, refresh dependencies, check config, and sync bundled skills across Hermes profiles.",
    ),
    "opencode": ProviderMetadata(
        name="opencode",
        title="OpenCode",
        description="OpenCode's coding agent CLI, with persisted auth/config/data directories mounted into the cuti container.",
        instruction_files=("AGENTS.md",),
        commands=("opencode",),
        setup_command="opencode",
        setup_hint="Start OpenCode inside the cuti container and complete provider-specific setup from the interactive CLI.",
        update_command="/usr/local/bin/cuti-install-opencode",
        update_hint="Refresh OpenCode inside the cuti container using the official install script path.",
    ),
}


class ProviderManager:
    """Manage enabled agent providers stored under ~/.cuti/providers.json."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir or Path.home() / ".cuti")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.storage_dir / "providers.json"
        self._providers: Dict[str, Dict[str, object]] = {}
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            self._providers = {}
            return

        try:
            decoded = json.loads(self.config_path.read_text())
        except json.JSONDecodeError:
            backup_path = self.config_path.with_suffix(".bak")
            self.config_path.rename(backup_path)
            self._providers = {}
            return

        self._providers = decoded if isinstance(decoded, dict) else {}

    def _save(self) -> None:
        self.config_path.write_text(
            json.dumps(self._providers, indent=2, sort_keys=True)
        )

    def _canonical_name(self, provider: str) -> str:
        candidate = provider.strip().lower()
        if candidate in KNOWN_PROVIDERS:
            return candidate

        available = ", ".join(sorted(KNOWN_PROVIDERS))
        raise ValueError(
            f"Unknown provider '{provider}'. Available providers: {available}"
        )

    def known_providers(self) -> Dict[str, ProviderMetadata]:
        return KNOWN_PROVIDERS

    def get_metadata(self, provider: str) -> ProviderMetadata:
        return KNOWN_PROVIDERS[self._canonical_name(provider)]

    def get_state(self, provider: str) -> Dict[str, object]:
        return self._providers.get(self._canonical_name(provider), {}).copy()

    def has_explicit_state(self, provider: str) -> bool:
        return self._canonical_name(provider) in self._providers

    def set_enabled(self, provider: str, enabled: bool, source: str = "manual") -> None:
        canonical = self._canonical_name(provider)
        self._providers[canonical] = {
            "enabled": bool(enabled),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
        }
        self._save()

    def is_enabled(self, provider: str) -> bool:
        canonical = self._canonical_name(provider)
        state = self._providers.get(canonical)
        if isinstance(state, dict) and "enabled" in state:
            return bool(state.get("enabled"))
        return KNOWN_PROVIDERS[canonical].default_enabled

    def selected_providers(self) -> List[str]:
        return [name for name in KNOWN_PROVIDERS if self.is_enabled(name)]

    def primary_provider(self) -> Optional[str]:
        selected = self.selected_providers()
        if not selected:
            return None
        if "claude" in selected:
            return "claude"
        return selected[0]

    def provider_instruction_files(
        self, providers: Optional[Iterable[str]] = None
    ) -> List[str]:
        selected = providers or self.selected_providers()
        files: List[str] = []
        seen = set()
        for provider in selected:
            for filename in self.get_metadata(provider).instruction_files:
                if filename not in seen:
                    seen.add(filename)
                    files.append(filename)
        return files
