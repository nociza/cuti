# Claude Code Configuration

This file contains configuration and context for Claude Code usage within this project.
It is dynamically managed by the cuti orchestration system.

Last updated: 2025-08-12T16:49:03.624379

## Project Overview

This is a production-ready cuti system with advanced agent orchestration capabilities.

## IMPORTANT: Python Package Management

**ALWAYS use `uv` for Python package management in this project.**

### Key Commands:
- **Install dependencies**: `uv sync` or `uv pip install <package>`
- **Add new dependency**: `uv add <package>`
- **Install in development mode**: `uv pip install -e .`
- **Build package**: `uv build`
- **Publish to PyPI**: `uv publish`
- **Install as tool**: `uv tool install cuti`

### For Containers:
- Use `uv pip install --system` when installing in Docker containers
- The devcontainer uses `uv` for all Python operations
- cuti is installed via `uv pip install --system -e .` in development containers

### Never use:
- ❌ `pip install` directly
- ❌ `python -m pip`
- ❌ `pip3`

Always prefer `uv` for faster, more reliable Python package management.

## Active Agents

The following agents are currently active and available for use:

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
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Or install in development mode
uv pip install -e .
```

### Running the Application
```bash
# Using uv run (recommended)
uv run cuti web
uv run cuti cli
uv run cuti agent list

# Or after installation
cuti web
cuti cli
cuti agent list
```

### Container Development
```bash
# Start dev container (uses uv internally)
cuti container

# Inside container, cuti is pre-installed via uv
cuti web
```

### Publishing to PyPI
```bash
# Build the package
uv build

# Publish to PyPI
uv publish

# After publishing, users can install with:
uv tool install cuti
```

## Orchestration Configuration

This file is automatically managed by the cuti orchestration system.
Manual changes will be overwritten when agents are toggled or updated.

To modify agent configuration:
1. Use the web interface at http://localhost:8000/agents
2. Use the CLI: `cuti agent toggle <agent-name>`
3. Modify `.cuti/agents.json` and reload
