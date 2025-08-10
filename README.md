# cuti

> **Production-ready cuti system with prompt aliases, task expansion, web interface, and comprehensive monitoring.**

A sophisticated queue management system for Claude Code that automatically handles rate limits, provides powerful prompt aliases for common development scenarios, expands complex tasks into manageable subtasks, and offers both CLI and modern web interfaces with real-time monitoring.

## 🚀 Quick Start with uvx

The fastest way to get started:

```bash
# Clone and set up
git clone <repository-url>
cd cuti

# Quick setup with uvx
uvx run ./run.py setup

# Start the web interface  
uvx run ./run.py web

# Or use the modern CLI
uvx run ./run.py cli --help
```

Open http://127.0.0.1:8000 in your browser for the full web interface!

## ✨ Features

### 🎯 Core Queue Management

- **Smart Rate Limit Handling**: Automatically detects and waits for Claude Code rate limit resets
- **Priority System**: Execute high-priority prompts first
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Persistent Storage**: Queue survives system restarts
- **Markdown Templates**: Rich prompt templates with YAML frontmatter

### 🔗 Prompt Aliases System

- **Pre-built Aliases**: 10+ ready-to-use aliases for common development tasks
- **Custom Aliases**: Create your own reusable prompt templates
- **Variable Substitution**: Dynamic variables like `${PROJECT_NAME}`, `${DATE}`
- **Alias Chaining**: Reference other aliases with `@alias-name` syntax

#### Built-in Development Aliases

| Alias                    | Description                                           | Use Case                   |
| ------------------------ | ----------------------------------------------------- | -------------------------- |
| `explore-codebase`     | Comprehensive codebase analysis and documentation     | Understanding new projects |
| `document-api`         | Generate OpenAPI/Swagger documentation                | API documentation          |
| `security-audit`       | Comprehensive security vulnerability assessment       | Security reviews           |
| `optimize-performance` | Performance analysis and optimization recommendations | Performance tuning         |
| `write-tests`          | Complete test suite creation (unit/integration/e2e)   | Test automation            |
| `refactor-code`        | Code quality improvement and refactoring              | Code maintenance           |
| `setup-cicd`           | CI/CD pipeline configuration                          | DevOps automation          |
| `add-logging`          | Structured logging implementation                     | Observability              |
| `fix-bugs`             | Systematic bug identification and resolution          | Bug fixing                 |
| `modernize-stack`      | Technology stack modernization                        | Tech debt                  |

### 📊 Task Expansion Engine

- **Smart Task Breakdown**: Automatically breaks complex tasks into manageable subtasks
- **Complexity Analysis**: Analyzes task complexity and estimates effort
- **Dependency Management**: Identifies task dependencies and execution order
- **Parallel Execution**: Identifies tasks that can run in parallel
- **Risk Assessment**: Identifies potential risks and success metrics
- **Template System**: Uses templates for common task patterns

### 🌐 Modern Web Interface

- **Real-time Dashboard**: Live queue status and system metrics
- **Interactive Management**: Add, cancel, and monitor prompts
- **Alias Management**: Create and manage prompt aliases
- **History Tracking**: Searchable prompt history with analytics
- **System Monitoring**: CPU, memory, disk, and network monitoring
- **Performance Metrics**: Token usage tracking and cost estimation

### 📱 Enhanced CLI Experience

- **Rich Terminal UI**: Beautiful tables, colors, and icons using Rich
- **Intuitive Commands**: Modern CLI with Typer framework
- **JSON Output**: Machine-readable output for scripting
- **Progress Indicators**: Visual progress bars and spinners

### 📈 Comprehensive Monitoring

- **System Metrics**: CPU, memory, disk, and network monitoring
- **Token Usage Tracking**: Detailed token consumption and cost analysis
- **Performance Analytics**: Response times, success rates, and throughput
- **Health Checks**: Automated system health monitoring
- **Event Logging**: Comprehensive event logging with severity levels
- **Data Export**: Export metrics in JSON/CSV formats

### 💾 Prompt History System

- **SQLite Storage**: Fast, reliable prompt history storage
- **Smart Search**: Full-text search across prompt content and metadata
- **Similarity Detection**: Find similar prompts to avoid duplication
- **Tagging System**: Organize prompts with custom tags
- **Usage Statistics**: Detailed analytics on prompt patterns
- **Data Export**: Export history for analysis and backup

## 📋 Installation

### Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

### Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

### Install cuti

#### Option 1: Development Setup (Recommended)

```bash
git clone <repository-url>
cd claude-code-queue
python run.py setup
```

#### Option 2: Direct Installation with uv

```bash
uv add git+<repository-url>
```

#### Option 3: Traditional pip Installation

```bash
pip install git+<repository-url>
```

## 🎮 Usage

