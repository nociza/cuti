"""
DevContainer Service for cuti
Automatically generates and manages dev containers for any project with Colima support.
"""

import json
import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import platform


class DevContainerService:
    """Manages dev container generation and execution for any project."""
    
    # Dockerfile template for cuti dev containers
    DOCKERFILE_TEMPLATE = '''FROM python:3.11-bullseye

# Build arguments
ARG USERNAME=cuti
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ARG NODE_VERSION=20

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \\
    && apt-get -y install --no-install-recommends \\
    curl \\
    ca-certificates \\
    git \\
    sudo \\
    zsh \\
    wget \\
    build-essential \\
    procps \\
    lsb-release \\
    locales \\
    fontconfig \\
    software-properties-common \\
    gnupg2 \\
    jq \\
    ripgrep \\
    fd-find \\
    bat \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \\
    && apt-get install -y nodejs \\
    && npm install -g npm@latest

# Create non-root user with sudo access
RUN groupadd --gid $USER_GID $USERNAME \\
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/zsh \\
    && echo $USERNAME ALL=\\(root\\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \\
    && chmod 0440 /etc/sudoers.d/$USERNAME \\
    && mkdir -p /home/$USERNAME/.local/bin \\
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Claude Code CLI with permissions flag
RUN npm install -g @anthropic-ai/claude-code \\
    && echo '#!/bin/bash\\nclaude-code --dangerously-skip-permissions "$@"' > /usr/local/bin/claude \\
    && chmod +x /usr/local/bin/claude

# Install cuti and dependencies
{CUTI_INSTALL}

# Switch to non-root user
USER $USERNAME

# Install uv for the non-root user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/$USERNAME/.cargo/bin:${PATH}"

# Install oh-my-zsh for better terminal experience
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \\
    && echo 'export PATH="/usr/local/bin:/home/$USERNAME/.cargo/bin:$HOME/.local/bin:$HOME/.local/share/uv/tools/cuti/bin:$PATH"' >> ~/.zshrc \\
    && echo 'export CUTI_IN_CONTAINER=true' >> ~/.zshrc \\
    && echo 'export CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true' >> ~/.zshrc \\
    && echo '' >> ~/.zshrc \\
    && echo '# Welcome message' >> ~/.zshrc \\
    && echo 'echo "🚀 Welcome to cuti dev container!"' >> ~/.zshrc \\
    && echo 'echo "   Commands available:"' >> ~/.zshrc \\
    && echo 'echo "     • cuti web        - Start the web interface"' >> ~/.zshrc \\
    && echo 'echo "     • cuti cli        - Start the CLI"' >> ~/.zshrc \\
    && echo 'echo "     • cuti agent list - List available agents"' >> ~/.zshrc \\
    && echo 'echo ""' >> ~/.zshrc

# Verify cuti installation
RUN python -c "import cuti; print('✅ cuti module imported successfully')" || echo "⚠️ cuti module not found" && \\
    which cuti || echo "⚠️ cuti command not found in PATH"

# Set working directory
WORKDIR /workspace

# Set shell
SHELL ["/bin/zsh", "-c"]

# Entry point
CMD ["/bin/zsh"]
'''

    DEVCONTAINER_JSON_TEMPLATE = {
        "name": "cuti Development Environment",
        "build": {
            "dockerfile": "Dockerfile",
            "context": ".",
            "args": {
                "USERNAME": "cuti",
                "USER_UID": "1000",
                "USER_GID": "1000",
                "NODE_VERSION": "20"
            }
        },
        "runArgs": [
            "--init",
            "--privileged",
            "--cap-add=SYS_PTRACE",
            "--security-opt", "seccomp=unconfined"
        ],
        "containerEnv": {
            "CUTI_IN_CONTAINER": "true",
            "CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS": "true",
            "PYTHONUNBUFFERED": "1",
            "TERM": "xterm-256color"
        },
        "mounts": [
            "source=${localEnv:HOME}/.claude,target=/home/cuti/.claude,type=bind,consistency=cached",
            "source=${localEnv:HOME}/.cuti,target=/home/cuti/.cuti-global,type=bind,consistency=cached",
            "source=cuti-venv-${localWorkspaceFolderBasename},target=/workspace/.venv,type=volume",
            "source=cuti-cache-${localWorkspaceFolderBasename},target=/home/cuti/.cache,type=volume"
        ],
        "forwardPorts": [8000, 8080, 3000, 5000, 5173],
        "postCreateCommand": "python -m cuti.cli.app devcontainer devcontainer-init 2>/dev/null || echo '✅ Container initialized'",
        "postStartCommand": "echo '🚀 cuti dev container ready! Run: python -m cuti.cli.app web'",
        "customizations": {
            "vscode": {
                "settings": {
                    "terminal.integrated.defaultProfile.linux": "zsh",
                    "python.defaultInterpreter": "/workspace/.venv/bin/python",
                    "python.terminal.activateEnvironment": True
                },
                "extensions": [
                    "ms-python.python",
                    "ms-python.vscode-pylance",
                    "GitHub.copilot",
                    "eamodio.gitlens"
                ]
            }
        },
        "remoteUser": "cuti"
    }
    
    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the dev container service."""
        self.working_dir = Path(working_directory) if working_directory else Path.cwd()
        self.devcontainer_dir = self.working_dir / ".devcontainer"
        self.colima_available = self._check_colima()
        self.docker_available = self._check_docker()
        
    def _check_colima(self) -> bool:
        """Check if Colima is available."""
        try:
            result = subprocess.run(
                ["colima", "version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def setup_colima(self) -> bool:
        """Setup Colima if not already running."""
        if not self.colima_available:
            print("📦 Colima not found. Please install it first:")
            print("  brew install colima")
            return False
        
        # Check if Colima is running
        try:
            result = subprocess.run(
                ["colima", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check various conditions that indicate Colima is not running
            is_not_running = (
                result.returncode != 0 or
                "is not running" in result.stdout.lower() or
                "error" in result.stderr.lower() or
                "empty value" in result.stderr.lower()
            )
            
            if is_not_running:
                print("🚀 Starting Colima (this may take a minute)...")
                
                # First try to stop any broken instance
                subprocess.run(
                    ["colima", "stop", "-f"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Detect architecture
                import platform
                arch = platform.machine()
                if arch == "arm64" or arch == "aarch64":
                    # M1/M2 Macs - use VZ virtualization
                    start_cmd = ["colima", "start", "--arch", "aarch64", "--vm-type", "vz", "--cpu", "2", "--memory", "4"]
                else:
                    # Intel Macs
                    start_cmd = ["colima", "start", "--cpu", "2", "--memory", "4"]
                
                # Start with appropriate settings
                start_result = subprocess.run(
                    start_cmd,
                    capture_output=False,  # Show output to user
                    text=True,
                    timeout=120  # Give it 2 minutes to start
                )
                
                if start_result.returncode != 0:
                    print("❌ Failed to start Colima with default settings")
                    print("🔄 Trying minimal configuration...")
                    
                    # Try with minimal settings
                    minimal_result = subprocess.run(
                        ["colima", "start"],
                        capture_output=False,
                        text=True,
                        timeout=120
                    )
                    
                    if minimal_result.returncode != 0:
                        print("❌ Failed to start Colima")
                        print("Please try starting Colima manually:")
                        print("  colima start")
                        return False
                
                # Verify it's running
                import time
                time.sleep(2)  # Give it a moment to stabilize
                
                verify_result = subprocess.run(
                    ["docker", "version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if verify_result.returncode == 0:
                    print("✅ Colima started successfully")
                    return True
                else:
                    print("⚠️  Colima started but Docker is not responding")
                    print("Try running: docker version")
                    return False
            else:
                print("✅ Colima is already running")
                return True
            
        except subprocess.TimeoutExpired:
            print("❌ Colima operation timed out")
            print("Please start Colima manually: colima start")
            return False
        except subprocess.SubprocessError as e:
            print(f"❌ Error with Colima: {e}")
            return False
    
    def generate_devcontainer(self, project_type: Optional[str] = None) -> bool:
        """Generate dev container configuration for the current project."""
        print(f"🔧 Generating dev container configuration in {self.working_dir}")
        
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
        devcontainer_json = self._generate_devcontainer_json(project_type)
        devcontainer_json_path = self.devcontainer_dir / "devcontainer.json"
        devcontainer_json_path.write_text(json.dumps(devcontainer_json, indent=2))
        print(f"✅ Created {devcontainer_json_path}")
        
        # Create initialization script
        self._create_init_script()
        
        return True
    
    def _detect_project_type(self) -> str:
        """Detect the project type based on files present."""
        if (self.working_dir / "package.json").exists():
            if (self.working_dir / "pyproject.toml").exists():
                return "fullstack"
            return "javascript"
        elif (self.working_dir / "pyproject.toml").exists():
            return "python"
        elif (self.working_dir / "requirements.txt").exists():
            return "python"
        elif (self.working_dir / "Gemfile").exists():
            return "ruby"
        elif (self.working_dir / "go.mod").exists():
            return "go"
        elif (self.working_dir / "Cargo.toml").exists():
            return "rust"
        else:
            return "general"
    
    def _generate_dockerfile(self, project_type: str) -> str:
        """Generate Dockerfile based on project type."""
        # Determine how to install cuti - check if this IS the cuti project
        if (self.working_dir / "src" / "cuti").exists() and (self.working_dir / "pyproject.toml").exists():
            # This is the cuti project itself - install from local source
            cuti_install = """
