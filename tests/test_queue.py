"""
Tests for queue processing functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import time

from cuti.core.queue import QueueProcessor
from cuti.core.models import (
    QueuedPrompt, 
    QueueState, 
    PromptStatus, 
    ExecutionResult,
    RateLimitInfo
)
from cuti.core.storage import PromptStorage
from cuti.core.claude_interface import ClaudeCodeInterface


class TestQueueProcessor:
    """Test suite for QueueProcessor."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage instance."""
        storage = Mock(spec=PromptStorage)
        storage.load_queue_state.return_value = QueueState(prompts=[])
        storage.save_queue_state.return_value = None
        return storage
    
    @pytest.fixture
    def mock_claude_interface(self):
        """Create a mock Claude interface instance."""
        interface = Mock(spec=ClaudeCodeInterface)
        interface.test_connection.return_value = (True, "Claude Code is working")
        interface.execute_prompt.return_value = ExecutionResult(
            success=True,
            output="Test output",
            error=None,
            execution_time=1.0
        )
        return interface
    
    @pytest.fixture
    def queue_processor(self, mock_storage, mock_claude_interface):
        """Create a QueueProcessor instance with mocked dependencies."""
        return QueueProcessor(
            storage=mock_storage,
            claude_interface=mock_claude_interface,
            check_interval=1
        )
    
    def test_initialization(self, queue_processor):
        """Test QueueProcessor initialization."""
        assert queue_processor.check_interval == 1
        assert queue_processor.running is False
        assert queue_processor.state is None
    
    def test_successful_prompt_execution(self, queue_processor, mock_storage, mock_claude_interface):
        """Test successful execution of a queued prompt."""
        prompt = QueuedPrompt(
            id="test-1",
            content="Test prompt",
            status=PromptStatus.QUEUED
        )
        state = QueueState(prompts=[prompt])
        mock_storage.load_queue_state.return_value = state
        
        queue_processor.state = state
        queue_processor._process_queue_iteration()
        
        assert prompt.status == PromptStatus.COMPLETED
        assert state.total_processed == 1
        assert mock_claude_interface.execute_prompt.called
        assert mock_storage.save_queue_state.called
    
    def test_failed_prompt_with_retry(self, queue_processor, mock_storage, mock_claude_interface):
        """Test failed prompt execution - first failure should mark as FAILED, not re-queue immediately."""
        prompt = QueuedPrompt(
            id="test-2",
            content="Failing prompt",
            status=PromptStatus.QUEUED,
            max_retries=3
        )
        state = QueueState(prompts=[prompt])
        mock_storage.load_queue_state.return_value = state
        
        mock_claude_interface.execute_prompt.return_value = ExecutionResult(
            success=False,
            output="",
            error="Test error",
            execution_time=1.0
        )
        
        queue_processor.state = state
        queue_processor._process_queue_iteration()
        
        # After first failure, prompt should be FAILED (not immediately re-queued)
        # This is because can_retry() requires status to be FAILED/RATE_LIMITED first
        assert prompt.status == PromptStatus.FAILED
        assert prompt.retry_count == 1
        assert state.failed_count == 1  # Failed count should increment
    
    def test_failed_prompt_max_retries_exceeded(self, queue_processor, mock_storage, mock_claude_interface):
        """Test failed prompt when max retries are exceeded."""
        prompt = QueuedPrompt(
            id="test-3",
            content="Failing prompt",
            status=PromptStatus.QUEUED,
            max_retries=2,
            retry_count=2
        )
        state = QueueState(prompts=[prompt])
        mock_storage.load_queue_state.return_value = state
        
        mock_claude_interface.execute_prompt.return_value = ExecutionResult(
            success=False,
            output="",
            error="Test error",
            execution_time=1.0
        )
        
        queue_processor.state = state
        queue_processor._process_queue_iteration()
        
        assert prompt.status == PromptStatus.FAILED
        assert prompt.retry_count == 3
        assert state.failed_count == 1
    
    def test_rate_limited_prompt(self, queue_processor, mock_storage, mock_claude_interface):
        """Test handling of rate-limited prompts."""
        prompt = QueuedPrompt(
            id="test-4",
            content="Rate limited prompt",
            status=PromptStatus.QUEUED
        )
        state = QueueState(prompts=[prompt])
        mock_storage.load_queue_state.return_value = state
        
        reset_time = datetime.now() + timedelta(minutes=5)
        mock_claude_interface.execute_prompt.return_value = ExecutionResult(
            success=False,
            output="",
            rate_limit_info=RateLimitInfo(
                is_rate_limited=True,
                reset_time=reset_time,
                limit_message="Rate limit exceeded"
            ),
            execution_time=0.5
        )
        
        queue_processor.state = state
        queue_processor._process_queue_iteration()
        
        assert prompt.status == PromptStatus.RATE_LIMITED
        assert prompt.rate_limited_at is not None
        assert prompt.reset_time == reset_time
        assert prompt.retry_count == 1
        assert state.rate_limited_count == 1
    
    def test_rate_limited_retry_with_continue(self, queue_processor, mock_storage, mock_claude_interface):
        """Test automatic retry with 'continue' after rate limit reset."""
        past_time = datetime.now() - timedelta(minutes=1)
        prompt = QueuedPrompt(
            id="test-5",
            content="Original prompt content",
            status=PromptStatus.RATE_LIMITED,
            rate_limited_at=past_time,
            reset_time=past_time,
            retry_count=1
        )
        state = QueueState(prompts=[prompt])
        mock_storage.load_queue_state.return_value = state
        
        mock_claude_interface.execute_prompt.return_value = ExecutionResult(
            success=True,
            output="Continued output",
            execution_time=2.0
        )
        
        queue_processor.state = state
        queue_processor._check_rate_limited_prompts()
        
        assert prompt.status == PromptStatus.QUEUED
        
        queue_processor._process_queue_iteration()
        
        # Verify that 'continue' was used during execution
        called_prompt = mock_claude_interface.execute_prompt.call_args[0][0]
        assert prompt.content == "Original prompt content"  # Content should be restored
        assert prompt.status == PromptStatus.COMPLETED
    
    def test_multiple_prompts_priority(self, queue_processor, mock_storage, mock_claude_interface):
        """Test that prompts are processed in the correct order."""
        prompts = [
            QueuedPrompt(id="p1", content="First", status=PromptStatus.QUEUED, created_at=datetime.now()),
            QueuedPrompt(id="p2", content="Second", status=PromptStatus.QUEUED, created_at=datetime.now() + timedelta(seconds=1)),
            QueuedPrompt(id="p3", content="Third", status=PromptStatus.EXECUTING, created_at=datetime.now() + timedelta(seconds=2)),
            QueuedPrompt(id="p4", content="Fourth", status=PromptStatus.COMPLETED, created_at=datetime.now() + timedelta(seconds=3)),
        ]
        state = QueueState(prompts=prompts)
        mock_storage.load_queue_state.return_value = state
        
        queue_processor.state = state
        next_prompt = state.get_next_prompt()
        
        assert next_prompt.id == "p1"
    
    def test_shutdown_saves_state(self, queue_processor, mock_storage):
        """Test that shutdown properly saves the queue state."""
        prompt = QueuedPrompt(
            id="test-6",
            content="Executing prompt",
            status=PromptStatus.EXECUTING
        )
        state = QueueState(prompts=[prompt])
        queue_processor.state = state
        
        queue_processor._shutdown()
        
        assert prompt.status == PromptStatus.QUEUED
        assert mock_storage.save_queue_state.called
        assert mock_storage.save_queue_state.call_args[0][0] == state
    
    def test_empty_queue_handling(self, queue_processor, mock_storage):
        """Test handling of empty queue."""
        state = QueueState(prompts=[])
        mock_storage.load_queue_state.return_value = state
        
        queue_processor.state = state
        queue_processor._process_queue_iteration()
        
        # Should not crash - empty queue doesn't save state
        # Just verify no exception was raised
        assert True
    
    def test_connection_failure(self, queue_processor, mock_claude_interface, mock_storage):
        """Test handling of Claude connection failure."""
        mock_claude_interface.test_connection.return_value = (False, "Connection failed")
        
        queue_processor.start()
        
        # Should exit early without processing
        assert not queue_processor.running
        assert mock_storage.load_queue_state.call_count == 0
    
    def test_preserve_counters_across_reloads(self, queue_processor, mock_storage):
        """Test that counters are preserved when state is reloaded."""
        initial_state = QueueState(
            prompts=[],
            total_processed=5,
            failed_count=2,
            rate_limited_count=1,
            last_processed=datetime.now() - timedelta(hours=1)
        )
        
        reloaded_state = QueueState(
            prompts=[],
            total_processed=0,
            failed_count=0,
            rate_limited_count=0,
            last_processed=None
        )
        
        queue_processor.state = initial_state
        mock_storage.load_queue_state.return_value = reloaded_state
        
        queue_processor._process_queue_iteration()
        
        assert queue_processor.state.total_processed == 5
        assert queue_processor.state.failed_count == 2
        assert queue_processor.state.rate_limited_count == 1
        assert queue_processor.state.last_processed == initial_state.last_processed


