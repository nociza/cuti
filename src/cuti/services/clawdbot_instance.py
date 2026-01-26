"""Clawdbot instance management for workspace configuration switching."""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ClawdbotInstance:
    """Represents a running or recently running Clawdbot instance."""

    instance_id: str
    pid: Optional[int]
    port: int
    workspace_path: str
    workspace_slug: str
    started_at: str
    container_id: Optional[str] = None
    last_heartbeat: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClawdbotInstance":
        """Create from dictionary."""
        return cls(
            instance_id=data.get("instance_id", ""),
            pid=data.get("pid"),
            port=data.get("port", 0),
            workspace_path=data.get("workspace_path", ""),
            workspace_slug=data.get("workspace_slug", ""),
            started_at=data.get("started_at", ""),
            container_id=data.get("container_id"),
            last_heartbeat=data.get("last_heartbeat"),
        )


class ClawdbotInstanceManager:
    """
    Manages Clawdbot instance state and configuration.

    Responsibilities:
    - Persist instance state across terminals
    - Detect running instances via port/PID checks
    - Update clawdbot.json with workspace configuration
    - Clean up stale instance entries

    Workspace Strategy:
    - Clawdbot agents work directly in /workspace (the mounted project)
    - No separate per-project workspace directories
    - SOUL.md, AGENTS.md can optionally be added to the project
    - Credentials and global config persist in ~/.clawdbot
    """

    SCHEMA_VERSION = 1
    INSTANCE_STATE_FILE = "instance-state.json"
    # Clawdbot agents work in /workspace (the mounted project directory)
    CONTAINER_WORKSPACE_PATH = "/workspace"

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or Path.home() / ".cuti" / "clawdbot"
        self.state_path = self.storage_dir / self.INSTANCE_STATE_FILE
        self.config_path = self.storage_dir / "config" / "clawdbot.json"
        self._state: Dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "instances": {},
            "updated_at": None,
        }
        self._load_state()

    # ------------------------------------------------------------------
    # State Management
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        """Load state from disk, handling corruption gracefully."""
        if not self.state_path.exists():
            return

        try:
            decoded = json.loads(self.state_path.read_text())
        except json.JSONDecodeError:
            # Backup corrupt file and start fresh
            backup = self.state_path.with_suffix(".corrupt")
            try:
                self.state_path.rename(backup)
            except OSError:
                pass
            return

        if isinstance(decoded, dict):
            # Migrate if schema version differs
            file_version = decoded.get("schema_version", 0)
            if file_version < self.SCHEMA_VERSION:
                decoded = self._migrate_state(decoded, file_version)
            self._state.update(decoded)

    def _migrate_state(self, old_state: Dict[str, Any], from_version: int) -> Dict[str, Any]:
        """Migrate state from older schema versions."""
        # Currently only version 1, so no migration needed
        old_state["schema_version"] = self.SCHEMA_VERSION
        return old_state

    def _save_state(self) -> None:
        """Persist state to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._state["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.state_path.write_text(json.dumps(self._state, indent=2))

    # ------------------------------------------------------------------
    # Instance Detection
    # ------------------------------------------------------------------

    def detect_running_instances(self) -> List[ClawdbotInstance]:
        """Return list of instances that appear to still be running."""
        self._cleanup_stale_instances()

        running = []
        instances_data = self._state.get("instances", {})

        for instance_id, data in instances_data.items():
            instance = ClawdbotInstance.from_dict(data)
            if self._is_instance_alive(instance):
                running.append(instance)

        return running

    def _is_instance_alive(self, instance: ClawdbotInstance) -> bool:
        """Check if an instance appears to still be running."""
        # Check if port is in use
        if not self.is_port_in_use(instance.port):
            return False

        # Check if PID is alive (if we have one)
        if instance.pid and not self._is_process_alive(instance.pid):
            return False

        return True

    def is_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        """Return True if the port is currently bound."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return False
            except OSError:
                return True

    def _is_process_alive(self, pid: int) -> bool:
        """Check if a process with given PID exists."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def find_instance_by_port(self, port: int) -> Optional[ClawdbotInstance]:
        """Find a running instance using the specified port."""
        running = self.detect_running_instances()
        for instance in running:
            if instance.port == port:
                return instance
        return None

    def _cleanup_stale_instances(self) -> None:
        """Remove entries for instances that are no longer running."""
        instances_data = self._state.get("instances", {})
        stale_ids = []

        for instance_id, data in instances_data.items():
            instance = ClawdbotInstance.from_dict(data)
            port_in_use = self.is_port_in_use(instance.port)
            pid_alive = instance.pid and self._is_process_alive(instance.pid)

            # Instance is stale if port is free or PID is dead
            if not port_in_use or (instance.pid and not pid_alive):
                stale_ids.append(instance_id)

        if stale_ids:
            for instance_id in stale_ids:
                del instances_data[instance_id]
            self._state["instances"] = instances_data
            self._save_state()

    # ------------------------------------------------------------------
    # Instance Registration
    # ------------------------------------------------------------------

    def register_instance(
        self,
        port: int,
        workspace_path: Path,
        workspace_slug: str,
        pid: Optional[int] = None,
        container_id: Optional[str] = None,
    ) -> str:
        """Register a new instance and return its ID."""
        instance_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat() + "Z"

        instance = ClawdbotInstance(
            instance_id=instance_id,
            pid=pid,
            port=port,
            workspace_path=str(workspace_path),
            workspace_slug=workspace_slug,
            started_at=now,
            container_id=container_id,
            last_heartbeat=now,
        )

        instances_data = self._state.setdefault("instances", {})
        instances_data[instance_id] = instance.to_dict()
        self._save_state()

        return instance_id

    def unregister_instance(self, instance_id: str) -> None:
        """Remove an instance from tracking."""
        instances_data = self._state.get("instances", {})
        if instance_id in instances_data:
            del instances_data[instance_id]
            self._save_state()

    def update_heartbeat(self, instance_id: str) -> None:
        """Update the heartbeat timestamp for an instance."""
        instances_data = self._state.get("instances", {})
        if instance_id in instances_data:
            instances_data[instance_id]["last_heartbeat"] = datetime.utcnow().isoformat() + "Z"
            self._save_state()

    # ------------------------------------------------------------------
    # Configuration Management
    # ------------------------------------------------------------------

    def generate_workspace_slug(self, workspace_path: Path) -> str:
        """Generate a stable slug for a workspace path."""
        resolved = workspace_path.resolve()
        digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:8]
        base_name = resolved.name or "workspace"
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", base_name).strip("-") or "workspace"
        return f"{sanitized}-{digest}"

    def update_workspace_config(self) -> bool:
        """
        Update clawdbot.json to set workspace to /workspace.

        This configures Clawdbot agents to work directly in the mounted
        project directory, not a separate data directory.

        Returns True if config was updated successfully.
        """
        config_dir = self.config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config
        config: Dict[str, Any] = {}
        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text())
            except (json.JSONDecodeError, OSError):
                config = {}

        # Remove any invalid meta keys we may have added previously
        if "meta" in config:
            meta = config["meta"]
            for invalid_key in ["hostWorkspacePath", "lastUpdated"]:
                meta.pop(invalid_key, None)
            if not meta:
                del config["meta"]

        # Ensure structure exists
        if "agents" not in config:
            config["agents"] = {}
        if "defaults" not in config["agents"]:
            config["agents"]["defaults"] = {}

        # Set workspace to /workspace (the mounted project directory)
        config["agents"]["defaults"]["workspace"] = self.CONTAINER_WORKSPACE_PATH

        try:
            self.config_path.write_text(json.dumps(config, indent=2))
            return True
        except OSError:
            return False

    def get_config(self) -> Dict[str, Any]:
        """Load and return the current clawdbot.json config."""
        if not self.config_path.exists():
            return {}
        try:
            return json.loads(self.config_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
