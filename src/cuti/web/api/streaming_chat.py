"""
Streaming chat WebSocket that shows all intermediate steps and tool usage in real-time.
"""

import json
import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.claude_stream_interface import (
    ClaudeStreamInterface,
    StreamEvent,
    StreamEventType
)
from ...core.mock_stream_interface import MockStreamInterface
from ...core.token_counter import TokenCounter, TokenMetrics

streaming_chat_router = APIRouter()


class StreamingSession:
    """Manages a streaming chat session."""
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.is_streaming = False
        self.is_cancelled = False
        self.current_task: Optional[asyncio.Task] = None
        self.start_time = datetime.now()
        self.stream_interface = ClaudeStreamInterface()
        self.token_counter = TokenCounter()
        self.message_history = []
        self.tool_stack = []  # Track nested tool usage
        self.last_token_update = datetime.now()
        
    async def send(self, data: Dict[str, Any]):
        """Send data to the WebSocket client."""
        try:
            await self.websocket.send_text(json.dumps(data))
        except Exception as e:
            print(f"Error sending to WebSocket: {e}")
    
    def cancel(self):
        """Cancel the current streaming operation."""
        self.is_cancelled = True
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()


class StreamingChatManager:
    """Manages streaming chat sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, StreamingSession] = {}
    
    def create_session(self, websocket: WebSocket) -> StreamingSession:
        """Create a new streaming session."""
        session_id = str(uuid.uuid4())[:8]
        session = StreamingSession(session_id, websocket)
        self.sessions[session_id] = session
        return session
    
    def remove_session(self, session_id: str):
        """Remove a session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.cancel()
            del self.sessions[session_id]


# Global manager
streaming_manager = StreamingChatManager()