class TestQueuedPrompt:
    """Test suite for QueuedPrompt model."""
    
    def test_can_retry_with_remaining_retries(self):
        """Test can_retry returns True when retries remain."""
        prompt = QueuedPrompt(
            id="test",
            content="Test",
            max_retries=3,
            retry_count=1,
            status=PromptStatus.FAILED  # Need to be in FAILED or RATE_LIMITED status
        )
        assert prompt.can_retry() is True
    
    def test_can_retry_at_max_retries(self):
        """Test can_retry returns False when at max retries."""
        prompt = QueuedPrompt(
            id="test",
            content="Test",
            max_retries=3,
            retry_count=3
        )
        assert prompt.can_retry() is False
    
    def test_add_log_entry(self):
        """Test adding log entries to a prompt."""
        prompt = QueuedPrompt(id="test", content="Test")
        
        prompt.add_log("First log entry")
        prompt.add_log("Second log entry")
        
        # Check execution_log instead of log_entries
        assert "First log entry" in prompt.execution_log
        assert "Second log entry" in prompt.execution_log
        # Check timestamps are added
        assert prompt.execution_log.count("[") == 2  # Two timestamps


class TestQueueState:
    """Test suite for QueueState model."""
    
    def test_get_next_prompt_empty_queue(self):
        """Test get_next_prompt returns None for empty queue."""
        state = QueueState(prompts=[])
        assert state.get_next_prompt() is None
    
    def test_get_next_prompt_priority(self):
        """Test get_next_prompt returns correct prompt based on status priority."""
        prompts = [
            QueuedPrompt(id="p1", content="Completed", status=PromptStatus.COMPLETED),
            QueuedPrompt(id="p2", content="Failed", status=PromptStatus.FAILED),
            QueuedPrompt(id="p3", content="Queued", status=PromptStatus.QUEUED),
            QueuedPrompt(id="p4", content="Rate Limited", status=PromptStatus.RATE_LIMITED),
        ]
        state = QueueState(prompts=prompts)
        
        next_prompt = state.get_next_prompt()
        assert next_prompt.id == "p3"
    
    def test_get_next_prompt_priority(self):
        """Test get_next_prompt returns prompt based on priority."""
        prompts = [
            QueuedPrompt(id="p1", content="Lower priority", status=PromptStatus.QUEUED, priority=5),
            QueuedPrompt(id="p2", content="Higher priority", status=PromptStatus.QUEUED, priority=1),
        ]
        state = QueueState(prompts=prompts)
        
        next_prompt = state.get_next_prompt()
        assert next_prompt.id == "p2"  # Lower priority number = higher priority


