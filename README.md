# cuti

> **Advanced multi-agent orchestration system for Claude Code with intelligent task routing, workspace management, and comprehensive monitoring.**

A production-ready AI agent orchestration platform that seamlessly integrates Claude Code, Gemini, and other AI services. Features intelligent task routing, collaborative agent workflows, real-time monitoring, and a modern web interface for managing complex development tasks.

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

## ✨ Key Features

### 🤖 Multi-Agent Orchestration
- **Agent Pool Management**: Centralized management of Claude, Gemini, and custom AI agents
- **Intelligent Task Routing**: Multiple routing strategies (capability-based, load-balanced, cost-optimized, speed-optimized)
- **Collaborative Workflows**: Agents can work together, sharing context and results
- **Dynamic Agent Creation**: Generate new agents on-demand using Claude's capabilities
- **Built-in Agent Library**: Pre-configured agents for code review, documentation, testing, UI design, and more

### 🔧 Claude Code Deep Integration
- **Native Claude CLI Integration**: Direct interface with Claude Code for file operations and tool use
- **MCP Server Support**: Full support for Model Context Protocol servers
- **Settings Management**: Per-project Claude configuration management
- **Log Synchronization**: Automatic sync of Claude conversation logs and TodoWrite data
- **Real Usage Monitoring**: Live tracking of actual token usage and costs

### 📂 Workspace Management
- **Project-Specific Workspaces**: Local `.cuti` directories for project isolation
- **Multi-Database Architecture**: Separate SQLite databases for history, metrics, and agent usage
- **Git Integration**: Automatic `.gitignore` updates and git context awareness
- **Workspace Backup**: Automated backup and cleanup systems

### 🎯 Core Queue Management
- **Smart Rate Limit Handling**: Automatic detection and handling of API rate limits
- **Priority Scheduling**: Execute high-priority tasks first
- **Markdown Templates**: Rich prompt templates with YAML frontmatter
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Persistent Storage**: Queue survives system restarts

### 🔗 Prompt Aliases System
- **Pre-built Aliases**: 10+ ready-to-use aliases for common development tasks
- **Custom Aliases**: Create your own reusable prompt templates
- **Variable Substitution**: Dynamic variables like `${PROJECT_NAME}`, `${DATE}`
- **Alias Chaining**: Reference other aliases with `@alias-name` syntax

### 📊 Advanced Monitoring & Analytics
- **Real-time Usage Tracking**: Live monitoring of token usage, costs, and rate limits
- **Burn Rate Calculation**: Predictive analysis of rate limit consumption
- **Multi-dimensional Analytics**: Daily, monthly breakdowns by model and feature
- **Plan-aware Monitoring**: Understands Claude subscription plans (Pro, Max5, Max20)
- **System Metrics**: CPU, memory, disk, and network monitoring
- **Performance Analytics**: Response times, success rates, and throughput

### 🌐 Modern Web Interface
- **Real-time Dashboard**: Live queue status and system metrics
- **WebSocket Updates**: Real-time updates without page refresh
- **Claude Chat Proxy**: Web-based chat interface that proxies to Claude Code CLI
- **Agent Management UI**: Visual interface for managing agents and configurations
- **Interactive Queue Management**: Add, cancel, and monitor prompts
- **History Browser**: Searchable prompt history with analytics

### 📱 Enhanced CLI Experience
- **Rich Terminal UI**: Beautiful tables, colors, and icons using Rich
- **Intuitive Commands**: Modern CLI with Typer framework
- **Agent Commands**: Dedicated commands for agent management and testing
- **JSON Output**: Machine-readable output for scripting
- **Progress Indicators**: Visual progress bars and spinners

### 📈 Task Expansion Engine
- **Smart Task Breakdown**: Automatically breaks complex tasks into manageable subtasks
- **Complexity Analysis**: Analyzes task complexity and estimates effort
- **Dependency Management**: Identifies task dependencies and execution order
- **Parallel Execution**: Identifies tasks that can run in parallel
- **Risk Assessment**: Identifies potential risks and success metrics

