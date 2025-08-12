## Cuti

The one stop solution for all your dev tasks for Claude Code and friends. Queue and route prompts, manage agents, monitor usage, and work through a simple CLI or a small web UI (mobile supported). Local-first; no telemetry.

### Install

```bash
# Install uv if needed (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install cuti
uv tool install cuti

# Verify
cuti --help
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
- Web UI (FastAPI) for status, agents, and history
- Real-time usage monitoring via claude-monitor
- Per-project workspace under `.cuti/`

### Dev containers

Dev container support is under development. Early preview:

```bash
cuti container --init
```

Requires Docker (or Colima on macOS). Details and troubleshooting live in `docs/devcontainer.md`.

### License

MIT. See `LICENSE`.