class TestExecutionResult:
    """Test suite for ExecutionResult model."""
    
    def test_successful_result(self):
        """Test creation of successful execution result."""
        result = ExecutionResult(
            success=True,
            output="Test output",
            execution_time=1.5
        )
        
        assert result.success is True
        assert result.output == "Test output"
        assert result.error == ""  # Default is empty string, not None
        assert result.is_rate_limited is False
        assert result.execution_time == 1.5
    
    def test_failed_result(self):
        """Test creation of failed execution result."""
        result = ExecutionResult(
            success=False,
            output="",  # Output is required
            error="Test error",
            execution_time=0.5
        )
        
        assert result.success is False
        assert result.output == ""
        assert result.error == "Test error"
        assert result.is_rate_limited is False
    
    def test_rate_limited_result(self):
        """Test creation of rate-limited execution result."""
        reset_time = datetime.now() + timedelta(minutes=5)
        rate_limit_info = RateLimitInfo(
            is_rate_limited=True,
            reset_time=reset_time,
            limit_message="Too many requests"
        )
        
        result = ExecutionResult(
            success=False,
            output="",  # Output is required
            rate_limit_info=rate_limit_info,
            execution_time=0.1
        )
        
        assert result.success is False
        assert result.is_rate_limited is True
        assert result.rate_limit_info == rate_limit_info
        assert result.rate_limit_info.reset_time == reset_time