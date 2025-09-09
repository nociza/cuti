"""
Goal file parser and synchronizer for master todo list management.
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from ..core.todo_models import TodoItem, TodoList, TodoStatus, TodoPriority


class GoalParser:
    """Parse and sync GOAL.md with master todo list."""
    
    def __init__(self, goal_file_path: Path = None):
        self.goal_file = goal_file_path or Path("GOAL.md")
        
    def parse_goal_file(self) -> TodoList:
        """Parse GOAL.md into a master TodoList."""
        if not self.goal_file.exists():
            return self._create_default_master_list()
        
        content = self.goal_file.read_text()
        master_list = TodoList(
            name="Master Goals",
            description="Project goals from GOAL.md",
            is_master=True,
            created_by="system",
            metadata={"source": "GOAL.md", "version": self._extract_version(content)}
        )
        
        # Parse the markdown structure
        sections = self._parse_sections(content)
        
        # Extract todos from each section
        for section_name, section_content in sections.items():
            if "goals" in section_name.lower() or "objective" in section_name.lower():
                todos = self._extract_todos(section_content, section_name)
                for todo in todos:
                    master_list.add_todo(todo)
        
        return master_list
    
    def _parse_sections(self, content: str) -> Dict[str, str]:
        """Parse markdown into sections."""
        sections = {}
        current_section = "root"
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('## '):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                # Start new section
                current_section = line[3:].strip()
                current_content = []
            elif line.startswith('### '):
                # Sub-section, add to current
                current_content.append(line)
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_todos(self, content: str, section: str) -> List[TodoItem]:
        """Extract todo items from markdown content."""
        todos = []
        current_category = section
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Update category from sub-headers
            if line.startswith('### '):
                current_category = line[4:].strip()
                continue
            
            # Parse todo items
            if line.startswith('- [ ] '):
                # Pending todo
                todo_content = line[6:].strip()
                todo = TodoItem(
                    content=todo_content,
                    status=TodoStatus.PENDING,
                    priority=self._infer_priority(todo_content),
                    created_by="goal_file",
                    metadata={
                        "category": current_category,
                        "section": section,
                        "original_format": "markdown_checkbox"
                    }
                )
                todos.append(todo)
                
            elif line.startswith('- [x] '):
                # Completed todo
                todo_content = line[6:].strip()
                todo = TodoItem(
                    content=todo_content,
                    status=TodoStatus.COMPLETED,
                    priority=self._infer_priority(todo_content),
                    created_by="goal_file",
                    completed_at=datetime.now(),  # Approximate
                    metadata={
                        "category": current_category,
                        "section": section,
                        "original_format": "markdown_checkbox"
                    }
                )
                todos.append(todo)
                
            elif line.startswith('- '):
                # Regular list item (treat as todo)
                todo_content = line[2:].strip()
                if todo_content and not todo_content.startswith('['):
                    todo = TodoItem(
                        content=todo_content,
                        status=TodoStatus.PENDING,
                        priority=self._infer_priority(todo_content),
                        created_by="goal_file",
                        metadata={
                            "category": current_category,
                            "section": section,
                            "original_format": "markdown_list"
                        }
                    )
                    todos.append(todo)
        
        return todos
    
    def _infer_priority(self, content: str) -> TodoPriority:
        """Infer priority from todo content."""
        content_lower = content.lower()
        
        # Check for priority indicators
        if any(word in content_lower for word in ['critical', 'urgent', 'asap', 'immediately']):
            return TodoPriority.CRITICAL
        elif any(word in content_lower for word in ['important', 'high', 'core', 'essential']):
            return TodoPriority.HIGH
        elif any(word in content_lower for word in ['low', 'optional', 'nice-to-have']):
            return TodoPriority.LOW
        else:
            return TodoPriority.MEDIUM
    
    def _extract_version(self, content: str) -> str:
        """Extract version from GOAL.md if present."""
        version_match = re.search(r'\*Version:\s*([^\*\n]+)\*', content)
        if version_match:
            return version_match.group(1).strip()
        return "1.0.0"
    
    def _create_default_master_list(self) -> TodoList:
        """Create a default master list if GOAL.md doesn't exist."""
        return TodoList(
            name="Master Goals",
            description="Default project goals (GOAL.md not found)",
            is_master=True,
            created_by="system",
            todos=[
                TodoItem(
                    content="Create GOAL.md with project objectives",
                    status=TodoStatus.PENDING,
                    priority=TodoPriority.HIGH,
                    created_by="system"
                ),
                TodoItem(
                    content="Define success criteria",
                    status=TodoStatus.PENDING,
                    priority=TodoPriority.MEDIUM,
                    created_by="system"
                ),
                TodoItem(
                    content="Set up development environment",
                    status=TodoStatus.PENDING,
                    priority=TodoPriority.HIGH,
                    created_by="system"
                )
            ]
        )
    
    def sync_with_database(self, todo_service, master_list: TodoList) -> TodoList:
        """Sync parsed goals with database, preserving existing data."""
        # Get existing master list from database
        db_master = todo_service.get_master_list()
        
        if not db_master:
            # First time, save the parsed list
            todo_service.save_list(master_list)
            return master_list
        
        # Merge: Add new todos, update existing ones
        existing_contents = {todo.content: todo for todo in db_master.todos}
        
        for parsed_todo in master_list.todos:
            if parsed_todo.content in existing_contents:
                # Update status if changed in GOAL.md
                existing = existing_contents[parsed_todo.content]
                if existing.status != parsed_todo.status:
                    existing.status = parsed_todo.status
                    if parsed_todo.status == TodoStatus.COMPLETED:
                        existing.completed_at = datetime.now()
            else:
                # New todo from GOAL.md
                db_master.add_todo(parsed_todo)
        
        # Save updated master list
        todo_service.save_list(db_master)
        return db_master
    
    def write_goal_file(self, master_list: TodoList) -> None:
        """Write master list back to GOAL.md format."""
        lines = ["# Project Goals - CUTI Enhancement", ""]
        
        # Group todos by category
        categories = {}
        for todo in master_list.todos:
            category = todo.metadata.get('category', 'General')
            if category not in categories:
                categories[category] = []
            categories[category].append(todo)
        
        # Write each category
        for category, todos in categories.items():
            lines.append(f"## {category}")
            lines.append("")
            
            # Write todos
            for todo in todos:
                if todo.status == TodoStatus.COMPLETED:
                    lines.append(f"- [x] {todo.content}")
                else:
                    lines.append(f"- [ ] {todo.content}")
            lines.append("")
        
        # Add metadata
        lines.append("---")
        lines.append(f"*Last Updated: {datetime.now().isoformat()}*")
        lines.append(f"*Version: {master_list.metadata.get('version', '1.0.0')}*")
        
        self.goal_file.write_text('\n'.join(lines))