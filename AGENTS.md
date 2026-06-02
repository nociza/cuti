# AGENTS.md — guide for coding agents working on cuti

cuti is a Python CLI + small FastAPI ops console. Its headline feature is the
**instant, containerized Claude Code dev environment** (`cuti container`), plus tooling
to manage agent-CLI providers, Claude accounts, session history, and usage analytics.

## Where things live

- `src/cuti/cli/` — Typer CLI (`cuti.cli.app:app`); one module per command group under
  `cli/commands/`.
- `src/cuti/services/` — business logic (`devcontainer.py`, `providers.py`,
  `provider_host.py`, `claude_account_manager.py`, usage/monitoring, history).
- `src/cuti/web/` — read-only ops console.
- `tests/` — pytest suite.

## Build, test, lint

```bash
uv pip install -e ".[dev]"
pytest
ruff check src tests
black src tests
```

## Conventions for changes

- Keep cuti **additive** to Claude Code; don't re-implement native features.
- Preserve **secure defaults**: the host Docker socket and inactive-account
  credentials must stay opt-in / shielded.
- Match the surrounding code style; reserve `print()`/`rich` for user-facing CLI
  output and route diagnostics through `cuti.utils.logger`.
- Update `CHANGELOG.md` for user-visible changes.

Once installed, the entry points are `cuti` (the full CLI, including `cuti openclaw`)
and `cuti-web` / `python -m cuti` (the ops console). `run.py` is only a dev bootstrap shim.
