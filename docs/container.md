# Container Management

The `cuti container` command provides a seamless development environment with all dependencies pre-installed, including Claude CLI, Python tools, and cuti itself.

## Quick Start

```bash
# First time on macOS - automatic dependency installation
cuti container
# ✅ Detects missing dependencies (Homebrew, Docker, Colima)
# 🛠️  Offers to install them automatically
# 🚀 Launches container with all tools pre-installed

# Subsequent runs - instant launch
cuti container

# Clean all Docker resources
cuti container clean --all --force
```

## Commands

### `cuti container`
Launches an interactive development container with your current directory mounted as `/workspace`.

**Features:**
- Automatic Docker/Colima setup
- Pre-installed tools (Claude CLI, Python, Node.js, uv, etc.)
- Persistent Claude authentication
- Current directory mounted as workspace

### `cuti container clean`
Manages Docker cleanup and resource removal.

```bash
# Clean current project's container
cuti container clean

# Clean ALL Docker resources (containers, images, volumes)
cuti container clean --all

# Skip confirmation prompt
cuti container clean --all --force
```

### `cuti container status`
Shows the current status of your development container environment.

### `cuti container stop`
Stops any running containers for the current project.

## Claude Authentication

The container uses a separate authentication system to handle the difference between macOS (Keychain) and Linux (credentials file) storage.

### How Authentication Works

1. **Separate Config Directory**: Uses `~/.cuti/container/` for container-specific Claude configuration
2. **One-Time Setup**: Authenticate once, persists forever
3. **Isolated from Host**: Avoids conflicts with macOS Keychain

### First Time Setup

1. Run the container:
   ```bash
   cuti container
   ```

2. Inside the container, authenticate Claude (one time only):
   ```bash
   claude login
   ```

3. Complete authentication in your browser

### Subsequent Sessions

Authentication persists automatically:
```bash
cuti container
claude --version  # Already authenticated!
```

### Authentication Storage

- **Config directory**: `~/.cuti/container/`
- **Credentials file**: `~/.cuti/container/.credentials.json`
- **CLAUDE.md**: Automatically copied from host if exists

## Docker Setup

### Automatic Dependency Installation (macOS)

On macOS, cuti will automatically detect and offer to install missing dependencies:

```bash
# First time on a new Mac - cuti handles everything
cuti container
# ✅ Checks for Homebrew, Docker, and Colima
# 🛠️  Offers to install missing dependencies
# 🚀 Launches container when ready
```

**What cuti installs automatically:**
- **Homebrew**: Package manager for macOS (if missing)
- **Colima**: Lightweight Docker runtime (recommended)
- **Docker Desktop**: Alternative with GUI (user choice)

### Manual Installation Options

If you prefer to install manually:

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Option 1: Install Colima (recommended)
brew install colima

# Option 2: Install Docker Desktop
brew install docker
```

### Manual Docker Control

```bash
# Start Colima manually
colima start

# Or use Docker Desktop
# Open Docker.app
```

## Container Features

### Pre-installed Tools
- **Claude CLI**: AI assistant with persistent auth
- **Python 3.11**: With uv package manager
- **Node.js 20**: With npm, yarn, pnpm
- **Development tools**: git, ripgrep, fd, bat, jq
- **Shell**: Zsh with Oh My Zsh

### Mounted Directories
- **Workspace**: Current directory → `/workspace`
- **Claude Config**: `~/.cuti/container/` → `/root/.claude`
- **Cuti Config**: `~/.cuti/` → `/root/.cuti-global`

### Environment Variables
- `CUTI_IN_CONTAINER=true`
- `CLAUDE_CONFIG_DIR=/root/.claude`
- `PYTHONUNBUFFERED=1`

## Project Types

The container automatically detects and configures based on your project:

- **Python**: Installs dependencies from `requirements.txt` or `pyproject.toml`
- **JavaScript**: Installs from `package.json` using npm/yarn/pnpm
- **Full-stack**: Handles both Python and JavaScript dependencies
- **General**: Basic development environment

## Troubleshooting

### Claude Not Authenticated

1. Check if credentials exist:
   ```bash
   ls ~/.cuti/container/.credentials.json
   ```

2. If missing, run `claude login` once inside the container

3. Credentials will persist in `~/.cuti/container/`

### Docker Issues

```bash
# Check Docker status
docker version

# Start Colima
colima start

# Clean up if needed
cuti container clean --all --force
```

### Container Won't Start

1. Clean Docker resources:
   ```bash
   cuti container clean --all --force
   ```

2. Rebuild container:
   ```bash
   cuti container --init
   ```

## Technical Details

### Architecture

The container system uses:
- **Base Image**: Python 3.11 on Debian Bullseye
- **Multi-stage Build**: Optimized for size and speed
- **Volume Mounts**: For workspace and configuration persistence
- **Separate Auth**: Isolated container credentials to avoid OS conflicts

### Why Separate Authentication?

- **macOS Claude**: Uses Keychain (not portable to Linux containers)
- **Linux Claude**: Uses `.credentials.json` file (portable)
- **Solution**: Separate `~/.cuti/container/` directory for container auth

### File Locations

| Purpose | Host Location | Container Location |
|---------|--------------|-------------------|
| Workspace | Current directory | `/workspace` |
| Claude Config | `~/.cuti/container/` | `/root/.claude` |
| Cuti Config | `~/.cuti/` | `/root/.cuti-global` |
| Python venv | Docker volume | `/workspace/.venv` |

## Advanced Usage

### Run Commands Directly

```bash
# Run a specific command in container
cuti container "python script.py"

# Run tests
cuti container "pytest"
```

### Initialize DevContainer Files

```bash
# Generate .devcontainer/ configuration
cuti container --init
```

This creates VS Code devcontainer configuration for your project.

### Skip Colima Auto-Setup

```bash
# If you manage Docker manually
cuti container --skip-colima
```