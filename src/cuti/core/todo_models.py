"""
Todo list models for hierarchical task management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


class TodoStatus(Enum):
    """Status of a todo item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TodoPriority(Enum):
    """Priority levels for todo items."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class TodoItem:
    """Represents a single todo item."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    status: TodoStatus = TodoStatus.PENDING
    priority: TodoPriority = TodoPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    created_by: str = "user"  # "user" or "claude"
    assigned_to: Optional[str] = None  # agent name if assigned
    parent_id: Optional[str] = None  # for sub-todos
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def mark_completed(self):
        """Mark this todo as completed."""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_in_progress(self):
        """Mark this todo as in progress."""
        self.status = TodoStatus.IN_PROGRESS
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
            "assigned_to": self.assigned_to,
            "parent_id": self.parent_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        """Create from dictionary."""
        if isinstance(data.get('status'), str):
            data['status'] = TodoStatus(data['status'])
        if isinstance(data.get('priority'), (str, int)):
            if isinstance(data['priority'], str):
                data['priority'] = TodoPriority[data['priority'].upper()]
            else:
                data['priority'] = TodoPriority(data['priority'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class TodoList:
    """Represents a todo list with hierarchy support."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    todos: List[TodoItem] = field(default_factory=list)
    parent_list_id: Optional[str] = None  # for sub-lists
    session_id: Optional[str] = None  # links to a work session
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "user"  # "user" or "claude"
    is_master: bool = False  # True for the master GOAL.md list
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_todo(self, todo: TodoItem) -> None:
        """Add a todo item to this list."""
        todo.parent_id = self.id
        self.todos.append(todo)
        self.updated_at = datetime.now()
    
    def remove_todo(self, todo_id: str) -> bool:
        """Remove a todo item by ID."""
        original_count = len(self.todos)
        self.todos = [t for t in self.todos if t.id != todo_id]
        if len(self.todos) < original_count:
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_todo(self, todo_id: str) -> Optional[TodoItem]:
        """Get a todo item by ID."""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None
    
    def get_progress(self) -> Dict[str, int]:
        """Get progress statistics."""
        stats = {
            "total": len(self.todos),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "blocked": 0,
            "cancelled": 0
        }
        
        for todo in self.todos:
            stats[todo.status.value] += 1
        
        if stats["total"] > 0:
            stats["completion_percentage"] = int(
                (stats["completed"] / stats["total"]) * 100
            )
        else:
            stats["completion_percentage"] = 0
        
        return stats
    
    def get_pending_todos(self) -> List[TodoItem]:
        """Get all pending todos."""
        return [t for t in self.todos if t.status == TodoStatus.PENDING]
    
    def get_in_progress_todos(self) -> List[TodoItem]:
        """Get all in-progress todos."""
        return [t for t in self.todos if t.status == TodoStatus.IN_PROGRESS]
    
    def get_completed_todos(self) -> List[TodoItem]:
        """Get all completed todos."""
        return [t for t in self.todos if t.status == TodoStatus.COMPLETED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "todos": [t.to_dict() for t in self.todos],
            "parent_list_id": self.parent_list_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "is_master": self.is_master,
            "metadata": self.metadata,
            "progress": self.get_progress()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoList':
        """Create from dictionary."""
        if 'todos' in data and isinstance(data['todos'], list):
            data['todos'] = [
                TodoItem.from_dict(t) if isinstance(t, dict) else t 
                for t in data['todos']
            ]
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        # Remove progress from data if present (it's computed)
        data.pop('progress', None)
        return cls(**data)


@dataclass
class TodoSession:
    """Represents a work session with associated todo lists."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    master_list: Optional[TodoList] = None
    sub_lists: List[TodoList] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_sub_list(self, sub_list: TodoList) -> None:
        """Add a sub-list to this session."""
        sub_list.session_id = self.id
        if self.master_list:
            sub_list.parent_list_id = self.master_list.id
        self.sub_lists.append(sub_list)
        self.updated_at = datetime.now()
    
    def get_all_todos(self) -> List[TodoItem]:
        """Get all todos from master and sub-lists."""
        todos = []
        if self.master_list:
            todos.extend(self.master_list.todos)
        for sub_list in self.sub_lists:
            todos.extend(sub_list.todos)
        return todos
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Get overall progress across all lists."""
        all_todos = self.get_all_todos()
        stats = {
            "total": len(all_todos),
            "pending": sum(1 for t in all_todos if t.status == TodoStatus.PENDING),
            "in_progress": sum(1 for t in all_todos if t.status == TodoStatus.IN_PROGRESS),
            "completed": sum(1 for t in all_todos if t.status == TodoStatus.COMPLETED),
            "blocked": sum(1 for t in all_todos if t.status == TodoStatus.BLOCKED),
            "cancelled": sum(1 for t in all_todos if t.status == TodoStatus.CANCELLED)
        }
        
        if stats["total"] > 0:
            stats["completion_percentage"] = int(
                (stats["completed"] / stats["total"]) * 100
            )
        else:
            stats["completion_percentage"] = 0
        
        stats["lists"] = {
            "master": self.master_list.get_progress() if self.master_list else None,
            "sub_lists": [sl.get_progress() for sl in self.sub_lists]
        }
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "master_list": self.master_list.to_dict() if self.master_list else None,
            "sub_lists": [sl.to_dict() for sl in self.sub_lists],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "active": self.active,
            "metadata": self.metadata,
            "overall_progress": self.get_overall_progress()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoSession':
        """Create from dictionary."""
        if 'master_list' in data and data['master_list']:
            data['master_list'] = TodoList.from_dict(data['master_list'])
        if 'sub_lists' in data and isinstance(data['sub_lists'], list):
            data['sub_lists'] = [
                TodoList.from_dict(sl) if isinstance(sl, dict) else sl 
                for sl in data['sub_lists']
            ]
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        # Remove computed fields
        data.pop('overall_progress', None)
        return cls(**data)