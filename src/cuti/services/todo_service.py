"""
Todo list service for managing hierarchical task lists.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import os

from ..core.todo_models import TodoItem, TodoList, TodoSession, TodoStatus, TodoPriority


class TodoService:
    """Service for managing todo lists with database persistence."""
    
    def __init__(self, storage_dir: str = ".cuti"):
        self.storage_dir = Path(storage_dir).expanduser()
        self.db_path = self.storage_dir / "databases" / "todos.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.goal_file = self.storage_dir / "GOAL.md"
        self._init_database()
        self._ensure_master_list()
    
    def _init_database(self):
        """Initialize the todo database."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        cursor = conn.cursor()
        
        # Todo items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todo_items (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                completed_at TEXT,
                created_by TEXT,
                assigned_to TEXT,
                parent_id TEXT,
                list_id TEXT,
                metadata TEXT
            )
        ''')
        
        # Todo lists table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todo_lists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                parent_list_id TEXT,
                session_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                created_by TEXT,
                is_master BOOLEAN,
                metadata TEXT
            )
        ''')
        
        # Todo sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todo_sessions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                master_list_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                active BOOLEAN,
                metadata TEXT,
                FOREIGN KEY (master_list_id) REFERENCES todo_lists(id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todo_list ON todo_items(list_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todo_status ON todo_items(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todo_parent ON todo_items(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_list_session ON todo_lists(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_list_master ON todo_lists(is_master)')
        
        conn.commit()
        conn.close()
    
    def _ensure_master_list(self):
        """Ensure master todo list exists and sync with GOAL.md."""
        master_list = self.get_master_list()
        
        if not master_list:
            # Create master list
            master_list = TodoList(
                name="Master Goals",
                description="Overall project goals from GOAL.md",
                is_master=True,
                created_by="system"
            )
            self.save_list(master_list)
        
        # Sync with GOAL.md if it exists (disabled for now due to locking)
        # if self.goal_file.exists():
        #     self._sync_goal_file(master_list)
    
    def _sync_goal_file(self, master_list: TodoList):
        """Sync master list with GOAL.md file."""
        try:
            content = self.goal_file.read_text()
            # Parse markdown for todo items (lines starting with - [ ] or - [x])
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('- [ ]'):
                    # Pending todo
                    todo_content = line[5:].strip()
                    if not any(t.content == todo_content for t in master_list.todos):
                        todo = TodoItem(
                            content=todo_content,
                            status=TodoStatus.PENDING,
                            created_by="goal_file"
                        )
                        master_list.add_todo(todo)
                
                elif line.startswith('- [x]'):
                    # Completed todo
                    todo_content = line[5:].strip()
                    existing = next((t for t in master_list.todos if t.content == todo_content), None)
                    if existing and existing.status != TodoStatus.COMPLETED:
                        existing.mark_completed()
            
            self.save_list(master_list)
        except Exception as e:
            print(f"Error syncing GOAL.md: {e}")
    
    def save_goal_file(self, master_list: TodoList):
        """Save master list to GOAL.md file."""
        lines = ["# Project Goals", ""]
        
        # Add pending todos
        pending = master_list.get_pending_todos()
        if pending:
            lines.append("## To Do")
            for todo in pending:
                lines.append(f"- [ ] {todo.content}")
            lines.append("")
        
        # Add in-progress todos
        in_progress = master_list.get_in_progress_todos()
        if in_progress:
            lines.append("## In Progress")
            for todo in in_progress:
                lines.append(f"- [ ] {todo.content} (in progress)")
            lines.append("")
        
        # Add completed todos
        completed = master_list.get_completed_todos()
        if completed:
            lines.append("## Completed")
            for todo in completed:
                lines.append(f"- [x] {todo.content}")
            lines.append("")
        
        # Add metadata
        lines.append(f"---")
        lines.append(f"Last updated: {datetime.now().isoformat()}")
        lines.append(f"Total tasks: {len(master_list.todos)}")
        progress = master_list.get_progress()
        lines.append(f"Completion: {progress['completion_percentage']}%")
        
        self.goal_file.write_text('\n'.join(lines))
    
    # CRUD operations for TodoItem
    
    def save_todo(self, todo: TodoItem, list_id: str, conn=None) -> str:
        """Save a todo item to database."""
        close_conn = False
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            close_conn = True
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO todo_items (
                    id, content, status, priority, created_at, updated_at,
                    completed_at, created_by, assigned_to, parent_id, list_id, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                todo.id, todo.content, todo.status.value, todo.priority.value,
                todo.created_at.isoformat() if todo.created_at else None,
                todo.updated_at.isoformat() if todo.updated_at else None,
                todo.completed_at.isoformat() if todo.completed_at else None,
                todo.created_by, todo.assigned_to, todo.parent_id, list_id,
                json.dumps(todo.metadata)
            ))
            
            if close_conn:
                conn.commit()
            return todo.id
        finally:
            if close_conn:
                conn.close()
    
    def get_todo(self, todo_id: str) -> Optional[TodoItem]:
        """Get a todo item by ID."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM todo_items WHERE id = ?', (todo_id,))
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                # Remove list_id as it's not part of TodoItem
                data.pop('list_id', None)
                return TodoItem.from_dict(data)
            return None
        finally:
            conn.close()
    
    def update_todo(self, todo_id: str, updates: Dict[str, Any]) -> bool:
        """Update a todo item."""
        todo = self.get_todo(todo_id)
        if not todo:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(todo, key):
                if key == 'status' and isinstance(value, str):
                    value = TodoStatus(value)
                elif key == 'priority' and isinstance(value, (str, int)):
                    if isinstance(value, str):
                        value = TodoPriority[value.upper()]
                    else:
                        value = TodoPriority(value)
                setattr(todo, key, value)
        
        todo.updated_at = datetime.now()
        
        # Get list_id for this todo
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('SELECT list_id FROM todo_items WHERE id = ?', (todo_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            list_id = result[0]
            self.save_todo(todo, list_id)  # This will create its own connection
            
            # Update GOAL.md if this is in the master list
            todo_list = self.get_list(list_id)
            if todo_list and todo_list.is_master:
                self.save_goal_file(todo_list)
            
            return True
        return False
    
    # CRUD operations for TodoList
    
    def save_list(self, todo_list: TodoList) -> str:
        """Save a todo list to database."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO todo_lists (
                    id, name, description, parent_list_id, session_id,
                    created_at, updated_at, created_by, is_master, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                todo_list.id, todo_list.name, todo_list.description,
                todo_list.parent_list_id, todo_list.session_id,
                todo_list.created_at.isoformat() if todo_list.created_at else None,
                todo_list.updated_at.isoformat() if todo_list.updated_at else None,
                todo_list.created_by, todo_list.is_master,
                json.dumps(todo_list.metadata)
            ))
            
            # Save todos (pass connection to avoid locking)
            for todo in todo_list.todos:
                self.save_todo(todo, todo_list.id, conn)
            
            conn.commit()
            
            # Update GOAL.md if this is the master list (disabled for now due to locking)
            # if todo_list.is_master:
            #     self.save_goal_file(todo_list)
            
            return todo_list.id
        finally:
            conn.close()
    
    def get_list(self, list_id: str) -> Optional[TodoList]:
        """Get a todo list by ID."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM todo_lists WHERE id = ?', (list_id,))
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                
                # Get todos for this list
                cursor.execute('SELECT * FROM todo_items WHERE list_id = ?', (list_id,))
                todo_rows = cursor.fetchall()
                
                todos = []
                for todo_row in todo_rows:
                    todo_data = dict(todo_row)
                    todo_data['metadata'] = json.loads(todo_data['metadata']) if todo_data['metadata'] else {}
                    # Remove list_id as it's not part of TodoItem
                    todo_data.pop('list_id', None)
                    todos.append(TodoItem.from_dict(todo_data))
                
                data['todos'] = todos
                return TodoList.from_dict(data)
            return None
        finally:
            conn.close()
    
    def get_master_list(self) -> Optional[TodoList]:
        """Get the master todo list."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id FROM todo_lists WHERE is_master = 1')
            row = cursor.fetchone()
            
            if row:
                return self.get_list(row['id'])
            return None
        finally:
            conn.close()
    
    def get_lists_for_session(self, session_id: str) -> List[TodoList]:
        """Get all todo lists for a session."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id FROM todo_lists WHERE session_id = ?', (session_id,))
            rows = cursor.fetchall()
            
            lists = []
            for row in rows:
                todo_list = self.get_list(row['id'])
                if todo_list:
                    lists.append(todo_list)
            
            return lists
        finally:
            conn.close()
    
    # CRUD operations for TodoSession
    
    def save_session(self, session: TodoSession) -> str:
        """Save a todo session to database."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO todo_sessions (
                    id, name, master_list_id, created_at, updated_at, active, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.id, session.name,
                session.master_list.id if session.master_list else None,
                session.created_at.isoformat() if session.created_at else None,
                session.updated_at.isoformat() if session.updated_at else None,
                session.active,
                json.dumps(session.metadata)
            ))
            
            # Save master list if present
            if session.master_list:
                self.save_list(session.master_list)
            
            # Save sub-lists
            for sub_list in session.sub_lists:
                sub_list.session_id = session.id
                self.save_list(sub_list)
            
            conn.commit()
            return session.id
        finally:
            conn.close()
    
    def get_session(self, session_id: str) -> Optional[TodoSession]:
        """Get a todo session by ID."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM todo_sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                
                # Get master list
                if data['master_list_id']:
                    data['master_list'] = self.get_list(data['master_list_id'])
                
                # Get sub-lists
                data['sub_lists'] = self.get_lists_for_session(session_id)
                
                return TodoSession.from_dict(data)
            return None
        finally:
            conn.close()
    
    def get_active_session(self) -> Optional[TodoSession]:
        """Get the active todo session."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id FROM todo_sessions WHERE active = 1 ORDER BY updated_at DESC LIMIT 1')
            row = cursor.fetchone()
            
            if row:
                return self.get_session(row['id'])
            return None
        finally:
            conn.close()
    
    def create_session(self, name: str) -> TodoSession:
        """Create a new todo session."""
        # Deactivate current active session
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('UPDATE todo_sessions SET active = 0')
        conn.commit()
        conn.close()
        
        # Create new session with master list
        session = TodoSession(name=name)
        session.master_list = self.get_master_list()
        
        self.save_session(session)
        return session
    
    # Helper methods
    
    def get_todos_by_status(self, status: TodoStatus) -> List[TodoItem]:
        """Get all todos with a specific status."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM todo_items WHERE status = ?', (status.value,))
            rows = cursor.fetchall()
            
            todos = []
            for row in rows:
                data = dict(row)
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                # Remove list_id as it's not part of TodoItem
                data.pop('list_id', None)
                todos.append(TodoItem.from_dict(data))
            
            return todos
        finally:
            conn.close()
    
    def get_recent_todos(self, limit: int = 10) -> List[TodoItem]:
        """Get recently created todos."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT * FROM todo_items ORDER BY created_at DESC LIMIT ?',
                (limit,)
            )
            rows = cursor.fetchall()
            
            todos = []
            for row in rows:
                data = dict(row)
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                # Remove list_id as it's not part of TodoItem
                data.pop('list_id', None)
                todos.append(TodoItem.from_dict(data))
            
            return todos
        finally:
            conn.close()