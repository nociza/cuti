"""
Claude Code authorization status API.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/claude-status", tags=["claude-status"])


@router.get("")
async def get_claude_status() -> Dict[str, Any]:
    """Check Claude Code authorization status."""
    try:
        # Check if claude command exists (check both claude and claude-code)
        # Use shell=True to get the full environment
        claude_cmd = None
        for cmd in ["claude", "claude-code"]:
            result = subprocess.run(
                f"which {cmd}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                claude_cmd = cmd
                break
        
        if not claude_cmd:
            return {
                "installed": False,
                "authorized": False,
                "error": "Claude Code not installed"
            }
        
        # Check if .claude config exists
        claude_config = Path.home() / ".claude"
        config_exists = claude_config.exists()
        
        # Try to check authorization status
        # Claude Code stores auth in various possible locations
        authorized = False
        subscription_plan = None
        
        if config_exists:
            # Check multiple possible config locations
            config_locations = [
                claude_config / "config.json",
                claude_config / "config" / "claude_config.json",
                claude_config / "config" / "index.json"
            ]
            
            for config_file in config_locations:
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                            # Check for auth token or API key
                            if config.get("apiKey") or config.get("token") or config.get("accessToken"):
                                authorized = True
                                subscription_plan = config.get("plan", config.get("subscription", "Unknown"))
                                break
                    except Exception:
                        pass
            
            # Additional check: if claude can run without login prompt, it's authorized
            if not authorized:
                try:
                    test_result = subprocess.run(
                        f"{claude_cmd} --version",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    # If command succeeds without error about login, assume authorized
                    if test_result.returncode == 0 and "login" not in test_result.stderr.lower():
                        authorized = True
                except:
                    pass
        
        # Try running claude --version to verify it works
        env = os.environ.copy()
        env["CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS"] = "true"
        version_result = subprocess.run(
            f"{claude_cmd} --version",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
            env=env
        )
        
        version = version_result.stdout.strip() if version_result.returncode == 0 else "Unknown"
        
        return {
            "installed": True,
            "authorized": authorized,
            "version": version,
            "config_exists": config_exists,
            "subscription_plan": subscription_plan,
            "config_path": str(claude_config),
            "error": None if authorized else "Not authorized. Run 'claude login' to authenticate."
        }
        
    except subprocess.TimeoutExpired:
        return {
            "installed": True,
            "authorized": False,
            "error": "Claude Code command timed out"
        }
    except Exception as e:
        return {
            "installed": False,
            "authorized": False,
            "error": str(e)
        }


@router.post("/verify")
async def verify_claude_auth() -> Dict[str, Any]:
    """Verify Claude Code can actually run a command."""
    try:
        # Find the claude command
        claude_cmd = None
        for cmd in ["claude", "claude-code"]:
            check = subprocess.run(
                f"which {cmd}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if check.returncode == 0:
                claude_cmd = cmd
                break
        
        if not claude_cmd:
            return {
                "success": False,
                "message": "Claude Code not found"
            }
        
        # Try a simple claude command
        env = os.environ.copy()
        env["CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS"] = "true"
        result = subprocess.run(
            f"{claude_cmd} --help",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Claude Code is working correctly"
            }
        else:
            return {
                "success": False,
                "message": "Claude Code command failed",
                "error": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Claude Code command timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to verify Claude Code",
            "error": str(e)
        }