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

try:
    from rich.console import Console
    from rich.prompt import Confirm, IntPrompt
except ImportError:
    # Fallback for environments without rich
    Console = None
    Confirm = None
    IntPrompt = None


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
ENV PATH="/root/.local/bin:${PATH}"

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create startup script to verify Claude auth
RUN echo '#!/bin/bash' > /usr/local/bin/setup-claude-auth.sh \\
    && echo '# Check if Claude config is available' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo 'if [ -d "$CLAUDE_CONFIG_DIR" ]; then' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '    echo "✅ Claude config found at: $CLAUDE_CONFIG_DIR"' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '    # Test Claude authentication' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '    if claude --version > /dev/null 2>&1; then' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '        echo "✅ Claude CLI authenticated and ready"' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '    else' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '        echo "⚠️  Claude CLI not authenticated. Run: claude login"' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '    fi' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo 'else' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '    echo "⚠️  Claude config not mounted. Authentication will not persist."' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo '    echo "    Please ensure ~/.claude exists on your host machine."' >> /usr/local/bin/setup-claude-auth.sh \\
    && echo 'fi' >> /usr/local/bin/setup-claude-auth.sh \\
    && chmod +x /usr/local/bin/setup-claude-auth.sh

# Create entrypoint script that runs auth setup
RUN echo '#!/bin/bash' > /entrypoint.sh \\
    && echo '# Run Claude auth setup' >> /entrypoint.sh \\
    && echo 'bash /usr/local/bin/setup-claude-auth.sh' >> /entrypoint.sh \\
    && echo '# Execute command' >> /entrypoint.sh \\
    && echo 'exec "$@"' >> /entrypoint.sh \\
    && chmod +x /entrypoint.sh

# Install cuti and dependencies
{CUTI_INSTALL}

# Configure environment for all users
ENV PATH="/usr/local/bin:/root/.local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

# Switch to non-root user
USER $USERNAME

# Install uv for the non-root user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/$USERNAME/.local/bin:${PATH}"

# Install oh-my-zsh for better terminal experience
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \\
    && echo '# Environment setup' >> ~/.zshrc \\
    && echo 'export PATH="/usr/local/bin:/home/$USERNAME/.cargo/bin:$HOME/.local/bin:$HOME/.local/share/uv/tools/cuti/bin:$PATH"' >> ~/.zshrc \\
    && echo 'export CUTI_IN_CONTAINER=true' >> ~/.zshrc \\
    && echo '# Custom prompt showing cuti' >> ~/.zshrc \\
    && echo 'PROMPT="%{$fg[cyan]%}cuti%{$reset_color%}:%{$fg[green]%}%~%{$reset_color%} $ "' >> ~/.zshrc \\
    && echo '' >> ~/.zshrc \\
    && echo '# Welcome message' >> ~/.zshrc \\
    && echo 'echo "🚀 Welcome to cuti dev container!"' >> ~/.zshrc \\
    && echo 'echo "   Commands available:"' >> ~/.zshrc \\
    && echo 'echo "     • cuti web        - Start the web interface"' >> ~/.zshrc \\
    && echo 'echo "     • cuti cli        - Start the CLI"' >> ~/.zshrc \\
    && echo 'echo "     • cuti agent list - List available agents"' >> ~/.zshrc \\
    && echo 'echo "     • claude          - Claude Code CLI"' >> ~/.zshrc \\
    && echo 'echo ""' >> ~/.zshrc

# Verify cuti installation
RUN python -c "import cuti; print('✅ cuti module imported successfully')" || echo "⚠️ cuti module not found" && \\
    which cuti || echo "⚠️ cuti command not found in PATH"

# Set working directory
WORKDIR /workspace

# Set shell
SHELL ["/bin/zsh", "-c"]

