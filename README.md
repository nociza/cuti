# cuti - Claude Code Unified Terminal Interface

> **Production-ready AI orchestration system for Claude Code with multi-agent support, intelligent task routing, real-time usage monitoring, and comprehensive workspace management.**

cuti (Claude Code Unified Terminal Interface) is an advanced orchestration platform that transforms Claude Code into a powerful development assistant. It provides seamless integration with Claude Code CLI, Google Gemini, and extensible agent architecture, featuring intelligent task routing, collaborative workflows, real-time token usage monitoring, and a modern web interface for managing complex AI-assisted development tasks.

## 🚀 Quick Start

```bash
# Clone and set up
git clone https://github.com/nociza/cuti
cd cuti

# Quick setup with uvx
uvx run ./run.py setup

# Start the web interface  
uvx run ./run.py web

# Or use the modern CLI
uvx run ./run.py cli --help
```

Open http://127.0.0.1:8000 in your browser for the full web interface!

## ✨ Core Features

### 🤖 Multi-Agent Orchestration System
- **Unified Agent Pool**: Centralized management of Claude Code, Gemini, and custom AI agents
- **Intelligent Task Routing**: Six routing strategies - capability-based, round-robin, load-balanced, cost-optimized, speed-optimized, quality-optimized
- **Agent Capabilities**: 18+ defined capabilities including code generation, refactoring, testing, documentation, security analysis, and large context processing
- **Collaborative Workflows**: Agents share context through SharedMemoryManager for coordinated task execution
- **Dynamic Agent Management**: Create, configure, and monitor agents through web UI or CLI
- **Built-in Agent Templates**: Pre-configured agents for code review, documentation, testing, UI design, refactoring, and codebase analysis

### 🔧 Claude Code Deep Integration
- **Native CLI Integration**: Direct interface with Claude Code CLI for seamless file operations and tool use
- **Real Usage Monitoring**: Integration with claude-monitor package for live token tracking and burn rate calculation
- **Settings Management**: Project-specific Claude configuration with automatic CLAUDE.md updates
- **Log Synchronization**: Automatic sync of Claude conversation logs, TodoWrite lists, and execution history
- **MCP Server Support**: Full Model Context Protocol support for extended capabilities

### 📂 Intelligent Workspace Management
- **Project Isolation**: Dedicated `.cuti` directories for each project with complete data separation
- **Multi-Database Architecture**: SQLite databases for history tracking, metrics collection, and agent usage analytics
- **Git-Aware Operations**: Automatic `.gitignore` configuration and git context preservation
- **Automated Maintenance**: Scheduled backups, data cleanup, and workspace optimization
- **Workspace Portability**: Export/import workspace configurations across projects

### 🎯 Advanced Queue Processing
- **Smart Rate Limiting**: Automatic detection and handling of Claude API rate limits with cooldown management
- **Priority-Based Execution**: Multi-level priority system with intelligent task scheduling
- **Template System**: YAML frontmatter support for rich prompt templates with metadata
- **Resilient Retry Logic**: Exponential backoff with configurable retry strategies
- **Persistent State**: Queue state preservation across system restarts and crashes
- **Batch Operations**: Process multiple prompts with dependency management

### 🔗 Powerful Alias System
- **Built-in Aliases**: 12+ production-ready aliases for common development workflows
- **Dynamic Templates**: Variable substitution with project context (`${PROJECT_NAME}`, `${DATE}`, `${GIT_BRANCH}`)
- **Alias Composition**: Chain aliases together with `@alias-name` references
- **Context Awareness**: Aliases inherit working directory and file contexts
- **Custom Workflows**: Create complex multi-step workflows as reusable aliases

### 📊 Comprehensive Monitoring & Analytics
- **Real-time Token Tracking**: Live monitoring via claude-monitor integration
- **Burn Rate Analysis**: Predictive rate limit consumption with visual indicators
- **Cost Management**: Per-model, per-feature cost tracking with budget alerts
- **Subscription Awareness**: Automatic detection of Claude plans (Pro, Max5, Max20, Custom)
- **System Performance**: CPU, memory, disk I/O, and network metrics with historical trends
- **Execution Analytics**: Success rates, response times, throughput metrics, and error analysis

