# Cuti

<div align="center">

[![PyPI Version](https://img.shields.io/pypi/v/cuti?color=blue&label=PyPI)](https://pypi.org/project/cuti/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cuti)](https://pypi.org/project/cuti/)
[![License](https://img.shields.io/pypi/l/cuti)](https://github.com/nociza/cuti/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/cuti?color=green&label=Downloads%2FMonth)](https://pypi.org/project/cuti/)
[![Downloads Total](https://static.pepy.tech/badge/cuti)](https://pepy.tech/project/cuti)

**Instant AI development environments with Claude Code and multi-agent orchestration**

[PyPI](https://pypi.org/project/cuti/) • [Documentation](#documentation) • [GitHub](https://github.com/nociza/cuti)

</div>

## 📊 Download Trends

<div align="center">

[![Downloads](https://img.shields.io/pypi/dm/cuti?style=for-the-badge&color=blue&label=Monthly)](https://pypi.org/project/cuti/)
[![Downloads](https://img.shields.io/pypi/dw/cuti?style=for-the-badge&color=green&label=Weekly)](https://pypi.org/project/cuti/)

</div>

## 🚀 Quick Start

```bash
# Install
pip install cuti  # or: uv tool install cuti

# Launch containerized dev environment
cuti container
```

That's it! You now have a fully configured AI development environment with:
- ✅ Cuti pre-installed and ready
- ✅ Claude CLI with persistent authentication  
- ✅ Python 3.11, Node.js 20, and dev tools
- ✅ Custom prompt showing `cuti:~/path $`
- ✅ Works from any project directory

The container mounts your current directory and preserves Claude authentication between sessions. Perfect for isolated, reproducible AI-assisted development.

## 🌟 Additional Features

Cuti also provides:
- **Multi-agent orchestration** (Claude, Gemini)
- **Command queuing** with priorities
- **Web UI** at `cuti web`
- **Rate limit handling** with smart retry
- **Todo system** for task management

See [documentation](#documentation) for details.

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| [Dev Container](docs/devcontainer.md) | Complete container guide |
| [Claude Auth](docs/claude-container-auth.md) | Container authentication |
| [Todo System](docs/todo-system.md) | Task management |
| [Rate Limits](docs/rate-limit-handling.md) | API limit handling |

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE)

---

<div align="center">

**[PyPI](https://pypi.org/project/cuti/)** • **[Issues](https://github.com/nociza/cuti/issues)**

</div>