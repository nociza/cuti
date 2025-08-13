# Todo System

Cuti includes a hierarchical todo list system for tracking tasks and goals.

## Architecture

- **Master Todo List**: Stored in `.cuti/GOAL.md`, represents overall project goals
- **Sub-lists**: Break down complex tasks into manageable pieces
- **Sessions**: Group related todo lists for work sessions
- **Database**: SQLite storage with full CRUD operations

## CLI Commands

### Basic Todo Management
```bash
# Add todos
cuti todo add "Task description" --priority high

# List todos
cuti todo list                    # All todos
cuti todo list --status pending   # Filter by status

# Update todos
cuti todo update <id> --status in_progress
cuti todo complete <id>           # Mark as completed

# Show progress
cuti todo progress               # Statistics and completion %
```

### Session Management
```bash
# Create work session
cuti todo session --new "Feature Development"

# Show active session
cuti todo session --show
```

### Queue Integration
```bash
# Convert todo to queue prompt
cuti queue from-todo <todo-id>

# Queue all pending todos
cuti queue from-todo --all-pending
```

## Todo States

- **pending**: Not started
- **in_progress**: Currently working on
- **completed**: Finished
- **blocked**: Waiting on dependencies
- **cancelled**: No longer needed

## Priority Levels

- **critical**: Urgent, must do immediately
- **high**: Important, do soon
- **medium**: Normal priority
- **low**: Do when time permits

## GOAL.md Format

The master todo list is synced with `.cuti/GOAL.md`:

```markdown
# Project Goals

## To Do
- [ ] Pending task 1
- [ ] Pending task 2

## In Progress
- [ ] Task being worked on (in progress)

## Completed
- [x] Completed task 1
- [x] Completed task 2

---
Last updated: 2025-08-13T12:00:00
Total tasks: 5
Completion: 40%
```

## Database Schema

### Tables

1. **todo_items**: Individual tasks
   - id, content, status, priority
   - created_at, updated_at, completed_at
   - created_by, assigned_to, parent_id
   - list_id, metadata

2. **todo_lists**: Todo list containers
   - id, name, description
   - parent_list_id, session_id
   - created_at, updated_at
   - created_by, is_master, metadata

3. **todo_sessions**: Work sessions
   - id, name, master_list_id
   - created_at, updated_at
   - active, metadata

## Claude Integration

Claude Code automatically:
- Checks `.cuti/GOAL.md` for tasks
- Updates todo status when completing work
- Creates sub-tasks for complex goals
- Uses todo context for better task understanding

See `CLAUDE.md` for Claude-specific instructions.

## Best Practices

1. **Break down large tasks**: Create sub-lists for complex goals
2. **Update status regularly**: Mark tasks as in_progress/completed
3. **Use priorities**: Focus on critical/high priority items
4. **Create sessions**: Group related work together
5. **Convert to prompts**: Queue todos for automated processing