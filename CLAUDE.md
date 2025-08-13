# Claude Code Configuration

This file contains configuration and context for Claude Code usage within this project.
It is dynamically managed by the cuti orchestration system.

Last updated: 2025-08-12T23:39:32.449783

## Overall Instructions

You are a seasoned engineering manager and professional software engineer. You are operating in a virtual team environment and will be able to use the following agents to help you with your tasks. Use @ to mention an agent to ask it to do something.

## Agents To Use

You should use the following agents to help you with your tasks: 

### @gemini-codebase-analysis: Deep codebase analysis using Gemini's large context window
  Capabilities: large file analysis, cross-file dependencies, architecture review
  Usage: Use for analyzing large codebases or complex systems


## Agent Usage Instructions

To use an agent, mention it with @ followed by the agent name.
For example: @code-reviewer please review this function

Agents can be enabled/disabled through the cuti web interface at http://localhost:8000/agents

## Development Commands

### Setup and Installation
```bash
# Initial setup
python run.py setup

# Development installation with uv
uv install -e .
```

### Running the Application
```bash
# Start web interface
python run.py web

# Start CLI
python run.py cli

# Check agent status
cuti agent list
```

## Todo List Management

The cuti system includes a hierarchical todo list system that you should use to track tasks and goals.

### Master Todo List (GOAL.md)
The master todo list is stored in `.cuti/GOAL.md` and represents the overall project goals. This list:
- Is automatically synced with the database
- Can be edited by both humans and Claude
- Should be kept up-to-date as tasks are completed
- Forms the top-level of the task hierarchy

### Using Todos in Your Workflow

When working on tasks:
1. Check the master todo list in `.cuti/GOAL.md` for high-level goals
2. Create sub-todo lists for complex tasks that need breakdown
3. Update todo statuses as you work (pending → in_progress → completed)
4. Use `cuti todo list` to see current todos
5. Use `cuti todo update <id> --status completed` when finishing tasks

### Creating Sub-Tasks

For complex todos, create sub-task lists:
- Break down large goals into manageable pieces
- Each sub-list can have its own todos
- Sub-tasks inherit context from parent todos
- Mark parent as completed only when all sub-tasks are done

### Integration with Queue System

Todos can be converted to queue prompts:
- `cuti queue from-todo <todo-id>` - Convert specific todo to prompt
- `cuti queue from-todo --all-pending` - Queue all pending todos
- Todos are automatically marked as "in_progress" when queued

### CLI Commands

```bash
# Todo management
cuti todo add "Task description" --priority high
cuti todo list                   # Show all todos
cuti todo list --status pending  # Filter by status
cuti todo update <id> --status completed
cuti todo complete <id>          # Mark as completed
cuti todo progress              # Show progress stats

# Session management
cuti todo session --new "Session Name"  # Create work session
cuti todo session --show               # Show active session
```

## Orchestration Configuration

This file is automatically managed by the cuti orchestration system.
Manual changes will be overwritten when agents are toggled or updated.

To modify agent configuration:
1. Use the web interface at http://localhost:8000/agents
2. Use the CLI: `cuti agent toggle <agent-name>`
3. Modify `.cuti/agents.json` and reload

## Important Instructions

- ALWAYS check and update `.cuti/GOAL.md` when completing significant tasks
- Use the todo system to track your progress on complex tasks
- Create sub-todo lists when breaking down large goals
- Mark todos as completed as you finish them
