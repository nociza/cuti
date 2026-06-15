from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cuti.core.models import ExecutionResult, PromptStatus, QueuedPrompt, QueueState
from cuti.core.queue import QueueProcessor
from cuti.core.storage import PromptStorage
from cuti.services.queue_service import QueueManager


def test_queue_manager_passive_operations_do_not_require_claude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_constructed(*args, **kwargs):
        raise RuntimeError("Claude should only be required for execution")

    monkeypatch.setattr(
        "cuti.services.queue_service.ClaudeCodeInterface", fail_if_constructed
    )

    manager = QueueManager(storage_dir=str(tmp_path))
    prompt = QueuedPrompt(id="passive", content="Inspect passive queue state")

    assert manager.add_prompt(prompt) is True
    assert manager.get_status().get_prompt("passive") is not None
    assert manager.remove_prompt("passive") is True

    with pytest.raises(RuntimeError, match="only be required for execution"):
        manager.start()


def test_queue_manager_reloads_storage_before_mutations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cuti.services.queue_service.ClaudeCodeInterface",
        lambda *args, **kwargs: pytest.fail("passive operations should stay passive"),
    )

    first_manager = QueueManager(storage_dir=str(tmp_path))
    second_manager = QueueManager(storage_dir=str(tmp_path))

    assert first_manager.add_prompt(QueuedPrompt(id="one", content="First")) is True
    assert second_manager.add_prompt(QueuedPrompt(id="two", content="Second")) is True
    assert first_manager.add_prompt(QueuedPrompt(id="three", content="Third")) is True

    prompt_ids = {prompt.id for prompt in PromptStorage(str(tmp_path)).load_queue_state().prompts}
    assert prompt_ids == {"one", "two", "three"}


def test_storage_round_trips_rate_limit_metadata_and_execution_log(
    tmp_path: Path,
) -> None:
    storage = PromptStorage(str(tmp_path))
    now = datetime.now().replace(microsecond=0)
    reset_time = now + timedelta(minutes=10)
    prompt = QueuedPrompt(
        id="rate1",
        content="Continue this work after the reset",
        status=PromptStatus.RATE_LIMITED,
        retry_count=2,
        max_retries=5,
        last_executed=now,
        rate_limited_at=now,
        reset_time=reset_time,
        execution_log="[2026-06-14 12:00:00] RATE LIMITED\n",
    )

    assert storage.save_queue_state(QueueState(prompts=[prompt])) is True

    loaded_prompt = storage.load_queue_state().get_prompt("rate1")

    assert loaded_prompt is not None
    assert loaded_prompt.status == PromptStatus.RATE_LIMITED
    assert loaded_prompt.retry_count == 2
    assert loaded_prompt.max_retries == 5
    assert loaded_prompt.last_executed == now
    assert loaded_prompt.rate_limited_at == now
    assert loaded_prompt.reset_time == reset_time
    assert loaded_prompt.content == "Continue this work after the reset"
    assert "RATE LIMITED" in loaded_prompt.execution_log
    assert "## Execution Log" not in loaded_prompt.content


def test_storage_removes_stale_status_files_when_prompt_returns_to_queue(
    tmp_path: Path,
) -> None:
    storage = PromptStorage(str(tmp_path))
    prompt = QueuedPrompt(
        id="stale1",
        content="Retry after reset",
        status=PromptStatus.RATE_LIMITED,
        reset_time=datetime.now() - timedelta(minutes=1),
        retry_count=1,
    )

    assert storage.save_queue_state(QueueState(prompts=[prompt])) is True
    assert list(storage.queue_dir.glob("stale1*.rate-limited.md"))

    prompt.status = PromptStatus.QUEUED
    assert storage.save_queue_state(QueueState(prompts=[prompt])) is True

    prompt_files = list(storage.queue_dir.glob("stale1*.md"))
    assert len(prompt_files) == 1
    assert prompt_files[0].name.endswith(".md")
    assert not prompt_files[0].name.endswith(".rate-limited.md")
    assert storage.load_queue_state().get_prompt("stale1").status == PromptStatus.QUEUED


def test_rate_limit_continue_retry_does_not_overwrite_persisted_prompt(
    tmp_path: Path,
) -> None:
    storage = PromptStorage(str(tmp_path))
    reset_time = datetime.now() - timedelta(minutes=1)
    prompt = QueuedPrompt(
        id="retry1",
        content="Original task content",
        status=PromptStatus.RATE_LIMITED,
        retry_count=1,
        rate_limited_at=reset_time,
        reset_time=reset_time,
    )
    assert storage.save_queue_state(QueueState(prompts=[prompt])) is True

    class _Interface:
        seen_content = ""

        def test_connection(self):
            return True, "ok"

        def execute_prompt(self, execution_prompt):
            self.seen_content = execution_prompt.content
            persisted_prompt = storage.load_queue_state().get_prompt("retry1")
            assert persisted_prompt is not None
            assert persisted_prompt.content == "Original task content"
            return ExecutionResult(success=True, output="continued")

    interface = _Interface()
    processor = QueueProcessor(storage, interface, check_interval=1)
    processor.state = storage.load_queue_state()

    processor._process_queue_iteration()

    completed_file = next(storage.completed_dir.glob("retry1*.md"))
    completed_prompt = storage.parser.parse_prompt_file(completed_file)
    assert interface.seen_content == "continue"
    assert completed_prompt is not None
    assert completed_prompt.content == "Original task content"
