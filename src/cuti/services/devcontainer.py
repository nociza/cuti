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
    && echo '#!/bin/bash' > /usr/local/bin/claude-wrapper \\
    && echo 'export ANTHROPIC_CLAUDE_BYPASS_PERMISSIONS=1' >> /usr/local/bin/claude-wrapper \\
    && echo 'exec claude "$@"' >> /usr/local/bin/claude-wrapper \\
    && chmod +x /usr/local/bin/claude-wrapper \\
    && ln -sf /usr/local/bin/claude-wrapper /usr/local/bin/claude-safe

{CUTI_INSTALL}

# Switch to non-root user
USER $USERNAME

# Install uv for the non-root user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/cuti/.local/bin:${PATH}"

# Create Claude config directory structure and ensure cuti is accessible
RUN mkdir -p /home/cuti/.claude/plugins/repos \\
    && mkdir -p /home/cuti/.claude/todos \\
    && mkdir -p /home/cuti/.claude/sessions \\
    && mkdir -p /home/cuti/.claude/settings \\
    && mkdir -p /home/cuti/.claude/projects \\
    && mkdir -p '/home/cuti/.claude/projects/-workspace' \\
    && chown -R cuti:cuti /home/cuti/.claude \\
    && mkdir -p /home/cuti/.local/bin \\
    && ln -sf /usr/local/bin/cuti /home/cuti/.local/bin/cuti \\
    && chown -R cuti:cuti /home/cuti/.local

# Install oh-my-zsh with simple configuration
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \\
    && echo 'export PATH="/usr/local/bin:/home/cuti/.local/bin:/root/.local/share/uv/tools/cuti/bin:$PATH"' >> ~/.zshrc \\
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
    && python -c "import cuti; print('✅ cuti installed from source')"
'''
        else:
            cuti_install = '''
# Install cuti from PyPI and make it accessible to all users
RUN /root/.local/bin/uv tool install cuti \\
    && chmod -R o+rx /root/.local \\
    && ln -sf /root/.local/share/uv/tools/cuti/bin/cuti /usr/local/bin/cuti \\
    && cuti --help > /dev/null && echo "✅ cuti installed from PyPI"
'''
        
        return self.DOCKERFILE_TEMPLATE.replace("{CUTI_INSTALL}", cuti_install)
    
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
            
            # Build image
            build_cmd = ["docker", "build", "-t", image_name, "-f", str(dockerfile_path), tmpdir]
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
        
        # Build container if needed
        image_name = "cuti-dev-universal"
        if not self._build_container_image(image_name, rebuild):
            return 1
        
        # Setup Claude config directory
        claude_config_dir = Path.home() / ".cuti" / "container"
        claude_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create complete Claude directory structure if it doesn't exist
        for subdir in ["plugins", "plugins/repos", "todos", "sessions", "settings", "projects", "projects/-workspace"]:
            (claude_config_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Create a basic config file if it doesn't exist
        config_file = claude_config_dir / "config.json"
        if not config_file.exists():
            import json
            basic_config = {"bypassPermissionsModeAccepted": True}
            config_file.write_text(json.dumps(basic_config, indent=2))
        
        # Run container
        print("🚀 Starting container...")
        current_dir = Path.cwd().resolve()
        
        # Create a volume name based on the current working directory  
        volume_name = f"cuti-claude-{current_dir.name.lower().replace('_', '-').replace(' ', '-')}"
        
        docker_args = [
            "docker", "run", "--rm", "--privileged", 
            "-v", f"{current_dir}:/workspace",
            "-v", f"{volume_name}:/home/cuti/.claude",
            "-v", f"{Path.home() / '.cuti'}:/home/cuti/.cuti-global",
            "-w", "/workspace",
            "--env", "CUTI_IN_CONTAINER=true",
            "--env", "ANTHROPIC_CLAUDE_BYPASS_PERMISSIONS=1",
            "--env", "PATH=/usr/local/bin:/home/cuti/.local/bin:/root/.local/share/uv/tools/cuti/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
            "--network", "host",
            image_name
        ]
        
        # Add interactive flags if no specific command
        if not command:
            docker_args.insert(2, "-it")
            docker_args.extend(["/bin/zsh", "-l"])
        else:
            docker_args.extend(["/bin/zsh", "-c", command])
        
        return subprocess.run(docker_args).returncode
    
    def clean(self) -> bool:
        """Clean up dev container files and images."""
        # Remove local .devcontainer directory
        if self.devcontainer_dir.exists():
            shutil.rmtree(self.devcontainer_dir)
            print(f"✅ Removed {self.devcontainer_dir}")
        
        # Remove Docker images
        for image in ["cuti-dev-universal", f"cuti-dev-{self.working_dir.name}"]:
            self._run_command(["docker", "rmi", "-f", image])
            print(f"✅ Removed Docker image {image}")
        
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