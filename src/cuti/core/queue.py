"""
Legacy Claude queue processing logic.
"""

import signal
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any

from .claude_interface import ClaudeCodeInterface
from .models import ExecutionResult, PromptStatus, QueuedPrompt, QueueState
from .storage import PromptStorage


class QueueProcessor:
    """Legacy queue processing engine."""

    def __init__(
        self,
        storage: PromptStorage,
        claude_interface: ClaudeCodeInterface,
        check_interval: int = 30,
    ):
        self.storage = storage
        self.claude_interface = claude_interface
        self.check_interval: float = check_interval
        self.running = False
        self.state: QueueState | None = None

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.stop()

    def start(self, callback: Callable[[QueueState], None] | None = None) -> None:
        """Start the queue processing loop."""
        print("Starting legacy queue processor...")

        is_working, message = self.claude_interface.test_connection()
        if not is_working:
            print(f"Error: {message}")
            return

        print(f"✓ {message}")

        self.state = self.storage.load_queue_state()
        print(f"✓ Loaded legacy queue with {len(self.state.prompts)} prompts")

        self.running = True

        try:
            while self.running:
                self._process_queue_iteration(callback)

                if self.running:
                    time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        except Exception as e:
            print(f"Error in queue processing: {e}")
        finally:
            self._shutdown()

    def stop(self) -> None:
        """Stop the queue processing loop."""
        self.running = False

    def _shutdown(self) -> None:
        """Clean shutdown procedure."""
        print("Shutting down...")

        if self.state:
            for prompt in self.state.prompts:
                if prompt.status == PromptStatus.EXECUTING:
                    prompt.status = PromptStatus.QUEUED
                    prompt.add_log("Execution interrupted during shutdown")

            self.storage.save_queue_state(self.state)
            print("✓ Queue state saved")

            print("Legacy queue processor stopped")

    def _process_queue_iteration(
        self, callback: Callable[[QueueState], None] | None = None
    ) -> None:
        """Process one iteration of the queue."""
        # Preserve counters across state reloads
        previous_total_processed = self.state.total_processed if self.state else 0
        previous_failed_count = self.state.failed_count if self.state else 0
        previous_rate_limited_count = self.state.rate_limited_count if self.state else 0
        previous_last_processed = self.state.last_processed if self.state else None

        self.state = self.storage.load_queue_state()

        # Restore counters
        self.state.total_processed = max(self.state.total_processed, previous_total_processed)
        self.state.failed_count = max(self.state.failed_count, previous_failed_count)
        self.state.rate_limited_count = max(self.state.rate_limited_count, previous_rate_limited_count)
        if previous_last_processed and (not self.state.last_processed or self.state.last_processed < previous_last_processed):
            self.state.last_processed = previous_last_processed

        self._check_rate_limited_prompts()

        next_prompt = self.state.get_next_prompt()

        if next_prompt is None:
            rate_limited_prompts = [
                p for p in self.state.prompts if p.status == PromptStatus.RATE_LIMITED
            ]
            if rate_limited_prompts:
                # Find the earliest reset time
                earliest_reset = None
                for prompt in rate_limited_prompts:
                    if prompt.reset_time:
                        if earliest_reset is None or prompt.reset_time < earliest_reset:
                            earliest_reset = prompt.reset_time

                if earliest_reset:
                    wait_seconds = max(0, (earliest_reset - datetime.now()).total_seconds())
                    if wait_seconds > 0:
                        reset_time_str = earliest_reset.strftime("%I:%M %p")
                        print(f"⏳ Rate limited. Next retry at {reset_time_str} ({wait_seconds/60:.1f} minutes)")

                        # Use a shorter check interval when waiting for rate limit reset
                        # Check every minute or at reset time, whichever is sooner
                        self.check_interval = min(60, max(1, wait_seconds))
                    else:
                        print("Rate limit should have reset, checking prompts...")
                else:
                    print(f"Waiting for rate limit reset ({len(rate_limited_prompts)} prompts rate limited)")
            else:
                print("No prompts in queue")

            if callback:
                callback(self.state)
            return

        print(f"Executing prompt {next_prompt.id}: {next_prompt.content[:50]}...")
        self._execute_prompt(next_prompt)

        self.storage.save_queue_state(self.state)

        if callback:
            callback(self.state)

    def _check_rate_limited_prompts(self) -> None:
        """Check if any rate-limited prompts should be retried."""
        if self.state is None:
            return

        current_time = datetime.now()

        for prompt in self.state.prompts:
            if prompt.status == PromptStatus.RATE_LIMITED:
                # If we have a specific reset time from the rate limit info, use that
                if prompt.reset_time:
                    if current_time >= prompt.reset_time:
                        if prompt.can_retry():
                            prompt.status = PromptStatus.QUEUED
                            prompt.add_log(f"Retrying after rate limit reset at {prompt.reset_time}")
                            print(f"✓ Prompt {prompt.id} ready for retry after rate limit reset")
                        else:
                            prompt.status = PromptStatus.FAILED
                            prompt.add_log(f"Max retries ({prompt.max_retries}) exceeded")
                            print(f"✗ Prompt {prompt.id} failed - max retries exceeded")
                # Fallback to time-based check (5+ minutes)
                elif (
                    prompt.rate_limited_at
                    and current_time >= prompt.rate_limited_at + timedelta(minutes=5)
                ):
                    if prompt.can_retry():
                        prompt.status = PromptStatus.QUEUED
                        prompt.add_log("Retrying after rate limit cooldown")
                        print(f"✓ Prompt {prompt.id} ready for retry after cooldown")
                    else:
                        prompt.status = PromptStatus.FAILED
                        prompt.add_log(f"Max retries ({prompt.max_retries}) exceeded")
                        print(f"✗ Prompt {prompt.id} failed - max retries exceeded")

    def _execute_prompt(self, prompt: QueuedPrompt) -> None:
        """Execute a single prompt."""
        prompt.status = PromptStatus.EXECUTING
        prompt.last_executed = datetime.now()

        # Check if this is a retry after rate limit
        is_rate_limit_retry = (prompt.retry_count > 0 and
                               prompt.rate_limited_at is not None and
                               prompt.reset_time is not None)

        execution_prompt = prompt

        if is_rate_limit_retry:
            execution_prompt = replace(prompt, content="continue")
            prompt.add_log(
                f"Retrying with 'continue' after rate limit (attempt {prompt.retry_count + 1}/{prompt.max_retries})"
            )
        else:
            prompt.add_log(
                f"Started execution (attempt {prompt.retry_count + 1}/{prompt.max_retries})"
            )

        if self.state is None:
            raise RuntimeError("Queue state is not loaded")

        self.storage.save_queue_state(self.state)

        result = self.claude_interface.execute_prompt(execution_prompt)

        self._process_execution_result(prompt, result)

    def _process_execution_result(
        self, prompt: QueuedPrompt, result: ExecutionResult
    ) -> None:
        """Process the result of prompt execution."""
        if self.state is None:
            raise RuntimeError("Queue state is not loaded")

        state = self.state
        execution_summary = f"Execution completed in {result.execution_time:.1f}s"

        if result.success:
            prompt.status = PromptStatus.COMPLETED
            prompt.add_log(f"{execution_summary} - SUCCESS")
            if result.output:
                prompt.add_log(f"Output:\n{result.output}")

            state.total_processed += 1
            print(f"✓ Prompt {prompt.id} completed successfully")

        elif result.is_rate_limited:
            was_already_rate_limited = prompt.status == PromptStatus.RATE_LIMITED
            prompt.status = PromptStatus.RATE_LIMITED
            prompt.rate_limited_at = datetime.now()
            prompt.retry_count += 1

            # Store the reset time if available
            if result.rate_limit_info and result.rate_limit_info.reset_time:
                prompt.reset_time = result.rate_limit_info.reset_time
                reset_time_str = result.rate_limit_info.reset_time.strftime("%I:%M %p")
                wait_time = (result.rate_limit_info.reset_time - datetime.now()).total_seconds()

                prompt.add_log(f"{execution_summary} - RATE LIMITED (resets at {reset_time_str})")
                print(f"⚠ Prompt {prompt.id} rate limited. Will retry at {reset_time_str} ({wait_time/60:.1f} minutes)")

                # Automatically send "continue" after rate limit reset
                if wait_time > 0:
                    print("📅 Scheduling automatic retry after rate limit reset...")
                    prompt.add_log(f"Scheduled for automatic retry at {reset_time_str}")
            else:
                prompt.add_log(f"{execution_summary} - RATE LIMITED")
                print(f"⚠ Prompt {prompt.id} rate limited, will retry later")

            if result.rate_limit_info and result.rate_limit_info.limit_message:
                prompt.add_log(f"Message: {result.rate_limit_info.limit_message}")

            if not was_already_rate_limited:
                state.rate_limited_count += 1

        else:
            prompt.retry_count += 1

            if prompt.can_retry():
                prompt.status = PromptStatus.QUEUED
                prompt.add_log(f"{execution_summary} - FAILED (will retry)")
                if result.error:
                    prompt.add_log(f"Error: {result.error}")
                print(
                    f"✗ Prompt {prompt.id} failed, will retry ({prompt.retry_count}/{prompt.max_retries})"
                )
            else:
                prompt.status = PromptStatus.FAILED
                prompt.add_log(f"{execution_summary} - FAILED (max retries exceeded)")
                if result.error:
                    prompt.add_log(f"Error: {result.error}")

                state.failed_count += 1
                print(
                    f"✗ Prompt {prompt.id} failed permanently after {prompt.max_retries} attempts"
                )

        state.last_processed = datetime.now()
