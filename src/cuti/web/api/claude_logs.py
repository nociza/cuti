"""
API endpoints for Claude logs and ground truth data.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Request, Query
from pydantic import BaseModel


class PromptHistoryResponse(BaseModel):
    prompts: List[Dict[str, Any]]
    session_id: Optional[str]
    total_count: int


class TodosResponse(BaseModel):
    todos: List[Dict[str, Any]]
    session_id: Optional[str]
    stats: Dict[str, int]


class SessionStatsResponse(BaseModel):
    session_id: str
    total_prompts: int
    total_responses: int
    total_tokens: int
    todos_count: int
    todos_completed: int
    todos_pending: int
    todos_in_progress: int


claude_logs_router = APIRouter(prefix="/claude-logs", tags=["claude-logs"])


@claude_logs_router.get("/history", response_model=PromptHistoryResponse)
async def get_prompt_history(
    request: Request,
    session_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
) -> Dict[str, Any]:
    """Get prompt history from Claude's ground truth logs."""
    logs_reader = request.app.state.claude_logs_reader
    
    prompts = logs_reader.get_prompt_history(session_id, limit)
    current_session = session_id or logs_reader.get_current_session_id()
    
    return {
        "prompts": prompts,
        "session_id": current_session,
        "total_count": len(prompts)
    }


@claude_logs_router.get("/todos", response_model=TodosResponse)
async def get_todos(
    request: Request,
    session_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get todos from Claude's todo files."""
    logs_reader = request.app.state.claude_logs_reader
    
    todos = logs_reader.get_todos(session_id)
    current_session = session_id or logs_reader.get_current_session_id()
    
    # Calculate stats
    stats = {
        "total": len(todos),
        "completed": len([t for t in todos if t.get('status') == 'completed']),
        "pending": len([t for t in todos if t.get('status') == 'pending']),
        "in_progress": len([t for t in todos if t.get('status') == 'in_progress'])
    }
    
    return {
        "todos": todos,
        "session_id": current_session,
        "stats": stats
    }


@claude_logs_router.get("/sessions")
async def get_sessions(request: Request) -> List[Dict[str, Any]]:
    """Get all available sessions for the current project."""
    logs_reader = request.app.state.claude_logs_reader
    return logs_reader.get_all_sessions()


@claude_logs_router.get("/conversation")
async def get_conversation(
    request: Request,
    session_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50)
) -> List[Dict[str, Any]]:
    """Get conversation context with user prompts and assistant responses."""
    logs_reader = request.app.state.claude_logs_reader
    return logs_reader.get_conversation_context(session_id, limit)


@claude_logs_router.get("/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    request: Request,
    session_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get statistics for the current or specified session."""
    logs_reader = request.app.state.claude_logs_reader
    stats = logs_reader.get_statistics(session_id)
    
    if not stats:
        # Return empty stats if no session found
        return {
            "session_id": session_id or "",
            "total_prompts": 0,
            "total_responses": 0,
            "total_tokens": 0,
            "todos_count": 0,
            "todos_completed": 0,
            "todos_pending": 0,
            "todos_in_progress": 0
        }
    
    return stats


@claude_logs_router.get("/current-session")
async def get_current_session(request: Request) -> Dict[str, Optional[str]]:
    """Get the current active session ID."""
    logs_reader = request.app.state.claude_logs_reader
    return {
        "session_id": logs_reader.get_current_session_id(),
        "project_name": logs_reader.project_name
    }