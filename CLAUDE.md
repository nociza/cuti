# Claude Code Configuration

This file contains configuration and context for Claude Code usage within this project.

## Project Overview

This is a production-ready cuti system that provides:

- **Queue Management**: Automatic handling of rate limits and retry logic
- **Prompt Aliases**: Pre-built aliases for common development tasks
- **Task Expansion**: Automatic breakdown of complex tasks into subtasks
- **Web Interface**: Modern FastAPI-based web UI with real-time updates
- **Monitoring**: Comprehensive system and usage monitoring
- **History Tracking**: SQLite-based prompt history with search capabilities

## Development Commands

### Setup and Installation
```bash
# Initial setup
python run.py setup

# Development installation with uv
uv install -e .

# Install dev dependencies
uv add --dev pytest pytest-asyncio black ruff mypy
```

### Testing and Quality
```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Code formatting
uv run black src/ tests/
uv run ruff check src/ tests/ --fix

# Linting
uv run ruff check src/ tests/
```

### Running the Application
```bash
# Start web interface
python run.py web

# Start CLI
python run.py cli

# Start queue processor  
python run.py start --verbose

# Check status
python run.py status
```

## Architecture

### Core Components
- **cli.py**: Modern Typer-based CLI interface
- **queue_manager.py**: Core queue processing logic
- **models.py**: Data models and enums
- **storage.py**: Persistent storage with markdown support
- **claude_interface.py**: Claude Code CLI integration
- **aliases.py**: Prompt alias management system
- **history.py**: SQLite-based history tracking
- **task_expansion.py**: Task breakdown engine
- **web/main.py**: FastAPI web application
- **web/monitoring.py**: System monitoring and metrics

### Storage Structure
```
~/.cuti/
├── queue/              # Active prompts
├── completed/          # Completed prompts  
├── failed/            # Failed prompts
├── aliases.json       # Prompt aliases
├── history.db         # SQLite history
├── metrics.db         # Monitoring data
└── queue-state.json   # Queue metadata
```

## Usage Patterns

### Common Aliases
- `explore-codebase`: Comprehensive code analysis
- `security-audit`: Security vulnerability assessment  
- `optimize-performance`: Performance optimization
- `write-tests`: Complete test suite creation
- `refactor-code`: Code quality improvements

### Custom Alias Creation
```bash
cuti alias create my-task "Custom task description with ${PROJECT_NAME}" \
  --description "My custom task" \
  --working-dir "." \
  --context-files "src/main.py"
```

### Task Expansion
Complex tasks are automatically broken down into:
- Subtasks with time estimates
- Dependency relationships
- Parallel execution opportunities  
- Risk assessments
- Success metrics

## Monitoring and Analytics

The system tracks:
- System performance (CPU, memory, disk, network)
- Token usage and costs
- Request success/failure rates
- Performance metrics
- Health status

Access via web interface at `/monitoring` or REST API at `/api/monitoring/*`

## Configuration

### Environment Variables
- `CLAUDE_QUEUE_STORAGE_DIR`: Custom storage location
- `CLAUDE_QUEUE_CLAUDE_COMMAND`: Claude CLI command
- `CLAUDE_QUEUE_WEB_HOST`: Web interface host
- `CLAUDE_QUEUE_WEB_PORT`: Web interface port

### Config File
Optional `~/.cuti/config.json` for detailed configuration.

## Performance Considerations

- Queue processes 10-50 prompts/hour (Claude rate limit dependent)
- Web interface handles 100+ concurrent users
- SQLite databases scale to millions of records
- Memory usage: 50-100MB typical
- Automatic cleanup of old metrics (90-day default)

## Security

- No sensitive data logged
- Local storage only (no external services)
- Rate limit respect prevents abuse
- Web interface CORS configurable
- No authentication required (designed for local use)

## Extension Points

The system is designed for extensibility:
- Custom aliases via JSON configuration
- Plugin-ready monitoring system
- REST API for integration
- WebSocket events for real-time updates
- Configurable task expansion templates