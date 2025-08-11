"""
Prompt history management system.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib


class PromptHistoryManager:
    """Manages prompt history with SQLite storage."""

    def __init__(self, base_dir: str = "~/.cuti"):
        self.base_dir = Path(base_dir).expanduser()
        self.db_path = self.base_dir / "history.db"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    working_directory TEXT NOT NULL,
                    context_files TEXT, -- JSON array
                    timestamp DATETIME NOT NULL,
                    estimated_tokens INTEGER,
                    success BOOLEAN,
                    execution_time REAL,
                    error_message TEXT,
                    output_preview TEXT,
                    tags TEXT -- JSON array of tags
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON prompt_history(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash ON prompt_history(content_hash)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_working_directory ON prompt_history(working_directory)
            """)
            
            conn.commit()

    def add_prompt_to_history(
        self,
        content: str,
        working_directory: str = ".",
        context_files: List[str] = None,
        estimated_tokens: Optional[int] = None,
        tags: List[str] = None
    ) -> bool:
        """Add a prompt to history."""
        if context_files is None:
            context_files = []
        if tags is None:
            tags = []
            
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO prompt_history (
                        content, content_hash, working_directory, context_files,
                        timestamp, estimated_tokens, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    content,
                    content_hash,
                    working_directory,
                    json.dumps(context_files),
                    datetime.now(),
                    estimated_tokens,
                    json.dumps(tags)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding prompt to history: {e}")
            return False

    def update_execution_result(
        self,
        content: str,
        success: bool,
        execution_time: Optional[float] = None,
        error_message: Optional[str] = None,
        output_preview: Optional[str] = None
    ) -> bool:
        """Update execution results for a prompt."""
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE prompt_history 
                    SET success = ?, execution_time = ?, error_message = ?, output_preview = ?
                    WHERE content_hash = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (
                    success,
                    execution_time,
                    error_message,
                    output_preview[:1000] if output_preview else None  # Limit preview size
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating execution result: {e}")
            return False

    def get_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get prompt history with pagination."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM prompt_history 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                results = []
                for row in cursor:
                    result = dict(row)
                    result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                    result['context_files'] = json.loads(result['context_files'] or '[]')
                    result['tags'] = json.loads(result['tags'] or '[]')
                    results.append(result)
                
                return results
        except Exception as e:
            print(f"Error getting history: {e}")
            return []

    def search_history(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search prompt history by content."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM prompt_history 
                    WHERE content LIKE ? OR working_directory LIKE ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (f'%{query}%', f'%{query}%', limit))
                
                results = []
                for row in cursor:
                    result = dict(row)
                    result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                    result['context_files'] = json.loads(result['context_files'] or '[]')
                    result['tags'] = json.loads(result['tags'] or '[]')
                    results.append(result)
                
                return results
        except Exception as e:
            print(f"Error searching history: {e}")
            return []

    def get_history_stats(self) -> Dict[str, Any]:
        """Get statistics about prompt history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_prompts,
                        COUNT(CASE WHEN success = 1 THEN 1 END) as successful_prompts,
                        COUNT(CASE WHEN success = 0 THEN 1 END) as failed_prompts,
                        AVG(execution_time) as avg_execution_time,
                        SUM(estimated_tokens) as total_estimated_tokens,
                        MIN(timestamp) as earliest_prompt,
                        MAX(timestamp) as latest_prompt
                    FROM prompt_history
                """)
                
                row = cursor.fetchone()
                if row:
                    stats = {
                        'total_prompts': row[0],
                        'successful_prompts': row[1] or 0,
                        'failed_prompts': row[2] or 0,
                        'success_rate': (row[1] or 0) / row[0] if row[0] > 0 else 0,
                        'avg_execution_time': row[3],
                        'total_estimated_tokens': row[4] or 0,
                        'earliest_prompt': row[5],
                        'latest_prompt': row[6]
                    }
                    
                    # Get popular working directories
                    cursor = conn.execute("""
                        SELECT working_directory, COUNT(*) as count
                        FROM prompt_history 
                        GROUP BY working_directory 
                        ORDER BY count DESC 
                        LIMIT 10
                    """)
                    stats['popular_directories'] = [
                        {'directory': row[0], 'count': row[1]} 
                        for row in cursor
                    ]
                    
                    # Get recent activity (last 7 days)
                    week_ago = datetime.now() - timedelta(days=7)
                    cursor = conn.execute("""
                        SELECT DATE(timestamp) as date, COUNT(*) as count
                        FROM prompt_history 
                        WHERE timestamp >= ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date DESC
                    """, (week_ago,))
                    stats['recent_activity'] = [
                        {'date': row[0], 'count': row[1]}
                        for row in cursor
                    ]
                    
                    return stats
                else:
                    return {
                        'total_prompts': 0,
                        'successful_prompts': 0,
                        'failed_prompts': 0,
                        'success_rate': 0,
                        'avg_execution_time': None,
                        'total_estimated_tokens': 0,
                        'earliest_prompt': None,
                        'latest_prompt': None,
                        'popular_directories': [],
                        'recent_activity': []
                    }
                    
        except Exception as e:
            print(f"Error getting history stats: {e}")
            return {}

    def get_similar_prompts(self, content: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar prompts in history (simple text similarity)."""
        words = set(content.lower().split())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM prompt_history 
                    ORDER BY timestamp DESC 
                    LIMIT 100
                """)  # Get recent prompts to compare against
                
                similar_prompts = []
                for row in cursor:
                    row_content = row['content'].lower()
                    row_words = set(row_content.split())
                    
                    # Simple Jaccard similarity
                    intersection = words.intersection(row_words)
                    union = words.union(row_words)
                    similarity = len(intersection) / len(union) if union else 0
                    
                    if similarity > 0.3:  # Threshold for similarity
                        result = dict(row)
                        result['similarity'] = similarity
                        result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                        result['context_files'] = json.loads(result['context_files'] or '[]')
                        result['tags'] = json.loads(result['tags'] or '[]')
                        similar_prompts.append(result)
                
                # Sort by similarity and return top results
                similar_prompts.sort(key=lambda x: x['similarity'], reverse=True)
                return similar_prompts[:limit]
                
        except Exception as e:
            print(f"Error finding similar prompts: {e}")
            return []

    def add_tags_to_prompt(self, prompt_id: int, tags: List[str]) -> bool:
        """Add tags to a specific prompt."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT tags FROM prompt_history WHERE id = ?
                """, (prompt_id,))
                
                row = cursor.fetchone()
                if not row:
                    return False
                
                existing_tags = set(json.loads(row[0] or '[]'))
                existing_tags.update(tags)
                
                conn.execute("""
                    UPDATE prompt_history 
                    SET tags = ? 
                    WHERE id = ?
                """, (json.dumps(list(existing_tags)), prompt_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error adding tags: {e}")
            return False

    def get_prompts_by_tag(self, tag: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get prompts filtered by tag."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM prompt_history 
                    WHERE tags LIKE ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (f'%"{tag}"%', limit))
                
                results = []
                for row in cursor:
                    result = dict(row)
                    result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                    result['context_files'] = json.loads(result['context_files'] or '[]')
                    result['tags'] = json.loads(result['tags'] or '[]')
                    
                    # Verify tag is actually in the list (not just substring match)
                    if tag in result['tags']:
                        results.append(result)
                
                return results
                
        except Exception as e:
            print(f"Error getting prompts by tag: {e}")
            return []

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all tags with usage counts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT tags FROM prompt_history 
                    WHERE tags IS NOT NULL AND tags != '[]'
                """)
                
                tag_counts = {}
                for row in cursor:
                    tags = json.loads(row[0] or '[]')
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # Sort by count descending
                return [
                    {'tag': tag, 'count': count}
                    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
                ]
                
        except Exception as e:
            print(f"Error getting all tags: {e}")
            return []

    def clear_history(self, older_than_days: Optional[int] = None) -> bool:
        """Clear history, optionally only entries older than specified days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if older_than_days:
                    cutoff_date = datetime.now() - timedelta(days=older_than_days)
                    conn.execute("""
                        DELETE FROM prompt_history 
                        WHERE timestamp < ?
                    """, (cutoff_date,))
                else:
                    conn.execute("DELETE FROM prompt_history")
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False

    def export_history(self, file_path: str, format: str = 'json') -> bool:
        """Export history to file in JSON or CSV format."""
        try:
            history = self.get_history(limit=10000)  # Get all history
            export_path = Path(file_path)
            
            if format.lower() == 'json':
                # Convert datetime objects to ISO format for JSON serialization
                for entry in history:
                    entry['timestamp'] = entry['timestamp'].isoformat()
                
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
                    
            elif format.lower() == 'csv':
                import csv
                
                with open(export_path, 'w', newline='', encoding='utf-8') as f:
                    if history:
                        fieldnames = [
                            'id', 'content', 'working_directory', 'context_files',
                            'timestamp', 'estimated_tokens', 'success', 
                            'execution_time', 'error_message', 'tags'
                        ]
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for entry in history:
                            # Convert lists to strings for CSV
                            entry['context_files'] = ','.join(entry['context_files'])
                            entry['tags'] = ','.join(entry['tags'])
                            writer.writerow({k: v for k, v in entry.items() if k in fieldnames})
            else:
                print(f"Unsupported export format: {format}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error exporting history: {e}")
            return False

    def get_duplicate_prompts(self) -> List[Dict[str, Any]]:
        """Find duplicate prompts in history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT content_hash, COUNT(*) as count, MAX(timestamp) as latest
                    FROM prompt_history 
                    GROUP BY content_hash
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC, latest DESC
                """)
                
                duplicates = []
                for row in cursor:
                    # Get all instances of this duplicate
                    instances_cursor = conn.execute("""
                        SELECT * FROM prompt_history 
                        WHERE content_hash = ?
                        ORDER BY timestamp DESC
                    """, (row[0],))
                    
                    instances = []
                    for instance_row in instances_cursor:
                        instance = dict(instance_row)
                        instance['timestamp'] = datetime.fromisoformat(instance['timestamp'])
                        instance['context_files'] = json.loads(instance['context_files'] or '[]')
                        instance['tags'] = json.loads(instance['tags'] or '[]')
                        instances.append(instance)
                    
                    duplicates.append({
                        'content_hash': row[0],
                        'count': row[1],
                        'latest': datetime.fromisoformat(row[2]),
                        'instances': instances
                    })
                
                return duplicates
                
        except Exception as e:
            print(f"Error finding duplicate prompts: {e}")
            return []