# Copy source code
COPY . /workspace

# Install cuti and all dependencies using uv
RUN cd /workspace && \\
    uv pip install --system pyyaml rich 'typer[all]' click fastapi uvicorn httpx watchdog aiofiles python-multipart && \\
    uv pip install --system -e . && \\
    echo "Testing cuti installation..." && \\
    python -c "from cuti.cli.app import app; print('✅ cuti module works')" && \\
    echo "Testing cuti command..." && \\
    which cuti && cuti --version || \\
    (echo "Creating cuti wrapper..." && \\
    echo '#!/usr/bin/env python3' > /usr/local/bin/cuti && \\
    echo 'from cuti.cli.app import app' >> /usr/local/bin/cuti && \\
    echo 'if __name__ == "__main__": app()' >> /usr/local/bin/cuti && \\
    chmod +x /usr/local/bin/cuti && \\
    /usr/local/bin/cuti --version && echo "✅ cuti command works")
"""
        else:
            # Regular project - install cuti from PyPI using uv
            cuti_install = """
# Install cuti using uv (once published to PyPI)
RUN uv tool install cuti && \\
    ln -sf $HOME/.local/share/uv/tools/cuti/bin/cuti /usr/local/bin/cuti && \\
    cuti --version && echo "✅ cuti installed via uv"
