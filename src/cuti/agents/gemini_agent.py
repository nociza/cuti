"""
Gemini CLI agent implementation.
"""

import subprocess
import asyncio
import json
import os
from typing import AsyncGenerator, Optional, Dict, Any, List
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


class GeminiAgent(BaseAgent):
    """Gemini CLI agent implementation."""
    
    def _initialize_metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="Gemini",
            version="1.0",
            capabilities=[
                AgentCapability.CODE_UNDERSTANDING,
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REFACTORING,
                AgentCapability.DEBUGGING,
                AgentCapability.TESTING,
                AgentCapability.DOCUMENTATION,
                AgentCapability.ARCHITECTURE_DESIGN,
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.MULTIMODAL_PROCESSING,
                AgentCapability.LARGE_CONTEXT_PROCESSING
            ],
            max_context_tokens=1_000_000,  # Gemini 1.5 Pro supports up to 1M tokens
            supports_streaming=True,
            supports_multimodal=True,
            cost_per_input_token=0.00125,  # Gemini 1.5 Pro pricing
            cost_per_output_token=0.00375,
            installation_command="pip install -U google-generativeai or uv pip install google-generativeai",
            authentication_required=True,
            supported_languages=["Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Rust", "Ruby", "PHP", "Swift"],
            special_features=["Long context window", "Multimodal understanding", "Code execution", "Function calling"]
        )
    
    async def initialize(self) -> bool:
        """Initialize the Gemini agent."""
        try:
            self.status = AgentStatus.INITIALIZING
            
            # Check for API key
            api_key = self.config.api_key or os.environ.get(self.config.api_key_env or 'GOOGLE_API_KEY')
            if not api_key:
                print("Gemini API key not found. Set GOOGLE_API_KEY environment variable.")
                self.status = AgentStatus.OFFLINE
                return False
            
            # Store API key for later use
            self._api_key = api_key
            
            # Test connection
            is_working = await self._test_connection()
            
            if is_working:
                self.status = AgentStatus.AVAILABLE
                self._initialized = True
                return True
            else:
                self.status = AgentStatus.OFFLINE
                return False
                
        except Exception as e:
            self.status = AgentStatus.ERROR
            print(f"Error initializing Gemini agent: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test Gemini CLI connection."""
        try:
            # Test with a simple prompt
            result = await self._run_gemini_command("Hello, respond with 'OK' if you're working.")
            return "OK" in result or "ok" in result.lower()
        except Exception:
            return False
    
    async def _run_gemini_command(self, prompt: str, context_files: Optional[List[str]] = None) -> str:
        """Run Gemini CLI command."""
        try:
            # Prepare command
            cmd = ["gemini", prompt]
            
            # Add context files if provided
            if context_files:
                for file in context_files:
                    if Path(file).exists():
                        cmd.extend(["-f", file])
            
            # Set environment with API key
            env = os.environ.copy()
            env['GOOGLE_API_KEY'] = self._api_key
            
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.config.working_directory
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Gemini command failed: {error_msg}")
            
            return stdout.decode()
            
        except asyncio.TimeoutError:
            raise RuntimeError(f"Gemini command timed out after {self.config.timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"Error running Gemini command: {str(e)}")
    
    async def execute_prompt(
        self, 
        prompt: QueuedPrompt,
        context: AgentExecutionContext
    ) -> ExecutionResult:
        """Execute a prompt with Gemini."""
        
        # Track execution
        self.add_execution(prompt.id, prompt)
        
        try:
            # Prepare enhanced prompt with context
            enhanced_prompt = await self._prepare_prompt(prompt, context)
            
            # Execute with Gemini
            start_time = asyncio.get_event_loop().time()
            output = await self._run_gemini_command(
                enhanced_prompt.content,
                enhanced_prompt.context_files
            )
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Estimate tokens (rough approximation)
            estimated_tokens = len(enhanced_prompt.content.split()) + len(output.split())
            
            # Store output in shared context if in collaboration mode
            if context.collaboration_mode:
                from .context import SharedMemoryManager
                memory_manager = SharedMemoryManager(self.config.working_directory)
                await memory_manager.set_context(
                    context.session_id,
                    f"gemini_output_{prompt.id}",
                    output,
                    self.name
                )
            
            return ExecutionResult(
                success=True,
                output=output,
                error=None,
                execution_time=execution_time,
                tokens_used=estimated_tokens
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Gemini execution error: {str(e)}",
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
        """Stream execution results from Gemini."""
        
        # Track execution
        self.add_execution(prompt.id, prompt)
        
        try:
            # Prepare enhanced prompt
            enhanced_prompt = await self._prepare_prompt(prompt, context)
            
            # Prepare command for streaming
            cmd = ["gemini", enhanced_prompt.content]
            
            # Add context files if provided
            if enhanced_prompt.context_files:
                for file in enhanced_prompt.context_files:
                    if Path(file).exists():
                        cmd.extend(["-f", file])
            
            # Set environment with API key
            env = os.environ.copy()
            env['GOOGLE_API_KEY'] = self._api_key
            
            # Create subprocess for streaming
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.config.working_directory
            )
            
            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode()
            
            # Wait for process to complete
            await process.wait()
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                yield f"\nError: {stderr.decode()}"
                
        except Exception as e:
            yield f"\nError during streaming: {str(e)}"
        finally:
            self.remove_execution(prompt.id)
    
    async def health_check(self) -> bool:
        """Check Gemini agent health."""
        try:
            is_working = await self._test_connection()
            
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
        """Check if Gemini CLI is installed."""
        try:
            result = subprocess.run(
                ['gemini', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    async def install(self) -> bool:
        """Install Gemini CLI."""
        try:
            # Try to install using pip
            result = subprocess.run(
                ['pip', 'install', '-U', 'gemini-cli'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("Gemini CLI installed successfully")
                return True
            else:
                print(f"Failed to install Gemini CLI: {result.stderr}")
                print(f"Please install manually: {self.metadata.installation_command}")
                return False
                
        except Exception as e:
            print(f"Error installing Gemini CLI: {e}")
            print(f"Please install manually: {self.metadata.installation_command}")
            return False
    
    async def can_handle_task(self, prompt: QueuedPrompt) -> float:
        """Gemini-specific task confidence assessment."""
        content_lower = prompt.content.lower()
        
        # Very high confidence for data analysis
        if any(keyword in content_lower for keyword in [
            'analyze', 'data', 'statistics', 'insights', 'trends', 'pattern'
        ]):
            return 0.95
        
        # High confidence for multimodal tasks
        if any(keyword in content_lower for keyword in [
            'image', 'video', 'audio', 'multimodal', 'visual'
        ]):
            return 0.9
        
        # High confidence for large context tasks
        if any(keyword in content_lower for keyword in [
            'large', 'context', 'document', 'corpus', 'dataset'
        ]):
            return 0.9
        
        # Good for code generation
        if any(keyword in content_lower for keyword in [
            'code', 'function', 'implement', 'create', 'build'
        ]):
            return 0.85
        
        # Good for general tasks
        return 0.7
    
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
        if context.collaboration_mode and system_prompt:
            enhanced_content += f"System Context: {system_prompt}\n\n"
        
        # Add main content
        enhanced_content += prompt.content
        
        # Add shared memory if available
        if context.shared_memory:
            enhanced_content += "\n\nShared Context:\n"
            for key, value in context.shared_memory.items():
                if not key.startswith('_'):  # Skip private keys
                    enhanced_content += f"- {key}: {value}\n"
        
        # Add collaboration data
        if context.collaboration_mode and context.coordination_data:
            enhanced_content += "\n\nCollaboration Info:\n"
            for key, value in context.coordination_data.items():
                enhanced_content += f"- {key}: {value}\n"
        
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