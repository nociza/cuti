"""
DEPRECATED: Claude Code usage monitoring integration.

This module has been replaced by claude_monitor_integration.py which uses 
the claude_monitor package directly as a library for better performance 
and more accurate data.

Use ClaudeMonitorIntegration from claude_monitor_integration.py instead.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import subprocess
from dataclasses import dataclass, asdict
import time

@dataclass
class TokenUsage:
    """Token usage data from Claude Code."""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    cost: float
    session_id: Optional[str] = None
    
@dataclass
class UsageStats:
    """Aggregated usage statistics."""
    total_tokens: int
    total_cost: float
    total_requests: int
    tokens_today: int
    cost_today: float
    requests_today: int
    tokens_this_month: int
    cost_this_month: float
    requests_this_month: int
    daily_limit: int
    monthly_limit: int
    daily_remaining: int
    monthly_remaining: int
    daily_percentage: float
    monthly_percentage: float


class ClaudeUsageMonitor:
    """Monitor Claude Code usage by reading from its data files."""
    
    # Token limits based on subscription plans
    PLAN_LIMITS = {
        'pro': {
            'daily': 1_000_000,  # 1M tokens per day
            'monthly': 30_000_000  # 30M tokens per month
        },
        'max5': {
            'daily': 5_000_000,  # 5M tokens per day
            'monthly': 150_000_000  # 150M tokens per month
        },
        'max20': {
            'daily': 20_000_000,  # 20M tokens per day
            'monthly': 600_000_000  # 600M tokens per month
        },
        'custom': {
            'daily': 10_000_000,  # Configurable
            'monthly': 300_000_000  # Configurable
        }
    }
    
    # Cost per token (approximate)
    TOKEN_COSTS = {
        'claude-3-opus': {'input': 0.000015, 'output': 0.000075},
        'claude-3-sonnet': {'input': 0.000003, 'output': 0.000015},
        'claude-3-haiku': {'input': 0.00000025, 'output': 0.00000125},
        'default': {'input': 0.000008, 'output': 0.000024}
    }
    
    def __init__(self, 
                 claude_data_path: Optional[str] = None,
                 plan: str = 'pro',
                 storage_dir: str = "~/.cuti"):
        """
        Initialize the usage monitor.
        
        Args:
            claude_data_path: Path to Claude Code data directory (auto-detect if None)
            plan: Subscription plan (pro, max5, max20, custom)
            storage_dir: Directory to store monitoring data
        """
        self.plan = plan
        self.limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['pro'])
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Find Claude Code data path
        if claude_data_path:
            self.claude_data_path = Path(claude_data_path).expanduser()
        else:
            self.claude_data_path = self._find_claude_data_path()
            
        # Initialize database
        self.db_path = self.storage_dir / "claude_usage.db"
        self._init_database()
        
    def _find_claude_data_path(self) -> Optional[Path]:
        """Auto-detect Claude Code data directory."""
        possible_paths = [
            Path("~/.claude/projects").expanduser(),
            Path("~/.config/claude/projects").expanduser(),
            Path("~/Library/Application Support/Claude/projects").expanduser(),
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
                
        return None
        
    def _init_database(self):
        """Initialize the usage tracking database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    model TEXT,
                    cost REAL,
                    session_id TEXT,
                    raw_data TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    request_count INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON token_usage(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_session ON token_usage(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON usage_sessions(session_id)")
            
            conn.commit()
            
    def read_claude_usage_data(self) -> List[Dict[str, Any]]:
        """
        Read usage data from Claude Code's data files.
        
        Returns:
            List of usage records
        """
        if not self.claude_data_path or not self.claude_data_path.exists():
            return []
            
        usage_data = []
        
        # Look for usage data in project directories
        for project_dir in self.claude_data_path.glob("*"):
            if not project_dir.is_dir():
                continue
                
            # Check for usage.json or similar files
            usage_files = list(project_dir.glob("**/*usage*.json")) + \
                         list(project_dir.glob("**/*metrics*.json")) + \
                         list(project_dir.glob("**/*tokens*.json"))
                         
            for usage_file in usage_files:
                try:
                    with open(usage_file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            usage_data.extend(data)
                        else:
                            usage_data.append(data)
                except (json.JSONDecodeError, IOError):
                    continue
                    
        # Also try to get data from Claude Code CLI if available
        try:
            result = subprocess.run(
                ["claude", "usage", "--json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                cli_data = json.loads(result.stdout)
                if isinstance(cli_data, list):
                    usage_data.extend(cli_data)
                else:
                    usage_data.append(cli_data)
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            pass
            
        return usage_data
        
    def process_usage_data(self, usage_data: List[Dict[str, Any]]) -> List[TokenUsage]:
        """
        Process raw usage data into TokenUsage objects.
        
        Args:
            usage_data: Raw usage data from Claude Code
            
        Returns:
            List of TokenUsage objects
        """
        processed = []
        
        for record in usage_data:
            try:
                # Handle different data formats
                timestamp = record.get('timestamp', record.get('created_at', datetime.now().isoformat()))
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp)
                    
                input_tokens = record.get('input_tokens', record.get('prompt_tokens', 0))
                output_tokens = record.get('output_tokens', record.get('completion_tokens', 0))
                total_tokens = record.get('total_tokens', input_tokens + output_tokens)
                
                model = record.get('model', 'claude-3-opus')
                
                # Calculate cost
                costs = self.TOKEN_COSTS.get(model, self.TOKEN_COSTS['default'])
                cost = (input_tokens * costs['input']) + (output_tokens * costs['output'])
                
                usage = TokenUsage(
                    timestamp=timestamp,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    model=model,
                    cost=cost,
                    session_id=record.get('session_id')
                )
                
                processed.append(usage)
                
            except Exception as e:
                print(f"Error processing usage record: {e}")
                continue
                
        return processed
        
    def store_usage_data(self, usage_records: List[TokenUsage]):
        """Store usage data in the database."""
        with sqlite3.connect(self.db_path) as conn:
            for record in usage_records:
                # Check if record already exists
                cursor = conn.execute("""
                    SELECT id FROM token_usage 
                    WHERE timestamp = ? AND total_tokens = ? AND session_id = ?
                """, (record.timestamp, record.total_tokens, record.session_id))
                
                if cursor.fetchone():
                    continue  # Skip duplicate
                    
                # Insert new record
                conn.execute("""
                    INSERT INTO token_usage (
                        timestamp, input_tokens, output_tokens, total_tokens,
                        model, cost, session_id, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.timestamp,
                    record.input_tokens,
                    record.output_tokens,
                    record.total_tokens,
                    record.model,
                    record.cost,
                    record.session_id,
                    json.dumps(asdict(record), default=str)
                ))
                
                # Update session data
                if record.session_id:
                    self._update_session(conn, record)
                    
            conn.commit()
            
    def _update_session(self, conn: sqlite3.Connection, record: TokenUsage):
        """Update session statistics."""
        cursor = conn.execute("""
            SELECT id, total_tokens, total_cost, request_count 
            FROM usage_sessions WHERE session_id = ?
        """, (record.session_id,))
        
        session = cursor.fetchone()
        if session:
            conn.execute("""
                UPDATE usage_sessions 
                SET total_tokens = ?, total_cost = ?, request_count = ?, end_time = ?
                WHERE session_id = ?
            """, (
                session[1] + record.total_tokens,
                session[2] + record.cost,
                session[3] + 1,
                record.timestamp,
                record.session_id
            ))
        else:
            conn.execute("""
                INSERT INTO usage_sessions (
                    session_id, start_time, end_time, total_tokens, total_cost, request_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.session_id,
                record.timestamp,
                record.timestamp,
                record.total_tokens,
                record.cost,
                1
            ))
            
    def get_usage_stats(self) -> UsageStats:
        """Get current usage statistics."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        with sqlite3.connect(self.db_path) as conn:
            # Total stats
            cursor = conn.execute("""
                SELECT 
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(cost), 0),
                    COUNT(*)
                FROM token_usage
            """)
            total_tokens, total_cost, total_requests = cursor.fetchone()
            
            # Today's stats
            cursor = conn.execute("""
                SELECT 
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(cost), 0),
                    COUNT(*)
                FROM token_usage
                WHERE timestamp >= ?
            """, (today_start,))
            tokens_today, cost_today, requests_today = cursor.fetchone()
            
            # This month's stats
            cursor = conn.execute("""
                SELECT 
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(cost), 0),
                    COUNT(*)
                FROM token_usage
                WHERE timestamp >= ?
            """, (month_start,))
            tokens_month, cost_month, requests_month = cursor.fetchone()
            
        # Calculate remaining tokens
        daily_remaining = max(0, self.limits['daily'] - tokens_today)
        monthly_remaining = max(0, self.limits['monthly'] - tokens_month)
        
        # Calculate percentages
        daily_percentage = (tokens_today / self.limits['daily']) * 100 if self.limits['daily'] > 0 else 0
        monthly_percentage = (tokens_month / self.limits['monthly']) * 100 if self.limits['monthly'] > 0 else 0
        
        return UsageStats(
            total_tokens=total_tokens,
            total_cost=total_cost,
            total_requests=total_requests,
            tokens_today=tokens_today,
            cost_today=cost_today,
            requests_today=requests_today,
            tokens_this_month=tokens_month,
            cost_this_month=cost_month,
            requests_this_month=requests_month,
            daily_limit=self.limits['daily'],
            monthly_limit=self.limits['monthly'],
            daily_remaining=daily_remaining,
            monthly_remaining=monthly_remaining,
            daily_percentage=daily_percentage,
            monthly_percentage=monthly_percentage
        )
        
    def get_usage_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get usage history for the specified number of days."""
        start_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    SUM(total_tokens) as tokens,
                    SUM(cost) as cost,
                    COUNT(*) as requests
                FROM token_usage
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (start_date,))
            
            return [
                {
                    'date': row[0],
                    'tokens': row[1],
                    'cost': row[2],
                    'requests': row[3]
                }
                for row in cursor
            ]
            
    def update_plan_limits(self, daily_limit: int, monthly_limit: int):
        """Update custom plan limits."""
        self.limits = {
            'daily': daily_limit,
            'monthly': monthly_limit
        }
        
    def refresh_data(self) -> UsageStats:
        """Refresh usage data from Claude Code and return current stats."""
        # Read latest data
        raw_data = self.read_claude_usage_data()
        
        # Process and store
        if raw_data:
            processed = self.process_usage_data(raw_data)
            self.store_usage_data(processed)
            
        # Return current stats
        return self.get_usage_stats()
        
    def monitor_realtime(self, callback: callable, interval: int = 10):
        """
        Monitor usage in real-time with callbacks.
        
        Args:
            callback: Function to call with updated stats
            interval: Update interval in seconds
        """
        while True:
            try:
                stats = self.refresh_data()
                callback(asdict(stats))
                time.sleep(interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)