"""
Claude Logs Reader - Reads prompt history and todos from Claude's ground truth logs.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib


class ClaudeLogsReader:
    """Reads and parses Claude's project logs and todos from ~/.claude/."""
    
    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the Claude logs reader."""
        self.working_dir = Path(working_directory) if working_directory else Path.cwd()
        self.claude_dir = Path.home() / ".claude"
        self.project_name = self._get_project_name()
        self.project_logs_dir = self.claude_dir / "projects" / self.project_name
        self.todos_dir = self.claude_dir / "todos"
        
    def _get_project_name(self) -> str:
        """Convert working directory path to Claude's project name format."""
        # Claude uses hyphen-separated absolute path as project name
        # Spaces are also replaced with hyphens
        return str(self.working_dir).replace("/", "-").replace(" ", "-")
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current active session ID from the most recent log file."""
        if not self.project_logs_dir.exists():
            return None
            
        # Get the most recently modified log file
        log_files = list(self.project_logs_dir.glob("*.jsonl"))
        if not log_files:
            return None
            
        latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
        return latest_log.stem  # Returns the UUID without .jsonl extension
    
    def get_prompt_history(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get prompt history from Claude logs.
        
        Args:
            session_id: Specific session ID to read from, or None for current session
            limit: Maximum number of prompts to return
            
        Returns:
            List of prompt entries with metadata
        """
        if session_id is None:
            session_id = self.get_current_session_id()
            
        if not session_id:
            return []
            
        log_file = self.project_logs_dir / f"{session_id}.jsonl"
        if not log_file.exists():
            return []
            
        prompts = []
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        
                        # Only include actual user prompts (not tool results)
                        if entry.get('type') == 'user' and entry.get('message'):
                            message = entry.get('message', {})
                            # Skip tool result messages
                            if message.get('role') == 'user' and isinstance(message.get('content'), str):
                                prompt_data = {
                                    'id': entry.get('uuid'),
                                    'content': message.get('content', ''),
                                    'timestamp': entry.get('timestamp'),
                                    'session_id': session_id,
                                    'cwd': entry.get('cwd'),
                                    'git_branch': entry.get('gitBranch'),
                                    'parent_uuid': entry.get('parentUuid'),
                                    'type': 'user'
                                }
                                prompts.append(prompt_data)
                            
                        # Also capture assistant responses for context
                        elif entry.get('type') == 'assistant':
                            message = entry.get('message', {})
                            content_text = ""
                            
                            # Extract text from content array
                            if isinstance(message.get('content'), list):
                                for content_item in message['content']:
                                    if content_item.get('type') == 'text':
                                        content_text = content_item.get('text', '')
                                        break
                            
                            if content_text:
                                response_data = {
                                    'id': entry.get('uuid'),
                                    'content': content_text[:500],  # Truncate long responses
                                    'timestamp': entry.get('timestamp'),
                                    'session_id': session_id,
                                    'parent_uuid': entry.get('parentUuid'),
                                    'type': 'assistant',
                                    'model': message.get('model'),
                                    'usage': message.get('usage', {})
                                }
                                prompts.append(response_data)
                                
                    except json.JSONDecodeError:
                        continue
                        
            # Sort by timestamp and limit
            prompts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return prompts[:limit]
            
        except Exception as e:
            print(f"Error reading log file: {e}")
            return []
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions for the current project."""
        if not self.project_logs_dir.exists():
            return []
            
        sessions = []
        for log_file in self.project_logs_dir.glob("*.jsonl"):
            session_id = log_file.stem
            
            # Get first and last timestamp from the file
            first_timestamp = None
            last_timestamp = None
            prompt_count = 0
            
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('type') == 'user':
                                prompt_count += 1
                                if not first_timestamp:
                                    first_timestamp = entry.get('timestamp')
                                last_timestamp = entry.get('timestamp')
                        except:
                            continue
                            
                if first_timestamp:
                    sessions.append({
                        'session_id': session_id,
                        'start_time': first_timestamp,
                        'last_activity': last_timestamp,
                        'prompt_count': prompt_count,
                        'file_size': log_file.stat().st_size
                    })
            except:
                continue
                
        # Sort by last activity
        sessions.sort(key=lambda x: x.get('last_activity', ''), reverse=True)
        return sessions
    
    def get_todos(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get todos from Claude's todo files.
        
        Args:
            session_id: Specific session ID to get todos for, or None for current session
            
        Returns:
            List of todo items
        """
        if session_id is None:
            session_id = self.get_current_session_id()
            
        if not session_id:
            return []
            
        # Claude stores todos with pattern: {session-id}-agent-{session-id}.json
        todo_file = self.todos_dir / f"{session_id}-agent-{session_id}.json"
        
        if not todo_file.exists():
            return []
            
        try:
            with open(todo_file, 'r') as f:
                todos = json.load(f)
                # Add session metadata to each todo
                for todo in todos:
                    todo['session_id'] = session_id
                return todos
        except Exception as e:
            print(f"Error reading todo file: {e}")
            return []
    
    def get_conversation_context(self, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the full conversation context (user prompts + assistant responses).
        
        Args:
            session_id: Session ID to read from
            limit: Maximum number of exchanges to return
            
        Returns:
            List of conversation entries in chronological order
        """
        history = self.get_prompt_history(session_id, limit * 2)  # Get both user and assistant
        
        # Group by parent-child relationship for proper conversation flow
        conversation = []
        user_prompts = {}
        assistant_responses = {}
        
        for entry in history:
            if entry['type'] == 'user':
                user_prompts[entry['id']] = entry
            elif entry['type'] == 'assistant':
                assistant_responses[entry.get('parent_uuid')] = entry
        
        # Build conversation pairs
        for prompt_id, prompt in user_prompts.items():
            exchange = {
                'user': prompt,
                'assistant': assistant_responses.get(prompt_id)
            }
            conversation.append(exchange)
        
        # Sort by timestamp and limit
        conversation.sort(
            key=lambda x: x['user'].get('timestamp', ''),
            reverse=True
        )
        
        return conversation[:limit]
    
    def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the current or specified session.
        
        Returns:
            Dictionary with session statistics
        """
        if session_id is None:
            session_id = self.get_current_session_id()
            
        if not session_id:
            return {}
            
        history = self.get_prompt_history(session_id, limit=1000)
        todos = self.get_todos(session_id)
        
        user_prompts = [h for h in history if h['type'] == 'user']
        assistant_responses = [h for h in history if h['type'] == 'assistant']
        
        total_tokens = 0
        for response in assistant_responses:
            if 'usage' in response:
                usage = response['usage']
                total_tokens += usage.get('input_tokens', 0)
                total_tokens += usage.get('output_tokens', 0)
        
        return {
            'session_id': session_id,
            'total_prompts': len(user_prompts),
            'total_responses': len(assistant_responses),
            'total_tokens': total_tokens,
            'todos_count': len(todos),
            'todos_completed': len([t for t in todos if t.get('status') == 'completed']),
            'todos_pending': len([t for t in todos if t.get('status') == 'pending']),
            'todos_in_progress': len([t for t in todos if t.get('status') == 'in_progress'])
        }