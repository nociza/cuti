"""
Claude Code Settings Manager - Manages .claude/settings.local.json configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ClaudeSettingsManager:
    """Manages Claude Code settings for projects."""
    
    # Default settings based on user's configuration
    DEFAULT_SETTINGS = {
        "cleanupPeriodDays": 180,
        "env": {
            "CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL": "0",
            "CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR": "1",
            "CLAUDE_CODE_ENABLE_TELEMETRY": "0",
            "DISABLE_TELEMETRY": "1",
            "DISABLE_AUTOUPDATER": "0",
            "DISABLE_BUG_COMMAND": "0",
            "DISABLE_COST_WARNINGS": "0",
            "DISABLE_ERROR_REPORTING": "0",
            "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "0"
        },
        "includeCoAuthoredBy": False,
        "model": "opus",
        "forceLoginMethod": "claudeai"
    }
    
    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the settings manager."""
        self.working_dir = Path(working_directory) if working_directory else Path.cwd()
        self.claude_dir = self.working_dir / ".claude"
        self.settings_file = self.claude_dir / "settings.local.json"
        self.global_settings_file = Path.home() / ".claude" / "settings.json"
    
    def ensure_claude_directory(self) -> bool:
        """Ensure .claude directory exists in the project."""
        if not self.claude_dir.exists():
            try:
                self.claude_dir.mkdir(parents=True, exist_ok=True)
                return True
            except Exception as e:
                print(f"Error creating .claude directory: {e}")
                return False
        return True
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from file or defaults."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading settings: {e}")
        
        # Check global settings
        if self.global_settings_file.exists():
            try:
                with open(self.global_settings_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Save settings to local file."""
        if not self.ensure_claude_directory():
            return {
                "success": False,
                "message": "Failed to create .claude directory"
            }
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            return {
                "success": True,
                "message": "Settings saved successfully",
                "path": str(self.settings_file)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error saving settings: {str(e)}"
            }
    
    def update_setting(self, key: str, value: Any) -> Dict[str, Any]:
        """Update a specific setting."""
        settings = self.get_current_settings()
        
        # Handle nested keys (e.g., "env.CLAUDE_CODE_ENABLE_TELEMETRY")
        if '.' in key:
            keys = key.split('.')
            current = settings
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
        else:
            settings[key] = value
        
        return self.save_settings(settings)
    
    def initialize_project_settings(self) -> Dict[str, Any]:
        """Initialize project with default Claude settings."""
        if self.settings_file.exists():
            return {
                "success": False,
                "message": "Settings file already exists",
                "path": str(self.settings_file)
            }
        
        return self.save_settings(self.DEFAULT_SETTINGS)
    
    def get_essential_settings(self) -> Dict[str, Any]:
        """Get essential Claude settings for UI display."""
        settings = self.get_current_settings()
        
        return {
            "model": settings.get("model", "opus"),
            "cleanupPeriodDays": settings.get("cleanupPeriodDays", 180),
            "includeCoAuthoredBy": settings.get("includeCoAuthoredBy", False),
            "forceLoginMethod": settings.get("forceLoginMethod", "claudeai"),
            "telemetry": settings.get("env", {}).get("CLAUDE_CODE_ENABLE_TELEMETRY", "0") == "1",
            "autoInstall": settings.get("env", {}).get("CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL", "0") == "0",
            "maintainWorkingDir": settings.get("env", {}).get("CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR", "1") == "1",
            "costWarnings": settings.get("env", {}).get("DISABLE_COST_WARNINGS", "0") == "0",
            "errorReporting": settings.get("env", {}).get("DISABLE_ERROR_REPORTING", "0") == "0",
            "autoUpdater": settings.get("env", {}).get("DISABLE_AUTOUPDATER", "0") == "0"
        }
    
    def set_essential_settings(self, essential: Dict[str, Any]) -> Dict[str, Any]:
        """Set essential settings from UI."""
        settings = self.get_current_settings()
        
        # Update main settings
        if "model" in essential:
            settings["model"] = essential["model"]
        if "cleanupPeriodDays" in essential:
            settings["cleanupPeriodDays"] = essential["cleanupPeriodDays"]
        if "includeCoAuthoredBy" in essential:
            settings["includeCoAuthoredBy"] = essential["includeCoAuthoredBy"]
        if "forceLoginMethod" in essential:
            settings["forceLoginMethod"] = essential["forceLoginMethod"]
        
        # Update environment variables
        if "env" not in settings:
            settings["env"] = {}
        
        if "telemetry" in essential:
            settings["env"]["CLAUDE_CODE_ENABLE_TELEMETRY"] = "1" if essential["telemetry"] else "0"
            settings["env"]["DISABLE_TELEMETRY"] = "0" if essential["telemetry"] else "1"
        
        if "autoInstall" in essential:
            settings["env"]["CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL"] = "0" if essential["autoInstall"] else "1"
        
        if "maintainWorkingDir" in essential:
            settings["env"]["CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR"] = "1" if essential["maintainWorkingDir"] else "0"
        
        if "costWarnings" in essential:
            settings["env"]["DISABLE_COST_WARNINGS"] = "0" if essential["costWarnings"] else "1"
        
        if "errorReporting" in essential:
            settings["env"]["DISABLE_ERROR_REPORTING"] = "0" if essential["errorReporting"] else "1"
        
        if "autoUpdater" in essential:
            settings["env"]["DISABLE_AUTOUPDATER"] = "0" if essential["autoUpdater"] else "1"
        
        return self.save_settings(settings)