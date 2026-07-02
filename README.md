# Cuti - Provider-Aware AI Development Runtime

<div align="center">

[![PyPI Version](https://img.shields.io/pypi/v/cuti?color=blue&label=PyPI)](https://pypi.org/project/cuti/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cuti)](https://pypi.org/project/cuti/)
[![License](https://img.shields.io/pypi/l/cuti)](https://github.com/nociza/cuti/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/cuti?color=green&label=Downloads%2FMonth)](https://pypi.org/project/cuti/)
[![Downloads Total](https://static.pepy.tech/badge/cuti)](https://pepy.tech/project/cuti)

**Instant containerized development with Claude Code by default, plus provider-aware runtime wiring for Codex, OpenClaw, Hermes, and OpenCode**

[PyPI](https://pypi.org/project/cuti/) • [Documentation](https://cutils.org/) • [GitHub](https://github.com/nociza/cuti)

</div>

## 📊 Download Trends

<div align="center">

[![Downloads](https://img.shields.io/pypi/dm/cuti?style=for-the-badge&color=blue&label=Monthly)](https://pypi.org/project/cuti/)
[![Downloads](https://img.shields.io/pypi/dw/cuti?style=for-the-badge&color=green&label=Weekly)](https://pypi.org/project/cuti/)

</div>

## 🚀 Quick Start - Docker Container with Claude Code

```bash
# Install Python package from PyPI
uv tool install cuti

# Launch Docker development environment with Claude
cuti container
```

That's it! You now have a fully configured AI-powered coding environment with:
- ✅ **Claude Code CLI** pre-configured with Anthropic integration
- ✅ **Persistent authentication** for Claude API across sessions  
- ✅ **Python 3.11**, **Node.js 20**, and essential dev tools
- ✅ **Custom prompt** showing `cuti:~/path $`
- ✅ **Auto-mounts** current directory for seamless workflow

The Docker container provides isolated, reproducible AI-assisted development with Claude Code mode as the default. Each `cuti container` run refreshes Claude Code in the persistent container runtime when Claude Code mode is active, so subsequent containers pick up the newest available Claude CLI without a rebuild.

## 🌟 Key Features - Provider Runtime & Observability

Run native AI coding tools in a consistent local environment:
- **Provider-aware containers** - Claude Code by default, with opt-in Codex, OpenClaw, Hermes, and OpenCode wiring
- **Read-only ops console** - Launch with `cuti web` to inspect provider readiness, recent native activity, legacy queue state, and workspace drift
- **Persistent provider state** - Mount auth, config, skills, and runtime installs across container sessions
- **Native CLI coordination** - Use Claude Code, Codex, OpenClaw, and other provider CLIs directly instead of reimplementing their agent loops
- **Claude version switching** - Easy CLI version management
- **Agent providers** - Run Claude Code mode by default, switch to OpenClaw mode with `cuti container --openclaw`, and add Codex, Claude Code, OpenCode, or other providers through `cuti providers ...`
- **Provider-aware setup** - cuti mounts provider auth/config/skills, persistent CLI runtimes, and workspace instruction files for enabled tools
- **Turnkey OpenClaw** - Run the current OpenClaw gateway, channels, browser, plugins, and voice-call flows with `qt-openclaw ...` or `qt-OpenClaw ...`
- **Claude chat history** - `cuti history` shows transcripts and reopens old Claude Code sessions
- **Legacy queue helpers** - Existing queue and todo commands remain available for compatibility, but new automation should prefer provider-native background/session features

Perfect for local AI-powered development environments where provider setup, state, and workspace visibility need to be repeatable.

## 🤖 Agent Providers

Claude Code mode is the default for `cuti container`. OpenClaw is a separate mode, started explicitly with `cuti container --openclaw` or `cuti container --claw`.

```bash
cuti providers list
cuti providers doctor

# Default mode: Claude Code. This also refreshes Claude Code for future containers.
cuti container

# OpenClaw mode: OpenClaw only unless add-ons are explicitly enabled.
cuti container --openclaw

# Add-ons for OpenClaw mode are read from provider config.
cuti providers enable claude
cuti providers enable codex
cuti providers enable opencode
cuti providers enable hermes
cuti container --openclaw

# Provider setup/update helpers still run in the right mode automatically.
cuti providers auth claude --login
qt-openclaw onboard
qt-openclaw up
cuti providers update codex
cuti providers update openclaw
cuti providers update hermes
```

When selected for the current mode, `cuti` handles the provider-specific container wiring for auth, config mounts, persistent CLI installation, and standard instruction files such as `CLAUDE.md`, `AGENTS.md`, `.hermes.md`, `HERMES.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, and `HEARTBEAT.md`. OpenClaw installs under `~/.cuti/provider-runtimes/openclaw`, keeps runtime state under `~/.openclaw`, and runs `openclaw doctor --non-interactive` during install/update/bootstrap. Hermes is currently marked experimental in cuti, but its state persists under `~/.hermes`, including Hermes profiles under `~/.hermes/profiles`. `~/.openclaw` is mounted when available so `hermes claw migrate --dry-run` can inspect OpenClaw data before migration, and `cuti providers update hermes` follows Hermes' native `hermes update` path so bundled skills and profile state stay aligned with upstream behavior.

### OpenClaw Qt Container

Use `qt-openclaw` or `qt-OpenClaw` for the current OpenClaw runtime.

```bash
qt-openclaw onboard
qt-openclaw up
qt-openclaw channels-login --channel whatsapp
qt-openclaw browser start
qt-openclaw plugins install @openclaw/voice-call
qt-openclaw voice-setup
qt-openclaw voicecall status
qt-openclaw dashboard --no-open
```

The command enables the OpenClaw provider automatically and runs inside OpenClaw mode, with `~/.openclaw`, `~/.agents`, and the persistent OpenClaw CLI runtime mounted for reuse.
OpenClaw's source-backed command families are exposed directly (`models`, `mcp`, `sandbox`, `memory`, `wiki`, `approvals`, `nodes`, `devices`, `hooks`, `webhooks`, `tasks`, `cron`, `security`, `secrets`, and more). For plugin commands added by future OpenClaw releases, use `qt-openclaw run <command> ...`; it forwards raw arguments to the installed OpenClaw CLI without requiring a cuti release.

## 📚 Documentation

### 📖 Documentation Guides

| Guide | Description |
|-------|-------------|
| [Docker Container Setup](docs/devcontainer.md) | Container runtime, provider selection, mounts, and auth |
| [Claude Authentication](docs/claude-container-auth.md) | Anthropic API & Claude CLI setup |
| [Claude Account Switching](docs/claude-account-switching.md) | Manage multiple Claude accounts |
| [Claude API Keys](docs/claude-api-keys.md) | Anthropic & AWS Bedrock API key management |
| [Legacy Task Helpers](docs/todo-system.md) | Local todo helpers and legacy queue conversion |
| [Legacy Queue Rate Limits](docs/rate-limit-handling.md) | Older Claude queue retry behavior |
| [Claude Chat History](docs/claude-history.md) | Inspect & resume Claude Code sessions |

## 🤝 Contributing

> **Note:** This project is under active development. Contributions welcome!

```bash
uv sync --extra dev
```

Submit PRs to [GitHub](https://github.com/nociza/cuti) | Report issues in [Issues](https://github.com/nociza/cuti/issues)

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE)

---

<div align="center">

**[PyPI](https://pypi.org/project/cuti/)** • **[Issues](https://github.com/nociza/cuti/issues)** • **[Contribute](https://github.com/nociza/cuti)**

</div>
