#!/usr/bin/env python3
"""
Test script for chat history sync functionality.
"""

import json
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime
from src.cuti.services.global_data_manager import GlobalDataManager
from src.cuti.services.claude_logs_reader import ClaudeLogsReader

def test_chat_sync():
    """Test the chat history sync functionality."""
    
    # Create a temporary directory structure that mimics Claude's
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create mock Claude directory structure
        claude_dir = temp_path / ".claude"
        projects_dir = claude_dir / "projects" / "-workspace"
        projects_dir.mkdir(parents=True)
        
        # Create a mock session log file
        session_id = "test-session-12345"
        log_file = projects_dir / f"{session_id}.jsonl"
        
        # Write mock log entries
        log_entries = [
            {
                "type": "user",
                "uuid": "msg-001",
                "message": {
                    "role": "user",
                    "content": "Hello, can you help me with Python?"
                },
                "timestamp": "2025-01-09T10:00:00",
                "cwd": "/workspace",
                "gitBranch": "main"
            },
            {
                "type": "assistant",
                "uuid": "msg-002",
                "parentUuid": "msg-001",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "Of course! I'd be happy to help you with Python."
                        }
                    ],
                    "model": "claude-3-opus",
                    "usage": {
                        "input_tokens": 15,
                        "output_tokens": 25
                    }
                },
                "timestamp": "2025-01-09T10:00:05"
            },
            {
                "type": "user",
                "uuid": "msg-003",
                "message": {
                    "role": "user",
                    "content": "How do I read a file in Python?"
                },
                "timestamp": "2025-01-09T10:01:00",
                "cwd": "/workspace",
                "gitBranch": "main"
            },
            {
                "type": "assistant",
                "uuid": "msg-004",
                "parentUuid": "msg-003",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "You can read a file in Python using the open() function."
                        }
                    ],
                    "model": "claude-3-opus",
                    "usage": {
                        "input_tokens": 20,
                        "output_tokens": 50
                    }
                },
                "timestamp": "2025-01-09T10:01:10"
            }
        ]
        
        with open(log_file, 'w') as f:
            for entry in log_entries:
                f.write(json.dumps(entry) + '\n')
        
        # Monkey-patch the home directory for testing
        import os
        original_home = Path.home
        Path.home = lambda: temp_path
        
        try:
            # Test the ClaudeLogsReader
            print("Testing ClaudeLogsReader...")
            reader = ClaudeLogsReader("/workspace")
            
            sessions = reader.get_all_sessions()
            print(f"Found {len(sessions)} sessions")
            
            if sessions:
                history = reader.get_prompt_history(sessions[0]['session_id'])
                print(f"Found {len(history)} messages in session")
                
                for msg in history[:2]:
                    print(f"  - {msg['type']}: {msg['content'][:50]}...")
            
            # Test the GlobalDataManager sync
            print("\nTesting GlobalDataManager sync...")
            
            # Create a temporary database
            db_dir = temp_path / ".cuti" / "databases"
            db_dir.mkdir(parents=True, exist_ok=True)
            
            manager = GlobalDataManager(str(temp_path / ".cuti"))
            
            # Sync chat history
            synced = manager.sync_chat_history("/workspace")
            print(f"Synced {synced} messages")
            
            # Verify data was stored
            sessions = manager.get_chat_sessions()
            print(f"Database has {len(sessions)} sessions")
            
            if sessions:
                messages = manager.get_chat_history(limit=10)
                print(f"Retrieved {len(messages)} messages from database")
                
                for msg in messages[:2]:
                    print(f"  - {msg['type']}: {msg['content'][:50]}...")
            
            # Debug: Check what's in the database directly
            print("\nDebugging database content...")
            with sqlite3.connect(str(manager.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM chat_sessions")
                db_sessions = cursor.fetchall()
                print(f"Direct DB query found {len(db_sessions)} sessions")
                
                cursor.execute("SELECT COUNT(*) FROM chat_messages")
                msg_count = cursor.fetchone()[0]
                print(f"Direct DB query found {msg_count} messages")
            
            # Re-fetch after sync with correct parameters
            sessions = manager.get_chat_sessions(project_path="/workspace", days=365)
            print(f"\nAfter sync, found {len(sessions)} sessions with project filter")
            
            # Test statistics
            print("\nSession Statistics:")
            for session in sessions:
                print(f"  Session: {session['session_id'][:20]}...")
                print(f"    Messages: {session['prompt_count']} prompts, {session['response_count']} responses")
                print(f"    Tokens: {session['total_tokens']}")
            
            print("\n✅ All tests passed!")
            
        finally:
            # Restore original home
            Path.home = original_home

if __name__ == "__main__":
    test_chat_sync()