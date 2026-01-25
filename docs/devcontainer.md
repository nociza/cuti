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

### 🔐 Persistent Claude Authentication
- Separate Linux credentials in `~/.cuti/claude-linux/`
- No conflicts with macOS Keychain
- One-time authentication for all containers
- 📚 [Complete Authentication Guide](claude-container-auth.md)

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

### 🐳 Docker-in-Docker Support
- Docker CLI installed in container (not the daemon)
- Host Docker socket mounted at `/var/run/docker.sock`
- Automatic sudo wrapper if needed for permissions
- Run Docker commands that execute on host's Docker daemon
- Build images, run containers, use docker-compose - all from within the container
- Perfect for projects that need containerization during development

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

### Claude CLI Configuration

The container comes with Claude CLI pre-configured for optimal usage:

#### Automatic Permissions Bypass
- **Built-in Alias**: `claude` automatically includes `--dangerously-skip-permissions`
- No need to manually add the flag for every command
- Works seamlessly in the containerized environment

```bash
# These commands are equivalent in the container:
claude "Explain this code"                              # Uses alias (recommended)
claude --dangerously-skip-permissions "Explain this code"  # Explicit flag (not needed)
```

#### Why This Matters
- The `--dangerously-skip-permissions` flag is required in containers
- Without it, Claude may fail with permission errors
- The alias ensures Claude always works correctly
- Simplifies usage and prevents common errors

#### Rebuild to Apply Updates
If you're using an older container image, rebuild to get the alias:
```bash
cuti container --rebuild
```

### 🦞 Clawdbot Addon (preview)

The dev container now installs the optional [Clawdbot](https://clawdbot.com) CLI (default **enabled**). Use the new wrappers to manage onboarding, gateway, and messaging without leaving the `cuti` workflow:

```bash
cuti addons list                 # view/toggle addon state
cuti clawdbot onboard            # run Clawdbot wizard (auth, workspace, channels)
cuti clawdbot gateway --port 18789  # stream gateway logs until Ctrl+C
cuti clawdbot channels-login     # scan WhatsApp / authorize Telegram bots
cuti clawdbot send --to +15551234567 --message "Hello"
```

Exposed host mounts:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `~/.cuti/clawdbot/config/` | `/home/cuti/.clawdbot` | Gateway config + channel credentials |
| `~/.cuti/clawdbot/workspaces/<project-id>/` | `/home/cuti/clawd` | Agent workspace + history for that project |

`<project-id>` combines the project folder name with a short hash of its absolute path, so each cuti workspace keeps its own logs/history even when multiple containers run concurrently, while configs stay global.

See [docs/clawdbot.md](clawdbot.md) for channel-specific steps (WhatsApp QR, Telegram tokens, smoke tests).

### Docker-in-Docker Usage
```bash
# Build Docker images inside the container
cuti container --command "docker build -t myapp ."

# Run containers from within the container
cuti container --command "docker run -d redis:latest"
cuti container --command "docker ps"

# Use docker-compose
cuti container --command "docker-compose up -d"

# Interactive container with Docker support
cuti container
# Inside container:
docker images
docker run hello-world
docker-compose --version
```

## Architecture

### Container Images

#### `cuti-dev-universal` (Default for most projects)
- Base: `python:3.11-bullseye`
- Cuti: Installed from PyPI via `uv tool install cuti`
- Claude CLI: Latest version with auth propagation
- Docker CLI: Installed for Docker-in-Docker support
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
| `~/.cuti/claude-linux/` | `/home/cuti/.claude-linux` | Linux Claude credentials |
| `~/.claude/` | `/home/cuti/.claude-macos` | macOS config (read-only) |
| `~/.cuti/` | `/root/.cuti-global` | Global cuti config |
| `/var/run/docker.sock` | `/var/run/docker.sock` | Docker socket for Docker-in-Docker |

### Environment Variables

Automatically set in container:
- `CUTI_IN_CONTAINER=true` - Indicates running in container
- `CLAUDE_CONFIG_DIR=/home/cuti/.claude-linux` - Linux Claude config location
- `CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true` - Skip permission checks
- `PYTHONUNBUFFERED=1` - Python unbuffered output
- `TERM=xterm-256color` - Color terminal support
- `ANTHROPIC_API_KEY` - Loaded from environment or file if available

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

### Docker Socket Issues After Container Exit (Fixed)

Previous versions had an issue where exiting the container would break the Docker socket connection on macOS with Colima. This has been fixed by:
- Using `--init` flag for proper signal handling
- Not modifying Docker socket permissions inside the container
- Installing only Docker CLI (not the full Docker engine)
- Adding proper signal traps for clean exit

If you experience this issue with an older version, restart Colima:
```bash
colima restart
```

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

### Claude Authentication

**✅ Solved:** Claude authentication persists across all containers using separate Linux credentials.

**Quick Setup:**
1. Run `cuti container`
2. Inside container, run `claude login` (first time only)
3. Authentication persists for all future containers

**How it works:**
- Linux credentials stored in `~/.cuti/claude-linux/`
- macOS credentials remain in Keychain (no conflicts)
- Settings copied from macOS automatically

📚 **For detailed setup and troubleshooting, see [Claude Container Authentication Guide](claude-container-auth.md)**

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

### Docker-in-Docker Access

**How Docker access works in the container:**
- The container automatically detects if Docker socket requires sudo
- If needed, creates a wrapper script that adds sudo automatically
- You can use `docker` commands normally - sudo is handled transparently

**Docker commands work normally:**
```bash
# Inside container - these all work
docker ps
docker build -t myapp .
docker-compose up -d
```

**If Docker still shows "permission denied":**
1. The container should auto-configure this, but if not:
   ```bash
   sudo docker ps  # Test with sudo
   ```
2. Exit and restart the container - the wrapper will be created

**Docker daemon not accessible:**
- Ensure Docker/Colima is running on your host machine
- On macOS with Colima: `colima status` and `colima start` if needed
- On Linux: `sudo systemctl status docker`

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
- Claude automatically uses `--dangerously-skip-permissions` via alias (see [Claude CLI Configuration](#claude-cli-configuration))
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
