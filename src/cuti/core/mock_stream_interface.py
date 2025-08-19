"""
Mock streaming interface that simulates Claude's intermediate steps for testing.
"""

import asyncio
from typing import AsyncIterator
from datetime import datetime
from .claude_stream_interface import StreamEvent, StreamEventType


class MockStreamInterface:
    """Mock interface that simulates streaming with intermediate steps."""
    
    async def stream_mock_response(self, prompt: str) -> AsyncIterator[StreamEvent]:
        """Generate a mock stream of events simulating Claude's work."""
        
        # Initialization
        yield StreamEvent(
            type=StreamEventType.INIT,
            content="Initializing Claude...",
            metadata={"mode": "mock"}
        )
        await asyncio.sleep(0.5)
        
        # Thinking phase
        yield StreamEvent(
            type=StreamEventType.THINKING,
            content="Analyzing your request..."
        )
        await asyncio.sleep(0.3)
        
        yield StreamEvent(
            type=StreamEventType.THINKING,
            content=f"Processing: {prompt[:50]}..."
        )
        await asyncio.sleep(0.5)
        
        # Simulate file operations based on keywords
        if "readme" in prompt.lower() or "understand" in prompt.lower():
            yield StreamEvent(
                type=StreamEventType.TOOL_START,
                content="Starting file search",
                metadata={"tool": "search"}
            )
            await asyncio.sleep(0.3)
            
            yield StreamEvent(
                type=StreamEventType.READING_FILE,
                content="Reading README.md",
                metadata={"file": "README.md"}
            )
            await asyncio.sleep(0.5)
            
            yield StreamEvent(
                type=StreamEventType.PROGRESS,
                content="Analyzing file structure..."
            )
            await asyncio.sleep(0.3)
            
            yield StreamEvent(
                type=StreamEventType.READING_FILE,
                content="Reading package.json",
                metadata={"file": "package.json"}
            )
            await asyncio.sleep(0.4)
            
            yield StreamEvent(
                type=StreamEventType.TOOL_END,
                content="File analysis complete",
                metadata={"tool": "search"}
            )
            await asyncio.sleep(0.2)
        
        # Simulate command execution
        if "test" in prompt.lower() or "run" in prompt.lower():
            yield StreamEvent(
                type=StreamEventType.RUNNING_COMMAND,
                content="Running: npm test",
                metadata={"command": "npm test"}
            )
            await asyncio.sleep(0.5)
            
            yield StreamEvent(
                type=StreamEventType.COMMAND_OUTPUT,
                content="✓ All tests passed (42 tests)"
            )
            await asyncio.sleep(0.3)
        
        # Start generating response text
        response_parts = [
            "Based on my analysis, ",
            "I can see that this is a comprehensive codebase ",
            "with multiple components and features. ",
            "The README file provides detailed information ",
            "about the project structure and usage. ",
            "Let me highlight the key points:\n\n",
            "1. **Project Overview**: This is the cuti project ",
            "which provides a powerful interface for Claude.\n",
            "2. **Key Features**: Real-time streaming, ",
            "token counting, and state persistence.\n",
            "3. **Architecture**: Built with FastAPI backend ",
            "and Alpine.js frontend.\n",
            "4. **Installation**: Uses uv for dependency management.\n\n",
            "The codebase is well-organized with clear separation ",
            "between backend services and frontend components."
        ]
        
        for part in response_parts:
            yield StreamEvent(
                type=StreamEventType.TEXT,
                content=part
            )
            await asyncio.sleep(0.1 + len(part) * 0.002)  # Simulate typing speed
        
        # Complete
        yield StreamEvent(
            type=StreamEventType.COMPLETE,
            content="Response complete",
            metadata={"mock": True}
        )