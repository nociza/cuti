from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from types import SimpleNamespace

from cuti.services.global_data_manager import GlobalDataManager


def test_import_claude_logs_is_idempotent_for_entries_without_ids(tmp_path, monkeypatch) -> None:
    manager = GlobalDataManager(str(tmp_path / ".cuti"))
    entry = SimpleNamespace(
        timestamp=datetime(2026, 3, 18, 12, 0, 0).isoformat(sep=" "),
        input_tokens=12,
        output_tokens=8,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        model="claude-sonnet",
        cost_usd=0.42,
        message_id=None,
        request_id=None,
        session_id=None,
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "cuti.services.claude_monitor_integration.ClaudeMonitorIntegration.load_usage_data",
        lambda self: [entry, entry],
    )

    first_import = manager.import_claude_logs(str(tmp_path / "logs"))
    second_import = manager.import_claude_logs(str(tmp_path / "logs"))

    with sqlite3.connect(str(manager.db_path)) as conn:
        stored = conn.execute("SELECT COUNT(*) FROM usage_records").fetchone()[0]

    assert first_import == 1
    assert second_import == 0
    assert stored == 1


def test_cleanup_old_data_runs_without_vacuum_transaction_error(tmp_path) -> None:
    manager = GlobalDataManager(str(tmp_path / ".cuti"))
    old_usage_time = (datetime.now() - timedelta(days=30)).isoformat(sep=" ")
    old_message_time = (datetime.now() - timedelta(days=30)).isoformat()

    with sqlite3.connect(str(manager.db_path), timeout=30.0) as conn:
        conn.execute(
            """
            INSERT INTO usage_records (
                timestamp, project_path, input_tokens, output_tokens,
                cache_creation_tokens, cache_read_tokens, total_tokens,
                model, cost, message_id, request_id, session_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                old_usage_time,
                "/tmp/project",
                10,
                5,
                0,
                0,
                15,
                "claude-sonnet",
                0.12,
                "message-1",
                "request-1",
                "session-1",
                "{}",
            ),
        )
        conn.execute(
            """
            INSERT INTO chat_sessions (
                session_id, project_path, start_time, last_activity,
                prompt_count, response_count, total_tokens, git_branch, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "session-1",
                "/tmp/project",
                old_message_time,
                old_message_time,
                1,
                1,
                15,
                "main",
                "{}",
            ),
        )
        conn.execute(
            """
            INSERT INTO chat_messages (
                id, session_id, message_type, content, timestamp,
                parent_uuid, model, input_tokens, output_tokens, cost,
                git_branch, cwd, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "chat-message-1",
                "session-1",
                "user",
                "hello",
                old_message_time,
                None,
                "claude-sonnet",
                10,
                5,
                0.12,
                "main",
                "/tmp/project",
                "{}",
            ),
        )
        conn.commit()

    manager.cleanup_old_data(days=1)

    with sqlite3.connect(str(manager.db_path), timeout=30.0) as conn:
        usage_count = conn.execute("SELECT COUNT(*) FROM usage_records").fetchone()[0]
        message_count = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
        session_count = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]

    assert usage_count == 0
    assert message_count == 0
    assert session_count == 0
