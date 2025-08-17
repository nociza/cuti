"""
Improved chat WebSocket with proper Claude Code SDK integration,
real-time progress tracking, and enhanced error handling.
"""

import json
import asyncio
import uuid
from typing import Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# Import our enhanced SDK interface
from ...core.claude_sdk_interface import (
    ClaudeSDKInterface, 
    StreamMessage, 
    MessageType
)

improved_chat_router = APIRouter()


class ChatSession:
    """Manages a chat session with cancellation and progress tracking."""
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.is_cancelled = False
        self.is_processing = False
        self.current_task: Optional[asyncio.Task] = None
        self.start_time = datetime.now()
        self.message_count = 0
        self.active_agents: Set[str] = set()
        self.sdk_interface: Optional[ClaudeSDKInterface] = None
        
    async def initialize_sdk(self):
        """Initialize the Claude SDK interface."""
        try:
            self.sdk_interface = ClaudeSDKInterface(
                system_prompt="You are a helpful AI assistant integrated with cuti.",
                max_turns=1,
                allowed_tools=["Read", "Write", "Bash", "Edit", "Search"],
                permission_mode='acceptEdits'
            )
            return True
        except Exception as e:
            await self.send_error(f"Failed to initialize Claude SDK: {str(e)}")
            return False
    
    async def send_message(self, message: Dict[str, Any]):
        """Send a message to the WebSocket client."""
        try:
            await self.websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending message: {e}")
    
    async def send_error(self, error_message: str):
        """Send an error message to the client."""
        await self.send_message({
            "type": "error",
            "content": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_progress(self, message: str, percentage: Optional[float] = None):
        """Send a progress update to the client."""
        data = {
            "type": "progress",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if percentage is not None:
            data["percentage"] = percentage
        await self.send_message(data)
    
    def cancel(self):
        """Cancel the current processing task."""
        self.is_cancelled = True
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
    
    def should_continue(self) -> bool:
        """Check if processing should continue."""
        return not self.is_cancelled and self.is_processing


class ImprovedChatManager:
    """Manages improved chat sessions with SDK integration."""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.message_history: list = []
        
    def create_session(self, websocket: WebSocket) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())[:8]
        session = ChatSession(session_id, websocket)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove a session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if session.current_task:
                session.cancel()
            del self.sessions[session_id]
    
    def record_message(self, session_id: str, role: str, content: str):
        """Record a message in history."""
        self.message_history.append({
            "session_id": session_id,
            "role": role,
            "content": content[:1000],  # Limit stored content
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 100 messages
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-100:]


# Global manager instance
chat_manager = ImprovedChatManager()


async def process_message_with_sdk(session: ChatSession, content: str, working_dir: str):
    """Process a message using the Claude SDK with progress tracking."""
    
    session.is_processing = True
    session.message_count += 1
    
    try:
        # Send processing started notification
        await session.send_message({
            "type": "processing_started",
            "session_id": session.session_id,
            "message_id": session.message_count,
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize SDK if not already done
        if not session.sdk_interface:
            await session.send_progress("Initializing Claude SDK...", 10)
            if not await session.initialize_sdk():
                return
        
        # Detect agent mentions
        agents = []
        if "@" in content:
            import re
            agent_pattern = r'@(\w+[-\w]*)'
            agents = re.findall(agent_pattern, content)
            
            if agents:
                await session.send_message({
                    "type": "agents_detected",
                    "agents": agents,
                    "message": f"Activating {len(agents)} agent(s)"
                })
        
        # Track progress metrics
        chunk_count = 0
        total_chars = 0
        last_update_time = datetime.now()
        response_parts = []
        
        # Process the message with streaming
        async for stream_msg in session.sdk_interface.stream_response(
            prompt=content,
            working_dir=working_dir
        ):
            # Check if cancelled
            if not session.should_continue():
                await session.send_message({
                    "type": "cancelled",
                    "message": "Processing cancelled by user"
                })
                break
            
            # Handle different message types
            if stream_msg.type == MessageType.STREAM:
                # Send content chunk
                chunk_count += 1
                total_chars += len(stream_msg.content)
                response_parts.append(stream_msg.content)
                
                await session.send_message({
                    "type": "stream",
                    "content": stream_msg.content,
                    "chunk_number": chunk_count
                })
                
                # Send periodic progress updates
                now = datetime.now()
                if (now - last_update_time).total_seconds() > 1:
                    await session.send_progress(
                        f"Processing... ({chunk_count} chunks, {total_chars} characters)",
                        min(95, 20 + (chunk_count * 2))  # Progressive percentage
                    )
                    last_update_time = now
            
            elif stream_msg.type == MessageType.PROGRESS:
                # Forward progress messages
                await session.send_progress(
                    stream_msg.content,
                    stream_msg.metadata.get("percentage")
                )
            
            elif stream_msg.type == MessageType.THINKING:
                # Claude is thinking
                await session.send_message({
                    "type": "thinking",
                    "message": "Claude is analyzing your request..."
                })
            
            elif stream_msg.type == MessageType.TOOL_USE:
                # Tool usage notification
                await session.send_message({
                    "type": "tool_use",
                    "tool": stream_msg.metadata.get("tool"),
                    "message": stream_msg.content
                })
            
            elif stream_msg.type == MessageType.AGENT_ACTIVATED:
                # Agent activation
                agent_name = stream_msg.metadata.get("agent")
                session.active_agents.add(agent_name)
                await session.send_message({
                    "type": "agent_activated",
                    "agent": agent_name,
                    "status": "active"
                })
            
            elif stream_msg.type == MessageType.AGENT_COMPLETED:
                # Agent completion
                agent_name = stream_msg.metadata.get("agent")
                session.active_agents.discard(agent_name)
                await session.send_message({
                    "type": "agent_completed",
                    "agent": agent_name,
                    "status": "completed"
                })
            
            elif stream_msg.type == MessageType.ERROR:
                # Error occurred
                await session.send_error(stream_msg.content)
                return
            
            elif stream_msg.type == MessageType.COMPLETE:
                # Processing complete
                await session.send_progress("Processing complete!", 100)
        
        # Record the complete message
        full_response = "".join(response_parts)
        chat_manager.record_message(session.session_id, "assistant", full_response)
        
        # Send completion notification
        if session.should_continue():
            duration = (datetime.now() - session.start_time).total_seconds()
            await session.send_message({
                "type": "complete",
                "session_id": session.session_id,
                "message_id": session.message_count,
                "duration": duration,
                "chunks": chunk_count,
                "characters": total_chars,
                "agents_used": list(agents),
                "timestamp": datetime.now().isoformat()
            })
        
    except asyncio.CancelledError:
        await session.send_message({
            "type": "cancelled",
            "message": "Processing was cancelled"
        })
    except Exception as e:
        await session.send_error(f"Processing error: {str(e)}")
    finally:
        session.is_processing = False
        session.active_agents.clear()


@improved_chat_router.websocket("/improved-chat-ws")
async def improved_chat_websocket(websocket: WebSocket):
    """Improved chat WebSocket with SDK integration and progress tracking."""
    
    await websocket.accept()
    
    # Create session
    session = chat_manager.create_session(websocket)
    
    # Send welcome message
    await session.send_message({
        "type": "connected",
        "session_id": session.session_id,
        "message": "Connected to improved chat with Claude SDK",
        "features": [
            "real_time_streaming",
            "progress_tracking",
            "agent_detection",
            "tool_usage_tracking",
            "cancellation_support",
            "error_recovery"
        ],
        "timestamp": datetime.now().isoformat()
    })
    
    # Check SDK availability
    try:
        sdk_test = ClaudeSDKInterface()
        if sdk_test.is_available():
            await session.send_message({
                "type": "sdk_status",
                "status": "ready",
                "message": "Claude Code SDK is ready"
            })
        else:
            await session.send_message({
                "type": "sdk_status",
                "status": "not_available",
                "message": "Claude Code SDK needs to be installed"
            })
    except Exception as e:
        await session.send_message({
            "type": "sdk_status",
            "status": "error",
            "message": f"SDK check failed: {str(e)}"
        })
    
    # Get working directory from app state
    app = websocket.scope.get("app")
    working_dir = str(app.state.working_directory) if app else "."
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            msg_type = message_data.get("type")
            
            if msg_type == "message":
                # Process user message
                content = message_data.get("content", "")
                
                # Record message
                chat_manager.record_message(session.session_id, "user", content)
                
                # Create processing task
                session.current_task = asyncio.create_task(
                    process_message_with_sdk(session, content, working_dir)
                )
                
            elif msg_type == "cancel":
                # Cancel current processing
                if session.is_processing:
                    session.cancel()
                    await session.send_message({
                        "type": "cancel_acknowledged",
                        "message": "Cancelling current processing..."
                    })
                else:
                    await session.send_message({
                        "type": "cancel_failed",
                        "message": "No active processing to cancel"
                    })
            
            elif msg_type == "ping":
                # Heartbeat/keepalive
                await session.send_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            elif msg_type == "get_history":
                # Get message history for this session
                session_history = [
                    msg for msg in chat_manager.message_history
                    if msg["session_id"] == session.session_id
                ]
                await session.send_message({
                    "type": "history",
                    "messages": session_history[-20:],  # Last 20 messages
                    "total": len(session_history)
                })
            
            elif msg_type == "get_status":
                # Get current session status
                await session.send_message({
                    "type": "status",
                    "session_id": session.session_id,
                    "is_processing": session.is_processing,
                    "message_count": session.message_count,
                    "active_agents": list(session.active_agents),
                    "uptime": (datetime.now() - session.start_time).total_seconds()
                })
                
    except WebSocketDisconnect:
        chat_manager.remove_session(session.session_id)
    except Exception as e:
        await session.send_error(f"WebSocket error: {str(e)}")
        chat_manager.remove_session(session.session_id)


@improved_chat_router.get("/chat-status")
async def get_chat_status():
    """Get overall chat system status."""
    active_sessions = []
    for session_id, session in chat_manager.sessions.items():
        active_sessions.append({
            "session_id": session_id,
            "is_processing": session.is_processing,
            "message_count": session.message_count,
            "active_agents": list(session.active_agents),
            "uptime": (datetime.now() - session.start_time).total_seconds()
        })
    
    return {
        "status": "operational",
        "active_sessions": len(active_sessions),
        "sessions": active_sessions,
        "total_messages": len(chat_manager.message_history),
        "sdk_available": ClaudeSDKInterface().is_available() if SDK_AVAILABLE else False
    }