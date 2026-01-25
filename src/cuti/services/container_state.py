"""Persistent state tracking for dev containers across workspaces."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ContainerStateManager:
    """Maintains per-workspace+global container metadata in ~/.cuti/container-state."""

    SCHEMA_VERSION = 1

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        base_dir = Path(storage_dir or Path.home() / ".cuti" / "container-state")
        base_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = base_dir / "state.json"
        self._state: Dict[str, Any] = {"version": self.SCHEMA_VERSION, "global": {}, "workspaces": {}}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.state_path.exists():
            return
        try:
            decoded = json.loads(self.state_path.read_text())
        except json.JSONDecodeError:
            backup = self.state_path.with_suffix(".corrupt")
            self.state_path.rename(backup)
            return
        if isinstance(decoded, dict):
            self._state.update(decoded)

    def _save(self) -> None:
        self.state_path.write_text(json.dumps(self._state, indent=2))

    # ------------------------------------------------------------------
    def record_workspace(self, workspace: Path, **metadata: Any) -> None:
        """Store metadata for a workspace; merges existing values."""

        workspace_key = str(Path(workspace).resolve())
        entry = self._state.setdefault("workspaces", {}).get(workspace_key, {})
        entry.update(metadata)
        entry["last_used"] = datetime.utcnow().isoformat()
        entry["workspace"] = workspace_key
        self._state["workspaces"][workspace_key] = entry
        self._save()

    def get_workspace(self, workspace: Path) -> Dict[str, Any]:
        workspace_key = str(Path(workspace).resolve())
        return dict(self._state.get("workspaces", {}).get(workspace_key, {}))

    # ------------------------------------------------------------------
    def update_global(self, **metadata: Any) -> None:
        global_state = self._state.setdefault("global", {})
        global_state.update(metadata)
        global_state["updated_at"] = datetime.utcnow().isoformat()
        self._save()

    def get_global(self) -> Dict[str, Any]:
        return dict(self._state.get("global", {}))

