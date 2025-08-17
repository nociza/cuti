# Claude Code Configuration

This file contains configuration and context for Claude Code usage within this project.
It is dynamically managed by the cuti orchestration system.

Last updated: 2025-08-17T05:16:33.173741

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

## Orchestration Configuration

This file is automatically managed by the cuti orchestration system.
Manual changes will be overwritten when agents are toggled or updated.

To modify agent configuration:
1. Use the web interface at http://localhost:8000/agents
2. Use the CLI: `cuti agent toggle <agent-name>`
3. Modify `.cuti/agents.json` and reload
