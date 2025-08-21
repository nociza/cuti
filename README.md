## Cuti

The one stop solution for all your dev tasks for Claude Code and friends. Queue and route prompts, manage agents, monitor usage, and work through a simple CLI or a small web UI (mobile supported). Local-first; no telemetry.

### Install

```bash
# Install uv if needed (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install cuti
uv tool install cuti

# Verify installation
cuti --help

# Check version
cuti --version  # or cuti -v
```

Requires Python 3.9+. Claude Code CLI is required. Google Gemini is optional and would suppliment the agent orchestration if you have a working google gemini cli.

### Quick start

```bash
# Start the web UI (http://127.0.0.1:8000)
cuti web

# Or use the CLI directly
cuti add "Explore this codebase and summarize key modules"
cuti start
cuti status
```

### What it does

- Multi-agent orchestration (Claude, Gemini) with simple routing
- Command queue with prompt aliases and history
- Hierarchical todo system with master goals and sub-tasks
- Automatic rate limit handling with smart retry after reset
- Web UI (FastAPI) for status, agents, and history
- Real-time usage monitoring via claude-monitor
- Per-project workspace under `.cuti/`

### Dev containers

Run your project in a containerized dev environment with cuti and all tools pre-configured:

```bash
# Start interactive container (works from any directory)
cuti container

# Run a specific command
cuti container "cuti web"
cuti container "python script.py"
```

Features:
- Cuti installed and ready (from PyPI via `uv tool install`)
- Claude CLI installed (note: auth limitations in containers)
- Custom prompt shows `cuti:~/path $`
- Works from any project directory
- Python 3.11, Node.js 20, development tools included

Requires Docker (or Colima on macOS). See `docs/devcontainer.md` for details and Claude authentication notes.

### License

MIT. See `LICENSE`.
