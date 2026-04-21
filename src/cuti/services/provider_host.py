"""Host-side provider status, setup, and update helpers."""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .claude_account_manager import ClaudeAccountManager
from .devcontainer import DevContainerService
from .providers import ProviderManager, ProviderMetadata


@dataclass
class ProviderHostStatus:
    """Resolved host-side status for one provider."""

    provider: str
    title: str
    enabled: bool
    default_enabled: bool
    explicit: bool
    commands: List[str]
    host_command_path: Optional[str]
    setup_state: str
    detail: str
    state_paths: List[Path]
    existing_state_paths: List[Path]
    setup_command: Optional[str]
    setup_hint: str
    update_command: Optional[str]
    update_hint: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""

        data = asdict(self)
        data["state_paths"] = [str(path) for path in self.state_paths]
        data["existing_state_paths"] = [str(path) for path in self.existing_state_paths]
        return data


class ProviderHostService:
    """Coordinate provider-oriented host workflows."""

    def __init__(
        self,
        working_directory: Optional[str] = None,
        *,
        provider_storage_dir: Optional[Path] = None,
    ):
        self.working_directory = working_directory
        self.provider_manager = ProviderManager(storage_dir=provider_storage_dir)
        self.storage_dir = self.provider_manager.storage_dir
        self.home_dir = Path.home()

    def _metadata(self, provider: str) -> ProviderMetadata:
        return self.provider_manager.get_metadata(provider)

    def _state_paths(self, provider: str) -> List[Path]:
        if provider == "claude":
            return [
                self.storage_dir / "claude-linux",
                self.storage_dir / "provider-runtimes" / "claude",
                self.storage_dir / "claude-accounts",
                self.home_dir / ".claude",
            ]
        if provider == "codex":
            return [
                self.storage_dir / "provider-runtimes" / "codex",
                self.home_dir / ".codex",
            ]
        if provider == "opencode":
            return [
                self.home_dir / ".opencode",
                self.home_dir / ".config" / "opencode",
                self.home_dir / ".local" / "share" / "opencode",
            ]
        if provider == "openclaw":
            return [
                self.home_dir / ".openclaw",
                self.home_dir / ".agents",
            ]
        if provider == "hermes":
            return [
                self.home_dir / ".hermes",
                self.home_dir / ".claude",
                self.home_dir / ".openclaw",
                self.home_dir / ".agents",
            ]
        return []

    @staticmethod
    def _path_has_files(path: Path) -> bool:
        if not path.exists():
            return False
        if path.is_file():
            return True
        return any(child.is_file() for child in path.rglob("*"))

    @staticmethod
    def _find_auth_like_files(paths: List[Path]) -> List[Path]:
        matches: List[Path] = []
        for path in paths:
            if not path.exists() or not path.is_dir():
                continue
            for child in path.rglob("*"):
                if not child.is_file():
                    continue
                lowered = child.name.lower()
                if "auth" in lowered or "token" in lowered or "credential" in lowered:
                    matches.append(child)
        return matches

    @staticmethod
    def _hermes_env_has_provider_secret(env_file: Path) -> bool:
        if not env_file.exists() or not env_file.is_file():
            return False

        try:
            lines = env_file.read_text().splitlines()
        except OSError:
            return False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip().upper()
            value = value.strip().strip('"').strip("'")
            if not value or value.startswith(("your-", "sk-your", "<", "${")):
                continue
            if key.endswith(("API_KEY", "_TOKEN", "_KEY")) or key in {
                "ANTHROPIC_TOKEN",
                "CLAUDE_CODE_OAUTH_TOKEN",
                "HF_TOKEN",
            }:
                return True

        return False

    def _status_for_claude(self, meta: ProviderMetadata) -> ProviderHostStatus:
        manager = ClaudeAccountManager(storage_dir=str(self.storage_dir))
        state_paths = self._state_paths("claude")
        existing_state_paths = [path for path in state_paths if path.exists()]
        active_account = manager.get_active_account()
        creds_path = self.storage_dir / "claude-linux" / ".credentials.json"
        accounts = manager.list_accounts()

        if active_account and creds_path.exists():
            setup_state = "ready"
            detail = f"Active Claude account: {active_account}"
        elif creds_path.exists():
            setup_state = "ready"
            detail = f"Claude credentials detected at {creds_path}"
        elif accounts:
            setup_state = "partial"
            detail = "Saved Claude accounts exist, but no active Linux credentials were detected."
        else:
            setup_state = "missing"
            detail = "No Claude credentials detected yet."

        return ProviderHostStatus(
            provider=meta.name,
            title=meta.title,
            enabled=self.provider_manager.is_enabled(meta.name),
            default_enabled=meta.default_enabled,
            explicit=self.provider_manager.has_explicit_state(meta.name),
            commands=list(meta.commands),
            host_command_path=shutil.which(meta.commands[0]) if meta.commands else None,
            setup_state=setup_state,
            detail=detail,
            state_paths=state_paths,
            existing_state_paths=existing_state_paths,
            setup_command=meta.setup_command,
            setup_hint=meta.setup_hint,
            update_command=meta.update_command,
            update_hint=meta.update_hint,
        )

    def _status_for_codex(self, meta: ProviderMetadata) -> ProviderHostStatus:
        state_paths = self._state_paths("codex")
        existing_state_paths = [path for path in state_paths if path.exists()]
        auth_file = self.home_dir / ".codex" / "auth.json"

        if os.environ.get("OPENAI_API_KEY"):
            setup_state = "ready"
            detail = "OPENAI_API_KEY is set in the host environment."
        elif auth_file.exists():
            setup_state = "ready"
            detail = f"Stored Codex auth detected at {auth_file}"
        elif self._path_has_files(self.home_dir / ".codex"):
            setup_state = "partial"
            detail = "Codex state exists, but no auth session was detected."
        else:
            setup_state = "missing"
            detail = "No Codex auth session detected yet."

        return ProviderHostStatus(
            provider=meta.name,
            title=meta.title,
            enabled=self.provider_manager.is_enabled(meta.name),
            default_enabled=meta.default_enabled,
            explicit=self.provider_manager.has_explicit_state(meta.name),
            commands=list(meta.commands),
            host_command_path=shutil.which(meta.commands[0]) if meta.commands else None,
            setup_state=setup_state,
            detail=detail,
            state_paths=state_paths,
            existing_state_paths=existing_state_paths,
            setup_command=meta.setup_command,
            setup_hint=meta.setup_hint,
            update_command=meta.update_command,
            update_hint=meta.update_hint,
        )

    def _status_for_opencode(self, meta: ProviderMetadata) -> ProviderHostStatus:
        state_paths = self._state_paths("opencode")
        existing_state_paths = [path for path in state_paths if path.exists()]
        auth_like_files = self._find_auth_like_files(state_paths)

        if auth_like_files:
            setup_state = "ready"
            detail = f"OpenCode auth or token files detected under {auth_like_files[0].parent}"
        elif any(self._path_has_files(path) for path in state_paths):
            setup_state = "partial"
            detail = (
                "OpenCode state/config files exist, but no auth-like file was detected."
            )
        else:
            setup_state = "missing"
            detail = "No OpenCode state detected yet."

        return ProviderHostStatus(
            provider=meta.name,
            title=meta.title,
            enabled=self.provider_manager.is_enabled(meta.name),
            default_enabled=meta.default_enabled,
            explicit=self.provider_manager.has_explicit_state(meta.name),
            commands=list(meta.commands),
            host_command_path=shutil.which(meta.commands[0]) if meta.commands else None,
            setup_state=setup_state,
            detail=detail,
            state_paths=state_paths,
            existing_state_paths=existing_state_paths,
            setup_command=meta.setup_command,
            setup_hint=meta.setup_hint,
            update_command=meta.update_command,
            update_hint=meta.update_hint,
        )

    def _status_for_openclaw(self, meta: ProviderMetadata) -> ProviderHostStatus:
        state_paths = self._state_paths("openclaw")
        existing_state_paths = [path for path in state_paths if path.exists()]
        credentials_dir = self.home_dir / ".openclaw" / "credentials"

        if self._path_has_files(credentials_dir):
            setup_state = "ready"
            detail = f"OpenClaw credentials detected under {credentials_dir}"
        elif any(self._path_has_files(path) for path in state_paths):
            setup_state = "partial"
            detail = (
                "OpenClaw state files exist, but no credential files were detected."
            )
        else:
            setup_state = "missing"
            detail = "No OpenClaw state detected yet."

        return ProviderHostStatus(
            provider=meta.name,
            title=meta.title,
            enabled=self.provider_manager.is_enabled(meta.name),
            default_enabled=meta.default_enabled,
            explicit=self.provider_manager.has_explicit_state(meta.name),
            commands=list(meta.commands),
            host_command_path=shutil.which(meta.commands[0]) if meta.commands else None,
            setup_state=setup_state,
            detail=detail,
            state_paths=state_paths,
            existing_state_paths=existing_state_paths,
            setup_command=meta.setup_command,
            setup_hint=meta.setup_hint,
            update_command=meta.update_command,
            update_hint=meta.update_hint,
        )

    def _status_for_hermes(self, meta: ProviderMetadata) -> ProviderHostStatus:
        state_paths = self._state_paths("hermes")
        existing_state_paths = [path for path in state_paths if path.exists()]
        hermes_dir = self.home_dir / ".hermes"
        env_file = hermes_dir / ".env"
        config_file = hermes_dir / "config.yaml"
        claude_credentials = [
            self.storage_dir / "claude-linux" / ".credentials.json",
            self.home_dir / ".claude" / ".credentials.json",
        ]
        openclaw_dir = self.home_dir / ".openclaw"

        if self._hermes_env_has_provider_secret(env_file):
            setup_state = "ready"
            detail = f"Hermes provider credentials detected in {env_file}"
        elif any(path.exists() for path in claude_credentials):
            setup_state = "ready"
            detail = (
                "Claude Code credentials detected for Hermes native Anthropic auth."
            )
        elif config_file.exists() or any(
            self._path_has_files(path) for path in state_paths
        ):
            setup_state = "partial"
            detail = "Hermes state exists, but no provider API key or Claude credential file was detected."
        else:
            setup_state = "missing"
            detail = "No Hermes state detected yet."

        if openclaw_dir.exists():
            detail = (
                f"{detail} OpenClaw migration source is available at {openclaw_dir}."
            )

        return ProviderHostStatus(
            provider=meta.name,
            title=meta.title,
            enabled=self.provider_manager.is_enabled(meta.name),
            default_enabled=meta.default_enabled,
            explicit=self.provider_manager.has_explicit_state(meta.name),
            commands=list(meta.commands),
            host_command_path=shutil.which(meta.commands[0]) if meta.commands else None,
            setup_state=setup_state,
            detail=detail,
            state_paths=state_paths,
            existing_state_paths=existing_state_paths,
            setup_command=meta.setup_command,
            setup_hint=meta.setup_hint,
            update_command=meta.update_command,
            update_hint=meta.update_hint,
        )

    def get_status(self, provider: str) -> ProviderHostStatus:
        """Return host-side status for one provider."""

        meta = self._metadata(provider)
        if meta.name == "claude":
            return self._status_for_claude(meta)
        if meta.name == "codex":
            return self._status_for_codex(meta)
        if meta.name == "opencode":
            return self._status_for_opencode(meta)
        if meta.name == "openclaw":
            return self._status_for_openclaw(meta)
        if meta.name == "hermes":
            return self._status_for_hermes(meta)
        raise ValueError(f"Unsupported provider '{provider}'")

    def list_statuses(self, *, enabled_only: bool = False) -> List[ProviderHostStatus]:
        """Return provider statuses for all known providers."""

        providers = list(self.provider_manager.known_providers())
        if enabled_only:
            providers = [
                provider
                for provider in providers
                if self.provider_manager.is_enabled(provider)
            ]
        return [self.get_status(provider) for provider in providers]

    def ensure_enabled(self, provider: str) -> bool:
        """Enable the provider if needed. Returns True when state changed."""

        canonical = self._metadata(provider).name
        if self.provider_manager.is_enabled(canonical):
            return False
        self.provider_manager.set_enabled(
            canonical, True, source="providers-host-command"
        )
        return True

    def _devcontainer_service(self) -> DevContainerService:
        return DevContainerService(
            self.working_directory,
            provider_storage_dir=self.storage_dir,
        )

    def run_setup(self, provider: str, *, rebuild: bool = False) -> int:
        """Run the provider's interactive setup/auth command inside the container."""

        status = self.get_status(provider)
        if not status.setup_command:
            raise ValueError(
                f"Provider '{status.provider}' does not define a setup command"
            )
        self.ensure_enabled(status.provider)
        return self._devcontainer_service().run_in_container(
            command=status.setup_command,
            rebuild=rebuild,
            interactive=True,
        )

    def run_update(self, provider: str, *, rebuild: bool = False) -> int:
        """Run the provider's update command inside the container."""

        status = self.get_status(provider)
        if not status.update_command:
            raise ValueError(
                f"Provider '{status.provider}' does not define an update command"
            )
        self.ensure_enabled(status.provider)
        return self._devcontainer_service().run_provider_update(
            status.provider,
            status.update_command,
            rebuild=rebuild,
        )