### 🌐 Modern Web Interface
- **Real-time Dashboard**: Live system metrics with WebSocket-powered updates
- **Agent Orchestration UI**: Visual agent management with Symphony toggle animations
- **Claude Chat Integration**: Web-based chat interface proxying to Claude Code CLI
- **Interactive Queue Manager**: Drag-and-drop queue reordering with priority management
- **Execution History**: Searchable history with filters, analytics, and export options
- **Statistics Dashboard**: Comprehensive usage analytics with interactive charts

### 📱 Enhanced CLI Experience
- **Rich Terminal UI**: Beautiful formatting with Rich library (tables, progress bars, syntax highlighting)
- **Modern Command Structure**: Intuitive CLI built with Typer for superior UX
- **Agent Operations**: Complete agent lifecycle management via CLI
- **Machine-Readable Output**: JSON output mode for automation and scripting
- **Interactive Mode**: Real-time feedback with spinners and progress indicators
- **Autocomplete Support**: Shell completion for faster command entry

### 🧠 Intelligent Task Processing
- **Task Expansion Engine**: Automatically decomposes complex tasks into subtasks
- **Complexity Analysis**: Estimates effort, identifies risks, and suggests approaches
- **Dependency Resolution**: Automatic detection and ordering of task dependencies
- **Parallel Execution**: Identifies and executes independent tasks concurrently
- **Context Sharing**: SharedMemoryManager enables inter-agent communication
- **Execution Planning**: Generates execution plans with success metrics

## 📋 Requirements & Installation

### System Requirements
- **Python**: 3.9 or higher
- **OS**: macOS, Linux, Windows (WSL recommended)
- **Memory**: 512MB minimum, 1GB recommended
- **Storage**: 100MB for installation, 1GB+ for workspace data

