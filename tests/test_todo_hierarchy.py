#!/usr/bin/env python3
"""Test the hierarchical todo system functionality directly."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, '/workspace/src')

from cuti.services.todo_service import TodoService
from cuti.services.claude_todo_sync import ClaudeTodoSync
from cuti.services.goal_parser import GoalParser
from cuti.core.todo_models import TodoItem, TodoList, TodoStatus, TodoPriority

def test_goal_sync():
    """Test syncing GOAL.md with master todo list."""
    print("\n=== Testing GOAL.md Sync ===")
    
    try:
        # Initialize services
        storage_dir = ".cuti"
        todo_service = TodoService(storage_dir)
        goal_parser = GoalParser(Path(storage_dir) / "GOAL.md")
        
        # Check if GOAL.md exists
        goal_file = Path("GOAL.md")
        if not goal_file.exists():
            print("❌ GOAL.md not found in workspace")
            return False
        
        print(f"✓ Found GOAL.md at {goal_file.absolute()}")
        
        # Parse GOAL.md
        master_list = goal_parser.parse_goal_file()
        print(f"✓ Parsed {len(master_list.todos)} todos from GOAL.md")
        
        # Sync with database
        master_list = goal_parser.sync_with_database(todo_service, master_list)
        print(f"✓ Synced master list with database (ID: {master_list.id})")
        
        # Display some todos
        print("\nMaster Goals:")
        for i, todo in enumerate(master_list.todos[:5], 1):
            status_char = "✓" if todo.status == TodoStatus.COMPLETED else "○"
            print(f"  {i}. [{status_char}] {todo.content[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_claude_sync():
    """Test Claude todo capture functionality."""
    print("\n=== Testing Claude Todo Capture ===")
    
    try:
        # Initialize Claude sync
        claude_sync = ClaudeTodoSync(".cuti")
        print("✓ Initialized ClaudeTodoSync")
        
        # Simulate Claude TodoWrite data
        claude_todos = [
            {
                "content": "Implement user authentication",
                "status": "in_progress",
                "activeForm": "Implementing user authentication"
            },
            {
                "content": "Write unit tests for auth module",
                "status": "pending",
                "activeForm": "Writing unit tests for auth module"
            },
            {
                "content": "Setup CI/CD pipeline",
                "status": "pending",
                "activeForm": "Setting up CI/CD pipeline"
            }
        ]
        
        # Capture todos
        sub_list = claude_sync.capture_todo_write(claude_todos, "test_agent")
        print(f"✓ Captured {len(sub_list.todos)} todos from Claude")
        print(f"✓ Created sub-list: {sub_list.name} (ID: {sub_list.id})")
        
        # Check if todos are linked to master goals
        linked_count = sum(1 for t in sub_list.todos if 'linked_goal_id' in t.metadata)
        print(f"✓ Linked {linked_count} todos to master goals")
        
        # Display captured todos
        print("\nCaptured Todos:")
        for i, todo in enumerate(sub_list.todos, 1):
            print(f"  {i}. [{todo.status.value}] {todo.content}")
            if 'linked_goal_id' in todo.metadata:
                print(f"     → Linked to: {todo.metadata.get('goal_content', 'N/A')[:40]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hierarchical_structure():
    """Test the hierarchical todo structure."""
    print("\n=== Testing Hierarchical Structure ===")
    
    try:
        todo_service = TodoService(".cuti")
        
        # Get master list
        master_list = todo_service.get_master_list()
        if not master_list:
            print("❌ No master list found")
            return False
        
        print(f"✓ Master List: {master_list.name}")
        print(f"  - Total todos: {len(master_list.todos)}")
        print(f"  - Completed: {sum(1 for t in master_list.todos if t.status == TodoStatus.COMPLETED)}")
        print(f"  - Pending: {sum(1 for t in master_list.todos if t.status == TodoStatus.PENDING)}")
        
        # Get active sessions
        sessions = todo_service.get_active_sessions()
        print(f"\n✓ Active Sessions: {len(sessions)}")
        
        for session in sessions:
            print(f"\n  Session: {session.name}")
            print(f"  - Sub-lists: {len(session.sub_lists)}")
            print(f"  - Progress: {session.get_overall_progress()}")
            
            # Show sub-lists
            for sub_list in session.sub_lists[:3]:
                print(f"\n    Sub-list: {sub_list.name}")
                print(f"    - Todos: {len(sub_list.todos)}")
                print(f"    - Created by: {sub_list.created_by}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_todo_operations():
    """Test basic todo CRUD operations."""
    print("\n=== Testing Todo Operations ===")
    
    try:
        todo_service = TodoService(".cuti")
        
        # Create a test todo
        test_todo = TodoItem(
            content="Test todo from direct API",
            priority=TodoPriority.HIGH,
            created_by="test_script"
        )
        
        # Get master list and add todo
        master_list = todo_service.get_master_list()
        if not master_list:
            print("Creating new master list...")
            master_list = TodoList(
                name="Master Goals",
                description="Test master list",
                is_master=True,
                created_by="test_script"
            )
            todo_service.save_list(master_list)
        
        master_list.add_todo(test_todo)
        todo_service.save_list(master_list)
        print(f"✓ Added test todo (ID: {test_todo.id})")
        
        # Update todo status
        success = todo_service.update_todo(
            test_todo.id, 
            {"status": TodoStatus.IN_PROGRESS}
        )
        print(f"✓ Updated todo status: {success}")
        
        # Get todo back
        retrieved = todo_service.get_todo(test_todo.id)
        if retrieved:
            print(f"✓ Retrieved todo: {retrieved.content}")
            print(f"  Status: {retrieved.status.value}")
        
        # List all todos
        all_todos = todo_service.get_all_todos(limit=5)
        print(f"\n✓ Total todos in database: {len(all_todos)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Hierarchical Todo System")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("GOAL.md Sync", test_goal_sync()))
    results.append(("Claude Todo Capture", test_claude_sync()))
    results.append(("Hierarchical Structure", test_hierarchical_structure()))
    results.append(("Todo Operations", test_todo_operations()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:25} {status}")
    
    total_passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)