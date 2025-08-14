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
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_project ON usage_records(project_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_model ON usage_records(model)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_project ON favorite_prompts(project_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_used ON favorite_prompts(last_used)')
            
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
            
            deleted = cursor.rowcount
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
            conn.commit()
        
        logger.info(f"Cleaned up {deleted} old usage records")
    
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