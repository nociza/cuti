"""
Log Synchronization Service - Syncs Claude logs with local workspace database.
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib
import re


class LogSyncService:
    """Synchronizes Claude logs with local workspace database."""
    
    def __init__(self, workspace_manager):
        """Initialize the log sync service."""
        self.workspace_manager = workspace_manager
        self.claude_logs_dir = Path.home() / ".claude" / "projects"
        self.history_db = workspace_manager.get_db_path("history.db")
        self.last_sync_file = workspace_manager.get_cache_path("last_sync.json")
    
    def sync_all(self) -> Dict[str, Any]:
        """Perform a full synchronization of all data sources."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "claude_logs": self.sync_claude_logs(),
            "todos": self.sync_todos(),
            "status": "success"
        }
        
        # Save last sync time
        self._save_last_sync(results)
        
        # Log sync operation
        self._log_sync_operation(results)
        
        return results
    
    def sync_claude_logs(self) -> Dict[str, int]:
        """Sync Claude logs to local database."""
        synced = 0
        skipped = 0
        errors = 0
        
        if not self.claude_logs_dir.exists():
            return {"synced": 0, "skipped": 0, "errors": 0}
        
        conn = sqlite3.connect(str(self.history_db))
        cursor = conn.cursor()
        
        # Get all session directories
        for session_dir in self.claude_logs_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            session_id = session_dir.name
            
            # Process conversation.md files
            conversation_file = session_dir / "conversation.md"
            if conversation_file.exists():
                try:
                    content = conversation_file.read_text()
                    prompts = self._parse_conversation_file(content, session_id)
                    
                    for prompt in prompts:
                        # Check if already exists
                        cursor.execute("""
                            SELECT id FROM command_history 
                            WHERE session_id = ? AND timestamp = ? AND command = ?
                        """, (prompt['session_id'], prompt['timestamp'], prompt['command']))
                        
                        if cursor.fetchone():
                            skipped += 1
                        else:
                            # Insert new record
                            cursor.execute("""
                                INSERT INTO command_history 
                                (session_id, timestamp, command, response, tokens_used, cost, 
                                 duration, status, cwd, git_branch, model, source, claude_log_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                prompt['session_id'],
                                prompt['timestamp'],
                                prompt['command'],
                                prompt.get('response', ''),
                                prompt.get('tokens_used', 0),
                                prompt.get('cost', 0.0),
                                prompt.get('duration', 0.0),
                                prompt.get('status', 'unknown'),
                                prompt.get('cwd', ''),
                                prompt.get('git_branch', ''),
                                prompt.get('model', 'unknown'),
                                'claude_logs',
                                prompt.get('log_id', '')
                            ))
                            synced += 1
                except Exception as e:
                    print(f"Error syncing session {session_id}: {e}")
                    errors += 1
        
        conn.commit()
        conn.close()
        
        return {"synced": synced, "skipped": skipped, "errors": errors}
    
    def sync_todos(self) -> Dict[str, int]:
        """Sync todos from Claude logs."""
        synced = 0
        skipped = 0
        errors = 0
        
        todos_dir = Path.home() / ".claude" / "todos"
        if not todos_dir.exists():
            return {"synced": 0, "skipped": 0, "errors": 0}
        
        conn = sqlite3.connect(str(self.history_db))
        cursor = conn.cursor()
        
        for todo_file in todos_dir.glob("*.json"):
            try:
                with open(todo_file, 'r') as f:
                    todos_data = json.load(f)
                
                session_id = todo_file.stem
                
                # Handle both array and object formats
                if isinstance(todos_data, list):
                    todos = todos_data
                elif isinstance(todos_data, dict):
                    todos = todos_data.get('todos', [])
                else:
                    todos = []
                
                for todo in todos:
                    if not isinstance(todo, dict):
                        continue
                    todo_id = todo.get('id', self._generate_todo_id(todo))
                    
                    # Check if exists
                    cursor.execute(
                        "SELECT id FROM todos WHERE todo_id = ?",
                        (todo_id,)
                    )
                    
                    if cursor.fetchone():
                        # Update existing
                        cursor.execute("""
                            UPDATE todos 
                            SET status = ?, content = ?
                            WHERE todo_id = ?
                        """, (
                            todo.get('status', 'pending'),
                            todo.get('content', ''),
                            todo_id
                        ))
                        skipped += 1
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO todos 
                            (session_id, todo_id, content, status, created_at, source)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            session_id,
                            todo_id,
                            todo.get('content', ''),
                            todo.get('status', 'pending'),
                            todo.get('created_at', datetime.now().isoformat()),
                            'claude_logs'
                        ))
                        synced += 1
                        
            except Exception as e:
                print(f"Error syncing todos from {todo_file}: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {"synced": synced, "skipped": skipped, "errors": errors}
    
    def _parse_conversation_file(self, content: str, session_id: str) -> List[Dict[str, Any]]:
        """Parse a conversation.md file to extract prompts and responses."""
        prompts = []
        
        # Split by Human/Assistant sections
        sections = re.split(r'^(Human:|Assistant:)', content, flags=re.MULTILINE)
        
        current_prompt = None
        for i in range(0, len(sections), 2):
            if i + 1 >= len(sections):
                break
            
            role = sections[i].strip(':')
            text = sections[i + 1].strip() if i + 1 < len(sections) else ''
            
            if role == 'Human':
                # Extract timestamp if available
                timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', text)
                timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()
                
                # Clean command text
                command = re.sub(r'\[.*?\]', '', text).strip()
                
                current_prompt = {
                    'session_id': session_id,
                    'timestamp': timestamp,
                    'command': command,
                    'log_id': self._generate_log_id(session_id, timestamp, command)
                }
                
            elif role == 'Assistant' and current_prompt:
                current_prompt['response'] = text
                
                # Try to extract token usage
                token_match = re.search(r'Tokens: (\d+)', text)
                if token_match:
                    current_prompt['tokens_used'] = int(token_match.group(1))
                
                prompts.append(current_prompt)
                current_prompt = None
        
        return prompts
    
    def _generate_todo_id(self, todo: Dict) -> str:
        """Generate a unique ID for a todo item."""
        content = todo.get('content', '')
        created = todo.get('created_at', '')
        return hashlib.md5(f"{content}{created}".encode()).hexdigest()[:16]
    
    def _generate_log_id(self, session_id: str, timestamp: str, command: str) -> str:
        """Generate a unique ID for a log entry."""
        return hashlib.md5(f"{session_id}{timestamp}{command}".encode()).hexdigest()[:16]
    
    def _save_last_sync(self, results: Dict):
        """Save the last sync results."""
        with open(self.last_sync_file, 'w') as f:
            json.dump(results, f, indent=2)
    
    def _log_sync_operation(self, results: Dict):
        """Log the sync operation to the database."""
        conn = sqlite3.connect(str(self.history_db))
        cursor = conn.cursor()
        
        total_synced = (
            results['claude_logs']['synced'] + 
            results['todos']['synced']
        )
        
        cursor.execute("""
            INSERT INTO sync_log (source, records_synced, status)
            VALUES (?, ?, ?)
        """, ('claude_logs', total_synced, results['status']))
        
        conn.commit()
        conn.close()
    
    def get_last_sync(self) -> Optional[Dict]:
        """Get information about the last sync."""
        if self.last_sync_file.exists():
            with open(self.last_sync_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get the current sync status."""
        conn = sqlite3.connect(str(self.history_db))
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM command_history WHERE source = 'claude_logs'")
        claude_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM command_history WHERE source = 'cuti'")
        cuti_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM todos")
        todos_count = cursor.fetchone()[0]
        
        # Get last sync
        cursor.execute("""
            SELECT sync_time, records_synced, status 
            FROM sync_log 
            ORDER BY id DESC 
            LIMIT 1
        """)
        last_sync = cursor.fetchone()
        
        conn.close()
        
        return {
            "claude_logs_count": claude_count,
            "cuti_count": cuti_count,
            "todos_count": todos_count,
            "last_sync": {
                "time": last_sync[0] if last_sync else None,
                "records": last_sync[1] if last_sync else 0,
                "status": last_sync[2] if last_sync else "never"
            }
        }
    
    def auto_sync(self, interval: int = 300):
        """Perform automatic synchronization at regular intervals."""
        import threading
        
        def sync_worker():
            while True:
                try:
                    self.sync_all()
                except Exception as e:
                    print(f"Auto-sync error: {e}")
                
                threading.Event().wait(interval)
        
        # Start sync thread
        sync_thread = threading.Thread(target=sync_worker, daemon=True)
        sync_thread.start()