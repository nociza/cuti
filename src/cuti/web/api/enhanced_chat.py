"""
Enhanced chat WebSocket with execution control and detailed streaming.
"""

import json
import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

enhanced_chat_router = APIRouter()


class ExecutionSession:
    """Manages a single execution session with cancellation support."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_cancelled = False
        self.current_agent = None
        self.current_task = None
        self.start_time = datetime.now()
        self.execution_task: Optional[asyncio.Task] = None
        
    def cancel(self):
        """Cancel the execution."""
        self.is_cancelled = True
        if self.execution_task and not self.execution_task.done():
            self.execution_task.cancel()
            
    def should_continue(self) -> bool:
        """Check if execution should continue."""
        return not self.is_cancelled


class EnhancedChatManager:
    """Manages enhanced chat sessions with execution tracking."""
    
    def __init__(self):
        self.active_sessions: Dict[str, ExecutionSession] = {}
        self.task_history = []  # In-memory for now, will be persisted
        
    def create_session(self, websocket: WebSocket) -> str:
        """Create a new execution session."""
        session_id = str(uuid.uuid4())[:8]
        self.active_sessions[session_id] = ExecutionSession(session_id)
        return session_id
        
    def get_session(self, session_id: str) -> Optional[ExecutionSession]:
        """Get an active session."""
        return self.active_sessions.get(session_id)
        
    def cancel_session(self, session_id: str) -> bool:
        """Cancel an active session."""
        session = self.get_session(session_id)
        if session:
            session.cancel()
            return True
        return False
        
    def remove_session(self, session_id: str):
        """Remove a session after completion."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
    def record_task(self, session_id: str, task_data: Dict[str, Any]):
        """Record a task in history."""
        task_record = {
            "id": str(uuid.uuid4())[:8],
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            **task_data
        }
        self.task_history.append(task_record)
        return task_record


# Global manager instance
chat_manager = EnhancedChatManager()


async def stream_with_details(
    websocket: WebSocket,
    session: ExecutionSession,
    content: str,
    working_dir: str,
    claude_interface
):
    """Stream execution with detailed progress and agent information."""
    
    try:
        # Send execution start with session info
        await websocket.send_text(json.dumps({
            "type": "execution_start",
            "session_id": session.session_id,
            "timestamp": datetime.now().isoformat(),
            "content": content
        }))
        
        # Check for agent references in content
        agent_mentions = []
        if "@" in content:
            # Extract agent mentions
            import re
            agent_pattern = r'@(\w+[-\w]*)'
            agent_mentions = re.findall(agent_pattern, content)
            
            if agent_mentions:
                await websocket.send_text(json.dumps({
                    "type": "agents_detected",
                    "agents": agent_mentions,
                    "message": f"Detected {len(agent_mentions)} agent(s): {', '.join(agent_mentions)}"
                }))
        
        # Simulate agent activation if agents detected
        if agent_mentions:
            for agent in agent_mentions:
                if not session.should_continue():
                    break
                    
                session.current_agent = agent
                await websocket.send_text(json.dumps({
                    "type": "agent_activated",
                    "agent": agent,
                    "status": "initializing",
                    "message": f"Activating {agent} agent..."
                }))
                await asyncio.sleep(0.5)  # Simulate initialization
                
                await websocket.send_text(json.dumps({
                    "type": "agent_status",
                    "agent": agent,
                    "status": "active",
                    "message": f"{agent} agent is now active"
                }))
        
        # Stream the actual Claude response
        if claude_interface and session.should_continue():
            response_chunks = []
            chunk_count = 0
            
            async for chunk in claude_interface.stream_prompt(content, working_dir):
                if not session.should_continue():
                    await websocket.send_text(json.dumps({
                        "type": "execution_cancelled",
                        "message": "Execution cancelled by user"
                    }))
                    break
                    
                response_chunks.append(chunk)
                chunk_count += 1
                
                # Send progress updates periodically
                if chunk_count % 10 == 0:
                    await websocket.send_text(json.dumps({
                        "type": "progress",
                        "chunks_received": chunk_count,
                        "current_agent": session.current_agent
                    }))
                
                # Send the actual content chunk
                await websocket.send_text(json.dumps({
                    "type": "stream",
                    "content": chunk,
                    "agent": session.current_agent
                }))
                
                # Detect task/todo mentions in the stream
                if "todo" in chunk.lower() or "task" in chunk.lower():
                    await websocket.send_text(json.dumps({
                        "type": "task_detected",
                        "message": "Task or todo item detected in response"
                    }))
            
            # Record the completed task
            full_response = "".join(response_chunks)
            task_record = chat_manager.record_task(session.session_id, {
                "content": content,
                "response": full_response[:500],  # Store first 500 chars
                "agents_used": agent_mentions,
                "status": "cancelled" if not session.should_continue() else "completed",
                "duration": (datetime.now() - session.start_time).total_seconds()
            })
            
            await websocket.send_text(json.dumps({
                "type": "task_recorded",
                "task_id": task_record["id"],
                "status": task_record["status"]
            }))
            
        else:
            # Demo mode with detailed streaming
            demo_response = f"Processing: {content}\n\n"
            
            if agent_mentions:
                demo_response += f"Agents involved: {', '.join(agent_mentions)}\n\n"
            
            demo_response += "This is a demo response. In production, Claude Code would process this request."
            
            words = demo_response.split()
            for i, word in enumerate(words):
                if not session.should_continue():
                    await websocket.send_text(json.dumps({
                        "type": "execution_cancelled",
                        "message": "Execution cancelled by user"
                    }))
                    break
                    
                await websocket.send_text(json.dumps({
                    "type": "stream",
                    "content": word + " ",
                    "agent": session.current_agent
                }))
                
                # Simulate progress
                if i % 5 == 0:
                    await websocket.send_text(json.dumps({
                        "type": "progress",
                        "percent": (i / len(words)) * 100,
                        "current_agent": session.current_agent
                    }))
                
                await asyncio.sleep(0.05)
        
        # Deactivate agents
        if agent_mentions:
            for agent in agent_mentions:
                await websocket.send_text(json.dumps({
                    "type": "agent_deactivated",
                    "agent": agent,
                    "message": f"{agent} agent completed"
                }))
        
        # Send execution complete
        if session.should_continue():
            await websocket.send_text(json.dumps({
                "type": "execution_complete",
                "session_id": session.session_id,
                "duration": (datetime.now() - session.start_time).total_seconds(),
                "agents_used": agent_mentions
            }))
        
    except asyncio.CancelledError:
        await websocket.send_text(json.dumps({
            "type": "execution_cancelled",
            "message": "Execution was cancelled"
        }))
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": f"Execution error: {str(e)}"
        }))


