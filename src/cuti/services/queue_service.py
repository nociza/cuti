"""
Queue management service - high-level queue operations.
"""

from datetime import datetime
from typing import Optional, Callable, Dict, Any

from ..core.models import QueuedPrompt, QueueState, PromptStatus
from ..core.storage import PromptStorage
from ..core.queue import QueueProcessor
from ..core.config import CutiConfig
from ..core.claude_interface import ClaudeCodeInterface


class QueueManager:
    """High-level queue management service."""

    def __init__(
        self,
        storage_dir: str = "~/.cuti",
        claude_command: str = "claude",
        check_interval: int = 30,
        timeout: int = 3600,
    ):
        self.config = CutiConfig(
            storage_dir=storage_dir,
            claude_command=claude_command,
            check_interval=check_interval,
            timeout=timeout,
        )
        
        self.storage = PromptStorage(storage_dir)
        self.claude_interface = ClaudeCodeInterface(claude_command, timeout)
        self.processor = QueueProcessor(
            self.storage, self.claude_interface, check_interval
        )
        
        self.state: Optional[QueueState] = None

    def start(self, callback: Optional[Callable[[QueueState], None]] = None) -> None:
        """Start the queue processing loop."""
        self.processor.start(callback)

    def stop(self) -> None:
        """Stop the queue processing loop."""
        self.processor.stop()

    def add_prompt(self, prompt: QueuedPrompt) -> bool:
        """Add a prompt to the queue."""
        try:
            if not self.state:
                self.state = self.storage.load_queue_state()

            self.state.add_prompt(prompt)

            success = self.storage.save_queue_state(self.state)
            if success:
                print(f"✓ Added prompt {prompt.id} to queue")
            else:
                print(f"✗ Failed to save prompt {prompt.id}")

            return success

        except Exception as e:
            print(f"Error adding prompt: {e}")
            return False

    def remove_prompt(self, prompt_id: str) -> bool:
        """Remove a prompt from the queue."""
        try:
            if not self.state:
                self.state = self.storage.load_queue_state()

            prompt = self.state.get_prompt(prompt_id)
            if prompt:
                if prompt.status == PromptStatus.EXECUTING:
                    print(f"Cannot remove executing prompt {prompt_id}")
                    return False

                prompt.status = PromptStatus.CANCELLED
                prompt.add_log("Cancelled by user")

                success = self.storage.save_queue_state(self.state)
                if success:
                    print(f"✓ Cancelled prompt {prompt_id}")
                else:
                    print(f"✗ Failed to cancel prompt {prompt_id}")

                return success
            else:
                print(f"Prompt {prompt_id} not found")
                return False

        except Exception as e:
            print(f"Error removing prompt: {e}")
            return False

    def get_status(self) -> QueueState:
        """Get current queue status."""
        if not self.state:
            self.state = self.storage.load_queue_state()
        return self.state

    def create_prompt_template(self, filename: str, priority: int = 0) -> str:
        """Create a prompt template file."""
        file_path = self.storage.create_prompt_template(filename, priority)
        return str(file_path)

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get basic rate limit information for testing."""
        if not self.state:
            self.state = self.storage.load_queue_state()

        current_time = datetime.now()
        rate_limited_prompts = [
            p for p in self.state.prompts if p.status == PromptStatus.RATE_LIMITED
        ]

        info = {
            "current_time": current_time,
            "has_rate_limited_prompts": len(rate_limited_prompts) > 0,
            "rate_limited_count": len(rate_limited_prompts),
            "prompts": [],
        }

        for prompt in rate_limited_prompts:
            info["prompts"].append(
                {
                    "id": prompt.id,
                    "rate_limited_at": prompt.rate_limited_at,
                    "retry_count": prompt.retry_count,
                    "max_retries": prompt.max_retries,
                }
            )

        return info