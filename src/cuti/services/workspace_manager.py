"""
Workspace Manager - Handles .cuti folder creation and management in project workspaces.
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import shutil


class WorkspaceManager:
    """Manages the .cuti folder in project workspaces."""
    
    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the workspace manager."""
        self.working_dir = Path(working_directory) if working_directory else Path.cwd()
        self.cuti_dir = self.working_dir / ".cuti"
        self.ensure_workspace()
    
    def ensure_workspace(self) -> Path:
        """Ensure the .cuti folder exists with proper structure."""
        # Create main .cuti directory
        self.cuti_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        subdirs = [
            "db",           # Database files
            "cache",        # Temporary cache
            "logs",         # Local logs
            "config",       # Workspace-specific config
            "backups"       # Backups of important data
        ]
        
        for subdir in subdirs:
            (self.cuti_dir / subdir).mkdir(exist_ok=True)
        
        # Create initial config if doesn't exist
        config_file = self.cuti_dir / "config" / "workspace.json"
        if not config_file.exists():
            self._create_initial_config(config_file)
        
        # Add to .gitignore
        self._update_gitignore()
        
        # Initialize databases
        self._init_databases()
        
        return self.cuti_dir
    
    def _create_initial_config(self, config_file: Path):
        """Create initial workspace configuration."""
        config = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "workspace_path": str(self.working_dir),
            "settings": {
                "auto_sync": True,
                "sync_interval": 300,  # 5 minutes
                "max_history_entries": 10000,
                "cleanup_days": 90
            }
        }
        
        config_file.write_text(json.dumps(config, indent=2))
    
    def _update_gitignore(self):
        """Add .cuti to .gitignore if not already present."""
        gitignore_path = self.working_dir / ".gitignore"
        cuti_entry = ".cuti/"
        
        # Check if we're in a git repository
        git_dir = self.working_dir / ".git"
        
        if git_dir.exists():
            # Read existing .gitignore
            if gitignore_path.exists():
                content = gitignore_path.read_text()
                lines = content.splitlines()
                
                # Check if .cuti is already in gitignore
                if not any(line.strip() in [".cuti", ".cuti/", "/.cuti/"] for line in lines):
                    # Add .cuti entry
                    with gitignore_path.open("a") as f:
                        if not content.endswith("\n") and content:
                            f.write("\n")
                        f.write("\n# Cuti workspace data\n")
                        f.write(".cuti/\n")
            else:
                # Create new .gitignore
                with gitignore_path.open("w") as f:
                    f.write("# Cuti workspace data\n")
                    f.write(".cuti/\n")
    
    def _init_databases(self):
        """Initialize workspace databases."""
        # History database
        history_db = self.get_db_path("history.db")
        self._init_history_db(history_db)
        
        # Metrics database
        metrics_db = self.get_db_path("metrics.db")
        self._init_metrics_db(metrics_db)
        
        # Agents database
        agents_db = self.get_db_path("agents.db")
        self._init_agents_db(agents_db)
    
    def _init_history_db(self, db_path: Path):
        """Initialize command history database."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                command TEXT NOT NULL,
                response TEXT,
                tokens_used INTEGER,
                cost REAL,
                duration REAL,
                status TEXT,
                cwd TEXT,
                git_branch TEXT,
                model TEXT,
                source TEXT DEFAULT 'cuti',
                claude_log_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, timestamp, command)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                todo_id TEXT UNIQUE,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT,
                source TEXT DEFAULT 'cuti'
            )
        """)
        
        # Add task execution history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_execution_history (
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
        """)
        
        # Add sub_tasks table for detailed tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_sub_tasks (
                id TEXT PRIMARY KEY,
                parent_task_id TEXT,
                agent_name TEXT,
                content TEXT,
                status TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_seconds REAL,
                metadata TEXT,
                FOREIGN KEY (parent_task_id) REFERENCES task_execution_history(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_time TEXT DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                records_synced INTEGER,
                status TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_session ON command_history(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON command_history(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_source ON command_history(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_session ON todos(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_session ON task_execution_history(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON task_execution_history(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_created ON task_execution_history(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subtask_parent ON task_sub_tasks(parent_task_id)")
        
        conn.commit()
        conn.close()
    
    def _init_metrics_db(self, db_path: Path):
        """Initialize metrics database."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                metric_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_usage REAL,
                network_sent REAL,
                network_recv REAL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_metrics(metric_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp)")
        
        conn.commit()
        conn.close()
    
    def _init_agents_db(self, db_path: Path):
        """Initialize agents database."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                invoked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                prompt TEXT,
                tokens_used INTEGER,
                duration REAL,
                status TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_registry (
                agent_name TEXT PRIMARY KEY,
                agent_type TEXT,
                description TEXT,
                capabilities TEXT,
                tools TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT,
                usage_count INTEGER DEFAULT 0
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_usage_name ON agent_usage(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_usage_session ON agent_usage(session_id)")
        
        conn.commit()
        conn.close()
    
    def get_db_path(self, db_name: str) -> Path:
        """Get the path to a database file."""
        return self.cuti_dir / "db" / db_name
    
    def get_config_path(self, config_name: str) -> Path:
        """Get the path to a config file."""
        return self.cuti_dir / "config" / config_name
    
    def get_cache_path(self, cache_name: str) -> Path:
        """Get the path to a cache file."""
        return self.cuti_dir / "cache" / cache_name
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get information about the current workspace."""
        return {
            "workspace_dir": str(self.working_dir),
            "cuti_dir": str(self.cuti_dir),
            "exists": self.cuti_dir.exists(),
            "databases": {
                "history": str(self.get_db_path("history.db")),
                "metrics": str(self.get_db_path("metrics.db")),
                "agents": str(self.get_db_path("agents.db"))
            },
            "size": self._get_folder_size(self.cuti_dir) if self.cuti_dir.exists() else 0
        }
    
    def _get_folder_size(self, folder: Path) -> int:
        """Get the total size of a folder in bytes."""
        total = 0
        for entry in folder.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
        return total
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data from the workspace."""
        cutoff_date = datetime.now().timestamp() - (days * 86400)
        
        # Clean up old metrics
        metrics_db = self.get_db_path("metrics.db")
        if metrics_db.exists():
            conn = sqlite3.connect(str(metrics_db))
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM usage_metrics WHERE datetime(timestamp) < datetime(?, 'unixepoch')",
                (cutoff_date,)
            )
            cursor.execute(
                "DELETE FROM system_metrics WHERE datetime(timestamp) < datetime(?, 'unixepoch')",
                (cutoff_date,)
            )
            conn.commit()
            conn.close()
    
    def backup_workspace(self) -> Path:
        """Create a backup of the workspace data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.tar.gz"
        backup_path = self.cuti_dir / "backups" / backup_name
        
        # Create tar.gz backup of db folder
        import tarfile
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(self.cuti_dir / "db", arcname="db")
            tar.add(self.cuti_dir / "config", arcname="config")
        
        # Clean up old backups (keep last 5)
        backups = sorted((self.cuti_dir / "backups").glob("backup_*.tar.gz"))
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                old_backup.unlink()
        
        return backup_path