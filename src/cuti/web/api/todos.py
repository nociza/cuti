"""
API endpoints for todo management.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from ...services.todo_service import TodoService
from ...services.claude_todo_sync import ClaudeTodoSync
from ...services.goal_parser import GoalParser
from ...core.todo_models import TodoItem, TodoList, TodoSession, TodoStatus, TodoPriority

router = APIRouter(prefix="/api/todos", tags=["todos"])

# Global sync service instance
claude_sync = None

def get_claude_sync() -> ClaudeTodoSync:
    """Get or create Claude sync service."""
    global claude_sync
    if not claude_sync:
        storage_dir = os.environ.get("CUTI_STORAGE_DIR", ".cuti")
        claude_sync = ClaudeTodoSync(storage_dir)
    return claude_sync


def get_todo_service() -> TodoService:
    """Get todo service instance."""
    storage_dir = os.environ.get("CUTI_STORAGE_DIR", ".cuti")
    return TodoService(storage_dir)


@router.get("/")
async def get_todos(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    session_id: Optional[str] = None,
    search: Optional[str] = None,
    todo_service: TodoService = Depends(get_todo_service)
) -> Dict[str, Any]:
    """Get all todos with optional filtering."""
    try:
        # Get master list
        master_list = todo_service.get_master_list()
        if not master_list:
            return {
                "master_todos": [],
                "statistics": {
                    "total": 0,
                    "completed": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "blocked": 0,
                    "completion_percentage": 0
                },
                "total_count": 0
            }
        
        # Apply filters
        todos = master_list.todos
        
        if status:
            try:
                status_enum = TodoStatus(status)
                todos = [t for t in todos if t.status == status_enum]
            except ValueError:
                pass
        
        if priority:
            try:
                priority_enum = TodoPriority[priority.upper()]
                todos = [t for t in todos if t.priority == priority_enum]
            except KeyError:
                pass
        
        if search:
            search_lower = search.lower()
            todos = [t for t in todos if search_lower in t.content.lower()]
        
        # Group master todos and sub-todos
        master_todos = []
        for todo in todos:
            if todo.parent_id is None or todo.parent_id == master_list.id:
                # This is a master todo
                sub_todos = [t for t in todos if t.parent_id == todo.id]
                master_todos.append({
                    "todo": todo.to_dict(),
                    "sub_todos": [st.to_dict() for st in sub_todos]
                })
        
        # Get statistics
        stats = master_list.get_progress()
        
        return {
            "master_todos": master_todos,
            "statistics": stats,
            "total_count": len(todos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_todo(
    todo_data: Dict[str, Any],
    todo_service: TodoService = Depends(get_todo_service)
) -> Dict[str, Any]:
    """Create a new todo."""
    try:
        # Create todo item
        todo = TodoItem(
            content=todo_data["content"],
            priority=TodoPriority[todo_data.get("priority", "medium").upper()],
            created_by="user"
        )
        
        if "description" in todo_data:
            todo.metadata["description"] = todo_data["description"]
        
        # Add to master list
        master_list = todo_service.get_master_list()
        if not master_list:
            raise HTTPException(status_code=500, detail="Master list not found")
        
        master_list.add_todo(todo)
        todo_service.save_list(master_list)
        
        return {"success": True, "todo": todo.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{todo_id}")
async def update_todo(
    todo_id: str,
    todo_data: Dict[str, Any],
    todo_service: TodoService = Depends(get_todo_service)
) -> Dict[str, Any]:
    """Update a todo."""
    try:
        updates = {}
        
        if "content" in todo_data:
            updates["content"] = todo_data["content"]
        
        if "status" in todo_data:
            updates["status"] = TodoStatus(todo_data["status"])
        
        if "priority" in todo_data:
            updates["priority"] = TodoPriority[todo_data["priority"].upper()]
        
        if "description" in todo_data:
            # This would go in metadata
            pass
        
        success = todo_service.update_todo(todo_id, updates)
        
        if success:
            todo = todo_service.get_todo(todo_id)
            return {"success": True, "todo": todo.to_dict() if todo else None}
        else:
            raise HTTPException(status_code=404, detail="Todo not found")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: str,
    todo_service: TodoService = Depends(get_todo_service)
) -> Dict[str, Any]:
    """Delete a todo."""
    try:
        # Get master list
        master_list = todo_service.get_master_list()
        if not master_list:
            raise HTTPException(status_code=500, detail="Master list not found")
        
        # Remove todo
        if master_list.remove_todo(todo_id):
            todo_service.save_list(master_list)
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Todo not found")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions")
async def get_sessions(
    todo_service: TodoService = Depends(get_todo_service)
) -> Dict[str, Any]:
    """Get all work sessions."""
    try:
        # Get active session if any
        session = todo_service.get_active_session()
        sessions = []
        
        if session:
            sessions.append({
                "id": session.id,
                "name": session.name,
                "active": session.active,
                "created_at": session.created_at.isoformat() if session.created_at else None
            })
        
        return {"work_sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{todo_id}/convert-to-prompt")
async def convert_to_prompt(
    todo_id: str,
    todo_service: TodoService = Depends(get_todo_service)
) -> Dict[str, Any]:
    """Convert todo to queue prompt."""
    try:
        from ...services.queue_service import QueueManager
        from ...core.models import QueuedPrompt
        
        # Get todo
        todo = todo_service.get_todo(todo_id)
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        # Create prompt
        storage_dir = os.environ.get("CUTI_STORAGE_DIR", ".cuti")
        manager = QueueManager(storage_dir)
        
        prompt = QueuedPrompt(
            content=f"Work on this task: {todo.content}",
            priority=todo.priority.value
        )
        
        if manager.add_prompt(prompt):
            # Update todo status
            todo_service.update_todo(todo_id, {"status": TodoStatus.IN_PROGRESS})
            return {"success": True, "message": "Todo converted to prompt", "prompt_id": prompt.id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create prompt")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/claude/capture")
async def capture_claude_todos(
    todos_data: Dict[str, Any],
    claude_sync: ClaudeTodoSync = Depends(get_claude_sync)
) -> Dict[str, Any]:
    """Capture todos from Claude's TodoWrite tool."""
    try:
        todos = todos_data.get("todos", [])
        agent_name = todos_data.get("agent_name", None)
        
        # Capture the todos
        sub_list = claude_sync.capture_todo_write(todos, agent_name)
        
        return {
            "success": True,
            "list_id": sub_list.id,
            "todos_created": len(sub_list.todos),
            "session_id": sub_list.session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/master")
async def get_master_goals(
    claude_sync: ClaudeTodoSync = Depends(get_claude_sync)
) -> Dict[str, Any]:
    """Get master goals from GOAL.md."""
    try:
        # Ensure master list is synced
        goal_parser = claude_sync.goal_parser
        master_list = goal_parser.parse_goal_file()
        master_list = goal_parser.sync_with_database(
            claude_sync.todo_service, master_list
        )
        
        return {
            "master_goals": master_list.to_dict(),
            "progress": master_list.get_progress()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/current")
async def get_current_session(
    claude_sync: ClaudeTodoSync = Depends(get_claude_sync)
) -> Dict[str, Any]:
    """Get current work session with hierarchical todos."""
    try:
        session = claude_sync.current_session
        if not session:
            return {"error": "No active session"}
        
        return {
            "session": session.to_dict(),
            "next_todo": claude_sync.suggest_next_todo().to_dict() if claude_sync.suggest_next_todo() else None,
            "current_todos": claude_sync.get_current_todos()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-goal")
async def sync_goal_file(
    claude_sync: ClaudeTodoSync = Depends(get_claude_sync)
) -> Dict[str, Any]:
    """Sync GOAL.md with master todo list."""
    try:
        goal_parser = claude_sync.goal_parser
        master_list = goal_parser.parse_goal_file()
        master_list = goal_parser.sync_with_database(
            claude_sync.todo_service, master_list
        )
        
        return {
            "success": True,
            "todos_synced": len(master_list.todos),
            "master_list_id": master_list.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
