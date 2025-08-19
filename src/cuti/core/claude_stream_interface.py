"""
Enhanced streaming interface for Claude Code that captures all intermediate steps,
tool usage, and provides real-time updates to the UI.
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re


class StreamEventType(Enum):
    """Types of streaming events."""
    INIT = "init"
    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_INPUT = "tool_input"
    TOOL_OUTPUT = "tool_output"
    TOOL_END = "tool_end"
    THINKING = "thinking"
    READING_FILE = "reading_file"
    WRITING_FILE = "writing_file"
    RUNNING_COMMAND = "running_command"
    COMMAND_OUTPUT = "command_output"
    ERROR = "error"
    WARNING = "warning"
    COMPLETE = "complete"
    PROGRESS = "progress"


@dataclass
class StreamEvent:
    """A streaming event with metadata."""
    type: StreamEventType
    content: str = ""
    metadata: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class ClaudeStreamInterface:
    """Streaming interface that captures all Claude's intermediate steps."""
    
    def __init__(self, claude_command: str = "claude"):
        self.claude_command = claude_command
        self.current_tool = None
        self.tool_depth = 0
        
    async def stream_with_steps(self,
                                prompt: str,
                                working_dir: str = ".",
                                context_files: Optional[List[str]] = None,
                                capture_all: bool = True) -> AsyncIterator[StreamEvent]:
        """Stream Claude's response with all intermediate steps.
        
        Args:
            prompt: The prompt to send to Claude
            working_dir: Working directory for execution
            context_files: Optional list of files to include as context
            capture_all: Whether to capture all output including tool usage
            
        Yields:
            StreamEvent objects with detailed step information
        """
        
        # Prepare the command
        cmd = [self.claude_command]
        
        # Add context files if provided
        full_prompt = prompt
        if context_files:
            for file in context_files:
                if Path(file).exists():
                    full_prompt = f"@{file} {full_prompt}"
        
        cmd.append(full_prompt)
        
        # Change to working directory
        original_cwd = os.getcwd()
        try:
            working_path = Path(working_dir).resolve()
            if not working_path.exists():
                working_path.mkdir(parents=True, exist_ok=True)
            os.chdir(working_path)
            
            # Send initialization event
            yield StreamEvent(
                type=StreamEventType.INIT,
                content="Starting Claude...",
                metadata={"working_dir": str(working_path)}
            )
            
            # Start the process with proper pipe configuration and verbose mode
            env = {**os.environ}
            env['CLAUDE_EXPERIMENTAL_STREAMING'] = '1'  # Enable experimental streaming if available
            env['CLAUDE_DEBUG'] = '1'  # Enable debug mode for more detailed output
            env['CLAUDE_VERBOSE'] = '1'  # Enable verbose mode
            
            # Add verbose flag to command if supported
            if '--verbose' not in cmd:
                cmd.insert(1, '--verbose')
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Create tasks for reading stdout and stderr
            stdout_task = asyncio.create_task(self._read_stdout(process))
            stderr_task = asyncio.create_task(self._read_stderr(process))
            
            # Process output streams
            buffer = ""
            line_count = 0
            
            while True:
                # Check if process has finished
                if process.returncode is not None:
                    break
                
                try:
                    # Read from stdout with timeout
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=0.1
                    )
                    
                    if not line:
                        # Check if process is still running
                        if process.returncode is None:
                            await asyncio.sleep(0.01)
                            continue
                        else:
                            break
                    
                    line_str = line.decode('utf-8', errors='replace')
                    line_count += 1
                    
                    # Parse and yield events based on line content
                    async for event in self._parse_line(line_str, line_count):
                        yield event
                    
                except asyncio.TimeoutError:
                    # No output available, check if still running
                    if process.returncode is not None:
                        break
                    continue
                except Exception as e:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        content=f"Stream error: {str(e)}"
                    )
            
            # Wait for process to complete
            returncode = await process.wait()
            
            # Read any remaining output
            remaining_stdout = await process.stdout.read()
            if remaining_stdout:
                for line in remaining_stdout.decode('utf-8', errors='replace').splitlines():
                    async for event in self._parse_line(line, line_count):
                        yield event
            
            # Read stderr for any errors
            stderr_output = await process.stderr.read()
            if stderr_output:
                stderr_text = stderr_output.decode('utf-8', errors='replace')
                if stderr_text.strip():
                    yield StreamEvent(
                        type=StreamEventType.WARNING,
                        content=stderr_text,
                        metadata={"source": "stderr"}
                    )
            
            # Send completion event
            yield StreamEvent(
                type=StreamEventType.COMPLETE,
                content="Response complete",
                metadata={"exit_code": returncode, "lines_processed": line_count}
            )
            
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=f"Execution error: {str(e)}",
                metadata={"error_type": type(e).__name__}
            )
        finally:
            # Return to original directory
            os.chdir(original_cwd)
    
    async def _parse_line(self, line: str, line_num: int) -> AsyncIterator[StreamEvent]:
        """Parse a line of output and yield appropriate events.
        
        This method detects various patterns in Claude's output to identify
        tool usage, file operations, command execution, etc.
        """
        
        line = line.rstrip()
        
        # Skip empty lines
        if not line:
            return
        
        # Detect tool usage patterns - expanded to catch more Claude output patterns
        tool_patterns = {
            r"Using tool:?\s*(\w+)": StreamEventType.TOOL_START,
            r"Tool\s+(\w+)\s+started": StreamEventType.TOOL_START,
            r"Running\s+(\w+)\s+tool": StreamEventType.TOOL_START,
            r"Executing\s+(\w+)": StreamEventType.TOOL_START,
            r"<(\w+)>": StreamEventType.TOOL_START,  # XML-style tool tags
            r"I'll use the (\w+) tool": StreamEventType.TOOL_START,
            r"Let me use (\w+)": StreamEventType.TOOL_START,
            r"Using (\w+) to": StreamEventType.TOOL_START,
        }
        
        for pattern, event_type in tool_patterns.items():
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                tool_name = match.group(1)
                self.current_tool = tool_name
                yield StreamEvent(
                    type=event_type,
                    content=f"Starting {tool_name} tool",
                    metadata={"tool": tool_name, "line": line_num}
                )
                return
        
        # Detect file operations
        if re.search(r"Reading\s+file:?\s*(.+)", line, re.IGNORECASE):
            match = re.search(r"Reading\s+file:?\s*(.+)", line, re.IGNORECASE)
            file_path = match.group(1).strip()
            yield StreamEvent(
                type=StreamEventType.READING_FILE,
                content=f"Reading {file_path}",
                metadata={"file": file_path, "operation": "read"}
            )
            return
        
        if re.search(r"Writing\s+to\s+file:?\s*(.+)", line, re.IGNORECASE):
            match = re.search(r"Writing\s+to\s+file:?\s*(.+)", line, re.IGNORECASE)
            file_path = match.group(1).strip()
            yield StreamEvent(
                type=StreamEventType.WRITING_FILE,
                content=f"Writing to {file_path}",
                metadata={"file": file_path, "operation": "write"}
            )
            return
        
        # Detect command execution
        if re.search(r"Running\s+command:?\s*(.+)", line, re.IGNORECASE):
            match = re.search(r"Running\s+command:?\s*(.+)", line, re.IGNORECASE)
            command = match.group(1).strip()
            yield StreamEvent(
                type=StreamEventType.RUNNING_COMMAND,
                content=f"Executing: {command}",
                metadata={"command": command}
            )
            return
        
        if re.search(r"^\$\s+(.+)", line):
            match = re.search(r"^\$\s+(.+)", line)
            command = match.group(1).strip()
            yield StreamEvent(
                type=StreamEventType.RUNNING_COMMAND,
                content=f"$ {command}",
                metadata={"command": command, "shell": True}
            )
            return
        
        # Detect command output (indented lines often indicate output)
        if line.startswith("  ") or line.startswith("\t"):
            yield StreamEvent(
                type=StreamEventType.COMMAND_OUTPUT,
                content=line.strip(),
                metadata={"indented": True}
            )
            return
        
        # Detect thinking/planning
        thinking_patterns = [
            r"Thinking",
            r"Planning",
            r"Analyzing",
            r"Let me",
            r"I'll",
            r"I will",
            r"First,",
            r"Next,",
            r"Now,",
        ]
        
        for pattern in thinking_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                yield StreamEvent(
                    type=StreamEventType.THINKING,
                    content=line,
                    metadata={"pattern": pattern}
                )
                return
        
        # Detect progress indicators
        if "%" in line or re.search(r"\d+/\d+", line):
            yield StreamEvent(
                type=StreamEventType.PROGRESS,
                content=line,
                metadata={"has_percentage": "%" in line}
            )
            return
        
        # Detect errors
        if any(word in line.lower() for word in ["error", "failed", "exception", "traceback"]):
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=line,
                metadata={"severity": "error"}
            )
            return
        
        # Detect warnings
        if any(word in line.lower() for word in ["warning", "warn", "caution"]):
            yield StreamEvent(
                type=StreamEventType.WARNING,
                content=line,
                metadata={"severity": "warning"}
            )
            return
        
        # Default to text output
        yield StreamEvent(
            type=StreamEventType.TEXT,
            content=line,
            metadata={"line": line_num}
        )
    
    async def _read_stdout(self, process):
        """Read stdout in background."""
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
        except:
            pass
    
    async def _read_stderr(self, process):
        """Read stderr in background."""
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
        except:
            pass