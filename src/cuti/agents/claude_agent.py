"""
Claude Code CLI agent implementation.
"""

import subprocess
import asyncio
from typing import AsyncGenerator, Optional
from pathlib import Path

from .base import (
    BaseAgent, 
    AgentCapability, 
    AgentMetadata, 
    AgentStatus,
    AgentConfig,
    AgentExecutionContext
)
from ..core.models import QueuedPrompt, ExecutionResult
from ..core.claude_interface import ClaudeCodeInterface


class ClaudeAgent(BaseAgent):
    """Claude Code CLI agent implementation."""
    
    def _initialize_metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="Claude Code",
            version="1.0",
            capabilities=[
                AgentCapability.CODE_UNDERSTANDING,
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REFACTORING,
                AgentCapability.DEBUGGING,
                AgentCapability.TESTING,
                AgentCapability.DOCUMENTATION,
                AgentCapability.ARCHITECTURE_DESIGN,
                AgentCapability.SECURITY_ANALYSIS,
                AgentCapability.PERFORMANCE_OPTIMIZATION,
                AgentCapability.FILE_SYSTEM_OPERATIONS,
                AgentCapability.API_INTEGRATION,
                AgentCapability.DATA_ANALYSIS
            ],
            max_context_tokens=200_000,
            supports_streaming=True,
            supports_multimodal=True,
            cost_per_input_token=0.000015,
            cost_per_output_token=0.000075,
            installation_command="Install Claude Desktop from https://claude.ai/download",
            authentication_required=True,
            supported_languages=["Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Rust", "Ruby", "PHP", "Swift"],
            special_features=["MCP servers", "File editing", "Web browsing", "Tool use"]
        )
    
    async def initialize(self) -> bool:
        """Initialize the Claude agent."""
        try:
            self.status = AgentStatus.INITIALIZING
            
            # Initialize the Claude interface
            claude_command = self.config.command or 'claude'
            self.interface = ClaudeCodeInterface(
                claude_command=claude_command,
                timeout=self.config.timeout
            )
            
            # Test connection
            is_working, message = self.interface.test_connection()
            
            if is_working:
                self.status = AgentStatus.AVAILABLE
                self._initialized = True
                return True
            else:
                self.status = AgentStatus.OFFLINE
                print(f"Claude agent initialization failed: {message}")
                return False
                
        except Exception as e:
            self.status = AgentStatus.ERROR
            print(f"Error initializing Claude agent: {e}")
            return False
    
    async def execute_prompt(
        self, 
        prompt: QueuedPrompt,
        context: AgentExecutionContext
    ) -> ExecutionResult:
        """Execute a prompt with Claude Code."""
        
        # Track execution
        self.add_execution(prompt.id, prompt)
        
        try:
            # Prepare enhanced prompt with context
            enhanced_prompt = await self._prepare_prompt(prompt, context)
            
            # Execute with Claude interface
            result = self.interface.execute_prompt(enhanced_prompt)
            
            # Store output in shared context if in collaboration mode
            if context.collaboration_mode:
                from .context import SharedMemoryManager
                memory_manager = SharedMemoryManager(self.config.working_directory)
                await memory_manager.set_context(
                    context.session_id,
                    f"claude_output_{prompt.id}",
                    result.output,
                    self.name
                )
            
            return result
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Claude execution error: {str(e)}",
                execution_time=0,
                tokens_used=0
            )
        finally:
            self.remove_execution(prompt.id)
    
    async def stream_prompt(
        self,
        prompt: QueuedPrompt,
        context: AgentExecutionContext
    ) -> AsyncGenerator[str, None]:
        """Stream execution results from Claude."""
        
        # Track execution
        self.add_execution(prompt.id, prompt)
        
        try:
            # Prepare enhanced prompt
            enhanced_prompt = await self._prepare_prompt(prompt, context)
            
            # Stream with Claude interface
            async for chunk in self.interface.stream_prompt_async(enhanced_prompt):
                yield chunk
                
        except Exception as e:
            yield f"\nError during streaming: {str(e)}"
        finally:
            self.remove_execution(prompt.id)
    
    async def health_check(self) -> bool:
        """Check Claude agent health."""
        try:
            is_working, _ = self.interface.test_connection()
            
            if is_working:
                self._health_check_failures = 0
                if self.status == AgentStatus.ERROR:
                    self.status = AgentStatus.AVAILABLE
                return True
            else:
                self._health_check_failures += 1
                if self._health_check_failures >= 3:
                    self.status = AgentStatus.ERROR
                return False
                
        except Exception:
            self._health_check_failures += 1
            return False
    
    async def is_installed(self) -> bool:
        """Check if Claude CLI is installed."""
        try:
            claude_command = self.config.command or 'claude'
            result = subprocess.run(
                [claude_command, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    async def install(self) -> bool:
        """
        Install Claude CLI.
        Note: Claude requires manual installation via desktop app.
        """
        print(f"To install Claude, please {self.metadata.installation_command}")
        return False  # Cannot auto-install
    
    async def can_handle_task(self, prompt: QueuedPrompt) -> float:
        """Claude-specific task confidence assessment."""
        content_lower = prompt.content.lower()
        
        # Very high confidence for general coding tasks
        if any(keyword in content_lower for keyword in [
            'code', 'function', 'class', 'implement', 'create', 'build', 'develop'
        ]):
            return 0.95
        
        # High confidence for debugging and refactoring
        if any(keyword in content_lower for keyword in [
            'debug', 'fix', 'error', 'refactor', 'improve', 'optimize'
        ]):
            return 0.9
        
        # High confidence for documentation
        if any(keyword in content_lower for keyword in [
            'document', 'readme', 'comment', 'explain', 'describe'
        ]):
            return 0.85
        
        # Good for architecture and design
        if any(keyword in content_lower for keyword in [
            'architecture', 'design', 'structure', 'pattern', 'system'
        ]):
            return 0.8
        
        # Medium confidence for general tasks
        return 0.6
    
    async def _prepare_prompt(
        self,
        prompt: QueuedPrompt,
        context: AgentExecutionContext
    ) -> QueuedPrompt:
        """Prepare prompt with context and collaboration info."""
        
        # Get system prompt
        system_prompt = await self.prepare_system_prompt(context)
        
        # Create enhanced content
        enhanced_content = ""
        
        # Add system prompt if in collaboration mode
        if context.collaboration_mode:
            enhanced_content += f"## System Context\n\n{system_prompt}\n\n"
        
        # Add main content
        enhanced_content += f"## Task\n\n{prompt.content}\n\n"
        
        # Add shared memory if available
        if context.shared_memory:
            enhanced_content += f"## Shared Context\n\n"
            for key, value in context.shared_memory.items():
                if not key.startswith('_'):  # Skip private keys
                    enhanced_content += f"**{key}**: {value}\n\n"
        
        # Add collaboration data
        if context.collaboration_mode and context.coordination_data:
            enhanced_content += f"## Collaboration Info\n\n"
            for key, value in context.coordination_data.items():
                enhanced_content += f"**{key}**: {value}\n\n"
        
        # Create new prompt with enhanced content
        enhanced_prompt = QueuedPrompt(
            content=enhanced_content,
            working_directory=prompt.working_directory,
            context_files=prompt.context_files,
            priority=prompt.priority,
            max_retries=prompt.max_retries,
            estimated_tokens=prompt.estimated_tokens
        )
        
        # Copy over other attributes
        enhanced_prompt.id = prompt.id
        enhanced_prompt.status = prompt.status
        enhanced_prompt.created_at = prompt.created_at
        
        return enhanced_prompt