"""
        
        # Add project-specific dependencies
        extra_deps = ""
        
        if project_type in ["javascript", "fullstack"]:
            extra_deps += """
# Install additional Node.js tools
RUN npm install -g yarn pnpm typescript ts-node nodemon
"""
        
        if project_type == "python":
            extra_deps += """
# Install additional Python tools
RUN pip install --no-cache-dir pytest pytest-asyncio httpx fastapi uvicorn
"""
        
        if project_type == "ruby":
            extra_deps += """
# Install Ruby
RUN apt-get update && apt-get install -y ruby-full ruby-bundler
"""
        
        if project_type == "go":
            extra_deps += """
# Install Go
RUN wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz \\
    && tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz \\
    && rm go1.21.5.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"
"""
        
        if project_type == "rust":
            extra_deps += """
# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
"""
        
        dockerfile = self.DOCKERFILE_TEMPLATE.replace("{CUTI_INSTALL}", cuti_install + extra_deps)
        return dockerfile
    
    def _generate_devcontainer_json(self, project_type: str) -> Dict[str, Any]:
        """Generate devcontainer.json based on project type."""
        config = self.DEVCONTAINER_JSON_TEMPLATE.copy()
        
        # Add project-specific extensions
        if project_type in ["javascript", "fullstack"]:
            config["customizations"]["vscode"]["extensions"].extend([
                "dbaeumer.vscode-eslint",
                "esbenp.prettier-vscode",
                "bradlc.vscode-tailwindcss"
            ])
        
        if project_type == "python":
            config["customizations"]["vscode"]["extensions"].extend([
                "ms-python.black-formatter",
                "charliermarsh.ruff"
            ])
        
        return config
    
    def _generate_standalone_dockerfile(self) -> str:
        """Generate a standalone Dockerfile for cuti container that works from any directory."""
        # Get the cuti installation path
        import cuti
        import sys
        cuti_path = Path(cuti.__file__).parent.parent  # Get to the src directory
        
        return '''FROM python:3.11-bullseye

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \\
    && apt-get -y install --no-install-recommends \\
    curl ca-certificates git sudo zsh wget build-essential \\
    procps lsb-release locales fontconfig \\
    software-properties-common gnupg2 jq ripgrep fd-find bat \\
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# Install Node.js for Claude CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \\
    && apt-get install -y nodejs && npm install -g npm@latest

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# Copy cuti source
COPY cuti /tmp/cuti-source

# Install cuti and dependencies using uv
RUN cd /tmp/cuti-source && \\
    uv pip install --system pyyaml rich 'typer[all]' click fastapi uvicorn httpx watchdog aiofiles python-multipart \\
    requests jinja2 psutil websockets pydantic-settings claude-monitor && \\
    uv pip install --system -e . && \\
    which cuti || (echo '#!/usr/bin/env python3' > /usr/local/bin/cuti && \\
    echo 'from cuti.cli.app import app' >> /usr/local/bin/cuti && \\
    echo 'if __name__ == "__main__": app()' >> /usr/local/bin/cuti && \\
    chmod +x /usr/local/bin/cuti)

# Install oh-my-zsh
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \\
    && echo 'export PATH="/root/.local/bin:/usr/local/bin:$PATH"' >> ~/.zshrc \\
    && echo 'export CUTI_IN_CONTAINER=true' >> ~/.zshrc \\
    && echo 'export CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true' >> ~/.zshrc \\
    && echo 'echo "🚀 Welcome to cuti dev container!"' >> ~/.zshrc \\
    && echo 'echo "   Current directory: $(pwd)"' >> ~/.zshrc \\
    && echo 'echo "   • cuti web        - Start web interface"' >> ~/.zshrc \\
    && echo 'echo "   • cuti cli        - Start CLI"' >> ~/.zshrc \\
    && echo 'echo "   • cuti agent list - List agents"' >> ~/.zshrc \\
    && echo 'echo ""' >> ~/.zshrc

WORKDIR /workspace
SHELL ["/bin/zsh", "-c"]
CMD ["/bin/zsh"]
'''
    
    def _create_init_script(self):
        """Create initialization script for the container."""
        init_script = '''#!/bin/bash
set -e

echo "🔧 Initializing cuti dev container..."

# Ensure Claude uses --dangerously-skip-permissions
if ! grep -q "dangerously-skip-permissions" ~/.zshrc; then
    echo 'alias claude="claude-code --dangerously-skip-permissions"' >> ~/.zshrc
fi

# Initialize Python virtual environment if needed
if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
    if [ ! -d ".venv" ]; then
        echo "📦 Creating Python virtual environment..."
        python -m venv .venv
    fi
    
    if [ -f "pyproject.toml" ]; then
        echo "📦 Installing Python dependencies with uv..."
        uv sync
    elif [ -f "requirements.txt" ]; then
        echo "📦 Installing Python dependencies..."
        .venv/bin/pip install -r requirements.txt
    fi
fi

# Install Node dependencies if needed
if [ -f "package.json" ]; then
    echo "📦 Installing Node.js dependencies..."
    if [ -f "yarn.lock" ]; then
        yarn install
    elif [ -f "pnpm-lock.yaml" ]; then
        pnpm install
    else
        npm install
    fi
fi

# Initialize cuti workspace
echo "🚀 Initializing cuti workspace..."
cuti init --quiet

echo "✅ Dev container initialization complete!"
'''
        
        init_script_path = self.devcontainer_dir / "init.sh"
        init_script_path.write_text(init_script)
        init_script_path.chmod(0o755)
        print(f"✅ Created {init_script_path}")
    
    def run_in_container(self, command: Optional[str] = None) -> int:
        """Run cuti in the dev container."""
        if not self.docker_available:
            print("❌ Docker is not available. Please start Docker or Colima first.")
            return 1
        
        # Always use the pre-built cuti-dev-cuti image
        container_image = "cuti-dev-cuti"
        
        # Check if the cuti container image exists
        check_image = subprocess.run(
            ["docker", "images", "-q", container_image],
            capture_output=True,
            text=True
        )
        
        if not check_image.stdout.strip():
            print("🔨 Building cuti dev container (one-time setup)...")
            print("This will take a few minutes on first run...")
            
            # Get the cuti installation directory
            import cuti
            cuti_module_path = Path(cuti.__file__).parent  # cuti module directory
            
            # Check if we're in a development environment (editable install)
            cuti_src_dir = cuti_module_path.parent.parent  # Try to get to project root
            dockerfile_path = cuti_src_dir / ".devcontainer" / "Dockerfile"
            
            if dockerfile_path.exists() and (cuti_src_dir / "pyproject.toml").exists():
                # We have the full source - use it
                print(f"Building from source at {cuti_src_dir}")
                build_result = subprocess.run(
                    ["docker", "build", "-t", container_image, "-f", str(dockerfile_path), str(cuti_src_dir)],
                    capture_output=True,
                    text=True
                )
            else:
                # Use the pre-built image from Docker Hub or build minimal
                print("Building minimal container...")
                
                # First, try to pull from registry (if published)
                pull_result = subprocess.run(
                    ["docker", "pull", "nociza/cuti:latest"],
                    capture_output=True,
                    text=True
                )
                
                if pull_result.returncode == 0:
                    # Tag it as our local image
                    subprocess.run(
                        ["docker", "tag", "nociza/cuti:latest", container_image],
                        capture_output=True
                    )
                    build_result = subprocess.CompletedProcess([], 0)  # Success
                else:
                    # Build a minimal container
                    import tempfile
                    with tempfile.TemporaryDirectory() as tmpdir:
                        temp_dockerfile = Path(tmpdir) / "Dockerfile"
                        
                        # Write a minimal Dockerfile
                        minimal_dockerfile = """FROM python:3.11-bullseye