# Set entrypoint to run auth setup
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["/bin/zsh", "-l"]
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
            "CLAUDE_CONFIG_DIR": "/host/.claude",
            "PYTHONUNBUFFERED": "1",
            "TERM": "xterm-256color"
        },
        "mounts": [
            "source=${localEnv:HOME}/.claude,target=/host/.claude,type=bind,readonly=true,consistency=cached",
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
        self.is_macos = platform.system() == "Darwin"
        self.homebrew_available = self._check_homebrew()
        self.colima_available = self._check_colima()
        self.docker_available = self._check_docker()
        
    def _check_homebrew(self) -> bool:
        """Check if Homebrew is available."""
        try:
            result = subprocess.run(
                ["brew", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
        
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
    
    def _prompt_user_install(self, tool: str, install_command: str) -> bool:
        """Prompt user to install a missing dependency."""
        if Console is None or Confirm is None:
            # Fallback for environments without rich
            print(f"\nMissing dependency: {tool}")
            print(f"To use containers, cuti needs {tool} installed.")
            print(f"Install command: {install_command}")
            response = input(f"Would you like cuti to install {tool} automatically? (y/N): ").lower()
            return response in ['y', 'yes']
        
        console = Console()
        console.print(f"\n[yellow]Missing dependency: {tool}[/yellow]")
        console.print(f"To use containers, cuti needs {tool} installed.")
        console.print(f"Install command: [cyan]{install_command}[/cyan]")
        
        return Confirm.ask(f"Would you like cuti to install {tool} automatically?")
    
    def _install_homebrew(self) -> bool:
        """Install Homebrew."""
        if Console is None:
            print("🍺 Installing Homebrew...")
        else:
            console = Console()
            console.print("🍺 Installing Homebrew...")
        
        install_script = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        
        result = subprocess.run(
            install_script,
            shell=True,
            capture_output=False,  # Show output to user
            text=True
        )
        
        if result.returncode == 0:
            # Update PATH for current session
            import os
            if "/opt/homebrew/bin" not in os.environ["PATH"]:
                os.environ["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{os.environ['PATH']}"
            
            if Console is None:
                print("✅ Homebrew installed successfully!")
            else:
                console = Console()
                console.print("✅ Homebrew installed successfully!")
            return True
        else:
            if Console is None:
                print("❌ Failed to install Homebrew")
            else:
                console = Console()
                console.print("❌ Failed to install Homebrew")
            return False
    
    def _install_with_brew(self, package: str) -> bool:
        """Install a package with Homebrew."""
        if Console is None:
            print(f"📦 Installing {package} with Homebrew...")
        else:
            console = Console()
            console.print(f"📦 Installing {package} with Homebrew...")
        
        result = subprocess.run(
            ["brew", "install", package],
            capture_output=False,  # Show output to user
            text=True
        )
        
        if result.returncode == 0:
            if Console is None:
                print(f"✅ {package} installed successfully!")
            else:
                console = Console()
                console.print(f"✅ {package} installed successfully!")
            return True
        else:
            if Console is None:
                print(f"❌ Failed to install {package}")
            else:
                console = Console()
                console.print(f"❌ Failed to install {package}")
            return False
    
    def ensure_dependencies(self) -> bool:
        """Ensure all required dependencies are installed on macOS."""
        if not self.is_macos:
            # Non-macOS systems - just check what's available
            return self.docker_available or self.colima_available
        
        # Check Homebrew first
        if not self.homebrew_available:
            if self._prompt_user_install("Homebrew", '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'):
                if not self._install_homebrew():
                    if Console is None:
                        print("Cannot proceed without Homebrew on macOS")
                    else:
                        console = Console()
                        console.print("[red]Cannot proceed without Homebrew on macOS[/red]")
                    return False
                self.homebrew_available = True
            else:
                if Console is None:
                    print("Skipped Homebrew installation. You'll need to install Docker manually.")
                else:
                    console = Console()
                    console.print("[yellow]Skipped Homebrew installation. You'll need to install Docker manually.[/yellow]")
                return False
        
        # Check Docker Desktop or Colima
        if not self.docker_available and not self.colima_available:
            if Console is None or IntPrompt is None:
                # Fallback for environments without rich
                print("\nContainer runtime needed")
                print("Choose an option:")
                print("1. Colima (lightweight, recommended)")
                print("2. Docker Desktop (GUI, more features)")  
                print("3. Skip installation")
                choice = input("Select option (1-3, default 1): ").strip() or "1"
            else:
                console = Console()
                console.print("\n[yellow]Container runtime needed[/yellow]")
                console.print("Choose an option:")
                console.print("1. [cyan]Colima[/cyan] (lightweight, recommended)")
                console.print("2. [cyan]Docker Desktop[/cyan] (GUI, more features)")
                console.print("3. [dim]Skip installation[/dim]")
                choice = str(IntPrompt.ask("Select option", choices=["1", "2", "3"], default=1))
            
            if choice == "1":
                # Install Colima
                if self._install_with_brew("colima"):
                    self.colima_available = True
                    if Console is None:
                        print("ℹ️  Colima installed. It will auto-start when you run containers.")
                    else:
                        console = Console()
                        console.print("ℹ️  Colima installed. It will auto-start when you run containers.")
                else:
                    return False
            elif choice == "2":
                # Install Docker Desktop
                if self._install_with_brew("docker"):
                    if Console is None:
                        print("✅ Docker Desktop installed!")
                        print("🔄 Please start Docker Desktop from your Applications folder")
                        print("   Then run 'cuti container' again")
                    else:
                        console = Console()
                        console.print("✅ Docker Desktop installed!")
                        console.print("🔄 Please start Docker Desktop from your Applications folder")
                        console.print("   Then run 'cuti container' again")
                    return False  # User needs to start Docker manually
                else:
                    return False
            else:
                if Console is None:
                    print("Skipped container runtime installation")
                else:
                    console = Console()
                    console.print("[yellow]Skipped container runtime installation[/yellow]")
                return False
        
        return True
    
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
# Create workspace directory
RUN mkdir -p /workspace

# Copy source code
COPY . /workspace

# Install cuti and all dependencies using uv
RUN cd /workspace && \\
    /root/.local/bin/uv pip install --system pyyaml rich 'typer[all]' click fastapi uvicorn httpx watchdog aiofiles python-multipart && \\
    /root/.local/bin/uv pip install --system -e . && \\
    echo "Testing cuti installation..." && \\
    python -c "from cuti.cli.app import app; print('✅ cuti module works')" && \\
    echo "Testing cuti command..." && \\
    which cuti && cuti --help > /dev/null && echo "✅ cuti command works"
"""
        else:
            # Regular project - install cuti from PyPI using uv
            cuti_install = """
# Install cuti using uv tool
RUN /root/.local/bin/uv tool install cuti && \\
    ln -sf /root/.local/share/uv/tools/cuti/bin/cuti /usr/local/bin/cuti && \\
    echo "Testing cuti installation..." && \\
    cuti --help > /dev/null && echo "✅ cuti installed via uv tool"
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
\
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
    
    def _setup_claude_host_config(self):
        """Setup Claude configuration on host for container usage."""
        claude_json_path = Path.home() / ".claude.json"
        
        # Check if we need to setup or update .claude.json
        needs_setup = False
        
        if not claude_json_path.exists():
            needs_setup = True
        else:
            # Check if bypassPermissionsModeAccepted is set
            try:
                import json
                with open(claude_json_path, 'r') as f:
                    config = json.load(f)
                    if not config.get('bypassPermissionsModeAccepted', False):
                        needs_setup = True
            except:
                needs_setup = True
        
        if needs_setup:
            print("🔧 Setting up Claude configuration for container usage...")
            
            # Create or update .claude.json
            config = {}
            if claude_json_path.exists():
                try:
                    with open(claude_json_path, 'r') as f:
                        config = json.load(f)
                except:
                    config = {}
            
            config['bypassPermissionsModeAccepted'] = True
            
            with open(claude_json_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Updated {claude_json_path}")
    
    def _build_minimal_container(self, container_image: str):
        """Build a minimal container as fallback."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dockerfile = Path(tmpdir) / "Dockerfile"
            
            # Write a comprehensive Dockerfile with all required tools
            minimal_dockerfile = """FROM python:3.11-bullseye

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
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Install Node.js for Claude CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \\
    && apt-get install -y nodejs \\
    && npm install -g npm@latest

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Verify Claude CLI is installed and accessible
RUN which claude || (echo "ERROR: Claude CLI not installed!" && exit 1)

# Install cuti from PyPI
RUN /root/.local/bin/uv tool install cuti \\
    && ln -sf /root/.local/share/uv/tools/cuti/bin/cuti /usr/local/bin/cuti

# Install oh-my-zsh for better terminal experience
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \\
    && echo 'export PATH="/usr/local/bin:/root/.local/bin:$PATH"' >> ~/.zshrc \\
    && echo 'export CUTI_IN_CONTAINER=true' >> ~/.zshrc \\
    && echo 'export CLAUDE_CONFIG_DIR="/root/.claude"' >> ~/.zshrc \\
    && echo 'echo "🚀 Welcome to cuti dev container!"' >> ~/.zshrc \\
    && echo 'echo "   Commands available:"' >> ~/.zshrc \\
    && echo 'echo "     • cuti web        - Start web interface"' >> ~/.zshrc \\
    && echo 'echo "     • cuti cli        - Start CLI"' >> ~/.zshrc \\
    && echo 'echo "     • claude          - Use Claude CLI"' >> ~/.zshrc \\
    && echo 'echo ""' >> ~/.zshrc

# Set working directory
WORKDIR /workspace

# Use zsh as default shell
SHELL ["/bin/zsh", "-c"]
CMD ["/bin/zsh", "-l"]
"""
            temp_dockerfile.write_text(minimal_dockerfile)
            
            print("Building container with Node.js and Claude CLI...")
            result = subprocess.run(
                ["docker", "build", "-t", container_image, "-f", str(temp_dockerfile), tmpdir],
                capture_output=False,  # Show build output to see any errors
                text=True
            )
            return result
    
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
        
        # Setup Claude configuration on host if needed
        self._setup_claude_host_config()
        
        # Determine which container to use based on current directory
        # If we're in the cuti source directory, use the dev container
        # Otherwise use the universal container with cuti from PyPI
        current_dir = Path.cwd()
        is_cuti_source = (current_dir / "src" / "cuti").exists() and (current_dir / "pyproject.toml").exists()
        
        if is_cuti_source:
            container_image = "cuti-dev-cuti"
        else:
            container_image = "cuti-dev-universal"
        
        # Check if the cuti container image exists
        check_image = subprocess.run(
            ["docker", "images", "-q", container_image],
            capture_output=True,
            text=True
        )
        
        if not check_image.stdout.strip():
            print("🔨 Building cuti dev container (one-time setup)...")
            print("This will take a few minutes on first run...")
            
            # Clean up dangling images first
            print("🧹 Cleaning up old Docker images...")
            subprocess.run(
                ["docker", "image", "prune", "-f"],
                capture_output=True,
                text=True
            )
            
            # Always use the embedded template for consistent behavior
            # This ensures the container works on any machine in any directory
            print(f"Building {container_image} with full cuti environment...")
            build_result = self._build_minimal_container(container_image)
            
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
        
        # Use separate config directory for containers to avoid macOS Keychain issues
        # Store in ~/.cuti/container/ to keep everything organized
        claude_config_mount = []
        cuti_dir = Path.home() / ".cuti"
        claude_container_path = cuti_dir / "container"
        claude_main_path = Path.home() / ".claude"
        
        # Create container config directory if it doesn't exist
        if not claude_container_path.exists():
            claude_container_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created container Claude config at {claude_container_path}")
            
            # Copy CLAUDE.md if it exists in main config
            if claude_main_path.exists():
                claude_md_src = claude_main_path / "CLAUDE.md"
                if claude_md_src.exists():
                    import shutil
                    shutil.copy2(claude_md_src, claude_container_path / "CLAUDE.md")
                    print(f"📄 Copied CLAUDE.md to container config")
        
        # Mount container-specific config directory
        claude_config_mount = [
            "-v", f"{claude_container_path}:/root/.claude",
            "--env", f"CLAUDE_CONFIG_DIR=/root/.claude"
        ]
        
        # Also mount main .claude for read-only access to project configs
        if claude_main_path.exists():
            claude_config_mount.extend([
                "-v", f"{claude_main_path}:/host/.claude-main:ro"
            ])
        
        print(f"✅ Using container Claude config from {claude_container_path}")
        
        # Check if container config has credentials
        if not (claude_container_path / ".credentials.json").exists():
            print(f"⚠️  First time setup: You'll need to login to Claude once in the container")
            print(f"    This login will persist for all future container sessions")
        
        # Determine if we need TTY based on the command and terminal availability
        use_tty = command is None or not command.strip()  # Only use TTY for interactive shell
        
        # Check if we're in a real terminal (not Claude Code or similar)
        import sys
        if not sys.stdin.isatty():
            use_tty = False
        
        docker_args = [
            "docker", "run",
            "--rm",
            "--privileged",
            "--network", "host",  # Allow network access for cuti web
            "-v", f"{Path.cwd()}:/workspace",  # Mount current directory as workspace
            "-v", f"{Path.home() / '.cuti'}:/root/.cuti-global",  # Mount cuti config to root user
            "-w", "/workspace",
            "--env", "CUTI_IN_CONTAINER=true",
            "--env", "IS_SANDBOX=1",  # Allow Claude --dangerously-skip-permissions as root
            "--env", "HOME=/root",  # Ensure HOME is set correctly
            "--env", "PATH=/root/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
            *claude_config_mount,  # Mount Claude config directory and set CLAUDE_CONFIG_DIR if it exists
        ]
        
        # Add TTY flags only if available
        if use_tty:
            docker_args.insert(2, "-it")
        
        docker_args.append(container_image)
        
        if command:
            docker_args.extend(["/bin/zsh", "-lc", command])
        else:
            docker_args.extend(["/bin/zsh", "-l"])
        
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