# Dev Container Documentation

The cuti dev container provides a fully configured development environment with cuti, Claude CLI, and all necessary tools pre-installed and configured.

## Quick Start

```bash
# Start an interactive container session (works from any directory)
cuti container

# Run a specific command in the container
cuti container --command "cuti web"
cuti container --command "claude 'Explain this project'"
```

## Key Features

### 🔐 Automatic Claude Authentication
- Claude configuration automatically propagates from your host machine
- No need to re-authenticate inside the container
- Uses `--dangerously-skip-permissions` flag for container compatibility
- Just run `claude` and it works

### 🎯 Smart Container Selection
- **Universal Container** (`cuti-dev-universal`): Used when running from any project directory
  - Installs cuti from PyPI via `uv tool install`
  - Perfect for using cuti with any project
  - Pre-configured with all tools
  
- **Development Container** (`cuti-dev-cuti`): Used when running from cuti source directory
  - Installs cuti from local source code
  - Ideal for cuti development and testing
  - Includes development dependencies

### 🎨 Custom Environment
- Custom prompt: `cuti:~/path $` for clear container identification
- Pre-configured with oh-my-zsh for better terminal experience
- All cuti commands available immediately
- Python 3.11, Node.js 20, and common development tools pre-installed

## Prerequisites

### macOS
```bash
# Install Colima (recommended Docker alternative for Mac)
brew install colima

# Start Colima
colima start

# Or use Docker Desktop
# Download from https://www.docker.com/products/docker-desktop
```

### Linux
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Windows
- Install Docker Desktop from https://www.docker.com/products/docker-desktop
- Or use WSL2 with Docker

## Usage Examples

### Interactive Development
```bash
# Start container from any project
cd ~/my-project
cuti container

# You'll see the custom prompt:
# cuti:/workspace $ 

# Inside container, all commands work:
cuti web          # Start web UI (accessible at http://localhost:8000)
cuti cli          # Start interactive CLI
cuti agent list   # List available agents
claude --help     # Use Claude CLI (already authenticated)
```

### Non-Interactive Commands
```bash
# Run cuti commands
cuti container --command "cuti add 'Review this code and suggest improvements'"
cuti container --command "cuti start"
cuti container --command "cuti status"

# Run Claude directly
cuti container --command "claude 'What does this project do?'"

# Run Python scripts
cuti container --command "python script.py"
```

### Web Development
```bash
# Start web UI in container (accessible from host)
cuti container --command "cuti web"
# Then open http://localhost:8000 in your browser

# Run development servers
cuti container --command "npm run dev"
cuti container --command "python manage.py runserver"
```

## Architecture

### Container Images

#### `cuti-dev-universal` (Default for most projects)
- Base: `python:3.11-bullseye`
- Cuti: Installed from PyPI via `uv tool install cuti`
- Claude CLI: Latest version with auth propagation
- Tools: git, zsh, ripgrep, fd-find, bat, jq, curl, wget
- Python: uv package manager, pytest, httpx, fastapi, uvicorn
- Node.js: v20 with latest npm
- Shell: Zsh with oh-my-zsh and custom cuti prompt

#### `cuti-dev-cuti` (For cuti development)
- Same base as universal
- Cuti: Installed from local source code
- Includes all cuti development dependencies
- Used automatically when running from cuti source directory

### Volume Mounts

The container automatically mounts:
| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| Current directory | `/workspace` | Your project files |
| `~/.claude/` | `/host/.claude` | Claude configuration |
| `~/.claude.json` | `/host/.claude.json` | Claude settings |
| `~/.cuti/` | `/root/.cuti-global` | Global cuti config |

### Environment Variables

Automatically set in container:
- `CUTI_IN_CONTAINER=true` - Indicates running in container
- `CLAUDE_CONFIG_DIR=/host/.claude` - Claude config location
- `CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true` - Skip permission checks
- `PYTHONUNBUFFERED=1` - Python unbuffered output
- `TERM=xterm-256color` - Color terminal support

### Network Configuration

Container runs with `--network host` for easy service access:
- Port 8000: cuti web interface
- Port 8080: Alternative web services
- Port 3000: Frontend dev servers
- Port 5000: Flask/FastAPI apps
- Port 5173: Vite dev server

## Project Type Detection

When generating dev containers, cuti automatically detects:

| Project Type | Detection Files | Additional Tools |
|-------------|----------------|------------------|
| Python | `pyproject.toml`, `requirements.txt` | pytest, black, ruff, mypy |
| JavaScript | `package.json` | yarn, pnpm, typescript, nodemon |
| Full-stack | Both Python + JS files | All Python + JS tools |
| Ruby | `Gemfile` | Ruby, Bundler |
| Go | `go.mod` | Go 1.21+ |
| Rust | `Cargo.toml` | Rust, Cargo |
| General | None of above | Basic dev tools |

## Troubleshooting

### Container Won't Start

1. **Check Docker/Colima is running:**
```bash
# For Colima
colima status

# For Docker
docker version
```

2. **Start if needed:**
```bash
# Colima (macOS)
colima start

# Docker Desktop - start from application
```

3. **Verify image exists:**
```bash
docker images | grep cuti-dev
```

### Claude Authentication Issues

**Important Note:** Claude Code uses a browser-based authentication system with limitations in containerized environments. Authentication tokens are session-based and not easily transferable to containers.