@enhanced_chat_router.websocket("/enhanced-chat-ws")
async def enhanced_chat_websocket(websocket: WebSocket):
    """Enhanced chat WebSocket with execution control and detailed streaming."""
    await websocket.accept()
    
    # Create session for this connection
    session_id = chat_manager.create_session(websocket)
    session = chat_manager.get_session(session_id)
    
    # Send session info
    await websocket.send_text(json.dumps({
        "type": "session_created",
        "session_id": session_id,
        "features": ["stop_execution", "agent_tracking", "task_history", "detailed_streaming"]
    }))
    
    # Get app and Claude interface
    app = websocket.scope.get("app")
    claude_interface = app.state.claude_interface if app else None
    working_dir = str(app.state.working_directory) if app else "."
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            msg_type = message_data.get("type")
            
            if msg_type == "message":
                # Start execution
                content = message_data.get("content", "")
                
                # Create execution task
                session.execution_task = asyncio.create_task(
                    stream_with_details(
                        websocket, session, content, 
                        working_dir, claude_interface
                    )
                )
                
                # Don't wait for completion, allow other messages
                
            elif msg_type == "stop":
                # Stop current execution
                if chat_manager.cancel_session(session_id):
                    await websocket.send_text(json.dumps({
                        "type": "stop_acknowledged",
                        "message": "Stopping execution..."
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        "type": "stop_failed",
                        "message": "No active execution to stop"
                    }))
                    
            elif msg_type == "get_task_history":
                # Send task history
                limit = message_data.get("limit", 50)
                history = chat_manager.task_history[-limit:]
                
                await websocket.send_text(json.dumps({
                    "type": "task_history",
                    "tasks": history,
                    "total": len(chat_manager.task_history)
                }))
                
            elif msg_type == "get_active_agents":
                # Get currently active agents
                active_agents = []
                for sid, sess in chat_manager.active_sessions.items():
                    if sess.current_agent:
                        active_agents.append({
                            "session_id": sid,
                            "agent": sess.current_agent,
                            "task": sess.current_task
                        })
                
                await websocket.send_text(json.dumps({
                    "type": "active_agents",
                    "agents": active_agents
                }))
                
    except WebSocketDisconnect:
        chat_manager.remove_session(session_id)
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": f"WebSocket error: {str(e)}"
        }))
        chat_manager.remove_session(session_id)


@enhanced_chat_router.get("/task-history")
async def get_task_history(limit: int = 50, offset: int = 0):
    """Get task execution history."""
    history = chat_manager.task_history[offset:offset + limit]
    return {
        "tasks": history,
        "total": len(chat_manager.task_history),
        "limit": limit,
        "offset": offset
    }


@enhanced_chat_router.post("/cancel-execution/{session_id}")
async def cancel_execution(session_id: str):
    """Cancel an active execution session."""
    if chat_manager.cancel_session(session_id):
        return {"status": "success", "message": "Execution cancelled"}
    return {"status": "error", "message": "Session not found or already completed"}