RUN apt-get update && apt-get install -y curl git zsh wget && apt-get clean
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
RUN uv pip install --system pyyaml rich typer click fastapi uvicorn httpx requests
RUN echo '#!/usr/bin/env python3' > /usr/local/bin/cuti-placeholder && \
    echo 'print("⚠️  cuti is not installed in this container")' >> /usr/local/bin/cuti-placeholder && \
    echo 'print("Please rebuild the container from the cuti source directory")' >> /usr/local/bin/cuti-placeholder && \
    chmod +x /usr/local/bin/cuti-placeholder && \
    ln -s /usr/local/bin/cuti-placeholder /usr/local/bin/cuti
WORKDIR /workspace
CMD ["/bin/bash"]
"""
                        temp_dockerfile.write_text(minimal_dockerfile)
                        
                        build_result = subprocess.run(
                            ["docker", "build", "-t", container_image, "-f", str(temp_dockerfile), tmpdir],
                            capture_output=True,
                            text=True
                        )
            
            if build_result.returncode != 0:
                print(f"❌ Failed to build container: {build_result.stderr}")
                print("\nTo fix this:")
                print("1. Navigate to the cuti source directory:")
                print("   cd ~/Documents/Projects/Personal\\ Projects/cuti")
                print("2. Build the container:")
                print("   docker build -t cuti-dev-cuti -f .devcontainer/Dockerfile .")
                print("3. Then run 'cuti container' from any directory")
                return 1
            
            print("✅ Container image built successfully")
        
        
        # Run the container
        print("🚀 Starting dev container...")
        
        docker_args = [
            "docker", "run",
            "--rm",
            "-it",
            "--privileged",
            "--network", "host",  # Allow network access for cuti web
            "-v", f"{Path.cwd()}:/workspace",  # Mount current directory as workspace
            "-v", f"{Path.home() / '.claude'}:/home/cuti/.claude",
            "-v", f"{Path.home() / '.cuti'}:/home/cuti/.cuti-global",
            "-w", "/workspace",
            "--env", "CUTI_IN_CONTAINER=true",
            "--env", "CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true",
            "--env", "PATH=/root/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
            container_image
        ]
        
        if command:
            # For commands, source the zshrc to get the aliases and PATH
            docker_args.extend(["/bin/zsh", "-lc", command])
        else:
            # Interactive shell
            docker_args.append("/bin/zsh")
        
        return subprocess.run(docker_args).returncode
    
    def clean(self) -> bool:
        """Clean up dev container files."""
        if self.devcontainer_dir.exists():
            shutil.rmtree(self.devcontainer_dir)
            print(f"✅ Removed {self.devcontainer_dir}")
        
        # Remove Docker image
        image_name = f"cuti-dev-{self.working_dir.name}"
        subprocess.run(
            ["docker", "rmi", image_name],
            capture_output=True
        )
        print(f"✅ Removed Docker image {image_name}")
        
        return True


def is_running_in_container() -> bool:
    """Check if we're running inside a container."""
    # Check for container environment variables
    if os.environ.get("CUTI_IN_CONTAINER") == "true":
        return True
    
    # Check for Docker/.dockerenv file
    if Path("/.dockerenv").exists():
        return True
    
    # Check for container in /proc/1/cgroup
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read() or "containerd" in f.read()
    except:
        return False


def get_claude_command(prompt: str) -> List[str]:
    """Get the Claude command with appropriate flags."""
    base_cmd = ["claude-code"]
    
    # Add --dangerously-skip-permissions if in container
    if is_running_in_container():
        base_cmd.append("--dangerously-skip-permissions")
    
    base_cmd.append(prompt)
    return base_cmd