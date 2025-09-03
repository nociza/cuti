"""API endpoints for prompt prefix management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path

from cuti.core.prompt_prefix import PromptPrefixManager


router = APIRouter(prefix="/api/prompt-prefix", tags=["prompt-prefix"])

# Initialize manager
manager = PromptPrefixManager()


class PrefixRequest(BaseModel):
    """Request model for saving a prefix."""
    name: str
    description: str
    prompt: str
    tools: List[str]


class SetActiveRequest(BaseModel):
    """Request to set the active prefix."""
    prefix: Optional[Dict] = None


@router.get("/all")
async def get_all_prefixes():
    """Get all templates and custom prefixes."""
    return manager.get_all_prefixes()


@router.get("/templates")
async def get_templates():
    """Get available prefix templates."""
    return {"templates": manager.get_templates()}


@router.get("/custom")
async def get_custom_prefixes():
    """Get custom prefixes."""
    return {"custom": manager.get_custom_prefixes()}


@router.get("/active")
async def get_active_prefix():
    """Get the currently active prefix."""
    prefix = manager.get_active_prefix()
    return {
        "active": prefix,
        "formatted": manager.format_prefix_for_chat(prefix) if prefix else ""
    }


@router.post("/custom")
async def save_custom_prefix(request: PrefixRequest):
    """Save a custom prefix."""
    prefix = {
        "name": request.name,
        "description": request.description,
        "prompt": request.prompt,
        "tools": request.tools,
        "is_template": False
    }
    
    success = manager.save_custom_prefix(prefix)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save custom prefix")
    
    return {"success": True, "message": "Custom prefix saved"}


@router.delete("/custom/{name}")
async def delete_custom_prefix(name: str):
    """Delete a custom prefix."""
    success = manager.delete_custom_prefix(name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete custom prefix")
    
    return {"success": True, "message": "Custom prefix deleted"}


@router.post("/active")
async def set_active_prefix(request: SetActiveRequest):
    """Set the active prefix."""
    success = manager.save_active_prefix(request.prefix)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set active prefix")
    
    return {"success": True, "message": "Active prefix updated"}


@router.post("/activate-template/{template_name}")
async def activate_template(template_name: str):
    """Activate a template as the current prefix."""
    templates = manager.get_templates()
    template = next((t for t in templates if t['name'] == template_name), None)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Mark as template when activating
    template['is_template'] = True
    success = manager.save_active_prefix(template)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to activate template")
    
    return {"success": True, "message": f"Template '{template_name}' activated"}


@router.post("/activate-custom/{custom_name}")
async def activate_custom(custom_name: str):
    """Activate a custom prefix."""
    customs = manager.get_custom_prefixes()
    custom = next((c for c in customs if c['name'] == custom_name), None)
    
    if not custom:
        raise HTTPException(status_code=404, detail="Custom prefix not found")
    
    success = manager.save_active_prefix(custom)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to activate custom prefix")
    
    return {"success": True, "message": f"Custom prefix '{custom_name}' activated"}


@router.post("/deactivate")
async def deactivate_prefix():
    """Deactivate the current prefix."""
    success = manager.save_active_prefix(None)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to deactivate prefix")
    
    return {"success": True, "message": "Prefix deactivated"}