### Web Interface (Recommended)

Start the modern web interface:

```bash
# Using run.py
python run.py web

# Or directly
claude-queue web --host 0.0.0.0 --port 8000
```

Features:

- 📊 **Real-time Dashboard**: Live metrics and queue status
- ➕ **Quick Actions**: Add prompts, expand tasks, manage queue
- 🔗 **Alias Management**: Create and manage prompt aliases
- 📚 **History Browser**: Search and analyze prompt history
- 📈 **Monitoring**: System performance and token usage tracking
- 🔄 **WebSocket Updates**: Real-time updates without page refresh

### CLI Interface

The enhanced CLI provides a rich terminal experience:

```bash
# Quick status check
claude-queue status --detailed

# Add a prompt using an alias
claude-queue add "explore-codebase" --priority 1

# Start the queue processor
claude-queue start --verbose

# Manage aliases
claude-queue alias create my-task "Implement user authentication with JWT tokens"
claude-queue alias list

# Search history
claude-queue history search "authentication" 
claude-queue history list --limit 10

# Task expansion
claude-queue expand "Build a REST API for user management"
```

### Prompt Aliases in Action

#### Using Built-in Aliases

```bash
# Comprehensive codebase analysis
claude-queue add "explore-codebase" --working-dir /path/to/project

# Security audit with automatic context
claude-queue add "security-audit" --priority 1

# Performance optimization analysis  
claude-queue add "optimize-performance"
```

#### Creating Custom Aliases

```bash
# Create a reusable deployment alias
claude-queue alias create deploy-app \
  "Deploy the ${PROJECT_NAME} application to production. Include: 1) Pre-deployment checks 2) Database migrations 3) Blue-green deployment 4) Health checks 5) Rollback plan" \
  --description "Production deployment checklist" \
  --working-dir "." \
  --context-files "deploy/config.yml" "scripts/deploy.sh"

# Use the custom alias
claude-queue add "deploy-app"
```

#### Variable Substitution

Aliases support dynamic variables:

- `${PROJECT_NAME}` - Current project/directory name
- `${WORKING_DIR}` - Working directory path
- `${DATE}` - Current date (YYYY-MM-DD)
- `${DATETIME}` - Current datetime (YYYY-MM-DD HH:MM:SS)

### Task Expansion

Transform high-level tasks into detailed execution plans:

```bash
# Expand a complex task
claude-queue expand "Build a production-ready web application with user authentication"
```

This automatically generates:

- ✅ **Subtask Breakdown**: Detailed subtasks with time estimates
- 🔄 **Dependency Mapping**: Task dependencies and execution order
- ⚡ **Parallel Execution**: Tasks that can run simultaneously
- ⚠️ **Risk Assessment**: Potential risks and mitigation strategies
- 🎯 **Success Metrics**: Measurable success criteria

### Advanced Queue Management

#### Template-based Prompts

Create rich prompt templates:

```bash
claude-queue template feature-implementation --priority 1
```

Edit the generated `.md` file:

```markdown
---
priority: 1
working_directory: /project/path
context_files:
  - src/main.py
  - docs/requirements.md
max_retries: 3
estimated_tokens: 2000
---

# Feature Implementation

Implement the user dashboard feature with the following requirements:

## Context
- Integration with existing authentication system
- Mobile-responsive design
- Real-time data updates

## Deliverables
- React components for dashboard
- API endpoints for data fetching  
- Unit and integration tests
- Updated documentation

## Acceptance Criteria
- [ ] Dashboard loads within 2 seconds
- [ ] Works on mobile devices
- [ ] All tests pass
- [ ] Code review approved
```

#### Monitoring and Analytics

View comprehensive monitoring data:

```bash
# System health check
curl http://localhost:8000/api/monitoring/system

# Token usage analytics  
curl http://localhost:8000/api/monitoring/tokens

# Performance metrics
curl http://localhost:8000/api/monitoring/performance
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
```

### Configuration File

Create `~/.claude-queue/config.json`:

```json
{
  "claude_command": "claude",
  "check_interval": 30,
  "timeout": 3600,
  "max_retries": 3,
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
  "aliases": {
    "auto_create_defaults": true,
    "allow_overrides": false
  }
}
```

## 📁 Project Structure

```
claude-code-queue/
├── src/cuti/
│   ├── cli.py                 # Modern CLI interface
│   ├── queue_manager.py       # Core queue management  
│   ├── models.py             # Data models
│   ├── storage.py            # Persistent storage
│   ├── claude_interface.py   # Claude Code integration
│   ├── aliases.py            # Prompt aliases system
│   ├── history.py            # Prompt history management
│   ├── task_expansion.py     # Task breakdown engine
│   └── web/
│       ├── main.py           # FastAPI web application
│       └── monitoring.py     # System monitoring
├── run.py                    # Main entry point
├── pyproject.toml           # Modern Python packaging
└── README.md               # This file
```

