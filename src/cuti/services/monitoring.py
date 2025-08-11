"""
System monitoring and metrics collection.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import psutil
import subprocess
from dataclasses import dataclass, asdict
from threading import Lock
import sqlite3


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_sent_mb: float
    network_recv_mb: float
    load_average: Optional[List[float]] = None


@dataclass
class ClaudeCodeMetrics:
    """Claude Code specific metrics."""
    timestamp: datetime
    tokens_used: int
    tokens_remaining: Optional[int]
    requests_made: int
    successful_requests: int
    failed_requests: int
    rate_limited_requests: int
    avg_response_time: float
    cost_estimate: float


class SystemMonitor:
    """Monitor system performance and Claude Code usage."""
    
    def __init__(self, base_dir: str = "~/.cuti"):
        self.base_dir = Path(base_dir).expanduser()
        self.metrics_db = self.base_dir / "metrics.db"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._lock = Lock()
        self._network_counters = None
        self._last_network_time = None
        
        self._init_database()
        
    def _init_database(self):
        """Initialize metrics database."""
        with sqlite3.connect(self.metrics_db) as conn:
            # System metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_used_gb REAL,
                    memory_total_gb REAL,
                    disk_percent REAL,
                    disk_used_gb REAL,
                    disk_total_gb REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    load_average TEXT
                )
            """)
            
            # Claude Code metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS claude_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    tokens_remaining INTEGER,
                    requests_made INTEGER DEFAULT 0,
                    successful_requests INTEGER DEFAULT 0,
                    failed_requests INTEGER DEFAULT 0,
                    rate_limited_requests INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    cost_estimate REAL DEFAULT 0
                )
            """)
            
            # Token usage tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    prompt_id TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0,
                    model_used TEXT
                )
            """)
            
            # Performance events table  
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    severity TEXT DEFAULT 'info'
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_claude_timestamp ON claude_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_timestamp ON token_usage(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON performance_events(timestamp)")
            
            conn.commit()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Network
            network_sent_mb, network_recv_mb = self._get_network_usage()
            
            # Load average (Unix-like systems only)
            load_average = None
            try:
                load_average = list(psutil.getloadavg())
            except (AttributeError, OSError):
                pass  # Windows doesn't support load average
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=round(cpu_percent, 2),
                memory_percent=round(memory_percent, 2),
                memory_used_gb=round(memory_used_gb, 2),
                memory_total_gb=round(memory_total_gb, 2),
                disk_percent=round(disk_percent, 2),
                disk_used_gb=round(disk_used_gb, 2),
                disk_total_gb=round(disk_total_gb, 2),
                network_sent_mb=round(network_sent_mb, 2),
                network_recv_mb=round(network_recv_mb, 2),
                load_average=load_average
            )
            
            # Store in database
            self._store_system_metrics(metrics)
            
            return asdict(metrics)
            
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            return {}
    
    def _get_network_usage(self) -> tuple[float, float]:
        """Get network usage in MB/s."""
        try:
            current_counters = psutil.net_io_counters()
            current_time = time.time()
            
            if self._network_counters and self._last_network_time:
                time_delta = current_time - self._last_network_time
                if time_delta > 0:
                    sent_delta = current_counters.bytes_sent - self._network_counters.bytes_sent
                    recv_delta = current_counters.bytes_recv - self._network_counters.bytes_recv
                    
                    sent_mb_per_sec = (sent_delta / (1024**2)) / time_delta
                    recv_mb_per_sec = (recv_delta / (1024**2)) / time_delta
                    
                    self._network_counters = current_counters
                    self._last_network_time = current_time
                    
                    return sent_mb_per_sec, recv_mb_per_sec
            
            # First run or error case
            self._network_counters = current_counters
            self._last_network_time = current_time
            return 0.0, 0.0
            
        except Exception:
            return 0.0, 0.0
    
    def _store_system_metrics(self, metrics: SystemMetrics):
        """Store system metrics in database."""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                conn.execute("""
                    INSERT INTO system_metrics (
                        timestamp, cpu_percent, memory_percent, memory_used_gb,
                        memory_total_gb, disk_percent, disk_used_gb, disk_total_gb,
                        network_sent_mb, network_recv_mb, load_average
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp,
                    metrics.cpu_percent,
                    metrics.memory_percent,
                    metrics.memory_used_gb,
                    metrics.memory_total_gb,
                    metrics.disk_percent,
                    metrics.disk_used_gb,
                    metrics.disk_total_gb,
                    metrics.network_sent_mb,
                    metrics.network_recv_mb,
                    json.dumps(metrics.load_average) if metrics.load_average else None
                ))
                conn.commit()
        except Exception as e:
            print(f"Error storing system metrics: {e}")
    
    def record_claude_request(
        self,
        prompt_id: str,
        input_tokens: int,
        output_tokens: int,
        response_time: float,
        success: bool,
        rate_limited: bool = False,
        model: str = "claude-3",
        cost_per_input_token: float = 0.000015,
        cost_per_output_token: float = 0.000075
    ):
        """Record a Claude Code request for monitoring."""
        try:
            total_tokens = input_tokens + output_tokens
            cost = (input_tokens * cost_per_input_token) + (output_tokens * cost_per_output_token)
            
            with sqlite3.connect(self.metrics_db) as conn:
                # Record token usage
                conn.execute("""
                    INSERT INTO token_usage (
                        timestamp, prompt_id, input_tokens, output_tokens,
                        total_tokens, cost, model_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    prompt_id,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    cost,
                    model
                ))
                
                # Update Claude metrics summary
                self._update_claude_metrics_summary(conn, response_time, success, rate_limited)
                
                conn.commit()
                
        except Exception as e:
            print(f"Error recording Claude request: {e}")
    
    def _update_claude_metrics_summary(self, conn, response_time: float, success: bool, rate_limited: bool):
        """Update Claude metrics summary."""
        today = datetime.now().date()
        
        # Get or create today's metrics
        cursor = conn.execute("""
            SELECT * FROM claude_metrics 
            WHERE DATE(timestamp) = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (today,))
        
        row = cursor.fetchone()
        if row:
            # Update existing
            new_requests = row[4] + 1  # requests_made
            new_successful = row[5] + (1 if success else 0)
            new_failed = row[6] + (1 if not success and not rate_limited else 0)
            new_rate_limited = row[7] + (1 if rate_limited else 0)
            
            # Calculate new average response time
            old_avg = row[8] or 0
            new_avg = ((old_avg * (new_requests - 1)) + response_time) / new_requests
            
            conn.execute("""
                UPDATE claude_metrics 
                SET requests_made = ?, successful_requests = ?, failed_requests = ?,
                    rate_limited_requests = ?, avg_response_time = ?
                WHERE id = ?
            """, (new_requests, new_successful, new_failed, new_rate_limited, new_avg, row[0]))
        else:
            # Create new
            conn.execute("""
                INSERT INTO claude_metrics (
                    timestamp, requests_made, successful_requests, failed_requests,
                    rate_limited_requests, avg_response_time
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                1,
                1 if success else 0,
                1 if not success and not rate_limited else 0,
                1 if rate_limited else 0,
                response_time
            ))
    
    def get_token_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get token usage statistics."""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                start_date = datetime.now() - timedelta(days=days)
                
                # Daily usage
                cursor = conn.execute("""
                    SELECT DATE(timestamp) as date, 
                           SUM(total_tokens) as tokens,
                           SUM(cost) as cost,
                           COUNT(*) as requests
                    FROM token_usage 
                    WHERE timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                """, (start_date,))
                
                daily_usage = [
                    {
                        'date': row[0],
                        'tokens': row[1] or 0,
                        'cost': row[2] or 0,
                        'requests': row[3] or 0
                    }
                    for row in cursor
                ]
                
                # Total stats
                cursor = conn.execute("""
                    SELECT SUM(total_tokens) as total_tokens,
                           SUM(cost) as total_cost,
                           COUNT(*) as total_requests,
                           AVG(total_tokens) as avg_tokens_per_request
                    FROM token_usage 
                    WHERE timestamp >= ?
                """, (start_date,))
                
                row = cursor.fetchone()
                totals = {
                    'total_tokens': row[0] or 0,
                    'total_cost': row[1] or 0,
                    'total_requests': row[2] or 0,
                    'avg_tokens_per_request': row[3] or 0
                }
                
                # Model breakdown
                cursor = conn.execute("""
                    SELECT model_used, 
                           SUM(total_tokens) as tokens,
                           SUM(cost) as cost,
                           COUNT(*) as requests
                    FROM token_usage 
                    WHERE timestamp >= ?
                    GROUP BY model_used
                """, (start_date,))
                
                model_breakdown = [
                    {
                        'model': row[0],
                        'tokens': row[1] or 0,
                        'cost': row[2] or 0,
                        'requests': row[3] or 0
                    }
                    for row in cursor
                ]
                
                return {
                    'daily_usage': daily_usage,
                    'totals': totals,
                    'model_breakdown': model_breakdown,
                    'period_days': days
                }
                
        except Exception as e:
            print(f"Error getting token usage stats: {e}")
            return {}
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for the specified time period."""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                start_time = datetime.now() - timedelta(hours=hours)
                
                # System performance trends
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent
                    FROM system_metrics 
                    WHERE timestamp >= ?
                    ORDER BY timestamp
                """, (start_time,))
                
                system_trends = [dict(row) for row in cursor]
                
                # Claude performance
                cursor = conn.execute("""
                    SELECT timestamp, avg_response_time, successful_requests, 
                           failed_requests, rate_limited_requests
                    FROM claude_metrics 
                    WHERE timestamp >= ?
                    ORDER BY timestamp
                """, (start_time,))
                
                claude_performance = [dict(row) for row in cursor]
                
                # Calculate averages for the period
                cursor = conn.execute("""
                    SELECT AVG(cpu_percent) as avg_cpu,
                           AVG(memory_percent) as avg_memory,
                           AVG(disk_percent) as avg_disk,
                           MAX(cpu_percent) as max_cpu,
                           MAX(memory_percent) as max_memory
                    FROM system_metrics 
                    WHERE timestamp >= ?
                """, (start_time,))
                
                row = cursor.fetchone()
                system_averages = dict(row) if row else {}
                
                return {
                    'system_trends': system_trends,
                    'claude_performance': claude_performance,
                    'system_averages': system_averages,
                    'period_hours': hours
                }
                
        except Exception as e:
            print(f"Error getting performance metrics: {e}")
            return {}
    
    def log_performance_event(self, event_type: str, event_data: Dict[str, Any], severity: str = 'info'):
        """Log a performance-related event."""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                conn.execute("""
                    INSERT INTO performance_events (timestamp, event_type, event_data, severity)
                    VALUES (?, ?, ?, ?)
                """, (
                    datetime.now(),
                    event_type,
                    json.dumps(event_data),
                    severity
                ))
                conn.commit()
        except Exception as e:
            print(f"Error logging performance event: {e}")
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent performance events."""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT timestamp, event_type, event_data, severity
                    FROM performance_events 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                events = []
                for row in cursor:
                    event = dict(row)
                    try:
                        event['event_data'] = json.loads(event['event_data'])
                    except:
                        pass  # Keep as string if not valid JSON
                    events.append(event)
                
                return events
                
        except Exception as e:
            print(f"Error getting recent events: {e}")
            return []
    
    def cleanup_old_metrics(self, days_to_keep: int = 90):
        """Clean up old metrics data."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.metrics_db) as conn:
                # Clean up old system metrics
                cursor = conn.execute("DELETE FROM system_metrics WHERE timestamp < ?", (cutoff_date,))
                system_deleted = cursor.rowcount
                
                # Clean up old token usage (keep longer - 180 days)
                token_cutoff = datetime.now() - timedelta(days=180)
                cursor = conn.execute("DELETE FROM token_usage WHERE timestamp < ?", (token_cutoff,))
                token_deleted = cursor.rowcount
                
                # Clean up old events
                cursor = conn.execute("DELETE FROM performance_events WHERE timestamp < ?", (cutoff_date,))
                events_deleted = cursor.rowcount
                
                conn.commit()
                
                self.log_performance_event(
                    'metrics_cleanup',
                    {
                        'system_metrics_deleted': system_deleted,
                        'token_records_deleted': token_deleted,
                        'events_deleted': events_deleted,
                        'days_to_keep': days_to_keep
                    },
                    'info'
                )
                
        except Exception as e:
            print(f"Error cleaning up old metrics: {e}")
    
    def get_health_check(self) -> Dict[str, Any]:
        """Get system health status."""
        try:
            system_metrics = self.get_system_metrics()
            
            # Define thresholds
            health_status = "healthy"
            issues = []
            
            # Check CPU usage
            if system_metrics.get('cpu_percent', 0) > 80:
                health_status = "warning"
                issues.append("High CPU usage")
            elif system_metrics.get('cpu_percent', 0) > 95:
                health_status = "critical"
                issues.append("Critical CPU usage")
            
            # Check memory usage
            if system_metrics.get('memory_percent', 0) > 85:
                health_status = "warning"
                issues.append("High memory usage")
            elif system_metrics.get('memory_percent', 0) > 95:
                health_status = "critical"
                issues.append("Critical memory usage")
            
            # Check disk usage
            if system_metrics.get('disk_percent', 0) > 85:
                health_status = "warning"
                issues.append("High disk usage")
            elif system_metrics.get('disk_percent', 0) > 95:
                health_status = "critical"
                issues.append("Critical disk usage")
            
            # Check database connectivity
            try:
                with sqlite3.connect(self.metrics_db, timeout=5) as conn:
                    conn.execute("SELECT 1").fetchone()
            except Exception:
                health_status = "critical"
                issues.append("Database connectivity issues")
            
            return {
                'status': health_status,
                'issues': issues,
                'timestamp': datetime.now().isoformat(),
                'system_metrics': system_metrics
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'issues': [f"Health check failed: {str(e)}"],
                'timestamp': datetime.now().isoformat()
            }
    
    def export_metrics(self, output_file: str, format: str = 'json', days: int = 30) -> bool:
        """Export metrics data to file."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.metrics_db) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get all metrics
                system_cursor = conn.execute("""
                    SELECT * FROM system_metrics WHERE timestamp >= ? ORDER BY timestamp
                """, (start_date,))
                system_metrics = [dict(row) for row in system_cursor]
                
                claude_cursor = conn.execute("""
                    SELECT * FROM claude_metrics WHERE timestamp >= ? ORDER BY timestamp  
                """, (start_date,))
                claude_metrics = [dict(row) for row in claude_cursor]
                
                token_cursor = conn.execute("""
                    SELECT * FROM token_usage WHERE timestamp >= ? ORDER BY timestamp
                """, (start_date,))
                token_usage = [dict(row) for row in token_cursor]
                
                events_cursor = conn.execute("""
                    SELECT * FROM performance_events WHERE timestamp >= ? ORDER BY timestamp
                """, (start_date,))
                events = [dict(row) for row in events_cursor]
                
                # Prepare export data
                export_data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'period_days': days,
                    'system_metrics': system_metrics,
                    'claude_metrics': claude_metrics,
                    'token_usage': token_usage,
                    'performance_events': events
                }
                
                # Write to file
                output_path = Path(output_file)
                
                if format.lower() == 'json':
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=2, default=str)
                elif format.lower() == 'csv':
                    import csv
                    
                    # Export each table to separate CSV files
                    base_name = output_path.stem
                    output_dir = output_path.parent
                    
                    for table_name, data in export_data.items():
                        if isinstance(data, list) and data:
                            csv_file = output_dir / f"{base_name}_{table_name}.csv"
                            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                                writer.writeheader()
                                writer.writerows(data)
                else:
                    raise ValueError(f"Unsupported format: {format}")
                
                return True
                
        except Exception as e:
            print(f"Error exporting metrics: {e}")
            return False