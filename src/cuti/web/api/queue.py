"""
Queue-related API endpoints.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...core.models import QueuedPrompt, PromptStatus

queue_router = APIRouter(prefix="/queue", tags=["queue"])


class PromptRequest(BaseModel):
    content: str
    priority: int = 0
    working_directory: str = "."
    context_files: List[str] = []
    max_retries: int = 3
    estimated_tokens: Optional[int] = None


@queue_router.get("/status")
async def get_queue_status(request: Request) -> Dict[str, Any]:
    """Get queue status."""
    queue_manager = request.app.state.queue_manager
    if not queue_manager:
        raise HTTPException(status_code=503, detail="Queue manager not available")
    
    state = queue_manager.get_status()
    stats = state.get_stats()
    
    # Add queue running status
    stats['queue_running'] = getattr(request.app.state, 'queue_running', False)
    
    return stats


@queue_router.get("/prompts")
async def get_prompts(
    request: Request,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get prompts from the queue."""
    queue_manager = request.app.state.queue_manager
    if not queue_manager:
        raise HTTPException(status_code=503, detail="Queue manager not available")
    
    state = queue_manager.get_status()
    prompts = state.prompts
    
    # Filter by status if provided
    if status:
        try:
            status_enum = PromptStatus(status)
            prompts = [p for p in prompts if p.status == status_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Limit results
    prompts = prompts[:limit]
    
    # Convert to dict format
    result = []
    for prompt in prompts:
        result.append({
            "id": prompt.id,
            "content": prompt.content,
            "status": prompt.status.value,
            "priority": prompt.priority,
            "working_directory": prompt.working_directory,
            "context_files": prompt.context_files,
            "max_retries": prompt.max_retries,
            "retry_count": prompt.retry_count,
            "estimated_tokens": prompt.estimated_tokens,
            "created_at": prompt.created_at.isoformat(),
            "last_executed": prompt.last_executed.isoformat() if prompt.last_executed else None,
            "execution_log": prompt.execution_log,
        })
    
    return result


@queue_router.post("/prompts")
async def add_prompt(request: Request, prompt_request: PromptRequest) -> Dict[str, str]:
    """Add a new prompt to the queue."""
    queue_manager = request.app.state.queue_manager
    alias_manager = request.app.state.alias_manager
    history_manager = request.app.state.history_manager
    
    if not queue_manager:
        raise HTTPException(status_code=503, detail="Queue manager not available")
    
    # Check if this is an alias
    resolved_prompt = alias_manager.resolve_alias(
        prompt_request.content, 
        prompt_request.working_directory
    )
    
    # Store in history
    history_manager.add_prompt_to_history(
        resolved_prompt,
        prompt_request.working_directory,
        prompt_request.context_files
    )
    
    # Create queued prompt
    queued_prompt = QueuedPrompt(
        content=resolved_prompt,
        working_directory=prompt_request.working_directory,
        priority=prompt_request.priority,
        context_files=prompt_request.context_files,
        max_retries=prompt_request.max_retries,
        estimated_tokens=prompt_request.estimated_tokens,
    )
    
    success = queue_manager.add_prompt(queued_prompt)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add prompt")
    
    return {
        "id": queued_prompt.id,
        "message": "Prompt added successfully"
    }


@queue_router.delete("/prompts/{prompt_id}")
async def remove_prompt(request: Request, prompt_id: str) -> Dict[str, str]:
    """Remove/cancel a prompt from the queue."""
    queue_manager = request.app.state.queue_manager
    if not queue_manager:
        raise HTTPException(status_code=503, detail="Queue manager not available")
    
    success = queue_manager.remove_prompt(prompt_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found or cannot be cancelled")
    
    return {"message": f"Prompt {prompt_id} cancelled successfully"}