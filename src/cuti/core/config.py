"""
Configuration management for cuti.
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class CutiConfig:
    """Configuration class for cuti system."""
    
    storage_dir: str = "~/.cuti"
    claude_command: str = "claude"
    check_interval: int = 30
    timeout: int = 3600
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    max_retries: int = 3
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "CutiConfig":
        """Load configuration from file and environment variables."""
        config = cls()
        
        # Load from config file if it exists
        if config_path is None:
            config_path = str(Path(config.storage_dir).expanduser() / "config.json")
        
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                
                for key, value in file_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            except Exception as e:
                print(f"Warning: Could not load config file {config_path}: {e}")
        
        # Override with environment variables
        env_mappings = {
            "CLAUDE_QUEUE_STORAGE_DIR": "storage_dir",
            "CLAUDE_QUEUE_CLAUDE_COMMAND": "claude_command", 
            "CLAUDE_QUEUE_CHECK_INTERVAL": "check_interval",
            "CLAUDE_QUEUE_TIMEOUT": "timeout",
            "CLAUDE_QUEUE_WEB_HOST": "web_host",
            "CLAUDE_QUEUE_WEB_PORT": "web_port",
            "CLAUDE_QUEUE_MAX_RETRIES": "max_retries",
        }
        
        for env_var, attr_name in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if attr_name in ["check_interval", "timeout", "web_port", "max_retries"]:
                    try:
                        setattr(config, attr_name, int(env_value))
                    except ValueError:
                        print(f"Warning: Invalid integer value for {env_var}: {env_value}")
                else:
                    setattr(config, attr_name, env_value)
        
        return config
    
    def save(self, config_path: Optional[str] = None) -> bool:
        """Save configuration to file."""
        if config_path is None:
            config_dir = Path(self.storage_dir).expanduser()
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = str(config_dir / "config.json")
        
        try:
            with open(config_path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)