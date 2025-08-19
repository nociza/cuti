"""
Enhanced Claude interface using the Claude Code SDK Python wrapper.
Provides streaming, progress tracking, and proper error handling.
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Try to import the Claude Code SDK
try:
    from claude_code_sdk import query, ClaudeCodeOptions
    from claude_code_sdk.exceptions import (
        ClaudeSDKError,
        CLINotFoundError,
        ProcessError,
        CLIJSONDecodeError
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    # Fallback definitions for when SDK is not installed
    class ClaudeSDKError(Exception):
        pass
    class CLINotFoundError(ClaudeSDKError):
        pass
    class ProcessError(ClaudeSDKError):
        def __init__(self, exit_code: int):
            self.exit_code = exit_code
    class CLIJSONDecodeError(ClaudeSDKError):
        pass


class MessageType(Enum):
    """Types of messages that can be sent during streaming."""
    PROGRESS = "progress"
    STREAM = "stream"
    TOOL_USE = "tool_use"
    ERROR = "error"
    COMPLETE = "complete"
    THINKING = "thinking"
    STATUS = "status"
    AGENT_ACTIVATED = "agent_activated"
    AGENT_COMPLETED = "agent_completed"


@dataclass
class StreamMessage:
    """Structured message for streaming responses."""
    type: MessageType
    content: str = ""
    metadata: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class ClaudeSDKInterface:
    """Enhanced interface for Claude Code using the official SDK."""
    
    def __init__(self, 
                 system_prompt: Optional[str] = None,
                 max_turns: int = 1,
                 allowed_tools: Optional[List[str]] = None,
                 permission_mode: str = 'acceptEdits'):
        """Initialize the Claude SDK interface.
        
        Args:
            system_prompt: Optional system prompt to use
            max_turns: Maximum number of conversation turns
            allowed_tools: List of allowed tools (e.g., ["Read", "Write", "Bash"])
            permission_mode: How to handle permissions ('acceptEdits', 'askUser', etc.)
        """
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.allowed_tools = allowed_tools or []
        self.permission_mode = permission_mode
        self._verify_installation()
    
    def _verify_installation(self):
        """Verify that Claude Code CLI and SDK are properly installed."""
        global SDK_AVAILABLE
        if not SDK_AVAILABLE:
            # Try to install the SDK automatically
            try:
                subprocess.run(
                    ["pip", "install", "claude-code-sdk"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                # Re-import after installation
                from claude_code_sdk import query, ClaudeCodeOptions
                SDK_AVAILABLE = True
            except Exception as e:
                raise RuntimeError(
                    "Claude Code SDK not installed. Please run: pip install claude-code-sdk"
                )
        
        # Verify Claude Code CLI is available
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "Claude Code CLI not available. Please install: npm install -g @anthropic-ai/claude-code"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Claude Code CLI not found. Please install: npm install -g @anthropic-ai/claude-code"
            )
    
    async def stream_response(self, 
                             prompt: str, 
                             working_dir: str = ".",
                             context_files: Optional[List[str]] = None) -> AsyncIterator[StreamMessage]:
        """Stream a response from Claude with detailed progress tracking.
        
        Args:
            prompt: The prompt to send to Claude
            working_dir: Working directory for execution
            context_files: Optional list of files to include as context
            
        Yields:
            StreamMessage objects containing progress and content
        """
        if not SDK_AVAILABLE:
            yield StreamMessage(
                type=MessageType.ERROR,
                content="Claude Code SDK not available. Please install it first."
            )
            return
        
        # Prepare the full prompt with context files
        full_prompt = prompt
        if context_files:
            context_refs = [f"@{file}" for file in context_files if Path(file).exists()]
            if context_refs:
                full_prompt = f"{' '.join(context_refs)} {prompt}"
        
        # Configure options
        options = ClaudeCodeOptions(
            system_prompt=self.system_prompt,
            max_turns=self.max_turns,
            allowed_tools=self.allowed_tools,
            permission_mode=self.permission_mode
        )
        
        try:
            # Change to working directory
            original_cwd = os.getcwd()
            working_path = Path(working_dir).resolve()
            if not working_path.exists():
                working_path.mkdir(parents=True, exist_ok=True)
            os.chdir(working_path)
            
            # Send initial status
            yield StreamMessage(
                type=MessageType.STATUS,
                content="Initializing Claude...",
                metadata={"step": "init"}
            )
            
            # Track progress
            chunk_count = 0
            total_content = []
            last_progress_time = datetime.now()
            
            # Stream the response
            async for message in query(prompt=full_prompt, options=options):
                chunk_count += 1
                
                # Handle different message types
                if hasattr(message, '__class__'):
                    message_type = message.__class__.__name__
                    
                    if message_type == "AssistantMessage":
                        # Extract content from assistant message
                        if hasattr(message, 'content'):
                            for block in message.content:
                                if hasattr(block, 'text'):
                                    content = block.text
                                    total_content.append(content)
                                    
                                    # Send stream message
                                    yield StreamMessage(
                                        type=MessageType.STREAM,
                                        content=content,
                                        metadata={"chunk": chunk_count}
                                    )
                                elif hasattr(block, 'tool_use'):
                                    # Tool use detected
                                    yield StreamMessage(
                                        type=MessageType.TOOL_USE,
                                        content=f"Using tool: {block.tool_use.name}",
                                        metadata={"tool": block.tool_use.name}
                                    )
                    
                    elif message_type == "ThinkingMessage":
                        # Claude is thinking
                        yield StreamMessage(
                            type=MessageType.THINKING,
                            content="Claude is thinking...",
                            metadata={"thinking": True}
                        )
                    
                    elif message_type == "ErrorMessage":
                        # Error occurred
                        yield StreamMessage(
                            type=MessageType.ERROR,
                            content=str(message),
                            metadata={"error": True}
                        )
                else:
                    # Plain text message
                    content = str(message)
                    total_content.append(content)
                    yield StreamMessage(
                        type=MessageType.STREAM,
                        content=content,
                        metadata={"chunk": chunk_count}
                    )
                
                # Send periodic progress updates
                now = datetime.now()
                if (now - last_progress_time).total_seconds() > 2:
                    yield StreamMessage(
                        type=MessageType.PROGRESS,
                        content=f"Processing... ({chunk_count} chunks received)",
                        metadata={
                            "chunks": chunk_count,
                            "elapsed": (now - last_progress_time).total_seconds()
                        }
                    )
                    last_progress_time = now
            
            # Change back to original directory
            os.chdir(original_cwd)
            
            # Send completion message
            yield StreamMessage(
                type=MessageType.COMPLETE,
                content="Response complete",
                metadata={
                    "total_chunks": chunk_count,
                    "total_length": sum(len(c) for c in total_content)
                }
            )
            
        except CLINotFoundError:
            yield StreamMessage(
                type=MessageType.ERROR,
                content="Claude Code CLI not found. Please install it first.",
                metadata={"error_type": "cli_not_found"}
            )
        except ProcessError as e:
            yield StreamMessage(
                type=MessageType.ERROR,
                content=f"Process failed with exit code {e.exit_code}",
                metadata={"error_type": "process_error", "exit_code": e.exit_code}
            )
        except CLIJSONDecodeError as e:
            yield StreamMessage(
                type=MessageType.ERROR,
                content=f"Failed to decode Claude response: {str(e)}",
                metadata={"error_type": "json_decode"}
            )
        except Exception as e:
            yield StreamMessage(
                type=MessageType.ERROR,
                content=f"Unexpected error: {str(e)}",
                metadata={"error_type": "unexpected", "details": str(e)}
            )
        finally:
            # Ensure we return to original directory
            try:
                os.chdir(original_cwd)
            except:
                pass
    
    async def execute_with_agents(self, 
                                 prompt: str,
                                 agents: List[str],
                                 working_dir: str = ".") -> AsyncIterator[StreamMessage]:
        """Execute a prompt with specific agents activated.
        
        Args:
            prompt: The prompt to execute
            agents: List of agent names to activate
            working_dir: Working directory
            
        Yields:
            StreamMessage objects with agent status updates
        """
        # Activate agents
        for agent in agents:
            yield StreamMessage(
                type=MessageType.AGENT_ACTIVATED,
                content=f"Activating {agent} agent...",
                metadata={"agent": agent, "status": "activating"}
            )
            await asyncio.sleep(0.1)  # Brief pause for UI
        
        # Process with agents
        agent_prompt = " ".join([f"@{agent}" for agent in agents]) + " " + prompt
        
        async for message in self.stream_response(agent_prompt, working_dir):
            yield message
        
        # Deactivate agents
        for agent in agents:
            yield StreamMessage(
                type=MessageType.AGENT_COMPLETED,
                content=f"{agent} agent completed",
                metadata={"agent": agent, "status": "completed"}
            )
    
    def is_available(self) -> bool:
        """Check if the Claude SDK is available and working."""
        try:
            self._verify_installation()
            return SDK_AVAILABLE
        except:
            return False
    
    async def simple_query(self, prompt: str) -> str:
        """Execute a simple query and return the full response.
        
        Args:
            prompt: The prompt to execute
            
        Returns:
            The complete response as a string
        """
        response_parts = []
        async for message in self.stream_response(prompt):
            if message.type == MessageType.STREAM:
                response_parts.append(message.content)
        return "".join(response_parts)