#### What's Implemented:
- Claude CLI is installed and available in the container
- `IS_SANDBOX=1` environment variable enables `--dangerously-skip-permissions` for root users
- Your `.claude` configuration directory is mounted to the container
- Commands like `claude --version` and `claude --help` work correctly

#### Current Limitations:
- `claude login` requires a browser and won't work in containers
- Authentication tokens are not stored in mountable config files
- The `setup-token` command requires an interactive terminal
- Even with config mounted, authentication doesn't transfer to the container

#### Technical Details:
The container uses:
- `IS_SANDBOX=1` to allow `--dangerously-skip-permissions` as root
- Mounts `~/.claude` to `/root/.claude` in the container
- Custom wrapper script at `/usr/local/bin/claude`

#### Workarounds:
1. **Use Claude on your host machine** for authenticated operations
2. **Use Claude web interface** at https://claude.ai
3. **Use Claude API** with API keys for programmatic access

#### Container Claude Status:
```bash
# Check Claude installation in container
cuti container "claude --version"

# Output:
# ✅ Claude configuration directory found
# 1.0.80 (Claude Code)

# Try to use Claude (will show auth error)
cuti container "claude --print 'Hello'"

# Output:
# Invalid API key · Please run /login
```

Note: Full Claude authentication in containers is a known limitation of the current Claude Code architecture. The container is prepared for when a solution becomes available.

### Cuti Not Found in Container

1. **Check which container is being used:**
```bash
docker images | grep cuti-dev
```

2. **Force rebuild:**
```bash
# Remove old images
docker rmi cuti-dev-universal cuti-dev-cuti

# Rebuild
cuti container
```

3. **Verify installation:**
```bash
docker run --rm cuti-dev-universal which cuti
docker run --rm cuti-dev-universal cuti --help
```

### "input device is not a TTY" Error

This occurs in non-interactive environments (like Claude Code). The container automatically detects and handles this - no action needed.

### Permission Issues

The container runs as root for simplicity. To fix file ownership after container use:

```bash
# On host after exiting container
sudo chown -R $(whoami) .
```

### Port Already in Use

If port 8000 is already in use:
```bash
# Find what's using the port
lsof -i :8000

# Kill the process or use different port
cuti container --command "cuti web --port 8001"
```

### Colima Specific Issues (macOS)

**Colima won't start:**
```bash
# Stop and clean
colima stop -f
colima delete

# Start with specific settings
colima start --arch aarch64 --vm-type vz --cpu 2 --memory 4
```

**Docker commands fail after Colima start:**
```bash
# Check Docker context
docker context ls

# Set to use Colima
docker context use colima
```

## Advanced Usage

### Custom Dockerfile

After generating dev container files:

```bash
# Generate container configuration
cuti devcontainer generate

# Edit .devcontainer/Dockerfile to add custom tools
# Then rebuild
docker build -t my-custom-cuti -f .devcontainer/Dockerfile .
```

### VS Code Integration

1. Install "Dev Containers" extension
2. Run `cuti devcontainer generate` in your project
3. Command Palette: "Dev Containers: Reopen in Container"
4. VS Code uses the generated configuration

### Running Services

```bash
# Database in background
cuti container --command "docker run -d postgres:15"

# Redis
cuti container --command "docker run -d redis:7"

# Your app
cuti container --command "cuti web"
```

### Persistent Data

Create named volumes for persistence:
```bash
# Create volume
docker volume create myproject-data

# Use in container
docker run -v myproject-data:/data ...
```

## Command Reference

### Main Commands

```bash
# Interactive container
cuti container

# Run specific command
cuti container --command "COMMAND"

# Generate dev container files
cuti devcontainer generate [--type TYPE]

# Clean up
cuti devcontainer clean
```

### Docker Management

```bash
# List cuti images
docker images | grep cuti

# Remove cuti images
docker rmi cuti-dev-universal cuti-dev-cuti

# Clean all Docker resources
docker system prune -a

# Check container logs
docker logs [container-name]

# Execute command in running container
docker exec -it [container-name] bash
```

## Implementation Details

### Container Build Process

1. **Detection**: Determines if running from cuti source or other project
2. **Image Selection**: Chooses `cuti-dev-universal` or `cuti-dev-cuti`
3. **Build Check**: Checks if image exists, builds if missing
4. **Mount Setup**: Configures volume mounts for project and configs
5. **Environment**: Sets environment variables
6. **Execution**: Runs container with appropriate flags

### File Locations

- Dockerfile templates: `src/cuti/services/devcontainer.py`
- Universal Dockerfile: `.devcontainer/Dockerfile.universal`
- Development Dockerfile: `.devcontainer/Dockerfile`
- Generated files: `.devcontainer/` in your project

### Security Considerations

- Containers run with `--privileged` for full functionality
- Claude uses `--dangerously-skip-permissions` only in containers
- Config directories mounted with appropriate permissions
- No telemetry or external connections
- Local-first approach

## Contributing

To improve dev container support:

1. Edit `src/cuti/services/devcontainer.py`
2. Update Dockerfile templates
3. Test with both container types:
   ```bash
   # Test universal container
   cd ~/some-project
   cuti container
   
   # Test development container  
   cd ~/cuti-source
   cuti container
   ```
4. Submit PR with test results

## Related Documentation

- [Todo System](todo-system.md) - Task management in cuti
- [Rate Limit Handling](rate-limit-handling.md) - How cuti handles API limits
- [Main README](../README.md) - Project overview

## License

Part of the cuti project - MIT License