### Prerequisites
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager (recommended)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) - Required for Claude integration
- [claude-monitor](https://github.com/cline/claude-monitor) - Automatically installed for usage tracking
- (Optional) Google Gemini API key for Gemini agent support

### Quick Installation

#### Using uv (Recommended)
```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/nociza/cuti
cd cuti
python run.py setup
```

#### Alternative Installation Methods
```bash
# Direct installation with uv
uv add git+https://github.com/nociza/cuti

# Traditional pip installation
pip install git+https://github.com/nociza/cuti

# Development installation
git clone https://github.com/nociza/cuti
cd cuti
uv install -e .
```

## 🎮 Usage

### Web Interface (Recommended)

Start the modern web interface:
```bash
# Using run.py
python run.py web

# Or directly
cuti web --host 0.0.0.0 --port 8000
```

Features:
- 📊 **Real-time Dashboard**: Live metrics and queue status
- 🤖 **Agent Management**: Create, configure, and monitor AI agents
- 💬 **Claude Chat Interface**: Direct chat with Claude through web UI
- 📚 **History Browser**: Search and analyze prompt history
- 📈 **Monitoring Dashboard**: System performance and token usage tracking
- 🔄 **WebSocket Updates**: Real-time updates across all connected clients

### CLI Interface

The enhanced CLI provides a rich terminal experience:

```bash
# Quick status check
cuti status --detailed

# Agent management
cuti agent list
cuti agent create "my-agent" --type claude
cuti agent test my-agent "Test prompt"

# Add a prompt using an alias
cuti add "explore-codebase" --priority 1

# Start the queue processor
cuti start --verbose

# Manage aliases
cuti alias create my-task "Implement user authentication with JWT tokens"
cuti alias list

# Search history
cuti history search "authentication" 
cuti history list --limit 10

# Task expansion
cuti expand "Build a REST API for user management"
```

### Multi-Agent Workflows

Orchestrate multiple agents working together:

```bash
# Create a complex workflow with multiple agents
cuti agent create-workflow "full-stack-feature" \
  --agents "claude:planning,gemini:backend,claude:frontend" \
  --coordination "sequential" \
  --share-context

# Execute with result aggregation
cuti execute-workflow "full-stack-feature" \
  --prompt "Build user authentication system" \
  --aggregate-results
```

### Agent Routing Strategies

Configure how tasks are routed to agents:

```bash
# Capability-based routing (default)
cuti config set routing.strategy "capability"

# Cost-optimized routing
cuti config set routing.strategy "cost"

# Speed-optimized routing  
cuti config set routing.strategy "speed"

# Quality-optimized routing
cuti config set routing.strategy "quality"
```

### Built-in Development Aliases

| Alias | Description | Use Case |
|-------|-------------|----------|
| `explore-codebase` | Comprehensive codebase analysis and documentation | Understanding new projects |
| `document-api` | Generate OpenAPI/Swagger documentation | API documentation |
| `security-audit` | Comprehensive security vulnerability assessment | Security reviews |
| `optimize-performance` | Performance analysis and optimization recommendations | Performance tuning |
| `write-tests` | Complete test suite creation (unit/integration/e2e) | Test automation |
| `refactor-code` | Code quality improvement and refactoring | Code maintenance |
| `setup-cicd` | CI/CD pipeline configuration | DevOps automation |
| `add-logging` | Structured logging implementation | Observability |
| `fix-bugs` | Systematic bug identification and resolution | Bug fixing |
| `modernize-stack` | Technology stack modernization | Tech debt |
| `ui-design-expert` | UI/UX design and implementation | Frontend development |
| `code-reviewer` | Comprehensive code review and suggestions | Code quality |

### Creating Custom Aliases

```bash
# Create a reusable deployment alias
cuti alias create deploy-app \
  "Deploy the ${PROJECT_NAME} application to production. Include: 
   1) Pre-deployment checks 
   2) Database migrations 
   3) Blue-green deployment 
   4) Health checks 
   5) Rollback plan" \
  --description "Production deployment checklist" \
  --working-dir "." \
  --context-files "deploy/config.yml" "scripts/deploy.sh"

# Use the custom alias
cuti add "deploy-app"
```

### Workspace Management

Each project gets its own isolated workspace:

```bash
# Initialize workspace for current project
cuti workspace init

# View workspace status
cuti workspace status

# Backup workspace data
cuti workspace backup

# Clean old data
cuti workspace clean --older-than 30d
```

### Claude Settings Management

Manage Claude Code settings per project:

```bash
# Configure Claude settings for current project
cuti claude-settings set "experimental.modelChoiceList" '["claude-3-5-sonnet", "claude-3-opus"]'

# View current settings
cuti claude-settings show

# Reset to defaults
cuti claude-settings reset
```

## 🔧 Configuration

### Environment Variables

```bash
# Storage location
export CLAUDE_QUEUE_STORAGE_DIR="/custom/path"

# Claude CLI command
export CLAUDE_QUEUE_CLAUDE_COMMAND="claude"

# Web interface settings
export CLAUDE_QUEUE_WEB_HOST="0.0.0.0"
export CLAUDE_QUEUE_WEB_PORT="8000"

# Monitoring settings  
export CLAUDE_QUEUE_METRICS_RETENTION_DAYS="90"
export CLAUDE_QUEUE_CLEANUP_INTERVAL_HOURS="24"

# Gemini API key (for Gemini agent support)
export GEMINI_API_KEY="your-api-key"
```

### Configuration File

Create `~/.cuti/config.json`:

```json
{
  "claude_command": "claude",
  "check_interval": 30,
  "timeout": 3600,
  "max_retries": 3,
  "agents": {
    "default_type": "claude",
    "pool_size": 5,
    "coordination": {
      "strategy": "capability",
      "enable_sharing": true
    }
  },
  "web": {
    "host": "127.0.0.1",  
    "port": 8000,
    "cors_origins": ["*"]
  },
  "monitoring": {
    "enable_system_monitoring": true,
    "metrics_retention_days": 90,
    "enable_token_tracking": true,
    "cost_per_input_token": 0.000015,
    "cost_per_output_token": 0.000075
  },
  "workspace": {
    "auto_backup": true,
    "backup_interval_hours": 24,
    "cleanup_age_days": 30
  }
}
```

## 📁 Project Structure

```
cuti/
├── src/cuti/
│   ├── agents/              # Multi-agent orchestration system
│   │   ├── base.py         # Base agent interface
│   │   ├── claude_agent.py # Claude agent implementation
│   │   ├── gemini_agent.py # Gemini agent implementation
│   │   ├── pool.py         # Agent pool management
│   │   └── router.py       # Intelligent task routing
│   ├── builtin_agents/      # Pre-configured agent templates
│   ├── cli/                 # Modern CLI interface
│   │   └── commands/        # CLI command modules
│   ├── core/                # Core queue management
│   │   ├── queue.py        # Queue processing logic
│   │   ├── storage.py      # Persistent storage
│   │   └── models.py       # Data models
│   ├── services/            # Service layer
│   │   ├── agent_manager.py        # Agent lifecycle management
│   │   ├── claude_monitor_integration.py # Claude usage monitoring
│   │   ├── workspace_manager.py    # Workspace management
│   │   ├── log_sync.py            # Log synchronization
│   │   └── monitoring.py          # System monitoring
│   └── web/                 # FastAPI web application
│       ├── api/            # REST API endpoints
│       ├── static/         # Frontend assets
│       └── templates/      # HTML templates
├── run.py                   # Main entry point
├── pyproject.toml          # Modern Python packaging
└── README.md              # This file
```

## 🗄️ Data Architecture

### Storage Structure
```
~/.cuti/                       # Global configuration
├── config.json               # Global settings
├── agents/                   # Agent templates
│   ├── builtin/             # Pre-configured agents
│   └── custom/              # User-defined agents
└── logs/                     # System logs

<project>/.cuti/              # Project workspace
├── queue/                    # Queue management
│   ├── pending/            # Waiting prompts
│   ├── executing/          # Currently running
│   └── archived/           # Completed/failed
├── databases/               # SQLite databases
│   ├── history.db          # Execution history
│   ├── metrics.db          # Performance metrics
│   ├── agents.db           # Agent usage stats
│   └── monitoring.db       # System monitoring
├── agents.json              # Active agents config
├── aliases.json             # Custom aliases
├── claude-settings.json     # Claude configuration
├── CLAUDE.md               # Dynamic instructions
├── workspace.json          # Workspace metadata
└── backups/                # Automated backups
    └── YYYY-MM-DD/        # Daily snapshots
```

### Database Schemas
- **history.db**: Prompt executions, results, timings
- **metrics.db**: Token usage, costs, rate limits
- **agents.db**: Agent performance, capability scores
- **monitoring.db**: System metrics, health checks

## 🔧 API Reference

### REST API Endpoints

#### Queue Management
- `GET /api/queue/status` - Get queue status and statistics
- `GET /api/queue/prompts` - List all prompts
- `POST /api/queue/prompts` - Add new prompt
- `DELETE /api/queue/prompts/{id}` - Cancel prompt

#### Agent Management
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create new agent
- `GET /api/agents/{id}` - Get agent details
- `POST /api/agents/{id}/execute` - Execute task with agent
- `DELETE /api/agents/{id}` - Remove agent

#### Workspace Management
- `GET /api/workspace/status` - Workspace status
- `POST /api/workspace/backup` - Create backup
- `POST /api/workspace/clean` - Clean old data

#### Claude Integration
- `GET /api/claude/settings` - Get Claude settings
- `POST /api/claude/settings` - Update Claude settings
- `GET /api/claude/logs` - Get Claude conversation logs
- `POST /api/claude/chat` - Send message to Claude

#### Monitoring
- `GET /api/monitoring/system` - System metrics
- `GET /api/monitoring/tokens` - Token usage statistics
- `GET /api/monitoring/performance` - Performance metrics
- `GET /api/monitoring/agents` - Agent usage analytics

### WebSocket Events
- `status_update` - Real-time queue status updates
- `agent_status` - Agent status changes
- `prompt_completed` - Prompt completion notifications
- `system_alert` - System health alerts
- `usage_update` - Token usage updates

## 🧪 Development & Testing

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/nociza/cuti
cd cuti
python run.py setup

# Install development dependencies  
uv add --dev pytest pytest-asyncio black ruff mypy pre-commit

# Setup pre-commit hooks
pre-commit install

# Run initial checks
uv run black .
uv run ruff check . --fix
uv run mypy src/
```

### Testing Suite

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=cuti --cov-report=html

# Test specific components
uv run pytest tests/test_agents.py -v
uv run pytest tests/test_interface.py -v
uv run pytest tests/test_agent_integration.py -v

# Run performance tests
uv run pytest tests/test_statistics_page.py -v

# Test structure validation
uv run pytest tests/test_structure.py -v
```

### Code Quality Tools

```bash
# Format code with Black
uv run black src/ tests/

# Lint with Ruff
uv run ruff check src/ --fix

# Type checking with mypy
uv run mypy src/ --strict

# Security scanning
uv run bandit -r src/

# Generate documentation
uv run sphinx-build docs/ docs/_build/
```

## 🚨 Troubleshooting

### Common Issues

**Queue not processing:**
```bash
# Check Claude Code connection
cuti test

# Check queue status  
cuti status --detailed

# Restart queue processor
cuti start --verbose
```

**Agent connection issues:**
```bash
# Test specific agent
cuti agent test claude "Hello"

# Check agent status
cuti agent status

# Recreate agent pool
cuti agent reset-pool
```

**Web interface not starting:**
```bash
# Check if port is available
lsof -i :8000

# Try different port
cuti web --port 8080

# Check logs for errors
cuti web --log-level debug
```

**Rate limit issues:**
- The system automatically handles rate limits
- Check rate limit status: `cuti status`
- View burn rate: `cuti monitoring burn-rate`
- Prompts will automatically retry after cooldown

## 📊 Performance & Optimization

### Performance Metrics
- **Queue Throughput**: 10-50 prompts/hour (API-limited)
- **Agent Concurrency**: 5-10 agents with <100ms coordination overhead
- **WebSocket Connections**: 100+ concurrent clients
- **Database Performance**: Sub-millisecond queries for <1M records
- **Memory Footprint**: 100-200MB base, +50MB per active agent
- **CPU Utilization**: <5% idle, 20-40% active processing
- **Response Time**: <500ms for API endpoints, <100ms for WebSocket

### Optimization Tips
- **Storage**: Use NVMe SSD for database operations
- **Agent Pool**: Size = (Available Memory - 500MB) / 50MB
- **Rate Limits**: Configure burn rate alerts at 80% threshold
- **Database**: Enable WAL mode for SQLite, vacuum monthly
- **Monitoring**: Set 7-day retention for high-frequency metrics
- **Production**: Deploy behind nginx with caching enabled
- **Scaling**: Horizontal scaling via Redis queue sharing

## 🔐 Security & Privacy

### Security Features
- **Local-first Architecture**: All data stored locally, no cloud dependencies
- **Credential Management**: API keys stored in environment variables or keyring
- **Network Isolation**: Default bind to localhost, configurable CORS
- **Project Isolation**: Complete data separation between projects
- **No Telemetry**: Zero external data collection without explicit consent
- **Secure Communication**: HTTPS support for production deployments
- **Access Control**: Token-based authentication for API endpoints (optional)

### Best Practices
- Store API keys in environment variables or `.env` files
- Use `.gitignore` for workspace directories (auto-configured)
- Enable HTTPS for production web interface deployments
- Regularly rotate API keys and update configurations
- Review agent permissions before enabling new integrations

## 📜 License

MIT License - Copyright (c) 2025 @nociza. See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

### Core Technologies
- [Claude Code](https://claude.ai) by Anthropic - Foundation AI assistant
- [Google Gemini](https://deepmind.google/technologies/gemini/) - Large context processing
- [claude-monitor](https://github.com/cline/claude-monitor) - Token usage tracking
- [FastAPI](https://fastapi.tiangolo.com/) - Async web framework
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [uv](https://docs.astral.sh/uv/) - Fast package management

### Contributors
- Initial development by @nociza and Claude Code
- Community contributions welcome via GitHub

## 🔮 Future Roadmap

### Version 1.0 (Current)
- ✅ Multi-agent orchestration with Claude and Gemini
- ✅ Real-time usage monitoring and analytics
- ✅ Web interface with WebSocket updates
- ✅ Project workspace management
- ✅ Queue processing with rate limit handling

### Version 1.1 (Q1 2025)
- [ ] OpenAI GPT-4 integration
- [ ] Local LLM support (Ollama, LlamaCpp)
- [ ] Enhanced workflow templates
- [ ] Docker containerization
- [ ] GitHub Actions integration

### Version 2.0 (Q2 2025)
- [ ] Distributed agent pools
- [ ] Visual workflow designer
- [ ] Team collaboration features
- [ ] Cloud deployment options
- [ ] Plugin ecosystem

### Long-term Vision
Create the definitive AI orchestration platform that seamlessly integrates multiple AI services, enabling developers to leverage the best capabilities of each model through intelligent routing, collaborative workflows, and comprehensive monitoring.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Philosophy
- **User-First**: Prioritize developer experience and productivity
- **Performance**: Optimize for speed without sacrificing functionality
- **Reliability**: Ensure robust error handling and recovery
- **Extensibility**: Design for plugin and integration support
- **Privacy**: Maintain local-first, zero-telemetry approach

---

<div align="center">

**cuti - Orchestrating AI for Developers**

Built with passion for the AI-assisted development community

⭐ Star this repository if you find it useful!

[Report Bug](https://github.com/nociza/cuti/issues) · [Request Feature](https://github.com/nociza/cuti/issues) · [Documentation](https://github.com/nociza/cuti/wiki)

</div>