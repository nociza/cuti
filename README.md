<div align="center">

# cuti

**Provider runtime and OpenClaw deployment console.**
Containerized [Claude Code](https://claude.com/claude-code) by default, with provider-aware runtime wiring for OpenClaw, Codex, Hermes, and OpenCode.

[![PyPI Version](https://img.shields.io/pypi/v/cuti?color=blue&label=PyPI)](https://pypi.org/project/cuti/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cuti)](https://pypi.org/project/cuti/)
[![License](https://img.shields.io/pypi/l/cuti)](https://github.com/nociza/cuti/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/cuti?color=green&label=Downloads%2FMonth)](https://pypi.org/project/cuti/)

[Quick Start](#-quick-start) • [Why cuti](#-why-cuti) • [Providers](#-agent-providers) • [Ops Console](#-ops-console) • [Commands](#-command-reference) • [Docs](#-documentation)

</div>

---

## 🚀 Quick Start

```bash
# Install from PyPI
uv tool install cuti        # or: pip install cuti

# Launch a provider-aware Docker development environment.
# Claude Code mode is the default.
cuti container
```

That's it. You're dropped into an isolated container with:

- ✅ **Claude Code CLI** pre-installed, kept up to date automatically, and wired through Claude's native permission modes
- ✅ **Persistent provider authentication** — log in once, reuse across every container session
- ✅ **Your current directory mounted** at `/workspace` for a seamless workflow
- ✅ **Python 3.11, Node.js 20**, and essential dev tools ready to go
- ✅ **A `cuti:~/path $` prompt** so you always know you're inside the sandbox

Every `cuti container` run refreshes the Claude Code CLI in a persistent runtime volume, so new containers always pick up the latest version — no image rebuilds required.

For OpenClaw deployments, start the OpenClaw runtime explicitly:

```bash
cuti openclaw onboard
cuti openclaw up
cuti openclaw dashboard --no-open
```

> **Prerequisites:** a Docker-compatible runtime. On macOS, cuti auto-configures [Colima](https://github.com/abiosoft/colima) for you (or use Docker Desktop and pass `--skip-colima`).

## 💡 Why cuti

AI coding CLIs are excellent at running agents. They're less excellent at being **set up the same way, every time, on every machine** — auth tokens, config files, skills, instruction files, and CLI versions all drift.

Claude Code now owns more of its autonomy and approval surface through native permission modes such as `auto`, `acceptEdits`, and `plan`. cuti deliberately does **not** reimplement provider-owned agent loops, queues, permissions, approvals, or task systems. Provider CLIs own execution; cuti owns the runtime around them:

| | What cuti does |
|---|---|
| 🐳 **Provider-aware containers** | One command to a fully wired environment — Claude Code by default, OpenClaw as an explicit mode, with opt-in Codex, Hermes, and OpenCode |
| 🔐 **Persistent provider state** | Auth, config, skills, and CLI runtime installs are mounted across container sessions — log in once |
| 🔒 **Native Claude permissions** | `CUTI_CLAUDE_PERMISSION_MODE` defaults to Claude `auto`, with `acceptEdits`, `plan`, `default`, `dontAsk`, or explicit `bypassPermissions` available |
| 🕸️ **OpenClaw deployment** | Gateway, channels, browser, plugins, voice-call, nodes, sandbox, cron, secrets, memory, and wiki flows run through `cuti openclaw` |
| 📄 **Instruction file management** | Standard files like `CLAUDE.md`, `AGENTS.md`, `SOUL.md`, and `HERMES.md` are wired per provider automatically |
| 📊 **Read-only ops console** | `cuti web` shows provider readiness, recent native activity, and workspace drift — without owning execution |
| 👤 **Claude account & version management** | Switch between Claude accounts, manage API keys, and pin or update CLI versions |
| 🕘 **Chat history** | `cuti history` browses Claude Code transcripts and reopens old sessions |

## 🤖 Agent Providers

cuti knows how to wire five provider CLIs into its containers:

| Provider | CLI | Status | Enabled by default |
|----------|-----|--------|:-:|
| **Claude Code** | `claude` | Stable | ✅ |
| **Codex** | `codex` | Stable | opt-in |
| **OpenClaw** | `openclaw` | Stable | opt-in (own mode) |
| **Hermes** | `hermes` | Experimental | opt-in |
| **OpenCode** | `opencode` | Stable | opt-in |

For each enabled provider, cuti handles the container wiring: auth and config mounts, persistent CLI installs under `~/.cuti/provider-runtimes/`, and the provider's instruction files in your workspace.

### Container modes

`cuti container` runs in one of two modes:

- **Claude Code mode** (default) — Claude Code plus any enabled add-on providers except OpenClaw.
- **OpenClaw mode** (`cuti container --openclaw` or `--claw`) — OpenClaw, plus any add-ons you've explicitly enabled.

```bash
# Inspect and manage providers
cuti providers list
cuti providers doctor                  # host-side readiness check
cuti providers status openclaw

# Enable add-ons, then launch the mode you want
cuti providers enable codex
cuti providers enable hermes
cuti container                         # Claude Code mode (default)
cuti container --openclaw              # OpenClaw mode

# Auth and updates run in the right mode automatically
cuti providers auth claude --login
cuti providers update codex
cuti providers update hermes           # follows Hermes' native `hermes update` path
```

**Provider state at a glance:**

- **Claude Code** — Linux-side credentials persist under `~/.cuti/claude-linux`, so container logins survive rebuilds.
- **OpenClaw** — installs under `~/.cuti/provider-runtimes/openclaw`, keeps state under `~/.openclaw`, and runs `openclaw doctor --non-interactive` on install, update, and bootstrap.
- **Hermes** *(experimental)* — state persists under `~/.hermes` (including profiles in `~/.hermes/profiles`). When `~/.openclaw` exists it's mounted read-only so `hermes claw migrate --dry-run` can inspect OpenClaw data before migrating.

### OpenClaw runtime

`cuti openclaw` runs the full OpenClaw stack — gateway, channels, browser automation, plugins, and voice calls — inside the cuti container, enabling the OpenClaw provider automatically:

```bash
cuti openclaw onboard                              # first-time setup
cuti openclaw up                                   # onboard → doctor → gateway
cuti openclaw channels-login --channel whatsapp    # QR/browser channel auth
cuti openclaw browser start
cuti openclaw plugins install @openclaw/voice-call
cuti openclaw voice-setup
cuti openclaw dashboard --no-open
```

OpenClaw's native command families are exposed directly (`models`, `mcp`, `sandbox`, `memory`, `wiki`, `approvals`, `nodes`, `devices`, `hooks`, `webhooks`, `tasks`, `cron`, `security`, `secrets`, and more). For anything newer than the current cuti release:

```bash
cuti openclaw run <command> ...    # forwards raw args to the installed OpenClaw CLI
```

## 📊 Ops Console

```bash
cuti web    # http://127.0.0.1:8000
```

A **strictly read-only** dashboard for your workspace — it never executes anything on your behalf:

- **Provider readiness matrix** — which CLIs are installed, authenticated, and up to date
- **Attention items** — prioritized drift warnings with suggested terminal commands
- **Recent native activity** — prompt history and Claude Code session trail
- **Workspace drift** — instruction file status and enabled-but-missing tools

Execution stays where it belongs: in the provider CLIs.

## 📖 Command Reference

| Command | Description |
|---------|-------------|
| `cuti container` | Launch the containerized dev environment (`--openclaw` for OpenClaw mode) |
| `cuti containers` | Manage running containers: `status`, `stop`, `enter`, `cleanup` |
| `cuti providers` | Provider selection and lifecycle: `list`, `enable`, `disable`, `status`, `doctor`, `auth`, `update` |
| `cuti openclaw` | Run OpenClaw commands inside the cuti OpenClaw container |
| `cuti web` | Start the read-only ops console |
| `cuti claude` | Manage Claude accounts and API keys: `list`, `use`, `save`, `add-api-key`, `update`, … |
| `cuti history` | Browse Claude chat history and resume sessions |
| `cuti tools` | Manage workspace CLI tools |
| `cuti sync` | Sync usage data |
| `cuti settings` / `favorites` / `alias` | Global settings, favorite prompts, and prompt aliases |
| `cuti queue` / `todo` / `agent` | **Legacy** — kept for compatibility; prefer provider-native background/session features |

Run `cuti --help` or `cuti <command> --help` for full details.

## 📚 Documentation

Full documentation lives at **[cutils.org](https://cutils.org/)**. Guides in this repo:

### Getting started

| Guide | Description |
|-------|-------------|
| [Docker Container Setup](docs/devcontainer.md) | Container runtime, provider selection, mounts, and auth |
| [Container Management](docs/container.md) | Named containers, status, cleanup |
| [Container Status Commands](docs/container-status-command.md) | `cuti containers status/stop/enter` reference |

### Claude Code

| Guide | Description |
|-------|-------------|
| [Claude Authentication](docs/claude-container-auth.md) | Anthropic API & Claude CLI auth inside containers |
| [Account Quick Start](docs/claude-account-quick-start.md) | Multiple Claude accounts in 5 minutes |
| [Account Switching](docs/claude-account-switching.md) | Managing multiple Claude accounts in depth |
| [API Keys](docs/claude-api-keys.md) | Anthropic & AWS Bedrock API key management |
| [Chat History](docs/claude-history.md) | Inspect & resume Claude Code sessions |

### Workspace tools

| Guide | Description |
|-------|-------------|
| [CLI Tools Management](docs/cli-tools-management.md) | Installing and enabling workspace tools |
| [Automatic Tools Activation](docs/automatic-tools-activation.md) | Shell-hook based tool activation |
| [Workspace Tools Architecture](docs/workspace-tools-architecture.md) | System/container/workspace tool scopes |

### Legacy

| Guide | Description |
|-------|-------------|
| [Legacy Task Helpers](docs/todo-system.md) | Local todo helpers and legacy queue conversion |
| [Legacy Queue Rate Limits](docs/rate-limit-handling.md) | Older Claude queue retry behavior |

## 🤝 Contributing

Contributions are welcome — this project is under active development.

```bash
git clone https://github.com/nociza/cuti.git
cd cuti
uv sync --extra dev

# Run the test suite
uv run --extra dev pytest
```

Open a [pull request](https://github.com/nociza/cuti/pulls) or file an [issue](https://github.com/nociza/cuti/issues).

## 📄 License

[Apache 2.0](LICENSE)

---

<div align="center">

**[PyPI](https://pypi.org/project/cuti/)** • **[Documentation](https://cutils.org/)** • **[Issues](https://github.com/nociza/cuti/issues)**

</div>
