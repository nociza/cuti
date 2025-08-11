"""
Web interface utilities.
"""

import json
from typing import Dict, Any, List
from fastapi import WebSocket


class WebSocketManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "general": [],
            "usage": [],
            "agents": [],
            "chat": []
        }
    
    async def connect(self, websocket: WebSocket, connection_type: str = "general"):
        """Accept a WebSocket connection and add to active connections."""
        await websocket.accept()
        if connection_type not in self.active_connections:
            self.active_connections[connection_type] = []
        self.active_connections[connection_type].append(websocket)
    
    def disconnect(self, websocket: WebSocket, connection_type: str = "general"):
        """Remove a WebSocket from active connections."""
        if connection_type in self.active_connections:
            if websocket in self.active_connections[connection_type]:
                self.active_connections[connection_type].remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_text(message)
        except Exception:
            # Connection might be closed
            pass
    
    async def send_json(self, data: Dict[str, Any], websocket: WebSocket):
        """Send JSON data to a specific WebSocket."""
        await self.send_personal_message(json.dumps(data), websocket)
    
    async def broadcast(self, message: str, connection_type: str = "general"):
        """Broadcast a message to all connections of a specific type."""
        if connection_type not in self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections[connection_type]:
            try:
                await connection.send_text(message)
            except Exception:
                # Mark for removal
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.active_connections[connection_type].remove(connection)
    
    async def broadcast_json(self, data: Dict[str, Any], connection_type: str = "general"):
        """Broadcast JSON data to all connections of a specific type."""
        await self.broadcast(json.dumps(data), connection_type)
    
    def get_connection_count(self, connection_type: str = None) -> int:
        """Get the number of active connections."""
        if connection_type:
            return len(self.active_connections.get(connection_type, []))
        else:
            return sum(len(conns) for conns in self.active_connections.values())


def format_execution_log(log_text: str) -> List[Dict[str, str]]:
    """Format execution log text into structured entries."""
    if not log_text:
        return []
    
    lines = log_text.strip().split('\n')
    entries = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Try to parse timestamp and message
        if line.startswith('[') and ']' in line:
            # Format: [timestamp] message
            parts = line.split(']', 1)
            if len(parts) == 2:
                timestamp = parts[0][1:]  # Remove opening [
                message = parts[1].strip()
                entries.append({
                    "timestamp": timestamp,
                    "message": message,
                    "type": "info"
                })
            else:
                entries.append({
                    "timestamp": "",
                    "message": line,
                    "type": "info"
                })
        else:
            entries.append({
                "timestamp": "",
                "message": line,
                "type": "info"
            })
    
    return entries


def validate_prompt_request(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate a prompt request."""
    if not data.get("content"):
        return False, "Prompt content is required"
    
    content = data["content"].strip()
    if len(content) < 1:
        return False, "Prompt content cannot be empty"
    
    # Validate priority
    priority = data.get("priority", 0)
    if not isinstance(priority, int) or priority < 0:
        return False, "Priority must be a non-negative integer"
    
    # Validate max_retries
    max_retries = data.get("max_retries", 3)
    if not isinstance(max_retries, int) or max_retries < 0:
        return False, "Max retries must be a non-negative integer"
    
    return True, ""


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '-')
    
    # Collapse multiple dashes
    filename = re.sub(r'-+', '-', filename)
    
    # Remove leading/trailing dashes
    filename = filename.strip('-')
    
    return filename[:50]  # Limit length