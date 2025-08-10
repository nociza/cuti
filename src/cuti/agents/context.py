"""
Shared context and memory management for agent collaboration.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import aiofiles


class SharedMemoryManager:
    """Manages shared memory and context for agent collaboration."""
    
    def __init__(self, working_directory: str = "."):
        self.working_directory = Path(working_directory)
        self.memory_store: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
    
    async def get_session_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create a lock for a session."""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]
    
    async def initialize_session(self, session_id: str, initial_context: Optional[Dict[str, Any]] = None):
        """Initialize a new collaboration session."""
        async with await self.get_session_lock(session_id):
            if session_id not in self.memory_store:
                self.memory_store[session_id] = {
                    "_created_at": datetime.now().isoformat(),
                    "_updated_at": datetime.now().isoformat(),
                    "_agents": [],
                    "_history": []
                }
                
                if initial_context:
                    self.memory_store[session_id].update(initial_context)
    
    async def get_context(self, session_id: str, key: Optional[str] = None) -> Any:
        """Get context for a session."""
        async with await self.get_session_lock(session_id):
            if session_id not in self.memory_store:
                return None
            
            if key:
                return self.memory_store[session_id].get(key)
            else:
                # Return non-private context
                return {
                    k: v for k, v in self.memory_store[session_id].items()
                    if not k.startswith('_')
                }
    
    async def set_context(self, session_id: str, key: str, value: Any, agent_name: Optional[str] = None):
        """Set context value for a session."""
        async with await self.get_session_lock(session_id):
            if session_id not in self.memory_store:
                await self.initialize_session(session_id)
            
            self.memory_store[session_id][key] = value
            self.memory_store[session_id]["_updated_at"] = datetime.now().isoformat()
            
            # Track agent contribution
            if agent_name:
                if agent_name not in self.memory_store[session_id]["_agents"]:
                    self.memory_store[session_id]["_agents"].append(agent_name)
                
                # Add to history
                self.memory_store[session_id]["_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_name,
                    "action": "set",
                    "key": key,
                    "value_preview": str(value)[:100] if value else None
                })
    
    async def append_to_list(self, session_id: str, key: str, value: Any, agent_name: Optional[str] = None):
        """Append to a list in the context."""
        async with await self.get_session_lock(session_id):
            if session_id not in self.memory_store:
                await self.initialize_session(session_id)
            
            if key not in self.memory_store[session_id]:
                self.memory_store[session_id][key] = []
            
            if not isinstance(self.memory_store[session_id][key], list):
                raise ValueError(f"Context key '{key}' is not a list")
            
            self.memory_store[session_id][key].append(value)
            self.memory_store[session_id]["_updated_at"] = datetime.now().isoformat()
            
            # Track agent contribution
            if agent_name:
                self.memory_store[session_id]["_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_name,
                    "action": "append",
                    "key": key,
                    "value_preview": str(value)[:100] if value else None
                })
    
    async def merge_results(self, session_id: str, results: Dict[str, Any], agent_name: Optional[str] = None):
        """Merge results from an agent into the session context."""
        async with await self.get_session_lock(session_id):
            if session_id not in self.memory_store:
                await self.initialize_session(session_id)
            
            # Merge results
            for key, value in results.items():
                if not key.startswith('_'):  # Don't merge private keys
                    self.memory_store[session_id][key] = value
            
            self.memory_store[session_id]["_updated_at"] = datetime.now().isoformat()
            
            # Track agent contribution
            if agent_name:
                self.memory_store[session_id]["_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_name,
                    "action": "merge",
                    "keys": list(results.keys())
                })
    
    async def save_session(self, session_id: str, file_path: Optional[Path] = None):
        """Save session context to a file."""
        async with await self.get_session_lock(session_id):
            if session_id not in self.memory_store:
                return
            
            if not file_path:
                file_path = self.working_directory / f"session_{session_id}.json"
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(self.memory_store[session_id], indent=2))
    
    async def load_session(self, session_id: str, file_path: Optional[Path] = None):
        """Load session context from a file."""
        if not file_path:
            file_path = self.working_directory / f"session_{session_id}.json"
        
        if not file_path.exists():
            return False
        
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            data = json.loads(content)
        
        async with await self.get_session_lock(session_id):
            self.memory_store[session_id] = data
            return True
    
    async def cleanup_session(self, session_id: str):
        """Clean up a session."""
        async with await self.get_session_lock(session_id):
            if session_id in self.memory_store:
                del self.memory_store[session_id]
            if session_id in self._locks:
                del self._locks[session_id]
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a session."""
        if session_id not in self.memory_store:
            return None
        
        session_data = self.memory_store[session_id]
        
        return {
            "session_id": session_id,
            "created_at": session_data.get("_created_at"),
            "updated_at": session_data.get("_updated_at"),
            "agents_involved": session_data.get("_agents", []),
            "history_length": len(session_data.get("_history", [])),
            "context_keys": [k for k in session_data.keys() if not k.startswith('_')]
        }
    
    def get_all_sessions(self) -> List[str]:
        """Get all active session IDs."""
        return list(self.memory_store.keys())