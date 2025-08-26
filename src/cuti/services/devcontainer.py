"""
DevContainer Service for cuti
Automatically generates and manages dev containers for any project with Colima support.
"""

import json
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import platform

try:
    from rich.console import Console
    from rich.prompt import Confirm, IntPrompt
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


class DevContainerService:
    """Manages dev container generation and execution for any project."""
    
    # Simplified Dockerfile template
    DOCKERFILE_TEMPLATE = '''FROM python:3.11-bullseye

# Build arguments
ARG USERNAME=cuti
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \\
    && apt-get -y install --no-install-recommends \\
        curl ca-certificates git sudo zsh wget build-essential \\
        procps lsb-release locales fontconfig gnupg2 jq \\
        ripgrep fd-find bat \\
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \\
    && apt-get install -y nodejs \\
    && npm install -g npm@latest

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Create non-root user with sudo access
RUN groupadd --gid $USER_GID $USERNAME \\
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/zsh \\
    && echo $USERNAME ALL=\\(root\\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \\
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Install Claude Code CLI (version 1.0.60 for stability)
RUN npm install -g @anthropic-ai/claude-code@1.0.60 \\
    && echo '#!/bin/bash' > /usr/local/bin/claude \\
    && echo 'export IS_SANDBOX=1' >> /usr/local/bin/claude \\
    && echo 'export CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true' >> /usr/local/bin/claude \\
    && echo 'export CLAUDE_CONFIG_DIR=${CLAUDE_CONFIG_DIR:-/home/cuti/.claude}' >> /usr/local/bin/claude \\
    && echo 'exec node /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js "$@"' >> /usr/local/bin/claude \\
    && chmod +x /usr/local/bin/claude

{CUTI_INSTALL}

# Switch to non-root user
USER $USERNAME

# Install uv for the non-root user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/cuti/.local/bin:${PATH}"

# Ensure home directory permissions are correct
RUN chown -R cuti:cuti /home/cuti

# Install oh-my-zsh with simple configuration
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \\
    && echo 'export PATH="/usr/local/bin:/home/cuti/.local/bin:/root/.local/share/uv/tools/cuti/bin:$PATH"' >> ~/.zshrc \\
    && echo 'export PYTHONPATH="/workspace/src:$PYTHONPATH"' >> ~/.zshrc \\
    && echo 'export CUTI_IN_CONTAINER=true' >> ~/.zshrc \\
    && echo 'export ANTHROPIC_CLAUDE_BYPASS_PERMISSIONS=1' >> ~/.zshrc \\
    && echo 'export CLAUDE_CONFIG_DIR=/home/cuti/.claude' >> ~/.zshrc \\
    && echo 'echo "🚀 Welcome to cuti dev container!"' >> ~/.zshrc \\
    && echo 'echo "Commands: cuti web | cuti cli | claude"' >> ~/.zshrc

WORKDIR /workspace
SHELL ["/bin/zsh", "-c"]
CMD ["/bin/zsh", "-l"]
'''

    # Simplified devcontainer.json template
    DEVCONTAINER_JSON_TEMPLATE = {
        "name": "cuti Development Environment",
        "build": {
            "dockerfile": "Dockerfile",
            "context": ".",
            "args": {
                "USERNAME": "cuti",
                "USER_UID": "1000",
                "USER_GID": "1000"
            }
        },
        "runArgs": ["--init", "--privileged"],
        "containerEnv": {
            "CUTI_IN_CONTAINER": "true",
            "ANTHROPIC_CLAUDE_BYPASS_PERMISSIONS": "1",
            "PYTHONUNBUFFERED": "1"
        },
        "mounts": [
            "source=${localEnv:HOME}/.claude,target=/home/cuti/.claude,type=bind,consistency=cached",
            "source=cuti-cache-${localWorkspaceFolderBasename},target=/home/cuti/.cache,type=volume"
        ],
        "forwardPorts": [8000, 8080, 3000, 5000],
        "postCreateCommand": "echo '✅ Container initialized'",
        "remoteUser": "cuti"
    }
    
    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the dev container service."""
        self.working_dir = Path(working_directory) if working_directory else Path.cwd()
        self.devcontainer_dir = self.working_dir / ".devcontainer"
        self.is_macos = platform.system() == "Darwin"
        
        # Check tool availability (cached for CLI compatibility)
        self.docker_available = self._check_tool_available("docker")
        self.colima_available = self._check_tool_available("colima")
    
    def _run_command(self, cmd: List[str], timeout: int = 30, show_output: bool = False) -> subprocess.CompletedProcess:
        """Run a command with consistent error handling."""
        try:
            return subprocess.run(
                cmd,
                capture_output=not show_output,
                text=True,
                timeout=timeout,
                check=False
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            raise RuntimeError(f"Command not found: {cmd[0]}")
    
    def _check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available."""
        try:
            result = self._run_command([tool, "--version"])
            return result.returncode == 0
        except RuntimeError:
            return False
    
    def _check_colima(self) -> bool:
        """Check if Colima is available (backward compatibility method)."""
        return self._check_tool_available("colima")
    
    def _check_docker(self) -> bool:
        """Check if Docker is available (backward compatibility method)."""
        return self._check_tool_available("docker")
    
    def _prompt_install(self, tool: str, install_cmd: str) -> bool:
        """Prompt user to install a missing tool."""
        if not _RICH_AVAILABLE:
            print(f"Missing dependency: {tool}")
            response = input(f"Install {tool} with '{install_cmd}'? (y/N): ")
            return response.lower() in ['y', 'yes']
        
        console = Console()
        console.print(f"[yellow]Missing dependency: {tool}[/yellow]")
        return Confirm.ask(f"Install {tool} automatically?")
    
    def _install_with_brew(self, package: str) -> bool:
        """Install a package with Homebrew."""
        print(f"📦 Installing {package}...")
        result = self._run_command(["brew", "install", package], timeout=300, show_output=True)
        
        if result.returncode == 0:
            print(f"✅ {package} installed successfully")
            return True
        else:
            print(f"❌ Failed to install {package}")
            return False
    
    def ensure_dependencies(self) -> bool:
        """Ensure Docker/Colima is available."""
        # Check if Docker is already available
        if self._check_tool_available("docker"):
            return True
        
        # On macOS, try to install dependencies
        if self.is_macos:
            # Check Homebrew
            if not self._check_tool_available("brew"):
                if self._prompt_install("Homebrew", "Official install script"):
                    install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                    result = self._run_command(install_cmd.split(), timeout=600, show_output=True)
                    if result.returncode != 0:
                        return False
                else:
                    return False
            
            # Install Colima (lightweight Docker alternative)
            if self._prompt_install("Colima", "brew install colima"):
                return self._install_with_brew("colima")
        
        return False
    
    def setup_colima(self) -> bool:
        """Setup and start Colima if needed (legacy method for CLI compatibility)."""
        return self._start_colima()
    
    def _start_colima(self) -> bool:
        """Start Colima if not running."""
        if not self._check_tool_available("colima"):
            return False
        
        # Check if running
        result = self._run_command(["colima", "status"])
        if result.returncode == 0 and "running" in result.stdout.lower():
            return True
        
        print("🚀 Starting Colima...")
        
        # Detect architecture for optimal settings
        arch = platform.machine()
        if arch in ["arm64", "aarch64"]:
            cmd = ["colima", "start", "--arch", "aarch64", "--vm-type", "vz", "--cpu", "2", "--memory", "4"]
        else:
            cmd = ["colima", "start", "--cpu", "2", "--memory", "4"]
        
        result = self._run_command(cmd, timeout=120, show_output=True)
        if result.returncode == 0:
            print("✅ Colima started successfully")
            return True
        else:
            print("❌ Failed to start Colima")
            return False
    
    def _generate_dockerfile(self, project_type: str) -> str:
        """Generate Dockerfile based on project type."""
        # Check if this is the cuti project itself
        if (self.working_dir / "src" / "cuti").exists() and (self.working_dir / "pyproject.toml").exists():
            cuti_install = '''
# Install cuti from local source
COPY . /workspace
RUN cd /workspace \\
    && /root/.local/bin/uv pip install --system pyyaml rich 'typer[all]' fastapi uvicorn httpx \\
    && /root/.local/bin/uv pip install --system -e . \\
    && python -c "import cuti; print('✅ cuti installed from source')" \\
    && echo '#!/usr/local/bin/python' > /usr/local/bin/cuti \\
    && echo 'import sys' >> /usr/local/bin/cuti \\
    && echo 'sys.path.insert(0, "/workspace/src")  # Ensure local source takes precedence' >> /usr/local/bin/cuti \\
    && echo 'from cuti.cli.app import app' >> /usr/local/bin/cuti \\
    && echo 'if __name__ == "__main__":' >> /usr/local/bin/cuti \\
    && echo '    app()' >> /usr/local/bin/cuti \\
    && chmod +x /usr/local/bin/cuti
'''
        else:
            cuti_install = '''
# Install cuti from PyPI and make it accessible to all users
RUN /root/.local/bin/uv pip install --system cuti \\
    && echo '#!/usr/local/bin/python' > /usr/local/bin/cuti \\
    && echo 'import sys' >> /usr/local/bin/cuti \\
    && echo 'from cuti.cli.app import app' >> /usr/local/bin/cuti \\
    && echo 'if __name__ == "__main__":' >> /usr/local/bin/cuti \\
    && echo '    app()' >> /usr/local/bin/cuti \\
    && chmod +x /usr/local/bin/cuti \\
    && cuti --help > /dev/null && echo "✅ cuti installed from PyPI"
'''
        
        return self.DOCKERFILE_TEMPLATE.replace("{CUTI_INSTALL}", cuti_install)
    
    def _setup_claude_host_config(self):
        """Setup Claude configuration on host for container usage."""
        # Create container-specific Claude config directory
        container_claude_dir = Path.home() / ".cuti" / "container" / ".claude"
        container_claude_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories that Claude CLI expects
        for subdir in ["plugins", "plugins/repos", "todos", "sessions", "projects", 
                       "statsig", "shell-snapshots", "ide"]:
            (container_claude_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Set permissions to be writable for all users and files
        import stat
        try:
            # Make the directory world-writable to avoid UID/GID issues
            container_claude_dir.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            for item in container_claude_dir.rglob("*"):
                if item.is_dir():
                    item.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                else:
                    # Make files readable and writable by all
                    item.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
        except Exception as e:
            print(f"⚠️  Could not set permissions: {e}")
        
        # Copy important files from host .claude if they exist (one-time sync)
        host_claude_dir = Path.home() / ".claude"
        
        # Copy credentials (most important)
        host_credentials = host_claude_dir / ".credentials.json"
        container_credentials = container_claude_dir / ".credentials.json"
        if host_credentials.exists() and not container_credentials.exists():
            import shutil
            shutil.copy2(host_credentials, container_credentials)
            print("🔑 Synced Claude credentials from host to container config")
        
        # Copy CLAUDE.md if it exists
        host_claude_md = host_claude_dir / "CLAUDE.md"
        container_claude_md = container_claude_dir / "CLAUDE.md"
        if host_claude_md.exists() and not container_claude_md.exists():
            import shutil
            shutil.copy2(host_claude_md, container_claude_md)
            print("📄 Synced CLAUDE.md to container config")
        
        # Copy plugins config if it exists
        host_plugins_config = host_claude_dir / "plugins" / "config.json"
        container_plugins_config = container_claude_dir / "plugins" / "config.json"
        if host_plugins_config.exists() and not container_plugins_config.exists():
            import shutil
            shutil.copy2(host_plugins_config, container_plugins_config)
            print("🔌 Synced plugins config to container")
        
        # Create or update container-specific .claude.json
        container_claude_json = container_claude_dir / ".claude.json"
        config = {}
        if container_claude_json.exists():
            try:
                with open(container_claude_json, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        
        # Always ensure bypassPermissionsModeAccepted is set
        if not config.get('bypassPermissionsModeAccepted', False):
            config['bypassPermissionsModeAccepted'] = True
            with open(container_claude_json, 'w') as f:
                json.dump(config, f, indent=2)
        
        # Check if credentials exist
        if container_credentials.exists():
            print(f"✅ Container Claude config ready at {container_claude_dir}")
            print("🔑 Claude credentials available - no login needed!")
        else:
            print(f"⚠️  No saved credentials at {container_claude_dir}")
            print("   Authenticate once in container with: claude login")
            print("   Credentials will persist across all containers")
        
        return container_claude_dir
    
    def _build_container_image(self, image_name: str, rebuild: bool = False) -> bool:
        """Build the container image."""
        if rebuild:
            print("🔨 Rebuilding container (forced rebuild)...")
            self._run_command(["docker", "rmi", "-f", image_name])
        else:
            # Check if image exists
            result = self._run_command(["docker", "images", "-q", image_name])
            if result.stdout.strip():
                return True
            print("🔨 Building container (first time setup)...")
        
        # Create temporary Dockerfile
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_content = self._generate_dockerfile("general")
            dockerfile_path.write_text(dockerfile_content)
            
            # For source builds, copy the entire cuti project to build context
            build_context = tmpdir
            if (self.working_dir / "src" / "cuti").exists() and (self.working_dir / "pyproject.toml").exists():
                import shutil
                # Copy necessary files for cuti installation
                shutil.copy2(self.working_dir / "pyproject.toml", tmpdir)
                shutil.copytree(self.working_dir / "src", Path(tmpdir) / "src")
                if (self.working_dir / "uv.lock").exists():
                    shutil.copy2(self.working_dir / "uv.lock", tmpdir)
                if (self.working_dir / "README.md").exists():
                    shutil.copy2(self.working_dir / "README.md", tmpdir)
                # Copy docs directory if needed for build
                if (self.working_dir / "docs").exists():
                    shutil.copytree(self.working_dir / "docs", Path(tmpdir) / "docs")
            
            # Build image
            build_cmd = ["docker", "build", "-t", image_name, "-f", str(dockerfile_path), build_context]
            if rebuild:
                build_cmd.append("--no-cache")
            
            result = self._run_command(build_cmd, timeout=1800, show_output=True)
            if result.returncode == 0:
                print("✅ Container built successfully")
                return True
            else:
                print(f"❌ Container build failed: {result.stderr}")
                return False
    
    def generate_devcontainer(self, project_type: Optional[str] = None) -> bool:
        """Generate dev container configuration."""
        print(f"🔧 Generating dev container in {self.working_dir}")
        
        # Create .devcontainer directory
        self.devcontainer_dir.mkdir(exist_ok=True)
        
        # Detect project type if not specified
        if not project_type:
            project_type = self._detect_project_type()
        
        # Generate Dockerfile
        dockerfile_content = self._generate_dockerfile(project_type)
        dockerfile_path = self.devcontainer_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        print(f"✅ Created {dockerfile_path}")
        
        # Generate devcontainer.json
        devcontainer_json_path = self.devcontainer_dir / "devcontainer.json"
        devcontainer_json_path.write_text(json.dumps(self.DEVCONTAINER_JSON_TEMPLATE, indent=2))
        print(f"✅ Created {devcontainer_json_path}")
        
        return True
    
    def _detect_project_type(self) -> str:
        """Detect project type based on files."""
        if (self.working_dir / "package.json").exists():
            return "javascript" if not (self.working_dir / "pyproject.toml").exists() else "fullstack"
        elif (self.working_dir / "pyproject.toml").exists() or (self.working_dir / "requirements.txt").exists():
            return "python"
        elif (self.working_dir / "go.mod").exists():
            return "go"
        elif (self.working_dir / "Cargo.toml").exists():
            return "rust"
        else:
            return "general"
    
    def run_in_container(self, command: Optional[str] = None, rebuild: bool = False) -> int:
        """Run command in dev container."""
        # Ensure Docker is available
        if not self._check_tool_available("docker"):
            if not self.ensure_dependencies():
                print("❌ Docker not available and couldn't install dependencies")
                return 1
            
            # Try to start Colima if on macOS
            if self.is_macos and not self._start_colima():
                print("❌ Couldn't start container runtime")
                return 1
        
        # Check Docker Desktop file sharing settings on macOS
        if self.is_macos:
            print("📝 Note: If workspace is read-only, check Docker Desktop settings:")
            print("   1. Open Docker Desktop → Settings → Resources → File Sharing")
            print("   2. Ensure your project directory is in the shared paths")
            print("   3. Try 'osxfs' or 'VirtioFS' file sharing implementation")
            print("")
        
        # Build container if needed
        image_name = "cuti-dev-universal"
        if not self._build_container_image(image_name, rebuild):
            return 1
        
        # Setup Claude configuration on host
        container_claude_dir = self._setup_claude_host_config()
        
        # Run container
        print("🚀 Starting container...")
        current_dir = Path.cwd().resolve()
        
        # Try different mount options based on Docker runtime
        # Colima typically handles mounts better than Docker Desktop on macOS
        mount_options = "rw"  # Start with basic read-write
        if self.is_macos:
            # Check if using Colima (which typically works better with mounts)
            colima_status = self._run_command(["colima", "status"])
            if colima_status.returncode == 0 and "running" in colima_status.stdout.lower():
                print("🐳 Using Colima runtime")
                mount_options = "rw"  # Colima usually handles basic rw well
            else:
                print("🐳 Using Docker Desktop - trying cached mode for better macOS compatibility")
                mount_options = "rw,cached"  # Docker Desktop on macOS needs cached mode
        
        docker_args = [
            "docker", "run", "--rm", "--privileged", 
            "-v", f"{current_dir}:/workspace:{mount_options}",  # Dynamic mount options
            "-v", f"{Path.home() / '.cuti'}:/root/.cuti-global", 
            "-v", f"{container_claude_dir}:/host-claude-config:ro",  # Mount host's container claude dir as read-only
            "-w", "/workspace",
            "--env", "CUTI_IN_CONTAINER=true",
            # Don't set CLAUDE_QUEUE_STORAGE_DIR here - let the init script decide based on writability
            "--env", "IS_SANDBOX=1", 
            "--env", "CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true",
            # Don't set CLAUDE_CONFIG_DIR here - let the init script decide based on writability
            "--env", "PYTHONUNBUFFERED=1",
            "--env", "PYTHONPATH=/workspace/src",
            "--env", "TERM=xterm-256color",
            "--env", "PATH=/usr/local/bin:/home/cuti/.local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
            "--network", "host",
            image_name
        ]
        
        # Setup initialization command for mounted directory
        init_script = """
# Test if workspace is writable
if touch /workspace/.test_write 2>/dev/null; then
    rm /workspace/.test_write
    WORKSPACE_WRITABLE=true
    echo "✅ Workspace is writable - Claude can edit code!"
    # Use workspace directories when writable
    export CLAUDE_QUEUE_STORAGE_DIR=/workspace/.cuti
    export CLAUDE_CONFIG_DIR=/workspace/.claude
else
    WORKSPACE_WRITABLE=false
    echo "⚠️  WARNING: Workspace mounted as read-only!"
    echo "    This prevents Claude from editing your code."
    echo ""
    echo "    To fix this on macOS:"
    echo "    1. If using Docker Desktop:"
    echo "       - Go to Settings → Resources → File Sharing"
    echo "       - Add your project directory to shared folders"
    echo "       - Switch to 'VirtioFS' under Settings → General"
    echo "    2. Or use Colima instead (recommended):"
    echo "       - brew install colima"
    echo "       - colima start --mount-type 9p"
    echo ""
    # Fall back to home directories when read-only
    export CLAUDE_QUEUE_STORAGE_DIR=/home/cuti/.cuti
    export CLAUDE_CONFIG_DIR=/home/cuti/.claude
fi

# Copy mounted claude config to a writable location if needed
if [ -d /host-claude-config ]; then
    # Remove existing .claude directory if it's a symlink or directory
    rm -rf /home/cuti/.claude 2>/dev/null || true
    
    # Copy the mounted config to home directory
    cp -r /host-claude-config /home/cuti/.claude 2>/dev/null || true
    
    # Ensure proper ownership
    sudo chown -R cuti:cuti /home/cuti/.claude 2>/dev/null || true
    
    # Create necessary Claude directories if they don't exist
    mkdir -p /home/cuti/.claude/plugins/repos 2>/dev/null || true
    mkdir -p /home/cuti/.claude/todos 2>/dev/null || true
    mkdir -p /home/cuti/.claude/sessions 2>/dev/null || true
    mkdir -p /home/cuti/.claude/projects 2>/dev/null || true
    mkdir -p /home/cuti/.claude/statsig 2>/dev/null || true
    mkdir -p /home/cuti/.claude/shell-snapshots 2>/dev/null || true
    mkdir -p /home/cuti/.claude/ide 2>/dev/null || true
fi

# Handle workspace directories based on writability
if [ "$WORKSPACE_WRITABLE" = "true" ]; then
    # Create workspace directories if they don't exist
    mkdir -p /workspace/.claude 2>/dev/null || true
    mkdir -p /workspace/.cuti 2>/dev/null || true
    
    # Ensure proper ownership for workspace directories
    sudo chown -R cuti:cuti /workspace/.claude 2>/dev/null || true
    sudo chown -R cuti:cuti /workspace/.cuti 2>/dev/null || true
    
    # Copy credentials from host config if not present in workspace
    if [ ! -f /workspace/.claude/.credentials.json ] && [ -f /home/cuti/.claude/.credentials.json ]; then
        cp /home/cuti/.claude/.credentials.json /workspace/.claude/.credentials.json 2>/dev/null || true
    fi
    
    echo "📁 Using workspace directories for Claude and cuti"
else
    # If read-only, copy workspace config to home if exists
    if [ -d /workspace/.claude ]; then
        echo "📁 Copying workspace .claude to home (workspace is read-only)..."
        cp -rn /workspace/.claude/* /home/cuti/.claude/ 2>/dev/null || true
        sudo chown -R cuti:cuti /home/cuti/.claude 2>/dev/null || true
    fi
fi

# Copy CLAUDE.md from workspace if it exists and not already present
if [ -f /workspace/CLAUDE.md ] && [ ! -f /home/cuti/.claude/CLAUDE.md ]; then
    cp /workspace/CLAUDE.md /home/cuti/.claude/CLAUDE.md 2>/dev/null || true
fi

# Check for existing credentials in the appropriate location
if [ "$WORKSPACE_WRITABLE" = "true" ]; then
    if [ -f /workspace/.claude/.credentials.json ]; then
        echo "🔑 Found saved Claude credentials in workspace - no login needed!"
    elif [ -f /home/cuti/.claude/.credentials.json ]; then
        cp /home/cuti/.claude/.credentials.json /workspace/.claude/.credentials.json 2>/dev/null || true
        echo "🔑 Copied credentials to workspace"
    else
        echo "⚠️  No saved credentials. Authenticate once with: claude login"
        echo "   Your credentials will be saved in the workspace."
    fi
else
    if [ -f /home/cuti/.claude/.credentials.json ]; then
        echo "🔑 Found saved Claude credentials - no login needed!"
    elif [ -f /workspace/.claude/.credentials.json ]; then
        cp /workspace/.claude/.credentials.json /home/cuti/.claude/.credentials.json 2>/dev/null || true
        echo "🔑 Copied credentials from workspace"
    else
        echo "⚠️  No saved credentials. Authenticate once with: claude login"
        echo "   Your credentials will be saved for all future containers."
    fi
    # Ensure home storage directory exists for read-only mode
    mkdir -p /home/cuti/.cuti 2>/dev/null || true
fi

# Ensure PYTHONPATH includes workspace source for local development
export PYTHONPATH="/workspace/src:$PYTHONPATH"
echo "🐍 Python path: $PYTHONPATH"

# Function to sync credentials back to host on exit
sync_credentials_to_host() {
    if [ -d /host-claude-config ] && [ -f /home/cuti/.claude/.credentials.json ]; then
        cp /home/cuti/.claude/.credentials.json /host-claude-config/.credentials.json 2>/dev/null || true
        echo "📤 Synced credentials back to host"
    fi
}

# Trap EXIT to sync credentials
trap sync_credentials_to_host EXIT
"""
        
        # Add interactive flags if no specific command
        if not command:
            docker_args.insert(2, "-it")
            full_command = f"{init_script}\nexec /bin/zsh -l"
            docker_args.extend(["/bin/zsh", "-c", full_command])
        else:
            full_command = f"{init_script}\n{command}"
            docker_args.extend(["/bin/zsh", "-c", full_command])
        
        return subprocess.run(docker_args).returncode
    
    def clean(self, clean_credentials: bool = False) -> bool:
        """Clean up dev container files and images."""
        # Remove local .devcontainer directory
        if self.devcontainer_dir.exists():
            shutil.rmtree(self.devcontainer_dir)
            print(f"✅ Removed {self.devcontainer_dir}")
        
        # Remove Docker images
        for image in ["cuti-dev-universal", f"cuti-dev-{self.working_dir.name}"]:
            self._run_command(["docker", "rmi", "-f", image])
            print(f"✅ Removed Docker image {image}")
        
        # Optionally remove persistent Claude credentials
        if clean_credentials:
            container_claude_dir = Path.home() / ".cuti" / "container" / ".claude"
            if container_claude_dir.exists():
                shutil.rmtree(container_claude_dir)
                print(f"✅ Removed container Claude config at {container_claude_dir}")
                print("   Note: You'll need to authenticate again in future containers")
        else:
            print("💡 Tip: Claude credentials preserved. Use --clean-credentials to remove them.")
        
        return True


# Utility functions
def is_running_in_container() -> bool:
    """Check if running inside a container."""
    # Check environment variable first
    if os.environ.get("CUTI_IN_CONTAINER") == "true":
        return True
    
    # Check for Docker environment file
    if Path("/.dockerenv").exists():
        return True
    
    # Check /proc/1/cgroup on Linux systems
    cgroup_path = Path("/proc/1/cgroup")
    if cgroup_path.exists():
        try:
            cgroup_content = cgroup_path.read_text()
            return "docker" in cgroup_content or "containerd" in cgroup_content
        except Exception:
            pass
    
    return False


def get_claude_command(prompt: str) -> List[str]:
    """Get Claude command with appropriate flags."""
    cmd = ["claude"]
    if is_running_in_container():
        cmd.append("--dangerously-skip-permissions")
    cmd.append(prompt)
    return cmd