## 🗄️ Storage Structure

```
~/.claude-queue/
├── queue/                   # Pending prompts
│   ├── 001-feature.md
│   └── 002-bugfix.executing.md
├── completed/               # Successful executions
│   └── 001-feature-completed.md  
├── failed/                  # Failed prompts
│   └── 003-failed-task.md
├── aliases.json            # Prompt aliases
├── history.db             # SQLite prompt history  
├── metrics.db             # SQLite monitoring data
├── task_templates.json    # Task expansion templates
└── queue-state.json       # Queue metadata
```

## 🔧 API Reference

### REST API Endpoints

#### Queue Management

- `GET /api/queue/status` - Get queue status and statistics
- `GET /api/queue/prompts` - List all prompts
- `POST /api/queue/prompts` - Add new prompt
- `DELETE /api/queue/prompts/{id}` - Cancel prompt

#### Alias Management

- `GET /api/aliases` - List all aliases
- `POST /api/aliases` - Create new alias
- `GET /api/aliases/{name}` - Get specific alias
- `DELETE /api/aliases/{name}` - Delete alias

#### History & Analytics

- `GET /api/history` - Get prompt history
- `GET /api/history/search?query={q}` - Search history
- `GET /api/history/stats` - Get history statistics

#### Task Expansion

- `POST /api/tasks/expand` - Expand task into subtasks

#### Monitoring

- `GET /api/monitoring/system` - System metrics
- `GET /api/monitoring/tokens` - Token usage statistics
- `GET /api/monitoring/performance` - Performance metrics

### WebSocket Events

- `status_update` - Real-time queue status updates
- `prompt_completed` - Prompt completion notifications
- `system_alert` - System health alerts

## 🧪 Development

### Setup Development Environment

```bash
git clone <repository-url>
cd claude-code-queue
python run.py setup

# Install development dependencies  
uv add --dev pytest pytest-asyncio black ruff mypy

# Run tests
uv run pytest

# Code formatting
uv run black .
uv run ruff check .
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_aliases.py

# With coverage
uv run pytest --cov=cuti
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Format code: `uv run black . && uv run ruff check .`
5. Run tests: `uv run pytest`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 🚨 Troubleshooting

### Common Issues

**Queue not processing:**

```bash
# Check Claude Code connection
claude-queue test

# Check queue status  
claude-queue status --detailed

# Restart queue processor
claude-queue start --verbose
```

**Web interface not starting:**

```bash
# Check if port is available
lsof -i :8000

# Try different port
claude-queue web --port 8080

# Check logs for errors
claude-queue web --log-level debug
```

**Rate limit issues:**

- The system automatically handles rate limits
- Check rate limit status: `claude-queue status`
- Prompts will automatically retry after cooldown period

**Alias not resolving:**

```bash
# List available aliases
claude-queue alias list

# Check specific alias
claude-queue alias show alias-name

# Test alias resolution
claude-queue add "alias-name" --dry-run
```

## 📊 Performance & Scaling

### Performance Characteristics

- **Queue Processing**: ~10-50 prompts/hour (depends on Claude Code limits)
- **Web Interface**: Handles 100+ concurrent connections
- **Database**: SQLite handles millions of history records efficiently
- **Memory Usage**: ~50-100MB typical usage
- **CPU Usage**: Minimal when idle, 10-30% during active processing

### Scaling Recommendations

- Use SSD storage for better database performance
- Monitor disk space (history and metrics grow over time)
- Configure appropriate retention policies
- Use reverse proxy (nginx) for production web deployments
- Consider database cleanup automation for long-running instances

## 📜 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [Claude](https://claude.ai) for the amazing AI capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Typer](https://typer.tiangolo.com/) for the modern CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [uv](https://docs.astral.sh/uv/) for fast Python package management

## 🔮 Roadmap

### Upcoming Features

- [ ] **Multi-Model Support**: Support for other AI models beyond Claude
- [ ] **Team Collaboration**: Shared queues and collaboration features
- [ ] **Advanced Scheduling**: Cron-like scheduling for recurring prompts
- [ ] **Plugin System**: Extensible plugin architecture
- [ ] **Docker Support**: Containerized deployment options
- [ ] **Cloud Integration**: AWS/GCP/Azure integration
- [ ] **Workflow Automation**: Visual workflow builder
- [ ] **Advanced Analytics**: ML-powered usage insights

### Long-term Vision

Transform cuti into the ultimate AI-powered development workflow platform, enabling teams to automate complex development tasks, maintain high code quality, and accelerate delivery through intelligent task management and execution.

---

**Made with ❤️ for the Claude Code community**

*Star this repository if you find it useful!*
