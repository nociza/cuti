# Cuti - AI Development Environment & Multi-Agent Orchestration

<div align="center">

[![PyPI Version](https://img.shields.io/pypi/v/cuti?color=blue&label=PyPI)](https://pypi.org/project/cuti/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cuti)](https://pypi.org/project/cuti/)
[![License](https://img.shields.io/pypi/l/cuti)](https://github.com/nociza/cuti/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/cuti?color=green&label=Downloads%2FMonth)](https://pypi.org/project/cuti/)
[![Downloads Total](https://static.pepy.tech/badge/cuti)](https://pepy.tech/project/cuti)

**Instant containerized development with Claude Code by default, plus provider-aware agent tooling**

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

The Docker container provides isolated, reproducible AI-assisted development with Claude as the default agent provider.

## 🌟 Key Features - AI Agent Orchestration & Automation

Build with multiple AI models and intelligent task management:
- **Multi-agent orchestration** - Claude API, Gemini integration
- **Command queuing system** with priority execution
- **Read-only ops console** - Launch with `cuti web` to inspect provider readiness, queue state, recent activity, and workspace drift
- **Smart rate limiting** - Automatic retry & backoff
- **Task automation** - Built-in todo system for AI agents
- **Claude version switching** - Easy CLI version management
- **Agent providers** - Enable Codex, OpenCode, OpenClaw, and future providers alongside Claude with `cuti providers ...`
- **Provider-aware setup** - cuti mounts provider auth/config/skills and updates common instruction files for enabled tools
- **Legacy Clawdbot sandbox** - Run the older gateway + messaging workflow separately with `cuti clawdbot ...`
- **Claude chat history** - `cuti history` shows transcripts and reopens old Claude Code sessions

Perfect for AI-powered development, automation workflows, and LLM orchestration.

## 🤖 Agent Providers

Claude is enabled by default. Additional providers are opt-in and can be enabled together:

```bash
cuti providers list
cuti providers doctor
cuti providers enable codex
cuti providers enable opencode
cuti providers enable openclaw
cuti providers auth claude --login
cuti container --rebuild
cuti providers update codex
```

When selected, `cuti` handles the provider-specific container wiring for auth, config mounts, CLI installation, and standard instruction files such as `CLAUDE.md`, `AGENTS.md`, `SOUL.md`, and `TOOLS.md`. The host CLI can also inspect readiness, launch setup flows, and refresh provider installs through `cuti providers ...`.

## 📚 Documentation

### 📖 Documentation Guides

| Guide | Description |
|-------|-------------|
| [Docker Container Setup](docs/devcontainer.md) | Container runtime, provider selection, mounts, and auth |
| [Claude Authentication](docs/claude-container-auth.md) | Anthropic API & Claude CLI setup |
| [Claude Account Switching](docs/claude-account-switching.md) | Manage multiple Claude accounts |
| [Claude API Keys](docs/claude-api-keys.md) | Anthropic & AWS Bedrock API key management |
| [Task Management](docs/todo-system.md) | AI agent todo system |
| [Rate Limit Handling](docs/rate-limit-handling.md) | Smart API throttling & retry logic |
| [Claude Chat History](docs/claude-history.md) | Inspect & resume Claude Code sessions |
| [Clawdbot Sandbox](docs/clawdbot.md) | Legacy Clawdbot gateway workflow in the separate sandbox profile |

## 🤝 Contributing

> **Note:** This project is under active development. Contributions welcome!

```bash
uv install -e .
```

Submit PRs to [GitHub](https://github.com/nociza/cuti) | Report issues in [Issues](https://github.com/nociza/cuti/issues)

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE)

---

<div align="center">

**[PyPI](https://pypi.org/project/cuti/)** • **[Issues](https://github.com/nociza/cuti/issues)** • **[Contribute](https://github.com/nociza/cuti)**

</div>

## 🦞 Clawdbot Sandbox

`cuti clawdbot` is a separate legacy sandbox workflow. It is not part of provider selection and uses its own hardened runtime profile plus persistent storage under `~/.cuti/clawdbot/`.

- `cuti clawdbot onboard` – run the official wizard with OAuth + skill setup
- `cuti clawdbot start` – launch the gateway, auto-pick a port, stream logs
- `cuti clawdbot config` – edit `clawdbot.json` safely inside the container
- `cuti clawdbot channels-login` – scan WhatsApp QR or add other channels
- `cuti clawdbot send --to +15551234567 --message "Hello"` – quick smoke test

See [docs/clawdbot.md](docs/clawdbot.md) for storage layout, channel details, and troubleshooting tips.
