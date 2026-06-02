# cuti — an instant, containerized Claude Code dev environment

<div align="center">

[![PyPI Version](https://img.shields.io/pypi/v/cuti?color=blue&label=PyPI)](https://pypi.org/project/cuti/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cuti)](https://pypi.org/project/cuti/)
[![License](https://img.shields.io/pypi/l/cuti)](https://github.com/nociza/cuti/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/cuti?color=green&label=Downloads%2FMonth)](https://pypi.org/project/cuti/)

**One command for a ready-to-use, isolated Claude Code workspace in Docker — plus tooling to manage agent-CLI providers, Claude accounts, history, and usage.**

[PyPI](https://pypi.org/project/cuti/) • [Documentation](https://github.com/nociza/cuti/tree/main/docs) • [GitHub](https://github.com/nociza/cuti)

</div>

## Quick start

```bash
# Install the CLI
uv tool install cuti          # or: pipx install cuti

# Launch a containerized Claude Code workspace for the current directory
cuti container
```

That's it. `cuti container` drops you into an isolated Docker environment with:

- ✅ **Claude Code CLI** pre-installed and authenticated (auth persists across runs)
- ✅ **Your current directory** auto-mounted at `/workspace`
- ✅ **Python 3.11**, **Node.js 20**, and the usual dev tooling
- ✅ The **newest Claude CLI** on each run, without a rebuild

> **Prerequisite:** Docker (or Colima on macOS). If Docker isn't running, cuti will offer to start Colima for you on macOS.

## Why cuti?

Claude Code is great, but running it directly puts an autonomous agent on your host
with your real credentials. cuti gives every project a clean, reproducible container,
keeps provider/account setup out of your shell, and adds the operational glue
(provider management, account switching, history, usage analytics) around it.

## Commands

```bash
cuti container               # launch the containerized Claude Code workspace (the headline)
cuti container --openclaw    # launch in OpenClaw mode instead
cuti container --docker-socket  # opt in to Docker-in-Docker (see Security below)

cuti containers status       # inspect / manage running containers
cuti providers list          # manage agent-CLI providers (claude, codex, opencode, openclaw, hermes)
cuti claude list             # switch between multiple Claude accounts / API keys
cuti history list            # browse and resume past Claude Code sessions
cuti sync now                # sync local Claude usage/cost analytics
cuti web                     # read-only ops console (provider readiness, sessions, drift)
```

Run `cuti --help` to see everything, grouped by area.

## Agent providers

Claude Code mode is the default. Other agent CLIs (Codex, OpenCode, OpenClaw, Hermes)
are opt-in providers:

```bash
cuti providers list
cuti providers doctor
cuti providers enable codex
cuti providers auth claude --login
cuti providers update codex
```

cuti wires up each enabled provider's auth, config mounts, persistent CLI runtime,
and standard instruction files (`CLAUDE.md`, `AGENTS.md`, `SOUL.md`, `TOOLS.md`, …)
inside the container.

### OpenClaw

OpenClaw is a separate container mode. Drive it with `cuti container --openclaw` or the
`cuti openclaw` subcommand:

```bash
cuti openclaw onboard
cuti openclaw up
cuti openclaw run <command> ...   # forward any OpenClaw command into the container
```

## Security

cuti runs the agent inside a container, but a few defaults are worth understanding:

- **Docker socket is *not* mounted by default.** Mounting the host Docker socket is
  root-equivalent on the host, so it's opt-in via `cuti container --docker-socket`.
  Only enable it when you trust the workload and explicitly need Docker-in-Docker.
- **Only the active Claude account's credentials are exposed** to the container.
  Saved (inactive) accounts under `~/.cuti/claude-accounts` are shadowed inside the
  container so an agent can't read other accounts' tokens.
- **The ops console (`cuti web`) is read-only** and binds to `127.0.0.1` by default.

## Documentation

| Guide | Description |
|-------|-------------|
| [Container setup](docs/devcontainer.md) | Container runtime, provider selection, mounts, and auth |
| [Claude authentication](docs/claude-container-auth.md) | Anthropic API & Claude CLI setup |
| [Account switching](docs/claude-account-switching.md) | Manage multiple Claude accounts |
| [API keys](docs/claude-api-keys.md) | Anthropic & AWS Bedrock API key management |
| [Chat history](docs/claude-history.md) | Inspect & resume Claude Code sessions |
| [CLI tools](docs/cli-tools-management.md) | Workspace tool catalog and activation |

## Contributing

```bash
git clone https://github.com/nociza/cuti && cd cuti
uv pip install -e ".[dev]"
pytest
```

Submit PRs and issues on [GitHub](https://github.com/nociza/cuti/issues).
See [CHANGELOG.md](CHANGELOG.md) for notable changes.

## License

Apache 2.0 — see [LICENSE](LICENSE).
