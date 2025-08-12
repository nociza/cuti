"""
Task history persistence and management.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class TaskHistoryEntry:
    """Represents a task execution in history."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = ""
    content: str = ""
    response: str = ""
    agents_used: List[str] = field(default_factory=list)
    sub_tasks: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"  # pending, executing, completed, failed, cancelled
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        data['agents_used'] = json.dumps(self.agents_used)
        data['sub_tasks'] = json.dumps(self.sub_tasks)
        data['metadata'] = json.dumps(self.metadata)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskHistoryEntry':
        """Create from dictionary."""
        if isinstance(data.get('agents_used'), str):
            data['agents_used'] = json.loads(data['agents_used'])
        if isinstance(data.get('sub_tasks'), str):
            data['sub_tasks'] = json.loads(data['sub_tasks'])
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


class TaskHistoryManager:
    """Manages task execution history in database."""
    
    def __init__(self, storage_dir: str = ".cuti"):
        self.storage_dir = Path(storage_dir)
        self.db_path = self.storage_dir / "databases" / "task_history.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the task history database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create main task history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_history (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                content TEXT,
                response TEXT,
                agents_used TEXT,
                sub_tasks TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_seconds REAL,
                tokens_used INTEGER,
                cost REAL,
                error_message TEXT,
                metadata TEXT
            )
        ''')
        
        # Create sub-tasks table for detailed tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sub_tasks (
                id TEXT PRIMARY KEY,
                parent_task_id TEXT,
                agent_name TEXT,
                content TEXT,
                status TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_seconds REAL,
                metadata TEXT,
                FOREIGN KEY (parent_task_id) REFERENCES task_history(id)
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_session ON task_history(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_status ON task_history(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_created ON task_history(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subtask_parent ON sub_tasks(parent_task_id)')
        
        conn.commit()
        conn.close()
    
    def add_task(self, task: TaskHistoryEntry) -> str:
        """Add a new task to history."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            task_dict = task.to_dict()
            cursor.execute('''
                INSERT INTO task_history (
                    id, session_id, content, response, agents_used, sub_tasks,
                    status, created_at, started_at, completed_at, duration_seconds,
                    tokens_used, cost, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_dict['id'], task_dict['session_id'], task_dict['content'],
                task_dict['response'], task_dict['agents_used'], task_dict['sub_tasks'],
                task_dict['status'], task_dict['created_at'], task_dict['started_at'],
                task_dict['completed_at'], task_dict['duration_seconds'],
                task_dict['tokens_used'], task_dict['cost'], task_dict['error_message'],
                task_dict['metadata']
            ))
            
            # Add sub-tasks if any
            for sub_task in task.sub_tasks:
                cursor.execute('''
                    INSERT INTO sub_tasks (
                        id, parent_task_id, agent_name, content, status,
                        started_at, completed_at, duration_seconds, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sub_task.get('id', str(uuid.uuid4())[:8]),
                    task.id,
                    sub_task.get('agent_name', ''),
                    sub_task.get('content', ''),
                    sub_task.get('status', 'pending'),
                    sub_task.get('started_at'),
                    sub_task.get('completed_at'),
                    sub_task.get('duration_seconds', 0),
                    json.dumps(sub_task.get('metadata', {}))
                ))
            
            conn.commit()
            return task.id
        finally:
            conn.close()
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing task."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically
            update_fields = []
            values = []
            
            for key, value in updates.items():
                if key in ['agents_used', 'sub_tasks', 'metadata']:
                    value = json.dumps(value) if not isinstance(value, str) else value
                elif key in ['created_at', 'started_at', 'completed_at'] and value:
                    value = value.isoformat() if isinstance(value, datetime) else value
                
                update_fields.append(f"{key} = ?")
                values.append(value)
            
            values.append(task_id)
            
            cursor.execute(
                f"UPDATE task_history SET {', '.join(update_fields)} WHERE id = ?",
                values
            )
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_task(self, task_id: str) -> Optional[TaskHistoryEntry]:
        """Get a single task by ID."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM task_history WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if row:
                return TaskHistoryEntry.from_dict(dict(row))
            return None
        finally:
            conn.close()
    
    def get_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> List[TaskHistoryEntry]:
        """Get tasks with optional filtering."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM task_history WHERE 1=1"
            params = []
            
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [TaskHistoryEntry.from_dict(dict(row)) for row in rows]
        finally:
            conn.close()
    
    def get_task_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about tasks."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            base_query = "FROM task_history"
            params = []
            
            if session_id:
                base_query += " WHERE session_id = ?"
                params.append(session_id)
            
            # Total tasks
            cursor.execute(f"SELECT COUNT(*) {base_query}", params)
            total = cursor.fetchone()[0]
            
            # Tasks by status
            cursor.execute(f"""
                SELECT status, COUNT(*) 
                {base_query}
                {'AND' if session_id else 'WHERE'} status IS NOT NULL
                GROUP BY status
            """, params)
            by_status = dict(cursor.fetchall())
            
            # Average duration
            cursor.execute(f"""
                SELECT AVG(duration_seconds) 
                {base_query}
                {'AND' if session_id else 'WHERE'} duration_seconds > 0
            """, params)
            avg_duration = cursor.fetchone()[0] or 0
            
            # Total cost
            cursor.execute(f"SELECT SUM(cost) {base_query}", params)
            total_cost = cursor.fetchone()[0] or 0
            
            # Total tokens
            cursor.execute(f"SELECT SUM(tokens_used) {base_query}", params)
            total_tokens = cursor.fetchone()[0] or 0
            
            # Most used agents
            cursor.execute(f"""
                SELECT agents_used, COUNT(*) as count
                {base_query}
                {'AND' if session_id else 'WHERE'} agents_used != '[]'
                GROUP BY agents_used
                ORDER BY count DESC
                LIMIT 5
            """, params)
            
            agent_usage = {}
            for row in cursor.fetchall():
                agents = json.loads(row[0])
                for agent in agents:
                    agent_usage[agent] = agent_usage.get(agent, 0) + 1
            
            return {
                "total_tasks": total,
                "by_status": by_status,
                "average_duration": avg_duration,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "most_used_agents": dict(sorted(
                    agent_usage.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5])
            }
        finally:
            conn.close()
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Remove tasks older than specified days."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Delete sub-tasks first
            cursor.execute('''
                DELETE FROM sub_tasks 
                WHERE parent_task_id IN (
                    SELECT id FROM task_history WHERE created_at < ?
                )
            ''', (cutoff_date,))
            
            # Delete main tasks
            cursor.execute(
                'DELETE FROM task_history WHERE created_at < ?',
                (cutoff_date,)
            )
            
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()


# Import for timedelta
from datetime import timedelta