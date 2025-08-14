"""
Background service for syncing Claude Code usage logs to persistent storage.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import threading
import time

from .global_data_manager import GlobalDataManager
from .claude_monitor_integration import ClaudeMonitorIntegration

logger = logging.getLogger(__name__)


class UsageSyncService:
    """Service for automatically syncing Claude usage data to persistent storage."""
    
    def __init__(self, 
                 sync_interval: int = 300,  # 5 minutes
                 claude_data_path: Optional[str] = None):
        """
        Initialize the usage sync service.
        
        Args:
            sync_interval: Seconds between sync attempts
            claude_data_path: Path to Claude data directory
        """
        self.sync_interval = sync_interval
        self.claude_data_path = claude_data_path or "~/.claude/projects"
        self.global_manager = GlobalDataManager()
        self.monitor = ClaudeMonitorIntegration(claude_data_path=self.claude_data_path)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_sync = None
        self._sync_count = 0
        self._error_count = 0
    
    def start(self):
        """Start the background sync service."""
        if self._running:
            logger.warning("Usage sync service is already running")
            return
        
        if not self.global_manager.settings.usage_tracking_enabled:
            logger.info("Usage tracking is disabled in global settings")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
        logger.info(f"Started usage sync service (interval: {self.sync_interval}s)")
    
    def stop(self):
        """Stop the background sync service."""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Stopped usage sync service")
    
    def _sync_loop(self):
        """Main sync loop running in background thread."""
        while self._running:
            try:
                # Perform sync
                self.sync_now()
                
                # Wait for next interval
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                self._error_count += 1
                
                # Exponential backoff on errors
                backoff = min(self.sync_interval * (2 ** min(self._error_count, 5)), 3600)
                time.sleep(backoff)
    
    def sync_now(self) -> int:
        """
        Perform immediate sync of usage data.
        
        Returns:
            Number of new records imported
        """
        try:
            if not self.global_manager.settings.usage_tracking_enabled:
                return 0
            
            logger.debug("Starting usage data sync")
            
            # Import Claude logs
            imported = self.global_manager.import_claude_logs(self.claude_data_path)
            
            if imported > 0:
                logger.info(f"Synced {imported} new usage records")
            
            # Update sync metadata
            self._last_sync = datetime.now()
            self._sync_count += 1
            
            # Reset error count on successful sync
            if imported >= 0:
                self._error_count = 0
            
            # Perform cleanup if needed (once per day)
            if self._should_cleanup():
                self._perform_cleanup()
            
            return imported
            
        except Exception as e:
            logger.error(f"Failed to sync usage data: {e}")
            self._error_count += 1
            return 0
    
    def _should_cleanup(self) -> bool:
        """Check if cleanup should be performed."""
        # Check if we've done cleanup today
        cleanup_marker = self.global_manager.global_dir / ".last_cleanup"
        
        if cleanup_marker.exists():
            last_cleanup = datetime.fromtimestamp(cleanup_marker.stat().st_mtime)
            if datetime.now() - last_cleanup < timedelta(days=1):
                return False
        
        return True
    
    def _perform_cleanup(self):
        """Perform data cleanup tasks."""
        try:
            logger.info("Performing data cleanup")
            
            # Clean old data
            self.global_manager.cleanup_old_data()
            
            # Create backup
            backup_path = self.global_manager.backup_database()
            if backup_path:
                logger.info(f"Created database backup: {backup_path}")
            
            # Update cleanup marker
            cleanup_marker = self.global_manager.global_dir / ".last_cleanup"
            cleanup_marker.touch()
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_status(self) -> dict:
        """Get current service status."""
        return {
            'running': self._running,
            'last_sync': self._last_sync.isoformat() if self._last_sync else None,
            'sync_count': self._sync_count,
            'error_count': self._error_count,
            'sync_interval': self.sync_interval,
            'tracking_enabled': self.global_manager.settings.usage_tracking_enabled
        }
    
    async def async_sync(self) -> int:
        """Async wrapper for sync_now."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.sync_now)


class UsageSyncManager:
    """Manager for usage sync service instances."""
    
    _instance: Optional[UsageSyncService] = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> UsageSyncService:
        """Get or create singleton sync service instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = UsageSyncService()
            return cls._instance
    
    @classmethod
    def start_service(cls):
        """Start the global sync service."""
        service = cls.get_instance()
        service.start()
    
    @classmethod
    def stop_service(cls):
        """Stop the global sync service."""
        if cls._instance:
            cls._instance.stop()
    
    @classmethod
    def sync_now(cls) -> int:
        """Trigger immediate sync."""
        service = cls.get_instance()
        return service.sync_now()
    
    @classmethod
    def get_status(cls) -> dict:
        """Get service status."""
        if cls._instance:
            return cls._instance.get_status()
        return {
            'running': False,
            'last_sync': None,
            'sync_count': 0,
            'error_count': 0,
            'sync_interval': 300,
            'tracking_enabled': False
        }