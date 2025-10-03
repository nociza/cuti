"""
Claude Account Manager - Manages multiple Claude accounts for container usage.
Supports Claude Code OAuth, Anthropic API keys, and AWS Bedrock credentials.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime

# Credential types
CredentialType = Literal["oauth", "anthropic_api", "bedrock_api"]


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
                api_key_file = account_dir / ".api_keys.json"
                has_oauth_creds = creds_file.exists()
                has_api_keys = api_key_file.exists()
                
                # Check if any credentials exist (OAuth or API keys)
                has_creds = has_oauth_creds or has_api_keys
                
                # Try to get account info from credentials
                account_type = info.get("type", "unknown")
                if has_oauth_creds:
                    try:
                        creds = json.loads(creds_file.read_text())
                        if "claudeAiOauth" in creds:
                            oauth = creds["claudeAiOauth"]
                            account_type = oauth.get("subscriptionType", "Pro").capitalize()
                    except Exception:
                        pass
                elif has_api_keys:
                    # For API key accounts, show the credential type
                    credential_type = info.get("credential_type", "API")
                    if credential_type == "anthropic_api":
                        account_type = "API (Anthropic)"
                    elif credential_type == "bedrock_api":
                        account_type = "API (Bedrock)"
                    else:
                        account_type = "API"
                
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
        
        # Check for API key credentials
        api_key_file = account_dir / ".api_keys.json"
        if api_key_file.exists():
            try:
                api_keys = json.loads(api_key_file.read_text())
                info["credential_type"] = account_meta.get("credential_type", "oauth")
                info["has_api_keys"] = True
                info["api_key_types"] = list(api_keys.keys())
            except Exception:
                pass
        
        return info
    
    def save_api_key(
        self,
        name: str,
        api_key: str,
        provider: CredentialType = "anthropic_api",
        region: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        use_bearer_token: bool = True
    ) -> bool:
        """Save API key credentials for an account.
        
        Args:
            name: Account name
            api_key: The API key (for Anthropic) or bearer token/model ID (for Bedrock)
            provider: Type of credential (anthropic_api or bedrock_api)
            region: AWS region (for Bedrock only)
            access_key_id: AWS access key ID (for Bedrock with access keys)
            secret_access_key: AWS secret access key (for Bedrock with access keys)
            use_bearer_token: If True, use AWS_BEARER_TOKEN_BEDROCK (preferred for Bedrock)
        """
        # Create account directory if it doesn't exist
        account_dir = self.accounts_dir / name
        account_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create API keys file
        api_key_file = account_dir / ".api_keys.json"
        if api_key_file.exists():
            api_keys = json.loads(api_key_file.read_text())
        else:
            api_keys = {}
        
        # Save credentials based on provider
        if provider == "anthropic_api":
            api_keys["anthropic"] = {
                "api_key": api_key,
                "provider": "anthropic",
                "created": datetime.now().isoformat()
            }
        elif provider == "bedrock_api":
            # Support two modes: Bearer token (preferred) or access keys
            if use_bearer_token:
                # Option D: Bedrock API key (bearer token)
                api_keys["bedrock"] = {
                    "bearer_token": api_key,
                    "region": region or "us-east-1",
                    "provider": "bedrock",
                    "auth_method": "bearer_token",
                    "created": datetime.now().isoformat()
                }
            else:
                # Option B: AWS access keys
                if not all([region, access_key_id, secret_access_key]):
                    raise ValueError("Bedrock with access keys requires region, access_key_id, and secret_access_key")
                api_keys["bedrock"] = {
                    "region": region,
                    "access_key_id": access_key_id,
                    "secret_access_key": secret_access_key,
                    "provider": "bedrock",
                    "auth_method": "access_keys",
                    "created": datetime.now().isoformat()
                }
        
        # Save API keys file with restricted permissions
        api_key_file.write_text(json.dumps(api_keys, indent=2))
        api_key_file.chmod(0o600)  # User read/write only
        
        # Update metadata
        metadata = self._load_metadata()
        if "accounts" not in metadata:
            metadata["accounts"] = {}
        
        if name not in metadata["accounts"]:
            metadata["accounts"][name] = {
                "created": datetime.now().isoformat(),
                "last_used": "never",
                "type": "API",
                "credential_type": provider
            }
        else:
            metadata["accounts"][name]["credential_type"] = provider
            metadata["accounts"][name]["type"] = "API"
        
        self._save_metadata(metadata)
        return True
    
    def get_api_key(self, name: str, provider: str = "anthropic") -> Optional[Dict[str, Any]]:
        """Get API key credentials for an account.
        
        Args:
            name: Account name
            provider: Provider name ('anthropic' or 'bedrock')
        
        Returns:
            Dictionary with API key credentials or None
        """
        account_dir = self.accounts_dir / name
        api_key_file = account_dir / ".api_keys.json"
        
        if not api_key_file.exists():
            return None
        
        try:
            api_keys = json.loads(api_key_file.read_text())
            return api_keys.get(provider)
        except Exception:
            return None
    
    def delete_api_key(self, name: str, provider: str) -> bool:
        """Delete specific API key from an account.
        
        Args:
            name: Account name
            provider: Provider name ('anthropic' or 'bedrock')
        """
        account_dir = self.accounts_dir / name
        api_key_file = account_dir / ".api_keys.json"
        
        if not api_key_file.exists():
            return False
        
        try:
            api_keys = json.loads(api_key_file.read_text())
            if provider in api_keys:
                del api_keys[provider]
                
                if api_keys:
                    # Still has other API keys
                    api_key_file.write_text(json.dumps(api_keys, indent=2))
                else:
                    # No more API keys, remove file
                    api_key_file.unlink()
                
                return True
        except Exception:
            return False
        
        return False
    
    def list_api_keys(self, name: str) -> List[str]:
        """List all API key providers for an account.
        
        Args:
            name: Account name
        
        Returns:
            List of provider names
        """
        account_dir = self.accounts_dir / name
        api_key_file = account_dir / ".api_keys.json"
        
        if not api_key_file.exists():
            return []
        
        try:
            api_keys = json.loads(api_key_file.read_text())
            return list(api_keys.keys())
        except Exception:
            return []
    
    def get_env_vars(self, name: str, include_claude_code_vars: bool = True) -> Dict[str, str]:
        """Get environment variables for an account's API keys.
        
        Args:
            name: Account name
            include_claude_code_vars: If True, include Claude Code specific vars
        
        Returns:
            Dictionary of environment variable names and values
        """
        env_vars = {}
        
        # Get all API keys for the account
        providers = self.list_api_keys(name)
        
        for provider in providers:
            api_key_info = self.get_api_key(name, provider)
            if not api_key_info:
                continue
            
            if provider == "anthropic":
                # Anthropic API key
                env_vars["ANTHROPIC_API_KEY"] = api_key_info.get("api_key", "")
            
            elif provider == "bedrock":
                # AWS Bedrock credentials
                auth_method = api_key_info.get("auth_method", "bearer_token")
                region = api_key_info.get("region", "us-east-1")
                
                if auth_method == "bearer_token":
                    # Option D: Bearer token (preferred)
                    env_vars["AWS_BEARER_TOKEN_BEDROCK"] = api_key_info.get("bearer_token", "")
                    env_vars["AWS_REGION"] = region
                else:
                    # Option B: Access keys
                    env_vars["AWS_ACCESS_KEY_ID"] = api_key_info.get("access_key_id", "")
                    env_vars["AWS_SECRET_ACCESS_KEY"] = api_key_info.get("secret_access_key", "")
                    env_vars["AWS_REGION"] = region
                
                # Add Claude Code-specific Bedrock variables
                if include_claude_code_vars:
                    env_vars["CLAUDE_CODE_USE_BEDROCK"] = "1"
                    # Optional: Allow override for small/fast model region
                    # User can customize this per account if needed
                    # env_vars["ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION"] = region
        
        return env_vars
    
    def get_env_vars_to_unset(self) -> list[str]:
        """Get list of all environment variables that should be unset when switching accounts.
        
        Returns:
            List of environment variable names to unset
        """
        return [
            # Anthropic
            "ANTHROPIC_API_KEY",
            # Bedrock
            "AWS_BEARER_TOKEN_BEDROCK",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION",
            "AWS_SESSION_TOKEN",
            # Claude Code Bedrock
            "CLAUDE_CODE_USE_BEDROCK",
            "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION",
        ]
    
    def generate_env_script(self, name: str, unset_first: bool = True) -> str:
        """Generate a shell script to export environment variables.
        
        Args:
            name: Account name
            unset_first: If True, unset variables before setting new ones
        
        Returns:
            Shell script content
        """
        env_vars = self.get_env_vars(name)
        
        if not env_vars:
            return "# No API keys configured for this account\n"
        
        lines = [
            "#!/bin/bash",
            f"# Environment variables for account: {name}",
            f"# Generated: {datetime.now().isoformat()}",
            ""
        ]
        
        # Optionally unset all variables first to avoid conflicts
        if unset_first:
            lines.append("# Unset previous API key variables")
            for var in self.get_env_vars_to_unset():
                lines.append(f"unset {var}")
            lines.append("")
        
        # Set new variables
        lines.append("# Set new API key variables")
        for key, value in env_vars.items():
            lines.append(f'export {key}="{value}"')
        
        lines.append("")
        lines.append("# Verify variables are set")
        lines.append('echo "✓ Environment variables configured for account: {}"'.format(name))
        
        return "\n".join(lines)
    
    def generate_unset_script(self) -> str:
        """Generate a shell script to unset all API key environment variables.
        
        Returns:
            Shell script content
        """
        lines = [
            "#!/bin/bash",
            "# Unset all Claude API key environment variables",
            f"# Generated: {datetime.now().isoformat()}",
            ""
        ]
        
        for var in self.get_env_vars_to_unset():
            lines.append(f"unset {var}")
        
        lines.append("")
        lines.append('echo "✓ All Claude API key variables unset"')
        
        return "\n".join(lines)
    
    def save_env_script(self, name: str) -> Optional[Path]:
        """Save environment variables script for an account.
        
        Args:
            name: Account name
        
        Returns:
            Path to the script file or None if no API keys
        """
        script_content = self.generate_env_script(name)
        
        if "# No API keys configured" in script_content:
            return None
        
        # Save to account directory
        account_dir = self.accounts_dir / name
        script_file = account_dir / "env.sh"
        
        script_file.write_text(script_content)
        script_file.chmod(0o600)  # User read/write only
        
        return script_file
