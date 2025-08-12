# cuti DevContainer Support

## Overview

cuti provides automatic dev container generation and management for ANY project, with Colima support on macOS and automatic permission handling for Claude Code.

## Features

- Automatic Container Generation: Creates optimized dev containers for any project type
- Colima Support: Uses Colima as the container runtime on macOS
- Automatic Permissions: Claude Code runs with `--dangerously-skip-permissions` in containers
- Project Detection: Automatically detects Python, Node.js, Ruby, Go, Rust projects
- Dependency Management: Installs project dependencies automatically
- Zero Configuration: Works out of the box with sensible defaults

## Quick Start

### 1. Run cuti in a Container (Easiest)

```bash
# In any project directory
cuti container

# This will:
# - Generate a dev container if it doesn't exist
# - Start Colima if on macOS
# - Build and run the container
# - Start cuti web interface inside the container
```

### 2. Initialize DevContainer Only

```bash
# Generate dev container configuration
cuti devcontainer init

# Or specify project type
cuti devcontainer init --type python
```

### 3. Start DevContainer

```bash
# Start the container and get an interactive shell
cuti devcontainer start

# Or run a specific command
cuti devcontainer start "cuti web"
```

## How It Works

### Container Generation

When you run `cuti container` or `cuti devcontainer init`, cuti will:

1. Detect Project Type: Analyzes your project files (package.json, pyproject.toml, etc.)
2. Generate Dockerfile: Creates an optimized Dockerfile with:
   - Python 3.11 base image
   - Node.js installation
   - Claude Code CLI with permissions flag
   - Project-specific tools (uv, npm, yarn, etc.)
   - Non-root user with sudo access
3. Create devcontainer.json: VS Code compatible configuration
4. Setup Scripts: Initialization scripts for dependencies

### Colima Integration

On macOS, cuti automatically:
- Detects if Colima is installed
- Starts Colima if not running
- Configures with optimal settings (4 CPU, 8GB RAM, 60GB disk)

### Permission Handling

Inside containers:
- Claude Code automatically uses `--dangerously-skip-permissions`
- No permission prompts or issues
- Full access to project files
- Seamless integration with cuti

## Project Types

cuti automatically detects and configures for:

| Project Type | Detection | Additional Setup |
|-------------|-----------|------------------|
| Python | `pyproject.toml`, `requirements.txt` | uv, black, ruff, pytest |
| JavaScript | `package.json` | yarn, pnpm, typescript, nodemon |
| Full-stack | `package.json` + `pyproject.toml` | Both Python and JS tools |
| Ruby | `Gemfile` | Ruby, Bundler |
| Go | `go.mod` | Go 1.21+ |
| Rust | `Cargo.toml` | Rust, Cargo |
| General | Default | Basic development tools |

## Commands

### Main Commands

```bash
# Quick start - run cuti in container
cuti container [COMMAND]

# Initialize dev container
cuti devcontainer init [--type TYPE] [--force]

# Start dev container
cuti devcontainer start [COMMAND] [--build/--no-build]

# Stop running container
cuti devcontainer stop

# Check status
cuti devcontainer status

# Clean up
cuti devcontainer clean
```

### Examples

```bash
# Run cuti web interface in container
cuti container

# Run specific command in container
cuti container "cuti add 'Fix the bug in auth.py'"

# Initialize for Python project
cuti devcontainer init --type python

# Start container with custom command
cuti devcontainer start "python manage.py runserver"

# Check if running in container
cuti devcontainer status
```

## Environment Variables

Inside the container, these variables are set:

- `CUTI_IN_CONTAINER=true` - Indicates running in container
- `CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true` - Skip Claude permissions
- `PYTHONUNBUFFERED=1` - Python unbuffered output
- `TERM=xterm-256color` - Color terminal support

## VS Code Integration

The generated dev container is fully compatible with VS Code:

1. Open your project in VS Code
2. Install "Dev Containers" extension
3. Command Palette: "Dev Containers: Reopen in Container"
4. VS Code will use the generated configuration

### Included Extensions

- Python + Pylance
- GitHub Copilot
- GitLens
- ESLint + Prettier (for JS projects)
- And more based on project type

## Mounts and Volumes

The container automatically mounts:

- Project Files: `/workspace` (your project)
- Claude Config: `~/.claude` → `/home/cuti/.claude`
- Global cuti: `~/.cuti` → `/home/cuti/.cuti-global`
- Python venv: Persistent volume for virtual environment
- Cache: Persistent volume for package caches

## Troubleshooting

### Colima Not Starting

```bash
# Install Colima
brew install colima

# Start manually with custom settings
colima start --cpu 4 --memory 8 --disk 60

# Check status
colima status
```

### Permission Issues

The container runs with:
- Privileged mode for full access
- Non-root user with sudo
- Claude with `--dangerously-skip-permissions`

If you still have issues:
```bash
# Rebuild container
cuti devcontainer start --build

# Or clean and restart
cuti devcontainer clean
cuti devcontainer init --force
```

### Port Forwarding

Default forwarded ports:
- 8000 - cuti web interface
- 8080 - Alternative web
- 3000 - Frontend dev server
- 5000 - Flask/FastAPI
- 5173 - Vite

Add more in `.devcontainer/devcontainer.json`:
```json
"forwardPorts": [8000, 8080, 3000, 5000, 5173, 9000]
```

### Container Not Building

```bash
# Check Docker/Colima
docker version
colima status

# View build logs
cd .devcontainer
docker build -t cuti-dev .

# Clean and retry
cuti devcontainer clean
cuti devcontainer init --force
```

## Advanced Usage

### Custom Dockerfile

Edit `.devcontainer/Dockerfile` after generation:

```dockerfile
# Add custom tools
RUN apt-get update && apt-get install -y postgresql-client

# Add custom Python packages
RUN pip install pandas numpy scikit-learn
```

### Custom Entry Point

Modify `.devcontainer/devcontainer.json`:

```json
{
  "postCreateCommand": "custom-setup.sh",
  "postStartCommand": "echo 'Custom start'",
  "postAttachCommand": "source .env && cuti web"
}
```

### Multi-Container Setup

Create `.devcontainer/docker-compose.yml`:

```yaml
version: '3.8'
services:
  cuti:
    build: .
    volumes:
      - ..:/workspace
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: password
  
  redis:
    image: redis:7
```

Then update `devcontainer.json`:
```json
{
  "dockerComposeFile": "docker-compose.yml",
  "service": "cuti"
}
```

## Benefits

### Why Use DevContainers?

1. Consistency: Same environment across all machines
2. Isolation: No conflicts with system packages
3. Permissions: No Claude permission issues
4. Portability: Share exact environment with team
5. Clean System: Keep your host system clean

### Why Colima?

- Lightweight Docker Desktop alternative
- Better performance on macOS
- Lower resource usage
- Open source
- Simple CLI interface

## Security Notes

- Containers run with `--privileged` for full functionality
- Claude uses `--dangerously-skip-permissions` only in containers
- Your home `.claude` directory is mounted read-only
- Non-root user with sudo access
- No telemetry or external connections

## Contributing

To improve devcontainer support:

1. Edit `src/cuti/services/devcontainer.py`
2. Add project type detection in `_detect_project_type()`
3. Add setup in `_generate_dockerfile()`
4. Test with `cuti devcontainer init --type YOUR_TYPE`

## License

Part of the cuti project - MIT License