async def stream_claude_response(session: StreamingSession, prompt: str, working_dir: str):
    """Stream Claude's response with all intermediate steps and token counting."""
    
    session.is_streaming = True
    session.token_counter.reset_current()
    
    try:
        # Count input tokens
        input_tokens = session.token_counter.count_prompt_tokens(prompt)
        
        # Send start event with token count
        await session.send({
            "type": "stream_start",
            "session_id": session.session_id,
            "prompt": prompt,
            "input_tokens": input_tokens,
            "input_cost": session.token_counter.format_cost(
                input_tokens * session.token_counter.pricing["input"]
            ),
            "timestamp": datetime.now().isoformat()
        })
        
        # Send initial token metrics
        await session.send({
            "type": "token_metrics",
            "metrics": session.token_counter.get_current_metrics().to_dict(),
            "session_metrics": session.token_counter.get_session_metrics().to_dict()
        })
        
        # Initialize metrics
        event_count = 0
        tool_count = 0
        file_count = 0
        command_count = 0
        text_buffer = []
        stream_start_time = datetime.now()
        
        # Use mock interface for demonstration (replace with real Claude when available)
        mock_interface = MockStreamInterface()
        
        # Stream the response with all steps
        async for event in mock_interface.stream_mock_response(prompt):
            # Check if cancelled
            if session.is_cancelled:
                await session.send({
                    "type": "stream_cancelled",
                    "message": "Stream cancelled by user"
                })
                break
            
            event_count += 1
            event_dict = event.to_dict()
            
            # Process different event types
            if event.type == StreamEventType.INIT:
                await session.send({
                    "type": "step",
                    "step_type": "init",
                    "content": event.content,
                    "metadata": event.metadata
                })
            
            elif event.type == StreamEventType.TOOL_START:
                tool_count += 1
                tool_name = event.metadata.get("tool", "unknown")
                session.tool_stack.append(tool_name)
                await session.send({
                    "type": "tool_start",
                    "tool": tool_name,
                    "content": event.content,
                    "depth": len(session.tool_stack),
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.TOOL_END:
                if session.tool_stack:
                    tool_name = session.tool_stack.pop()
                    await session.send({
                        "type": "tool_end",
                        "tool": tool_name,
                        "depth": len(session.tool_stack),
                        "timestamp": event.timestamp
                    })
            
            elif event.type == StreamEventType.READING_FILE:
                file_count += 1
                await session.send({
                    "type": "file_operation",
                    "operation": "read",
                    "file": event.metadata.get("file"),
                    "content": event.content,
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.WRITING_FILE:
                file_count += 1
                await session.send({
                    "type": "file_operation",
                    "operation": "write",
                    "file": event.metadata.get("file"),
                    "content": event.content,
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.RUNNING_COMMAND:
                command_count += 1
                await session.send({
                    "type": "command",
                    "command": event.metadata.get("command"),
                    "content": event.content,
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.COMMAND_OUTPUT:
                await session.send({
                    "type": "command_output",
                    "content": event.content,
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.THINKING:
                await session.send({
                    "type": "thinking",
                    "content": event.content,
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.PROGRESS:
                await session.send({
                    "type": "progress",
                    "content": event.content,
                    "metadata": event.metadata,
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.ERROR:
                await session.send({
                    "type": "error",
                    "content": event.content,
                    "severity": event.metadata.get("severity", "error"),
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.WARNING:
                await session.send({
                    "type": "warning",
                    "content": event.content,
                    "timestamp": event.timestamp
                })
            
            elif event.type == StreamEventType.TEXT:
                # Buffer text for smoother display
                text_buffer.append(event.content)
                
                # Count tokens in the text
                chunk_tokens, total_output = session.token_counter.count_streaming_tokens(event.content)
                
                # Calculate token rate
                elapsed = (datetime.now() - stream_start_time).total_seconds()
                token_rate = session.token_counter.get_token_rate(total_output, elapsed)
                
                # Send buffered text periodically with token info
                if len(text_buffer) >= 3 or event_count % 10 == 0:
                    await session.send({
                        "type": "text",
                        "content": "\n".join(text_buffer),
                        "timestamp": event.timestamp
                    })
                    text_buffer.clear()
                
                # Send token updates periodically (every 0.5 seconds)
                now = datetime.now()
                if (now - session.last_token_update).total_seconds() > 0.5:
                    metrics = session.token_counter.get_current_metrics()
                    await session.send({
                        "type": "token_update",
                        "output_tokens": metrics.output_tokens,
                        "total_tokens": metrics.total_tokens,
                        "output_cost": session.token_counter.format_cost(metrics.output_cost),
                        "total_cost": session.token_counter.format_cost(metrics.total_cost),
                        "token_rate": round(token_rate, 1),
                        "elapsed_seconds": round(elapsed, 1)
                    })
                    session.last_token_update = now
            
            elif event.type == StreamEventType.COMPLETE:
                # Send any remaining buffered text
                if text_buffer:
                    # Count final tokens
                    for text in text_buffer:
                        session.token_counter.count_streaming_tokens(text)
                    
                    await session.send({
                        "type": "text",
                        "content": "\n".join(text_buffer),
                        "timestamp": event.timestamp
                    })
                    text_buffer.clear()
                
                # Get final token metrics
                final_metrics = session.token_counter.get_current_metrics()
                session_metrics = session.token_counter.get_session_metrics()
                duration = (datetime.now() - stream_start_time).total_seconds()
                final_rate = session.token_counter.get_token_rate(final_metrics.output_tokens, duration)
                
                # Send completion with statistics and final token count
                await session.send({
                    "type": "stream_complete",
                    "statistics": {
                        "duration": duration,
                        "events": event_count,
                        "tools_used": tool_count,
                        "files_accessed": file_count,
                        "commands_run": command_count
                    },
                    "token_metrics": {
                        "input_tokens": final_metrics.input_tokens,
                        "output_tokens": final_metrics.output_tokens,
                        "total_tokens": final_metrics.total_tokens,
                        "input_cost": session.token_counter.format_cost(final_metrics.input_cost),
                        "output_cost": session.token_counter.format_cost(final_metrics.output_cost),
                        "total_cost": session.token_counter.format_cost(final_metrics.total_cost),
                        "tokens_per_second": round(final_rate, 1)
                    },
                    "session_totals": {
                        "total_input": session_metrics.input_tokens,
                        "total_output": session_metrics.output_tokens,
                        "total_cost": session.token_counter.format_cost(session_metrics.total_cost)
                    },
                    "timestamp": event.timestamp
                })
            
            # Send periodic status updates
            if event_count % 20 == 0:
                await session.send({
                    "type": "status",
                    "events_processed": event_count,
                    "tools_active": len(session.tool_stack),
                    "is_streaming": True
                })
        
    except asyncio.CancelledError:
        await session.send({
            "type": "stream_cancelled",
            "message": "Stream was cancelled"
        })
    except Exception as e:
        await session.send({
            "type": "stream_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
    finally:
        session.is_streaming = False
        session.tool_stack.clear()


@streaming_chat_router.websocket("/streaming-chat-ws")
async def streaming_chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming chat with full step visibility."""
    
    await websocket.accept()
    
    # Create session
    session = streaming_manager.create_session(websocket)
    
    # Send welcome message
    await session.send({
        "type": "connected",
        "session_id": session.session_id,
        "features": [
            "intermediate_steps",
            "tool_usage_tracking",
            "file_operations",
            "command_execution",
            "thinking_display",
            "real_time_progress",
            "cancellation"
        ],
        "timestamp": datetime.now().isoformat()
    })
    
    # Get working directory
    app = websocket.scope.get("app")
    working_dir = str(app.state.working_directory) if app else "."
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            if msg_type == "message":
                # Stream response with all steps
                prompt = message.get("content", "")
                
                # Record in history
                session.message_history.append({
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Start streaming task
                session.current_task = asyncio.create_task(
                    stream_claude_response(session, prompt, working_dir)
                )
                
            elif msg_type == "cancel":
                # Cancel streaming
                if session.is_streaming:
                    session.cancel()
                    await session.send({
                        "type": "cancel_acknowledged",
                        "message": "Cancelling stream..."
                    })
                else:
                    await session.send({
                        "type": "cancel_failed",
                        "message": "No active stream to cancel"
                    })
            
            elif msg_type == "get_history":
                # Send message history
                await session.send({
                    "type": "history",
                    "messages": session.message_history[-50:],  # Last 50 messages
                    "total": len(session.message_history)
                })
            
            elif msg_type == "ping":
                # Heartbeat
                await session.send({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        streaming_manager.remove_session(session.session_id)
    except Exception as e:
        await session.send({
            "type": "error",
            "error": f"WebSocket error: {str(e)}"
        })
        streaming_manager.remove_session(session.session_id)