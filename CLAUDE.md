# cuti — Claude Code project guide

cuti is a Python CLI + small FastAPI ops console whose headline feature is the
**instant, containerized Claude Code dev environment** (`cuti container`), plus tooling
to manage agent-CLI providers, Claude accounts, session history, and usage analytics.

## Architecture

- `src/cuti/cli/` — the Typer CLI (`cuti.cli.app:app`). One module per command group
  under `cli/commands/` (container, devcontainer, providers, claude_account, openclaw,
  history, sync, tools, settings, favorites).
- `src/cuti/services/` — business logic. Notable: `devcontainer.py` (the heart of
  `cuti container`), `providers.py` / `provider_host.py` (provider management),
  `claude_account_manager.py` (account/API-key switching), `claude_monitor_integration.py`
  + `usage_sync_service.py` (usage analytics), `claude_history.py` / `claude_logs_reader.py`.
- `src/cuti/web/` — the read-only ops console (`cuti web`): one page + the
  `/api/ops/summary` endpoint.
- `src/cuti/utils/` — shared helpers and constants.

## Development

```bash
uv pip install -e ".[dev]"   # editable install with dev tools
pytest                       # run the test suite
ruff check src tests         # lint
black src tests              # format
```

`run.py` is only a developer bootstrap shim. Once installed, use the console scripts:
`cuti` (full CLI, including `cuti openclaw`) and `cuti-web` / `python -m cuti` (ops console).

## Conventions

- Keep cuti **additive** to Claude Code — integrate with native features (todos,
  subagents, resume) rather than re-implementing them.
- **Secure defaults**: never mount the host Docker socket or expose inactive-account
  credentials unless the user explicitly opts in.
- Reserve `print()` / `rich` for intentional user-facing CLI output; route diagnostics
  through `cuti.utils.logger`.
