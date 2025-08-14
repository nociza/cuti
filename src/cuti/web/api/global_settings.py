"""
API endpoints for global settings and usage statistics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...services.global_data_manager import GlobalDataManager, GlobalSettings
from ...services.usage_sync_service import UsageSyncManager

router = APIRouter(prefix="/api/global", tags=["global_settings"])


class GlobalSettingsUpdate(BaseModel):
    """Model for updating global settings."""
    usage_tracking_enabled: Optional[bool] = None
    auto_cleanup_days: Optional[int] = None
    privacy_mode: Optional[bool] = None
    favorite_prompts_enabled: Optional[bool] = None
    max_storage_mb: Optional[int] = None
    claude_plan: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    theme: Optional[str] = None


class FavoritePromptCreate(BaseModel):
    """Model for creating a favorite prompt."""
    title: str
    content: str
    tags: Optional[List[str]] = []
    project_path: Optional[str] = None


class FavoritePromptUpdate(BaseModel):
    """Model for updating a favorite prompt."""
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


# Global data manager instance
_manager: Optional[GlobalDataManager] = None


def get_manager() -> GlobalDataManager:
    """Get or create global data manager instance."""
    global _manager
    if _manager is None:
        _manager = GlobalDataManager()
    return _manager


@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """Get current global settings."""
    manager = get_manager()
    settings = manager.settings
    storage_info = manager.get_storage_info()
    
    return {
        "settings": {
            "usage_tracking_enabled": settings.usage_tracking_enabled,
            "auto_cleanup_days": settings.auto_cleanup_days,
            "privacy_mode": settings.privacy_mode,
            "favorite_prompts_enabled": settings.favorite_prompts_enabled,
            "max_storage_mb": settings.max_storage_mb,
            "claude_plan": settings.claude_plan,
            "notifications_enabled": settings.notifications_enabled,
            "theme": settings.theme
        },
        "storage": storage_info
    }


@router.put("/settings")
async def update_settings(update: GlobalSettingsUpdate) -> Dict[str, str]:
    """Update global settings."""
    manager = get_manager()
    settings = manager.settings
    
    # Update settings
    if update.usage_tracking_enabled is not None:
        settings.usage_tracking_enabled = update.usage_tracking_enabled
    if update.auto_cleanup_days is not None:
        settings.auto_cleanup_days = update.auto_cleanup_days
    if update.privacy_mode is not None:
        settings.privacy_mode = update.privacy_mode
    if update.favorite_prompts_enabled is not None:
        settings.favorite_prompts_enabled = update.favorite_prompts_enabled
    if update.max_storage_mb is not None:
        settings.max_storage_mb = update.max_storage_mb
    if update.claude_plan is not None:
        settings.claude_plan = update.claude_plan
    if update.notifications_enabled is not None:
        settings.notifications_enabled = update.notifications_enabled
    if update.theme is not None:
        settings.theme = update.theme
    
    # Save settings
    manager.save_settings(settings)
    
    return {"status": "success", "message": "Settings updated"}


@router.get("/usage/stats")
async def get_usage_stats(
    days: int = Query(30, ge=1, le=365),
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """Get usage statistics."""
    manager = get_manager()
    stats = manager.get_usage_stats(days=days, project_path=project_path)
    return stats


@router.get("/usage/projects")
async def get_project_stats() -> List[Dict[str, Any]]:
    """Get usage statistics by project."""
    manager = get_manager()
    stats = manager.get_usage_stats(days=365)
    return stats.get("project_breakdown", [])


@router.post("/usage/sync")
async def sync_usage() -> Dict[str, Any]:
    """Manually trigger usage data sync."""
    imported = UsageSyncManager.sync_now()
    status = UsageSyncManager.get_status()
    
    return {
        "imported": imported,
        "status": status
    }


@router.get("/usage/sync/status")
async def get_sync_status() -> Dict[str, Any]:
    """Get sync service status."""
    return UsageSyncManager.get_status()


@router.post("/usage/sync/start")
async def start_sync_service() -> Dict[str, str]:
    """Start the background sync service."""
    UsageSyncManager.start_service()
    return {"status": "success", "message": "Sync service started"}


@router.post("/usage/sync/stop")
async def stop_sync_service() -> Dict[str, str]:
    """Stop the background sync service."""
    UsageSyncManager.stop_service()
    return {"status": "success", "message": "Sync service stopped"}


@router.get("/favorites")
async def get_favorites(
    project_path: Optional[str] = None,
    tags: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get favorite prompts."""
    manager = get_manager()
    
    if not manager.settings.favorite_prompts_enabled:
        return []
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    favorites = manager.get_favorite_prompts(
        project_path=project_path,
        tags=tag_list
    )
    
    return [
        {
            "id": f.id,
            "title": f.title,
            "content": f.content,
            "project_path": f.project_path,
            "tags": f.tags,
            "created_at": f.created_at.isoformat(),
            "last_used": f.last_used.isoformat() if f.last_used else None,
            "use_count": f.use_count
        }
        for f in favorites
    ]


@router.post("/favorites")
async def create_favorite(favorite: FavoritePromptCreate) -> Dict[str, str]:
    """Create a new favorite prompt."""
    manager = get_manager()
    
    if not manager.settings.favorite_prompts_enabled:
        raise HTTPException(status_code=400, detail="Favorite prompts are disabled")
    
    favorite_id = manager.add_favorite_prompt(
        title=favorite.title,
        content=favorite.content,
        tags=favorite.tags,
        project_path=favorite.project_path
    )
    
    return {"id": favorite_id, "status": "success"}


@router.post("/favorites/{favorite_id}/use")
async def use_favorite(favorite_id: str) -> Dict[str, str]:
    """Mark a favorite prompt as used."""
    manager = get_manager()
    
    favorites = manager.get_favorite_prompts()
    if not any(f.id == favorite_id for f in favorites):
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    manager.use_favorite_prompt(favorite_id)
    
    return {"status": "success", "message": "Favorite marked as used"}


@router.post("/data/cleanup")
async def cleanup_data(days: Optional[int] = None) -> Dict[str, str]:
    """Clean up old usage data."""
    manager = get_manager()
    manager.cleanup_old_data(days)
    return {"status": "success", "message": "Old data cleaned up"}


@router.post("/data/backup")
async def create_backup() -> Dict[str, Any]:
    """Create a backup of global data."""
    manager = get_manager()
    backup_path = manager.backup_database()
    
    if backup_path:
        return {"status": "success", "backup_path": backup_path}
    else:
        raise HTTPException(status_code=500, detail="Backup failed")


@router.post("/data/export")
async def export_data(format: str = "json") -> Dict[str, Any]:
    """Export all global data."""
    manager = get_manager()
    
    # Create export in temp directory
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix=f'.{format}', 
        delete=False
    ) as f:
        export_path = f.name
    
    if manager.export_data(export_path, format):
        # Read and return the exported data
        with open(export_path, 'r') as f:
            import json
            data = json.load(f)
        
        # Clean up temp file
        Path(export_path).unlink()
        
        return data
    else:
        raise HTTPException(status_code=500, detail="Export failed")