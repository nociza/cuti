"""
API endpoints for Claude Code settings management.
"""

from typing import Dict, Any
from fastapi import APIRouter, Request
from pydantic import BaseModel


class EssentialSettings(BaseModel):
    model: str = "opus"
    cleanupPeriodDays: int = 180
    includeCoAuthoredBy: bool = False
    forceLoginMethod: str = "claudeai"
    telemetry: bool = False
    autoInstall: bool = True
    maintainWorkingDir: bool = True
    costWarnings: bool = True
    errorReporting: bool = True
    autoUpdater: bool = True


claude_settings_router = APIRouter(prefix="/claude-settings", tags=["claude-settings"])


@claude_settings_router.get("/")
async def get_settings(request: Request) -> Dict[str, Any]:
    """Get current Claude Code settings."""
    settings_manager = request.app.state.claude_settings_manager
    return {
        "settings": settings_manager.get_current_settings(),
        "essential": settings_manager.get_essential_settings(),
        "path": str(settings_manager.settings_file)
    }


@claude_settings_router.get("/essential")
async def get_essential_settings(request: Request) -> Dict[str, Any]:
    """Get essential Claude Code settings for UI."""
    settings_manager = request.app.state.claude_settings_manager
    return settings_manager.get_essential_settings()


@claude_settings_router.post("/essential")
async def update_essential_settings(
    request: Request,
    settings: EssentialSettings
) -> Dict[str, Any]:
    """Update essential Claude Code settings from UI."""
    settings_manager = request.app.state.claude_settings_manager
    result = settings_manager.set_essential_settings(settings.dict())
    
    if result["success"]:
        return {
            "success": True,
            "message": "Settings updated successfully",
            "settings": settings_manager.get_essential_settings()
        }
    else:
        return result


@claude_settings_router.post("/initialize")
async def initialize_settings(request: Request) -> Dict[str, Any]:
    """Initialize project with default Claude settings."""
    settings_manager = request.app.state.claude_settings_manager
    return settings_manager.initialize_project_settings()


@claude_settings_router.put("/")
async def update_all_settings(
    request: Request,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """Update all Claude Code settings."""
    settings_manager = request.app.state.claude_settings_manager
    return settings_manager.save_settings(settings)