## 📋 Installation

### Prerequisites
- Python 3.9+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- (Optional) Google Gemini API key for Gemini agent support

### Install uv (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

### Install cuti

#### Option 1: Development Setup (Recommended)
```bash
git clone https://github.com/nociza/cuti
cd cuti
python run.py setup
```

#### Option 2: Direct Installation with uv
```bash
uv add git+https://github.com/nociza/cuti
```

#### Option 3: Traditional pip Installation
```bash
pip install git+https://github.com/nociza/cuti
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

## 🗄️ Storage Structure

```
~/.cuti/                    # Global cuti directory
├── config.json            # Global configuration
├── agents/                # Agent configurations
└── logs/                  # System logs

<project>/.cuti/           # Project-specific workspace
├── queue/                 # Pending prompts
├── completed/             # Successful executions
├── failed/               # Failed prompts
├── databases/            # SQLite databases
│   ├── history.db       # Prompt history
│   ├── metrics.db       # Monitoring data
│   └── agents.db        # Agent usage tracking
├── claude-settings.json  # Project Claude settings
├── workspace.json       # Workspace metadata
└── backups/            # Workspace backups
```

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

## 🧪 Development

### Setup Development Environment

```bash
git clone https://github.com/nociza/cuti
cd cuti
python run.py setup

# Install development dependencies  
uv add --dev pytest pytest-asyncio black ruff mypy

# Run tests
uv run pytest

# Code formatting
uv run black .
uv run ruff check . --fix

# Type checking
uv run mypy src/
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_agents.py

# With coverage
uv run pytest --cov=cuti

# Integration tests
uv run pytest tests/test_agent_integration.py
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

## 📊 Performance & Scaling

### Performance Characteristics
- **Queue Processing**: ~10-50 prompts/hour (depends on API limits)
- **Agent Pool**: Handles 5-10 concurrent agents efficiently
- **Web Interface**: Supports 100+ concurrent connections
- **Database**: SQLite handles millions of records efficiently
- **Memory Usage**: ~100-200MB typical (varies with agent pool size)
- **CPU Usage**: Minimal when idle, 20-40% during active processing

### Scaling Recommendations
- Use SSD storage for better database performance
- Configure appropriate agent pool size based on usage
- Monitor disk space (databases grow over time)
- Set up retention policies for old data
- Use reverse proxy (nginx) for production deployments
- Consider Redis for distributed deployments

## 🔐 Security

- **Local-first Architecture**: All data stored locally by default
- **API Key Management**: Secure handling of API credentials
- **Network Security**: CORS configuration, local-only by default
- **Data Isolation**: Project-specific data isolation
- **No Telemetry**: No data sent to external services without explicit configuration

## 📜 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [Claude](https://claude.ai) by Anthropic for amazing AI capabilities
- [Google Gemini](https://deepmind.google/technologies/gemini/) for large context support
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Typer](https://typer.tiangolo.com/) for the modern CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [uv](https://docs.astral.sh/uv/) for fast Python package management

## 🔮 Roadmap

### Upcoming Features
- [ ] **More AI Models**: OpenAI GPT, Anthropic API, local models
- [ ] **Distributed Processing**: Multi-machine agent pools
- [ ] **Advanced Scheduling**: Cron-like scheduling for recurring tasks
- [ ] **Plugin System**: Extensible plugin architecture
- [ ] **Docker Support**: Containerized deployment
- [ ] **Cloud Integration**: AWS/GCP/Azure integration
- [ ] **Visual Workflow Builder**: Drag-and-drop workflow creation
- [ ] **Team Collaboration**: Shared queues and team features

### Long-term Vision

Transform cuti into the ultimate AI agent orchestration platform, enabling teams to leverage multiple AI services collaboratively for complex development tasks, with intelligent routing, comprehensive monitoring, and seamless integration into existing workflows.

---

**Built with ❤️ for the AI-assisted development community**

*Star this repository if you find it useful!*