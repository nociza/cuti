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
    """WebSocket endpoint for chat interface."""
    await websocket_manager.connect(websocket, "chat")
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "execute_prompt":
                # Handle prompt execution
                prompt = message_data.get("prompt", "")
                
                # Send acknowledgment
                await websocket_manager.send_personal_message(
                    json.dumps({
                        "type": "execution_started",
                        "prompt": prompt,
                        "timestamp": "2024-01-01T00:00:00Z"
                    }),
                    websocket
                )
                
                # Here you would actually execute the prompt
                # For now, just simulate a response
                await asyncio.sleep(2)
                
                await websocket_manager.send_personal_message(
                    json.dumps({
                        "type": "execution_completed",
                        "prompt": prompt,
                        "result": "Simulated response for: " + prompt,
                        "timestamp": "2024-01-01T00:00:00Z"
                    }),
                    websocket
                )
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "chat")