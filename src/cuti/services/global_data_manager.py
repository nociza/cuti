"""
Global data management service for persistent usage statistics and user preferences.
Manages data stored in ~/.cuti directory across all projects.
"""

import os
import sqlite3
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Represents a usage record from Claude Code."""
    timestamp: datetime
    project_path: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    model: str
    cost: float
    message_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass 
class FavoritePrompt:
    """Represents a favorite prompt saved by the user."""
    id: str
    title: str
    content: str
    project_path: str
    tags: List[str]
    created_at: datetime
    last_used: Optional[datetime] = None
    use_count: int = 0
    metadata: Optional[Dict] = None


@dataclass
class GlobalSettings:
    """Global settings for cuti."""
    usage_tracking_enabled: bool = True
    auto_cleanup_days: int = 90  # Auto-cleanup data older than N days
    privacy_mode: bool = False  # Don't store prompt content
    favorite_prompts_enabled: bool = True
    max_storage_mb: int = 500  # Max storage for global data
    claude_plan: str = 'pro'  # pro, max5, max20
    notifications_enabled: bool = True
    theme: str = 'auto'  # light, dark, auto
    metadata: Optional[Dict] = None


class GlobalDataManager:
    """Manages global cuti data stored in user's home directory."""
    
    def __init__(self, global_dir: Optional[str] = None):
        """
        Initialize the global data manager.
        
        Args:
            global_dir: Path to global cuti directory (defaults to ~/.cuti)
        """
        self.global_dir = Path(global_dir or "~/.cuti").expanduser()
        self.db_path = self.global_dir / "databases" / "global.db"
        self.settings_path = self.global_dir / "settings.json"
        self.backups_dir = self.global_dir / "backups"
        
        # Create directory structure
        self._init_directories()
        
        # Initialize database
        self._init_database()
        
        # Load settings
        self.settings = self._load_settings()
    
    def _init_directories(self):
        """Create necessary directory structure."""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        
        # Create README for users
        readme_path = self.global_dir / "README.md"
        if not readme_path.exists():
            readme_content = """# Cuti Global Data Directory

This directory contains global data for the cuti orchestration system.

## Contents

- `databases/` - SQLite databases for usage tracking and favorites
- `settings.json` - Global settings and preferences
- `backups/` - Automatic backups of databases

## Privacy

You can disable usage tracking in the settings or delete this directory
to remove all stored data. Run `cuti settings` to manage preferences.
"""
            readme_path.write_text(readme_content)
    
    def _init_database(self):
        """Initialize the global database."""
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            # Usage records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    project_path TEXT,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cache_creation_tokens INTEGER DEFAULT 0,
                    cache_read_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER NOT NULL,
                    model TEXT,
                    cost REAL,
                    message_id TEXT,
                    request_id TEXT,
                    session_id TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, message_id, request_id)
                )
            ''')
            
            # Favorite prompts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorite_prompts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    project_path TEXT,
                    tags TEXT,
                    created_at DATETIME NOT NULL,
                    last_used DATETIME,
                    use_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Project statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_stats (
                    project_path TEXT PRIMARY KEY,
                    first_used DATETIME NOT NULL,
                    last_used DATETIME NOT NULL,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Chat history tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    project_path TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    last_activity DATETIME NOT NULL,
                    prompt_count INTEGER DEFAULT 0,
                    response_count INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    git_branch TEXT,
                    metadata TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,  -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    parent_uuid TEXT,
                    model TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost REAL,
                    git_branch TEXT,
                    cwd TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_project ON usage_records(project_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_model ON usage_records(model)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_project ON favorite_prompts(project_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_used ON favorite_prompts(last_used)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_project ON chat_sessions(project_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_time ON chat_sessions(last_activity)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)')
            
            conn.commit()
    
    def _load_settings(self) -> GlobalSettings:
        """Load global settings from file."""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
                    return GlobalSettings(**data)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        
        # Return default settings
        return GlobalSettings()
    
    def save_settings(self, settings: GlobalSettings):
        """Save global settings to file."""
        self.settings = settings
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(asdict(settings), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def import_claude_logs(self, claude_data_path: Optional[str] = None) -> int:
        """
        Import usage data from Claude Code logs.
        
        Args:
            claude_data_path: Path to Claude data directory
            
        Returns:
            Number of records imported
        """
        if not self.settings.usage_tracking_enabled:
            return 0
        
        try:
            # Use claude_monitor_integration to load data
            from .claude_monitor_integration import ClaudeMonitorIntegration
            
            monitor = ClaudeMonitorIntegration(
                claude_data_path=claude_data_path,
                plan_type=self.settings.claude_plan
            )
            
            # Load all available data
            entries = monitor.load_usage_data()
            
            if not entries:
                return 0
            
            # Get current project path
            project_path = os.getcwd()
            
            # Convert and store records
            imported = 0
            with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
                cursor = conn.cursor()
                
                for entry in entries:
                    try:
                        # Check if record already exists
                        cursor.execute('''
                            SELECT id FROM usage_records
                            WHERE timestamp = ? AND message_id = ? AND request_id = ?
                        ''', (entry.timestamp, entry.message_id, entry.request_id))
                        
                        if cursor.fetchone():
                            continue
                        
                        # Insert new record
                        cursor.execute('''
                            INSERT INTO usage_records (
                                timestamp, project_path, input_tokens, output_tokens,
                                cache_creation_tokens, cache_read_tokens, total_tokens,
                                model, cost, message_id, request_id, session_id, metadata
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            entry.timestamp,
                            project_path,
                            entry.input_tokens,
                            entry.output_tokens,
                            entry.cache_creation_tokens,
                            entry.cache_read_tokens,
                            entry.input_tokens + entry.output_tokens + 
                            entry.cache_creation_tokens + entry.cache_read_tokens,
                            entry.model,
                            entry.cost_usd,
                            entry.message_id,
                            entry.request_id,
                            getattr(entry, 'session_id', None),
                            json.dumps({'imported_at': datetime.now().isoformat()})
                        ))
                        
                        imported += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to import record: {e}")
                        continue
                
                # Update project stats
                self._update_project_stats(conn, project_path)
                
                conn.commit()
            
            logger.info(f"Imported {imported} usage records")
            return imported
            
        except Exception as e:
            logger.error(f"Failed to import Claude logs: {e}")
            return 0
    
    def _update_project_stats(self, conn: sqlite3.Connection, project_path: str):
        """Update project statistics."""
        cursor = conn.cursor()
        
        # Get aggregated stats for project
        cursor.execute('''
            SELECT 
                MIN(timestamp) as first_used,
                MAX(timestamp) as last_used,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                COUNT(*) as total_requests
            FROM usage_records
            WHERE project_path = ?
        ''', (project_path,))
        
        row = cursor.fetchone()
        if row and row[0]:  # Check if we have data
            cursor.execute('''
                INSERT OR REPLACE INTO project_stats (
                    project_path, first_used, last_used, 
                    total_tokens, total_cost, total_requests
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_path, row[0], row[1], row[2] or 0, row[3] or 0, row[4] or 0))
    
    def get_usage_stats(self, 
                        days: int = 30,
                        project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Args:
            days: Number of days to include
            project_path: Filter by project (None for all)
            
        Returns:
            Dictionary with usage statistics
        """
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            # Build query conditions
            conditions = ["timestamp >= ?"]
            params = [datetime.now() - timedelta(days=days)]
            
            if project_path:
                conditions.append("project_path = ?")
                params.append(project_path)
            
            where_clause = " AND ".join(conditions)
            
            # Get total stats
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(total_tokens) as total_tokens,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(cache_creation_tokens) as cache_creation_tokens,
                    SUM(cache_read_tokens) as cache_read_tokens,
                    SUM(cost) as total_cost
                FROM usage_records
                WHERE {where_clause}
            ''', params)
            
            row = cursor.fetchone()
            
            # Get today's stats
            today_conditions = conditions + ["DATE(timestamp) = DATE('now')"]
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as requests,
                    SUM(total_tokens) as tokens,
                    SUM(cost) as cost
                FROM usage_records
                WHERE {" AND ".join(today_conditions)}
            ''', params)
            
            today_row = cursor.fetchone()
            
            # Get this month's stats
            month_conditions = conditions + ["DATE(timestamp) >= DATE('now', 'start of month')"]
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as requests,
                    SUM(total_tokens) as tokens,
                    SUM(cost) as cost
                FROM usage_records
                WHERE {" AND ".join(month_conditions)}
            ''', params)
            
            month_row = cursor.fetchone()
            
            # Get model breakdown
            cursor.execute(f'''
                SELECT 
                    model,
                    COUNT(*) as requests,
                    SUM(total_tokens) as tokens,
                    SUM(cost) as cost
                FROM usage_records
                WHERE {where_clause}
                GROUP BY model
                ORDER BY tokens DESC
            ''', params)
            
            model_breakdown = [
                {
                    'model': row[0] or 'unknown',
                    'requests': row[1],
                    'tokens': row[2] or 0,
                    'cost': row[3] or 0
                }
                for row in cursor.fetchall()
            ]
            
            # Get project breakdown (if not filtering by project)
            project_breakdown = []
            if not project_path:
                cursor.execute(f'''
                    SELECT 
                        project_path,
                        COUNT(*) as requests,
                        SUM(total_tokens) as tokens,
                        SUM(cost) as cost
                    FROM usage_records
                    WHERE {where_clause}
                    GROUP BY project_path
                    ORDER BY tokens DESC
                    LIMIT 10
                ''', params)
                
                project_breakdown = [
                    {
                        'project': Path(row[0]).name if row[0] else 'unknown',
                        'path': row[0],
                        'requests': row[1],
                        'tokens': row[2] or 0,
                        'cost': row[3] or 0
                    }
                    for row in cursor.fetchall()
                ]
            
            return {
                'total': {
                    'requests': row[0] or 0,
                    'tokens': row[1] or 0,
                    'input_tokens': row[2] or 0,
                    'output_tokens': row[3] or 0,
                    'cache_creation_tokens': row[4] or 0,
                    'cache_read_tokens': row[5] or 0,
                    'cost': row[6] or 0
                },
                'today': {
                    'requests': today_row[0] or 0,
                    'tokens': today_row[1] or 0,
                    'cost': today_row[2] or 0
                },
                'this_month': {
                    'requests': month_row[0] or 0,
                    'tokens': month_row[1] or 0,
                    'cost': month_row[2] or 0
                },
                'model_breakdown': model_breakdown,
                'project_breakdown': project_breakdown,
                'period_days': days,
                'project_filter': project_path
            }
    
    def add_favorite_prompt(self, 
                           title: str,
                           content: str,
                           tags: List[str] = None,
                           project_path: Optional[str] = None) -> str:
        """
        Add a favorite prompt.
        
        Args:
            title: Prompt title
            content: Prompt content
            tags: List of tags
            project_path: Associated project path
            
        Returns:
            ID of the created favorite
        """
        if not self.settings.favorite_prompts_enabled:
            return ""
        
        import uuid
        prompt_id = str(uuid.uuid4())[:8]
        
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO favorite_prompts (
                    id, title, content, project_path, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                prompt_id,
                title,
                content,
                project_path or os.getcwd(),
                json.dumps(tags or []),
                datetime.now()
            ))
            
            conn.commit()
        
        return prompt_id
    
    def get_favorite_prompts(self,
                            project_path: Optional[str] = None,
                            tags: Optional[List[str]] = None) -> List[FavoritePrompt]:
        """
        Get favorite prompts.
        
        Args:
            project_path: Filter by project
            tags: Filter by tags
            
        Returns:
            List of favorite prompts
        """
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if project_path:
                conditions.append("project_path = ?")
                params.append(project_path)
            
            query = '''
                SELECT id, title, content, project_path, tags, 
                       created_at, last_used, use_count, metadata
                FROM favorite_prompts
            '''
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY use_count DESC, last_used DESC"
            
            cursor.execute(query, params)
            
            favorites = []
            for row in cursor.fetchall():
                # Filter by tags if specified
                prompt_tags = json.loads(row[4]) if row[4] else []
                if tags and not any(tag in prompt_tags for tag in tags):
                    continue
                
                favorites.append(FavoritePrompt(
                    id=row[0],
                    title=row[1],
                    content=row[2],
                    project_path=row[3],
                    tags=prompt_tags,
                    created_at=datetime.fromisoformat(row[5]),
                    last_used=datetime.fromisoformat(row[6]) if row[6] else None,
                    use_count=row[7] or 0,
                    metadata=json.loads(row[8]) if row[8] else None
                ))
            
            return favorites
    
    def use_favorite_prompt(self, prompt_id: str):
        """Mark a favorite prompt as used."""
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE favorite_prompts
                SET last_used = ?, use_count = use_count + 1
                WHERE id = ?
            ''', (datetime.now(), prompt_id))
            
            conn.commit()
    
    def sync_chat_history(self, project_path: Optional[str] = None) -> int:
        """
        Sync chat history from Claude logs to database.
        
        Args:
            project_path: Project path to sync (defaults to current directory)
            
        Returns:
            Number of messages synced
        """
        try:
            from .claude_logs_reader import ClaudeLogsReader
            
            # Use current directory if not specified
            if project_path is None:
                project_path = os.getcwd()
            
            reader = ClaudeLogsReader(project_path)
            
            # Get all sessions for the project
            sessions = reader.get_all_sessions()
            
            if not sessions:
                logger.info("No chat sessions found to sync")
                return 0
            
            synced_messages = 0
            
            with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
                cursor = conn.cursor()
                
                for session_info in sessions:
                    session_id = session_info['session_id']
                    
                    # Check if session already exists
                    cursor.execute('SELECT session_id FROM chat_sessions WHERE session_id = ?', (session_id,))
                    session_exists = cursor.fetchone() is not None
                    
                    # Get full history for this session
                    history = reader.get_prompt_history(session_id, limit=10000)
                    
                    if not history:
                        continue
                    
                    # Extract session metadata
                    first_msg = min(history, key=lambda x: x.get('timestamp', ''))
                    last_msg = max(history, key=lambda x: x.get('timestamp', ''))
                    
                    user_msgs = [h for h in history if h['type'] == 'user']
                    assistant_msgs = [h for h in history if h['type'] == 'assistant']
                    
                    total_tokens = sum(
                        msg.get('usage', {}).get('input_tokens', 0) + 
                        msg.get('usage', {}).get('output_tokens', 0)
                        for msg in assistant_msgs
                    )
                    
                    # Insert or update session
                    if not session_exists:
                        cursor.execute('''
                            INSERT INTO chat_sessions (
                                session_id, project_path, start_time, last_activity,
                                prompt_count, response_count, total_tokens, git_branch, metadata
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            session_id,
                            project_path,
                            first_msg.get('timestamp'),
                            last_msg.get('timestamp'),
                            len(user_msgs),
                            len(assistant_msgs),
                            total_tokens,
                            first_msg.get('git_branch'),
                            json.dumps({
                                'file_size': session_info.get('file_size', 0),
                                'synced_at': datetime.now().isoformat()
                            })
                        ))
                    else:
                        cursor.execute('''
                            UPDATE chat_sessions
                            SET last_activity = ?, prompt_count = ?, response_count = ?, 
                                total_tokens = ?
                            WHERE session_id = ?
                        ''', (
                            last_msg.get('timestamp'),
                            len(user_msgs),
                            len(assistant_msgs),
                            total_tokens,
                            session_id
                        ))
                    
                    # Insert messages
                    for msg in history:
                        msg_id = msg.get('id')
                        
                        # Check if message already exists
                        cursor.execute('SELECT id FROM chat_messages WHERE id = ?', (msg_id,))
                        if cursor.fetchone():
                            continue
                        
                        # Calculate costs if assistant message
                        cost = None
                        input_tokens = None
                        output_tokens = None
                        
                        if msg['type'] == 'assistant' and 'usage' in msg:
                            usage = msg['usage']
                            input_tokens = usage.get('input_tokens', 0)
                            output_tokens = usage.get('output_tokens', 0)
                            
                            # Simple cost calculation (adjust rates as needed)
                            # Assuming Claude 3 rates
                            input_cost = input_tokens * 0.000015  # $15 per million
                            output_cost = output_tokens * 0.000075  # $75 per million
                            cost = input_cost + output_cost
                        
                        cursor.execute('''
                            INSERT INTO chat_messages (
                                id, session_id, message_type, content, timestamp,
                                parent_uuid, model, input_tokens, output_tokens, cost,
                                git_branch, cwd, metadata
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            msg_id,
                            session_id,
                            msg['type'],
                            msg.get('content', ''),
                            msg.get('timestamp'),
                            msg.get('parent_uuid'),
                            msg.get('model'),
                            input_tokens,
                            output_tokens,
                            cost,
                            msg.get('git_branch'),
                            msg.get('cwd'),
                            json.dumps({'synced_at': datetime.now().isoformat()})
                        ))
                        
                        synced_messages += 1
                
                conn.commit()
            
            logger.info(f"Synced {synced_messages} chat messages from {len(sessions)} sessions")
            return synced_messages
            
        except Exception as e:
            logger.error(f"Failed to sync chat history: {e}")
            return 0
    
    def get_chat_history(self, 
                        session_id: Optional[str] = None,
                        project_path: Optional[str] = None,
                        days: int = 30,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get chat history from database.
        
        Args:
            session_id: Specific session to retrieve
            project_path: Filter by project
            days: Number of days to look back
            limit: Maximum messages to return
            
        Returns:
            List of chat messages with metadata
        """
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if session_id:
                conditions.append("m.session_id = ?")
                params.append(session_id)
            
            if project_path:
                conditions.append("s.project_path = ?")
                params.append(project_path)
            
            if days:
                cutoff = datetime.now() - timedelta(days=days)
                conditions.append("m.timestamp >= ?")
                params.append(cutoff.isoformat())
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f'''
                SELECT 
                    m.id, m.session_id, m.message_type, m.content,
                    m.timestamp, m.parent_uuid, m.model,
                    m.input_tokens, m.output_tokens, m.cost,
                    m.git_branch, m.cwd,
                    s.project_path
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.session_id
                WHERE {where_clause}
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', params + [limit])
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'session_id': row[1],
                    'type': row[2],
                    'content': row[3],
                    'timestamp': row[4],
                    'parent_uuid': row[5],
                    'model': row[6],
                    'input_tokens': row[7],
                    'output_tokens': row[8],
                    'cost': row[9],
                    'git_branch': row[10],
                    'cwd': row[11],
                    'project_path': row[12]
                })
            
            return messages
    
    def get_chat_sessions(self,
                         project_path: Optional[str] = None,
                         days: int = 30) -> List[Dict[str, Any]]:
        """
        Get chat sessions from database.
        
        Args:
            project_path: Filter by project
            days: Number of days to look back
            
        Returns:
            List of chat sessions with metadata
        """
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if project_path:
                conditions.append("project_path = ?")
                params.append(project_path)
            
            if days:
                cutoff = datetime.now() - timedelta(days=days)
                conditions.append("last_activity >= ?")
                params.append(cutoff.isoformat())
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f'''
                SELECT 
                    session_id, project_path, start_time, last_activity,
                    prompt_count, response_count, total_tokens, git_branch
                FROM chat_sessions
                WHERE {where_clause}
                ORDER BY last_activity DESC
            ''', params)
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'project_path': row[1],
                    'start_time': row[2],
                    'last_activity': row[3],
                    'prompt_count': row[4],
                    'response_count': row[5],
                    'total_tokens': row[6],
                    'git_branch': row[7]
                })
            
            return sessions
    
    def cleanup_old_data(self, days: Optional[int] = None):
        """
        Clean up old usage data.
        
        Args:
            days: Days to keep (uses settings if not specified)
        """
        if not self.settings.usage_tracking_enabled:
            return
        
        days = days or self.settings.auto_cleanup_days
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
            cursor = conn.cursor()
            
            # Delete old usage records
            cursor.execute('''
                DELETE FROM usage_records
                WHERE timestamp < ?
            ''', (cutoff_date,))
            
            deleted_usage = cursor.rowcount
            
            # Delete old chat messages
            cursor.execute('''
                DELETE FROM chat_messages
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_messages = cursor.rowcount
            
            # Delete orphaned chat sessions
            cursor.execute('''
                DELETE FROM chat_sessions
                WHERE session_id NOT IN (
                    SELECT DISTINCT session_id FROM chat_messages
                )
            ''')
            
            deleted_sessions = cursor.rowcount
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
            conn.commit()
        
        logger.info(f"Cleaned up {deleted_usage} usage records, {deleted_messages} chat messages, {deleted_sessions} sessions")
    
    def backup_database(self) -> Optional[str]:
        """
        Create a backup of the database.
        
        Returns:
            Path to backup file if successful
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backups_dir / f"global_{timestamp}.db"
            
            shutil.copy2(self.db_path, backup_path)
            
            # Keep only last 5 backups
            backups = sorted(self.backups_dir.glob("global_*.db"))
            if len(backups) > 5:
                for old_backup in backups[:-5]:
                    old_backup.unlink()
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about storage usage."""
        total_size = 0
        file_count = 0
        
        for path in self.global_dir.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size
                file_count += 1
        
        return {
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
            'database_size_mb': round(self.db_path.stat().st_size / (1024 * 1024), 2) if self.db_path.exists() else 0,
            'max_storage_mb': self.settings.max_storage_mb,
            'usage_percentage': round((total_size / (1024 * 1024)) / self.settings.max_storage_mb * 100, 1)
        }
    
    def export_data(self, output_path: str, format: str = 'json') -> bool:
        """
        Export all data for backup or migration.
        
        Args:
            output_path: Path to export file
            format: Export format (json, csv)
            
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(str(self.db_path), timeout=30.0) as conn:
                cursor = conn.cursor()
                
                data = {
                    'settings': asdict(self.settings),
                    'export_date': datetime.now().isoformat(),
                    'usage_records': [],
                    'favorite_prompts': [],
                    'project_stats': []
                }
                
                # Export usage records
                cursor.execute('SELECT * FROM usage_records ORDER BY timestamp DESC')
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    record = dict(zip(columns, row))
                    data['usage_records'].append(record)
                
                # Export favorites
                cursor.execute('SELECT * FROM favorite_prompts ORDER BY created_at DESC')
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    favorite = dict(zip(columns, row))
                    data['favorite_prompts'].append(favorite)
                
                # Export project stats
                cursor.execute('SELECT * FROM project_stats ORDER BY last_used DESC')
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    stats = dict(zip(columns, row))
                    data['project_stats'].append(stats)
                
                # Write to file
                output = Path(output_path)
                with open(output, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False