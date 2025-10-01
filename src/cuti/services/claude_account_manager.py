"""
Claude Account Manager - Manages multiple Claude accounts for container usage.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class ClaudeAccountManager:
    """Manages multiple Claude Code accounts for container environments."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """Initialize the account manager."""
        # Detect if running in container and use appropriate storage path
        if storage_dir is None:
            if os.environ.get("CUTI_IN_CONTAINER") == "true":
                # In container, the .cuti directory is mounted and symlinked
                # Use the symlink at ~/.cuti which points to .cuti-shared
                storage_dir = "~/.cuti"
            else:
                storage_dir = "~/.cuti"
        
        self.storage_dir = Path(storage_dir).expanduser()
        self.accounts_dir = self.storage_dir / "claude-accounts"
        self.active_dir = self.storage_dir / "claude-linux"
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata file to track account info
        self.metadata_file = self.accounts_dir / "accounts.json"
        self._ensure_metadata()
    
    def _ensure_metadata(self):
        """Ensure accounts metadata file exists."""
        if not self.metadata_file.exists():
            self.metadata_file.write_text(json.dumps({
                "accounts": {},
                "active": None,
                "last_updated": datetime.now().isoformat()
            }, indent=2))
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load accounts metadata."""
        try:
            return json.loads(self.metadata_file.read_text())
        except Exception:
            return {
                "accounts": {},
                "active": None,
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save accounts metadata."""
        metadata["last_updated"] = datetime.now().isoformat()
        self.metadata_file.write_text(json.dumps(metadata, indent=2))
    
    def list_accounts(self, include_backups: bool = False) -> List[Dict[str, Any]]:
        """List all saved Claude accounts.
        
        Args:
            include_backups: If True, include auto-generated backup accounts
        """
        metadata = self._load_metadata()
        accounts = []
        
        for name, info in metadata.get("accounts", {}).items():
            # Skip backup accounts unless explicitly requested
            if not include_backups and name.startswith("backup_"):
                continue
                
            account_dir = self.accounts_dir / name
            if account_dir.exists():
                creds_file = account_dir / ".credentials.json"
                has_creds = creds_file.exists()
                
                # Try to get account info from credentials
                account_type = info.get("type", "unknown")
                if has_creds:
                    try:
                        creds = json.loads(creds_file.read_text())
                        if "claudeAiOauth" in creds:
                            oauth = creds["claudeAiOauth"]
                            account_type = oauth.get("subscriptionType", "Pro").capitalize()
                    except Exception:
                        pass
                
                accounts.append({
                    "name": name,
                    "type": account_type,
                    "created": info.get("created", "unknown"),
                    "last_used": info.get("last_used", "never"),
                    "has_credentials": has_creds,
                    "is_active": name == metadata.get("active"),
                    "is_backup": name.startswith("backup_")
                })
        
        return sorted(accounts, key=lambda x: x["name"])
    
    def count_backup_accounts(self) -> int:
        """Count the number of auto-generated backup accounts."""
        metadata = self._load_metadata()
        return sum(1 for name in metadata.get("accounts", {}).keys() if name.startswith("backup_"))
    
    def get_active_account(self) -> Optional[str]:
        """Get the currently active account name."""
        metadata = self._load_metadata()
        return metadata.get("active")
    
    def save_account(self, name: str) -> bool:
        """Save current credentials as a named account."""
        # Validate name
        if not name or not name.strip():
            raise ValueError("Account name cannot be empty")
        
        # Sanitize name for filesystem
        safe_name = "".join(c for c in name if c.isalnum() or c in ('-', '_', ' ')).strip()
        if not safe_name:
            raise ValueError("Account name must contain valid characters")
        
        # Check if credentials exist
        creds_file = self.active_dir / ".credentials.json"
        if not creds_file.exists():
            raise ValueError("No credentials found. Please authenticate with 'claude login' first.")
        
        # Create account directory
        account_dir = self.accounts_dir / safe_name
        account_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files from active directory
        for item in self.active_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, account_dir / item.name)
            elif item.is_dir():
                dest_dir = account_dir / item.name
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(item, dest_dir)
        
        # Update metadata
        metadata = self._load_metadata()
        if "accounts" not in metadata:
            metadata["accounts"] = {}
        
        # Get account type from credentials
        account_type = "Pro"
        try:
            creds = json.loads(creds_file.read_text())
            if "claudeAiOauth" in creds:
                oauth = creds["claudeAiOauth"]
                account_type = oauth.get("subscriptionType", "Pro").capitalize()
        except Exception:
            pass
        
        existing_created = None
        if safe_name in metadata["accounts"]:
            existing_created = metadata["accounts"][safe_name].get("created")
        
        metadata["accounts"][safe_name] = {
            "created": existing_created or datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "type": account_type
        }
        metadata["active"] = safe_name
        
        self._save_metadata(metadata)
        return True
    
    def use_account(self, name: str) -> bool:
        """Load credentials from a named account."""
        account_dir = self.accounts_dir / name
        
        if not account_dir.exists():
            raise ValueError(f"Account '{name}' not found")
        
        creds_file = account_dir / ".credentials.json"
        if not creds_file.exists():
            raise ValueError(f"Account '{name}' has no credentials")
        
        # Clear current credentials directory
        for item in self.active_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        
        # Copy account files to active directory
        for item in account_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, self.active_dir / item.name)
            elif item.is_dir():
                dest_dir = self.active_dir / item.name
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(item, dest_dir)
        
        # Update metadata
        metadata = self._load_metadata()
        metadata["active"] = name
        if name in metadata.get("accounts", {}):
            metadata["accounts"][name]["last_used"] = datetime.now().isoformat()
        
        self._save_metadata(metadata)
        return True
    
    def delete_account(self, name: str) -> bool:
        """Delete a named account."""
        account_dir = self.accounts_dir / name
        
        if not account_dir.exists():
            raise ValueError(f"Account '{name}' not found")
        
        # Remove account directory
        shutil.rmtree(account_dir)
        
        # Update metadata
        metadata = self._load_metadata()
        if name in metadata.get("accounts", {}):
            del metadata["accounts"][name]
        
        # Clear active if this was the active account
        if metadata.get("active") == name:
            metadata["active"] = None
        
        self._save_metadata(metadata)
        return True
    
    def new_account(self) -> bool:
        """Prepare for creating a new account by clearing current credentials."""
        # Back up current credentials if they exist
        creds_file = self.active_dir / ".credentials.json"
        backup_needed = creds_file.exists()
        
        if backup_needed:
            # Find a unique backup name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            counter = 1
            while (self.accounts_dir / backup_name).exists():
                backup_name = f"backup_{timestamp}_{counter}"
                counter += 1
            
            # Save current credentials as backup
            self.save_account(backup_name)
        
        # Clear all credential and session files
        # These files contain authentication data that needs to be removed
        credential_files = [
            ".credentials.json",    # Main credentials file
            ".claude.json",         # Claude configuration (may contain tokens)
            "session.json",         # Session data
            ".session",             # Alternative session file
        ]
        
        for filename in credential_files:
            file_path = self.active_dir / filename
            if file_path.exists():
                file_path.unlink()
        
        # Also clear any backup or corrupted credential files
        # These may be created by Claude and can contain auth tokens
        for item in self.active_dir.iterdir():
            if item.is_file():
                # Remove backup/corrupted versions of credential files
                if any(pattern in item.name for pattern in [
                    ".credentials", ".claude.json", ".session", "session.json"
                ]) and any(suffix in item.name for suffix in [
                    ".backup", ".bak", ".old", ".corrupted"
                ]):
                    item.unlink()
        
        # Clear session-related directories
        session_dirs = [
            "sessions",         # Active sessions
            "shell-snapshots",  # Shell session snapshots
            "statsig",          # Analytics/session tracking
        ]
        
        for dirname in session_dirs:
            dir_path = self.active_dir / dirname
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path)
                # Recreate empty directory to maintain structure
                dir_path.mkdir(parents=True, exist_ok=True)
        
        # Clear active account in metadata
        metadata = self._load_metadata()
        metadata["active"] = None
        self._save_metadata(metadata)
        
        return backup_needed
    
    def get_account_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an account."""
        account_dir = self.accounts_dir / name
        
        if not account_dir.exists():
            return None
        
        metadata = self._load_metadata()
        account_meta = metadata.get("accounts", {}).get(name, {})
        
        creds_file = account_dir / ".credentials.json"
        has_creds = creds_file.exists()
        
        info = {
            "name": name,
            "path": str(account_dir),
            "created": account_meta.get("created", "unknown"),
            "last_used": account_meta.get("last_used", "never"),
            "has_credentials": has_creds,
            "is_active": name == metadata.get("active"),
            "type": account_meta.get("type", "unknown")
        }
        
        # Get additional info from credentials if available
        if has_creds:
            try:
                creds = json.loads(creds_file.read_text())
                if "claudeAiOauth" in creds:
                    oauth = creds["claudeAiOauth"]
                    info["subscription_type"] = oauth.get("subscriptionType", "Pro")
                    info["email"] = oauth.get("email", "unknown")
            except Exception:
                pass
        
        return info

