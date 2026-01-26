# Cuti - AI Development Environment & Multi-Agent Orchestration

<div align="center">

[![PyPI Version](https://img.shields.io/pypi/v/cuti?color=blue&label=PyPI)](https://pypi.org/project/cuti/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cuti)](https://pypi.org/project/cuti/)
[![License](https://img.shields.io/pypi/l/cuti)](https://github.com/nociza/cuti/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/cuti?color=green&label=Downloads%2FMonth)](https://pypi.org/project/cuti/)
[![Downloads Total](https://static.pepy.tech/badge/cuti)](https://pepy.tech/project/cuti)

**Instant containerized development with Claude Code, Anthropic API integration, and intelligent agent orchestration**

[PyPI](https://pypi.org/project/cuti/) • [Documentation](https://cutils.org/) • [GitHub](https://github.com/nociza/cuti)

</div>

## 📊 Download Trends

<div align="center">

[![Downloads](https://img.shields.io/pypi/dm/cuti?style=for-the-badge&color=blue&label=Monthly)](https://pypi.org/project/cuti/)
[![Downloads](https://img.shields.io/pypi/dw/cuti?style=for-the-badge&color=green&label=Weekly)](https://pypi.org/project/cuti/)

</div>

## 🚀 Quick Start - Docker Container with Claude Code CLI

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

The Docker container provides isolated, reproducible AI-assisted development with Claude Code terminal integration.

## 🌟 Key Features - AI Agent Orchestration & Automation

Build with multiple AI models and intelligent task management:
- **Multi-agent orchestration** - Claude API, Gemini integration
- **Command queuing system** with priority execution
- **Web UI dashboard** - Launch with `cuti web`
- **Smart rate limiting** - Automatic retry & backoff
- **Task automation** - Built-in todo system for AI agents
- **Claude version switching** - Easy CLI version management
- **Optional Clawdbot addon** - Run Clawdbot gateway + messaging from the same dev container (`cuti clawdbot ...`)

Perfect for AI-powered development, automation workflows, and LLM orchestration.

## 📚 Documentation

### 📖 Documentation Guides

| Guide | Description |
|-------|-------------|
| [Docker Container Setup](docs/devcontainer.md) | Complete containerized environment guide |
| [Claude Authentication](docs/claude-container-auth.md) | Anthropic API & Claude CLI setup |
| [Claude Account Switching](docs/claude-account-switching.md) | Manage multiple Claude accounts |
| [Claude API Keys](docs/claude-api-keys.md) | Anthropic & AWS Bedrock API key management |
| [Task Management](docs/todo-system.md) | AI agent todo system |
| [Rate Limit Handling](docs/rate-limit-handling.md) | Smart API throttling & retry logic |
| [Clawdbot Integration](docs/clawdbot.md) | Run the Clawdbot gateway + channels inside cuti |

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

## 🦞 Clawdbot Integration

Clawdbot ships with cuti now—no manual install needed. The addon runs entirely inside the dev container, auto-links your Clawdbot workspace/config from `~/.cuti/clawdbot/`, and keeps every command interactive (OAuth, QR codes, etc.).

- `cuti clawdbot onboard` – run the official wizard with OAuth + skill setup
- `cuti clawdbot start` – launch the gateway, auto-pick a port, stream logs
- `cuti clawdbot config` – edit `clawdbot.json` safely inside the container
- `cuti clawdbot channels-login` – scan WhatsApp QR or add other channels
- `cuti clawdbot send --to +15551234567 --message "Hello"` – quick smoke test

See [docs/clawdbot.md](docs/clawdbot.md) for storage layout, channel details, and troubleshooting tips.
