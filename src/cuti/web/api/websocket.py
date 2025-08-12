"""
WebSocket API endpoints.
"""

import json
import asyncio
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

websocket_router = APIRouter()


class WebSocketManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, list] = {
            "general": [],
            "usage": [],
            "agents": [],
            "chat": []
        }
    
    async def connect(self, websocket: WebSocket, connection_type: str = "general"):
        await websocket.accept()
        if connection_type not in self.active_connections:
            self.active_connections[connection_type] = []
        self.active_connections[connection_type].append(websocket)
    
    def disconnect(self, websocket: WebSocket, connection_type: str = "general"):
        if connection_type in self.active_connections:
            if websocket in self.active_connections[connection_type]:
                self.active_connections[connection_type].remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str, connection_type: str = "general"):
        for connection in self.active_connections.get(connection_type, []):
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected connections
                self.active_connections[connection_type].remove(connection)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def broadcast_message(message: Dict[str, Any], connection_type: str = "general"):
    """Broadcast a message to all connected WebSocket clients."""
    message_str = json.dumps(message)
    await websocket_manager.broadcast(message_str, connection_type)


@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates."""
    await websocket_manager.connect(websocket, "general")
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Echo received data (can be extended for specific functionality)
            await websocket_manager.send_personal_message(
                json.dumps({"type": "echo", "data": data}),
                websocket
            )
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "general")


@websocket_router.websocket("/usage-ws")
async def usage_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for usage monitoring updates."""
    await websocket_manager.connect(websocket, "usage")
    try:
        while True:
            # Send periodic usage updates
            await asyncio.sleep(5)  # Send updates every 5 seconds
            
            # Get current usage stats (this would need to be implemented)
            usage_data = {
                "type": "usage_update",
                "timestamp": "2024-01-01T00:00:00Z",
                "tokens_used": 0,
                "cost": 0.0,
                "requests": 0
            }
            
            await websocket_manager.send_personal_message(
                json.dumps(usage_data),
                websocket
            )
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "usage")


@websocket_router.websocket("/agent-ws")
async def agent_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for agent system updates."""
    await websocket_manager.connect(websocket, "agents")
    try:
        while True:
            # Send periodic agent updates
            await asyncio.sleep(3)  # Send updates every 3 seconds
            
            try:
                from ...agents.pool import AgentPool
                
                pool = AgentPool()
                agent_names = pool.get_available_agents()
                
                agent_data = {
                    "type": "agent_update",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "agents": [
                        {
                            "id": name,
                            "status": "available",
                            "last_activity": None
                        }
                        for name in agent_names
                    ]
                }
                
            except ImportError:
                agent_data = {
                    "type": "agent_update",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "agents": [],
                    "error": "Agent system not available"
                }
            
            await websocket_manager.send_personal_message(
                json.dumps(agent_data),
                websocket
            )
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "agents")


@websocket_router.websocket("/chat-ws")
async def chat_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat interface with Claude Code proxy."""
    await websocket_manager.connect(websocket, "chat")
    
    # Get app from websocket scope
    app = websocket.scope.get("app")
    
    # Get Claude interface from app state
    claude_interface = app.state.claude_interface if app else None
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                # Handle chat message
                content = message_data.get("content", "")
                
                # Send start signal
                await websocket.send_text(json.dumps({
                    "type": "start",
                    "timestamp": "2024-01-01T00:00:00Z"
                }))
                
                try:
                    # Check if message contains @ agent reference
                    # The @ syntax will be handled by Claude Code itself
                    # We just proxy the message directly
                    
                    if claude_interface:
                        # Execute through Claude Code CLI
                        # Stream the response back
                        # Get working directory from app state
                        working_dir = str(app.state.working_directory) if app else "."
                        
                        async for chunk in claude_interface.stream_prompt(content, working_dir):
                            await websocket.send_text(json.dumps({
                                "type": "stream",
                                "content": chunk
                            }))
                    else:
                        # Fallback for demo mode
                        demo_response = f"I received your message: {content}"
                        if "@" in content:
                            demo_response += "\n\nNote: Agent invocation detected. In production, this would be handled by Claude Code."
                        
                        # Simulate streaming
                        for word in demo_response.split():
                            await websocket.send_text(json.dumps({
                                "type": "stream",
                                "content": word + " "
                            }))
                            await asyncio.sleep(0.05)
                    
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": f"Error executing prompt: {str(e)}"
                    }))
                
                # Send end signal
                await websocket.send_text(json.dumps({
                    "type": "end",
                    "timestamp": "2024-01-01T00:00:00Z"
                }))
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "chat")