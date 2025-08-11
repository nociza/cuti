"""
API endpoints for workspace management and synchronization.
"""

from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel


class SyncRequest(BaseModel):
    force: bool = False


workspace_router = APIRouter(prefix="/workspace", tags=["workspace"])


@workspace_router.get("/info")
async def get_workspace_info(request: Request) -> Dict[str, Any]:
    """Get information about the current workspace."""
    workspace_manager = request.app.state.workspace_manager
    return workspace_manager.get_workspace_info()


@workspace_router.get("/sync/status")
async def get_sync_status(request: Request) -> Dict[str, Any]:
    """Get the current synchronization status."""
    log_sync_service = request.app.state.log_sync_service
    return log_sync_service.get_sync_status()


@workspace_router.post("/sync/now")
async def sync_now(request: Request, sync_request: SyncRequest) -> Dict[str, Any]:
    """Trigger immediate synchronization."""
    log_sync_service = request.app.state.log_sync_service
    try:
        results = log_sync_service.sync_all()
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@workspace_router.post("/backup")
async def create_backup(request: Request) -> Dict[str, Any]:
    """Create a backup of workspace data."""
    workspace_manager = request.app.state.workspace_manager
    try:
        backup_path = workspace_manager.backup_workspace()
        return {
            "success": True,
            "backup_path": str(backup_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@workspace_router.post("/cleanup")
async def cleanup_old_data(request: Request, days: int = 90) -> Dict[str, Any]:
    """Clean up old data from the workspace."""
    workspace_manager = request.app.state.workspace_manager
    try:
        workspace_manager.cleanup_old_data(days)
        return {
            "success": True,
            "message": f"Cleaned up data older than {days} days"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))