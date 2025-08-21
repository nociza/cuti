"""
Container Usage Sync Service
Syncs Claude usage data from container back to host's global database.
"""

import os
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import time
import threading

logger = logging.getLogger(__name__)


class ContainerUsageSync:
    """Syncs Claude usage data from container to host."""
    
    def __init__(self):
        """Initialize the container usage sync service."""
        self.is_container = os.environ.get("CUTI_IN_CONTAINER") == "true"
        
        # Paths for container environment
        if self.is_container:
            # In container, Claude data is in /root/.claude
            self.container_claude_path = Path("/root/.claude")
            # Host's .cuti is mounted at /root/.cuti-global
            self.host_cuti_path = Path("/root/.cuti-global")
            # Also available at /home/cuti/.cuti for the cuti user
            self.alt_host_path = Path("/home/cuti/.cuti")
        else:
            # On host, use regular paths
            self.container_claude_path = None
            self.host_cuti_path = Path.home() / ".cuti"
            self.alt_host_path = None
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_sync = None
        self._sync_count = 0
    
    def should_run(self) -> bool:
        """Check if sync service should run."""
        # Only run in container environment
        if not self.is_container:
            return False
        
        # Check if paths exist
        if not self.container_claude_path or not self.container_claude_path.exists():
            logger.debug("Container Claude path doesn't exist")
            return False
        
        if not self.host_cuti_path.exists():
            logger.debug("Host cuti path not mounted")
            return False
        
        return True
    
    def sync_usage_data(self) -> int:
        """
        Sync usage data from container Claude logs to host database.
        
        Returns:
            Number of records synced
        """
        if not self.should_run():
            return 0
        
        try:
            records_synced = 0
            
            # Find Claude usage logs in container
            claude_logs = self.container_claude_path / "projects"
            if not claude_logs.exists():
                logger.debug("No Claude project logs found in container")
                return 0
            
            # Get or create host database
            host_db_path = self.host_cuti_path / "databases" / "global.db"
            host_db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to host database
            conn = sqlite3.connect(str(host_db_path))
            cursor = conn.cursor()
            
            # Ensure usage_logs table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    project_path TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cache_creation_tokens INTEGER,
                    cache_read_tokens INTEGER,
                    total_tokens INTEGER,
                    model TEXT,
                    cost REAL,
                    message_id TEXT,
                    request_id TEXT,
                    session_id TEXT,
                    metadata TEXT,
                    source TEXT DEFAULT 'container',
                    synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, message_id, request_id)
                )
            """)
            
            # Process each project directory
            for project_dir in claude_logs.iterdir():
                if not project_dir.is_dir():
                    continue
                
                # Look for usage.json or similar files
                for usage_file in project_dir.glob("*.json"):
                    try:
                        with open(usage_file, 'r') as f:
                            usage_data = json.load(f)
                        
                        # Process usage data based on format
                        if isinstance(usage_data, list):
                            for record in usage_data:
                                if self._insert_usage_record(cursor, record, str(project_dir)):
                                    records_synced += 1
                        elif isinstance(usage_data, dict):
                            if self._insert_usage_record(cursor, usage_data, str(project_dir)):
                                records_synced += 1
                    
                    except Exception as e:
                        logger.debug(f"Error processing {usage_file}: {e}")
                        continue
            
            # Also check for Claude monitor data if available
            claude_monitor_path = self.container_claude_path / ".claude-monitor"
            if claude_monitor_path.exists():
                records_synced += self._sync_claude_monitor_data(cursor, claude_monitor_path)
            
            # Commit changes
            conn.commit()
            conn.close()
            
            if records_synced > 0:
                logger.info(f"Synced {records_synced} usage records from container to host")
                
                # Update sync timestamp
                sync_marker = self.host_cuti_path / ".container_last_sync"
                sync_marker.write_text(datetime.now().isoformat())
            
            self._last_sync = datetime.now()
            self._sync_count += 1
            
            return records_synced
            
        except Exception as e:
            logger.error(f"Error syncing container usage data: {e}")
            return 0
    
    def _insert_usage_record(self, cursor, record: Dict[str, Any], project_path: str) -> bool:
        """Insert a usage record into the database."""
        try:
            # Extract fields from record
            timestamp = record.get('timestamp', datetime.now().isoformat())
            input_tokens = record.get('input_tokens', 0)
            output_tokens = record.get('output_tokens', 0)
            cache_creation = record.get('cache_creation_tokens', 0)
            cache_read = record.get('cache_read_tokens', 0)
            total_tokens = record.get('total_tokens', 
                                    input_tokens + output_tokens + cache_creation + cache_read)
            model = record.get('model', 'unknown')
            cost = record.get('cost', 0.0)
            message_id = record.get('message_id')
            request_id = record.get('request_id')
            session_id = record.get('session_id')
            metadata = json.dumps(record.get('metadata', {}))
            
            # Insert with conflict handling
            cursor.execute("""
                INSERT OR IGNORE INTO usage_logs (
                    timestamp, project_path, input_tokens, output_tokens,
                    cache_creation_tokens, cache_read_tokens, total_tokens,
                    model, cost, message_id, request_id, session_id, metadata, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'container')
            """, (
                timestamp, project_path, input_tokens, output_tokens,
                cache_creation, cache_read, total_tokens,
                model, cost, message_id, request_id, session_id, metadata
            ))
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.debug(f"Failed to insert usage record: {e}")
            return False
    
    def _sync_claude_monitor_data(self, cursor, monitor_path: Path) -> int:
        """Sync data from claude-monitor if available."""
        records_synced = 0
        
        try:
            # Look for claude-monitor database
            monitor_db = monitor_path / "usage.db"
            if monitor_db.exists():
                # Connect to monitor database
                monitor_conn = sqlite3.connect(str(monitor_db))
                monitor_cursor = monitor_conn.cursor()
                
                # Try to read usage data
                try:
                    monitor_cursor.execute("""
                        SELECT timestamp, model, input_tokens, output_tokens,
                               cache_creation_tokens, cache_read_tokens, cost
                        FROM usage_logs
                        WHERE timestamp > datetime('now', '-7 days')
                        ORDER BY timestamp DESC
                    """)
                    
                    for row in monitor_cursor.fetchall():
                        record = {
                            'timestamp': row[0],
                            'model': row[1],
                            'input_tokens': row[2],
                            'output_tokens': row[3],
                            'cache_creation_tokens': row[4],
                            'cache_read_tokens': row[5],
                            'cost': row[6]
                        }
                        
                        if self._insert_usage_record(cursor, record, "container"):
                            records_synced += 1
                
                except Exception as e:
                    logger.debug(f"Error reading claude-monitor data: {e}")
                
                monitor_conn.close()
        
        except Exception as e:
            logger.debug(f"Error accessing claude-monitor: {e}")
        
        return records_synced
    
    def start_background_sync(self, interval: int = 300):
        """
        Start background sync service.
        
        Args:
            interval: Seconds between sync attempts (default 5 minutes)
        """
        if not self.should_run():
            logger.info("Container usage sync not needed in this environment")
            return
        
        if self._running:
            logger.warning("Container usage sync already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._sync_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()
        logger.info(f"Started container usage sync (interval: {interval}s)")
    
    def _sync_loop(self, interval: int):
        """Background sync loop."""
        while self._running:
            try:
                self.sync_usage_data()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                time.sleep(interval * 2)  # Backoff on error
    
    def stop_background_sync(self):
        """Stop background sync service."""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        # Do final sync
        self.sync_usage_data()
        logger.info("Stopped container usage sync")


# Global instance for easy access
_container_sync = None


def get_container_sync() -> ContainerUsageSync:
    """Get or create container sync instance."""
    global _container_sync
    if _container_sync is None:
        _container_sync = ContainerUsageSync()
    return _container_sync


def start_container_sync(interval: int = 300):
    """Start container usage sync if in container."""
    sync = get_container_sync()
    sync.start_background_sync(interval)


def sync_now() -> int:
    """Perform immediate sync."""
    sync = get_container_sync()
    return sync.sync_usage_data()