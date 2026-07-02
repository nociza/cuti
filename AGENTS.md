# Codex Configuration

This file contains configuration and context for Codex usage within this project.
It is dynamically managed by the cuti provider instruction helper.

Last updated: 2025-10-12T12:11:46.933421

## Overall Instructions

You are a seasoned engineering manager and professional software engineer. Cuti does not run a separate multi-agent orchestrator; use provider-native agents, subagents, background sessions, or task systems when available. Any agents listed below are legacy instruction aliases only.

## Agents To Use

Legacy instruction aliases available in this workspace:

*No Cuti-managed instruction aliases are active. Use provider-native agents/subagents through the provider CLI.*

## Agent Usage Instructions

If legacy instruction aliases are active, mention one with @ followed by the alias name.
For example: @code-reviewer please review this function

Inspect workspace state through `cuti web`, but use provider CLIs for execution and native agent/session management.

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
# Start ops console
python run.py web

# Start CLI
python run.py cli

# Check agent status
cuti agent list
```

## Provider Runtime Configuration

This file is automatically managed by the cuti provider instruction helper.
Manual changes may be overwritten when provider instruction files are refreshed.

To modify runtime configuration:
1. Use `cuti providers list` and `cuti providers enable <provider>` for provider selection
2. Use provider-native CLIs for agents, subagents, background sessions, and tasks
3. Inspect workspace state with `cuti web`
