"""
DevContainer Service for cuti
Automatically generates and manages dev containers for any project with Colima support.
"""

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from rich.console import Console
    from rich.prompt import Confirm, IntPrompt
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

from .providers import ProviderManager


class DevContainerService:
    """Manages dev container generation and execution for any project."""

    RUNTIME_PROFILE_CLOUD = "cloud"
    RUNTIME_PROFILE_CLAWDBOT_SANDBOX = "clawdbot_sandbox"
    CLAWDBOT_SECCOMP_FILENAME = "kuyuchi-clawdbot-seccomp.json"
    CLAWDBOT_SECCOMP_DIR = Path.home() / ".cuti" / "seccomp"

    DEFAULT_CLAWDBOT_SECCOMP_PROFILE: Dict[str, Any] = {
        "defaultAction": "SCMP_ACT_ALLOW",
        "architectures": [
            "SCMP_ARCH_X86_64",
            "SCMP_ARCH_X86",
            "SCMP_ARCH_X32",
            "SCMP_ARCH_AARCH64",
            "SCMP_ARCH_ARM",
        ],
        "syscalls": [
            {
                "names": [
                    "add_key",
                    "bpf",
                    "delete_module",
                    "finit_module",
                    "init_module",
                    "kexec_load",
                    "keyctl",
                    "open_by_handle_at",
                    "perf_event_open",
                    "process_vm_readv",
                    "process_vm_writev",
                    "ptrace",
                    "request_key",
                    "userfaultfd",
                ],
                "action": "SCMP_ACT_ERRNO",
                "args": [],
            }
        ],
    }

    # Security checklist derived from docs/kuyuchi-threat-model.md
    RUNTIME_SECURITY_CHECKLIST: Dict[str, Dict[str, Any]] = {
        RUNTIME_PROFILE_CLAWDBOT_SANDBOX: {
            "required_flags": [
                ("--cap-drop", "ALL"),
                ("--security-opt", "no-new-privileges:true"),
                ("--pids-limit", "256"),
                ("--read-only", None),
            ],
            "required_tmpfs_prefixes": [
                "/tmp:",
                "/run:",
            ],
            "required_security_opt_prefixes": [
                "seccomp=",
            ],
            "allowed_mount_targets": {
                "/workspace",
                "/home/cuti/.clawdbot",
                "/home/cuti/clawd",
            },
            "forbidden_mount_targets": {
                "/var/run/docker.sock",
                "/home/cuti/.cuti-shared",
                "/home/cuti/.claude-linux",
                "/home/cuti/.claude-macos",
            },
            "forbidden_network_values": {"host"},
            "require_workspace_mount": True,
        }
    }
    
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

# Install Docker CLI and docker-compose for Docker-in-Docker support
RUN apt-get update && apt-get install -y --no-install-recommends \\
    apt-transport-https ca-certificates curl gnupg lsb-release \\
    && curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - \\
    && echo "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \\
    && apt-get update \\
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \\
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create enhanced docker-compose wrapper
RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            '# Enhanced docker-compose wrapper for cuti containers' \
            '# Ensures proper permissions and compatibility' \
            '' \
            '# First check if we can access Docker' \
            'if ! docker version &>/dev/null 2>&1; then' \
            '    # Try with sudo if available' \
            '    if command -v sudo &>/dev/null && sudo -n docker version &>/dev/null 2>&1; then' \
            '        # sudo works without password, use it' \
            '        if [ "$1" = "--version" ] || [ "$1" = "-v" ]; then' \
            '            exec sudo docker compose version' \
            '        else' \
            '            exec sudo docker compose "$@"' \
            '        fi' \
            '    else' \
            '        # Docker not accessible, show helpful error' \
            '        echo "Error: Cannot access Docker. Please check:" >&2' \
            '        echo "  1. Docker socket is mounted: -v /var/run/docker.sock:/var/run/docker.sock" >&2' \
            '        echo "  2. User is in docker group: groups | grep docker" >&2' \
            '        echo "  3. Socket permissions: ls -la /var/run/docker.sock" >&2' \
            '        exit 1' \
            '    fi' \
            'fi' \
            '' \
            '# Docker is accessible, use docker compose directly' \
            'if [ "$1" = "--version" ] || [ "$1" = "-v" ]; then' \
            '    exec docker compose version' \
            'else' \
            '    exec docker compose "$@"' \
            'fi'; \
    } > /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose

# Configure locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8

# Install Node.js and pnpm
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \\
    && apt-get install -y nodejs \\
    && npm install -g npm@latest \\
    && npm install -g pnpm@latest \\
    && echo '#!/bin/bash' > /usr/local/bin/npm-original \\
    && echo 'exec /usr/bin/npm "$@"' >> /usr/local/bin/npm-original \\
    && chmod +x /usr/local/bin/npm-original \\
    && echo '#!/bin/bash' > /usr/local/bin/npm \\
    && echo '# npm aliased to pnpm for better performance' >> /usr/local/bin/npm \\
    && echo 'exec pnpm "$@"' >> /usr/local/bin/npm \\
    && chmod +x /usr/local/bin/npm

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Create non-root user with sudo access and Docker permissions
RUN groupadd --gid $USER_GID $USERNAME \\
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/zsh \\
    && echo $USERNAME ALL=\\(root\\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \\
    && chmod 0440 /etc/sudoers.d/$USERNAME \\
    && (getent group docker || groupadd -g 991 docker) \\
    && usermod -aG docker $USERNAME \\
    && chmod 755 /usr/local/bin/docker-compose \\
    && chown root:docker /usr/local/bin/docker-compose

# Native installer helpers for agent providers
RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'export HOME="${HOME:-/home/cuti}"' \
            'curl -fsSL https://claude.ai/install.sh | bash -s -- "$@"'; \
    } > /usr/local/bin/cuti-install-claude \
    && chmod +x /usr/local/bin/cuti-install-claude

RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'export HOME="${HOME:-/home/cuti}"' \
            'export CODEX_INSTALL_DIR="${CODEX_INSTALL_DIR:-$HOME/.local/bin}"' \
            'curl -fsSL https://github.com/openai/codex/releases/latest/download/install.sh | sh -s -- "$@"'; \
    } > /usr/local/bin/cuti-install-codex \
    && chmod +x /usr/local/bin/cuti-install-codex

RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'export HOME="${HOME:-/home/cuti}"' \
            'curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path "$@"'; \
    } > /usr/local/bin/cuti-install-opencode \
    && chmod +x /usr/local/bin/cuti-install-opencode

RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'export HOME="${HOME:-/home/cuti}"' \
            '/usr/local/bin/npm-original install -g openclaw@latest "$@"'; \
    } > /usr/local/bin/cuti-install-openclaw \
    && chmod +x /usr/local/bin/cuti-install-openclaw

RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'export IS_SANDBOX=1' \
            'export CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true' \
            'export CLAUDE_CONFIG_DIR=/home/cuti/.claude-linux' \
            'CLAUDE_CLI="/home/cuti/.local/bin/claude"' \
            'if [ ! -x "$CLAUDE_CLI" ]; then' \
            '    echo "Claude CLI not found. Rebuild the container or run: /usr/local/bin/cuti-install-claude" >&2' \
            '    exit 1' \
            'fi' \
            'exec "$CLAUDE_CLI" "$@"'; \
    } > /usr/local/bin/claude \
    && chmod +x /usr/local/bin/claude

RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'export PATH="/home/cuti/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"' \
            'CODEX_CLI="/home/cuti/.local/bin/codex"' \
            'if [ ! -x "$CODEX_CLI" ]; then' \
            '    echo "Codex CLI not found. Enable the codex provider or run: /usr/local/bin/cuti-install-codex" >&2' \
            '    exit 1' \
            'fi' \
            'exec "$CODEX_CLI" "$@"'; \
    } > /usr/local/bin/codex \
    && chmod +x /usr/local/bin/codex

RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'export PATH="/home/cuti/.opencode/bin:/home/cuti/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"' \
            'OPENCODE_CLI="/home/cuti/.opencode/bin/opencode"' \
            'if [ ! -x "$OPENCODE_CLI" ]; then' \
            '    echo "OpenCode CLI not found. Enable the opencode provider or run: /usr/local/bin/cuti-install-opencode" >&2' \
            '    exit 1' \
            'fi' \
            'exec "$OPENCODE_CLI" "$@"'; \
    } > /usr/local/bin/opencode \
    && chmod +x /usr/local/bin/opencode

RUN { \
        printf '%s\\n' \
            '#!/bin/bash' \
            'set -euo pipefail' \
            'OPENCLAW_PACKAGE_ROOT="$(/usr/local/bin/npm-original root -g 2>/dev/null || true)/openclaw"' \
            'OPENCLAW_ENTRY="$OPENCLAW_PACKAGE_ROOT/openclaw.mjs"' \
            'if [ ! -f "$OPENCLAW_ENTRY" ]; then' \
            '    echo "OpenClaw CLI not found. Enable the openclaw provider or run: /usr/local/bin/cuti-install-openclaw" >&2' \
            '    exit 1' \
            'fi' \
            'exec node "$OPENCLAW_ENTRY" "$@"'; \
    } > /usr/local/bin/openclaw \
    && chmod +x /usr/local/bin/openclaw

{CUTI_INSTALL}

# Switch to non-root user
USER $USERNAME

# Install uv for the non-root user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/cuti/.local/bin:${PATH}"

# Install Claude Code via the native installer
RUN HOME=/home/cuti /usr/local/bin/cuti-install-claude

# Install oh-my-zsh with simple configuration
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \\
    && echo 'export PATH="/home/cuti/.opencode/bin:/usr/local/bin:/home/cuti/.local/bin:/root/.local/share/uv/tools/cuti/bin:$PATH"' >> ~/.zshrc \\
    && echo 'export PYTHONPATH="/workspace/src:$PYTHONPATH"' >> ~/.zshrc \\
    && echo 'export CUTI_IN_CONTAINER=true' >> ~/.zshrc \\
    && echo 'export ANTHROPIC_CLAUDE_BYPASS_PERMISSIONS=1' >> ~/.zshrc \\
    && echo 'export CLAUDE_CONFIG_DIR=/home/cuti/.claude-linux' >> ~/.zshrc \\
    && echo 'export CODEX_HOME=/home/cuti/.codex' >> ~/.zshrc \\
    && echo 'export XDG_CONFIG_HOME=/home/cuti/.config' >> ~/.zshrc \\
    && echo 'export XDG_DATA_HOME=/home/cuti/.local/share' >> ~/.zshrc \\
    && echo 'alias claude="claude --dangerously-skip-permissions"' >> ~/.zshrc \\
    && echo 'alias npm-original="/usr/local/bin/npm-original"' >> ~/.zshrc \\
    && echo 'echo "🚀 Welcome to cuti dev container!"' >> ~/.zshrc \\
    && echo 'echo "Commands: cuti | claude | codex | opencode | openclaw"' >> ~/.zshrc \\
    && echo 'echo "📦 pnpm is the default package manager (npm commands use pnpm)"' >> ~/.zshrc \\
    && echo 'echo "   Use npm-original for actual npm if needed"' >> ~/.zshrc

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
        "runArgs": ["--init"],
        "containerEnv": {
            "CUTI_IN_CONTAINER": "true",
            "ANTHROPIC_CLAUDE_BYPASS_PERMISSIONS": "1",
            "PYTHONUNBUFFERED": "1"
        },
        "mounts": [
            "source=${localEnv:HOME}/.cuti/claude-linux,target=/home/cuti/.claude-linux,type=bind,consistency=cached",
            "source=${localEnv:HOME}/.claude,target=/home/cuti/.claude-macos,type=bind,consistency=cached,readonly",
            "source=cuti-cache-${localWorkspaceFolderBasename},target=/home/cuti/.cache,type=volume"
        ],
        "forwardPorts": [8000, 8080, 3000, 5000],
        "postCreateCommand": "echo '✅ Container initialized'",
        "remoteUser": "cuti"
    }
    
    def __init__(
        self,
        working_directory: Optional[str] = None,
        *,
        provider_storage_dir: Optional[Path] = None,
    ):
        """Initialize the dev container service."""
        self.working_dir = Path(working_directory) if working_directory else Path.cwd()
        self.devcontainer_dir = self.working_dir / ".devcontainer"
        self.is_macos = platform.system() == "Darwin"
        self.provider_manager = ProviderManager(storage_dir=provider_storage_dir)
        self._selected_providers_cache: Optional[List[str]] = None
        
        # Check tool availability (cached for CLI compatibility)
        self.docker_available = self._check_tool_available("docker")
        self.colima_available = self._check_tool_available("colima")

    def _run_command(self, cmd: List[str], timeout: int = 30, show_output: bool = False) -> subprocess.CompletedProcess:
        """Run a command with consistent error handling."""
        try:
            if show_output:
                # Use Popen to show output in real-time but still capture it
                import sys
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                output = []
                for line in process.stdout:
                    print(line, end='')
                    sys.stdout.flush()
                    output.append(line)
                
                process.wait(timeout=timeout)
                return subprocess.CompletedProcess(
                    cmd, 
                    process.returncode,
                    stdout=''.join(output),
                    stderr=None
                )
            else:
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False
                )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            raise RuntimeError(f"Command not found: {cmd[0]}")

    def _selected_providers(self) -> List[str]:
        """Return the enabled provider IDs for the cloud container profile."""

        if self._selected_providers_cache is None:
            self._selected_providers_cache = self.provider_manager.selected_providers()
        return list(self._selected_providers_cache)

    def _is_provider_enabled(self, provider: str) -> bool:
        """Return True when a provider is selected for the container runtime."""

        return provider in self._selected_providers()

    def _primary_provider(self) -> Optional[str]:
        """Return the primary provider for prompts/help text."""

        providers = self._selected_providers()
        if not providers:
            return None
        if "claude" in providers:
            return "claude"
        return providers[0]

    def _clawdbot_workspace_slug(self) -> str:
        """Return a stable slug for the current project to scope Clawdbot history."""

        resolved = self.working_dir.resolve()
        digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:8]
        base_name = resolved.name or "workspace"
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", base_name).strip("-") or "workspace"
        return f"{sanitized}-{digest}"

    def _prepare_clawdbot_storage(self) -> Tuple[Path, Path]:
        """Ensure Clawdbot config/workspace live under ~/.cuti/clawdbot."""

        root = Path.home() / ".cuti" / "clawdbot"
        root.mkdir(parents=True, exist_ok=True)

        config_dir = root / "config"
        workspaces_root = root / "workspaces"
        workspaces_root.mkdir(parents=True, exist_ok=True)
        workspace_dir = workspaces_root / self._clawdbot_workspace_slug()

        self._migrate_legacy_dir(Path.home() / ".clawdbot", config_dir, "Clawdbot config")
        self._migrate_legacy_dir(Path.home() / "clawd", workspace_dir, "Clawdbot workspace")

        config_dir.mkdir(parents=True, exist_ok=True)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        return config_dir, workspace_dir

    def _migrate_legacy_dir(self, legacy_path: Path, new_path: Path, label: str) -> None:
        """Move/copy legacy directories into the new ~/.cuti hierarchy."""

        try:
            if legacy_path.exists() and not new_path.exists():
                shutil.move(str(legacy_path), str(new_path))
                print(f"🔁 Migrated legacy {label} to {new_path}")
        except Exception as exc:
            print(f"⚠️  Could not migrate {label}: {exc}")

    def _prepare_agents_storage(self) -> Path:
        """Ensure shared AGENTS-based personal skill storage exists."""

        agents_dir = Path.home() / ".agents"
        (agents_dir / "skills").mkdir(parents=True, exist_ok=True)
        return agents_dir

    def _prepare_codex_storage(self) -> Path:
        """Ensure Codex home storage exists on the host."""

        codex_dir = Path.home() / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        return codex_dir

    def _prepare_opencode_storage(self) -> Tuple[Path, Path, Path]:
        """Ensure OpenCode storage directories exist on the host."""

        home_dir = Path.home() / ".opencode"
        config_dir = Path.home() / ".config" / "opencode"
        data_dir = Path.home() / ".local" / "share" / "opencode"

        (home_dir / "bin").mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        return home_dir, config_dir, data_dir

    def _prepare_openclaw_storage(self) -> Path:
        """Ensure OpenClaw state storage exists on the host."""

        openclaw_dir = Path.home() / ".openclaw"
        openclaw_dir.mkdir(parents=True, exist_ok=True)
        (openclaw_dir / "credentials").mkdir(parents=True, exist_ok=True)
        return openclaw_dir

    def _selected_providers_env_value(self) -> str:
        """Return selected providers as a comma-separated environment value."""

        return ",".join(self._selected_providers())

    def _prepare_cloud_provider_mounts(self) -> Tuple[Optional[Path], List[str]]:
        """Prepare host storage and mount specs for selected cloud providers."""

        providers = set(self._selected_providers())
        mount_args: List[str] = []
        linux_claude_dir: Optional[Path] = None

        if "claude" in providers:
            linux_claude_dir = self._setup_claude_host_config()
            mount_args.extend(
                [
                    "-v",
                    f"{linux_claude_dir}:/home/cuti/.claude-linux:rw",
                    "-v",
                    f"{Path.home() / '.claude'}:/home/cuti/.claude-macos:ro",
                ]
            )

        if providers & {"codex", "opencode", "openclaw"}:
            agents_dir = self._prepare_agents_storage()
            mount_args.extend(["-v", f"{agents_dir}:/home/cuti/.agents:rw"])

        if "codex" in providers:
            codex_dir = self._prepare_codex_storage()
            mount_args.extend(["-v", f"{codex_dir}:/home/cuti/.codex:rw"])

        if "opencode" in providers:
            opencode_home, opencode_config, opencode_data = self._prepare_opencode_storage()
            mount_args.extend(
                [
                    "-v",
                    f"{opencode_home}:/home/cuti/.opencode:rw",
                    "-v",
                    f"{opencode_config}:/home/cuti/.config/opencode:rw",
                    "-v",
                    f"{opencode_data}:/home/cuti/.local/share/opencode:rw",
                ]
            )

        if "openclaw" in providers:
            openclaw_dir = self._prepare_openclaw_storage()
            mount_args.extend(["-v", f"{openclaw_dir}:/home/cuti/.openclaw:rw"])

        return linux_claude_dir, mount_args
    
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

        # Add tools installation if the setup script exists
        tools_setup = ""
        container_tools_path = Path("/workspace/.cuti/container_tools.sh")
        if container_tools_path.exists():
            tools_setup = f'''
# Install additional CLI tools
COPY .cuti/container_tools.sh /tmp/container_tools.sh
RUN chmod +x /tmp/container_tools.sh && /tmp/container_tools.sh
'''
        
        dockerfile = self.DOCKERFILE_TEMPLATE.replace("{CUTI_INSTALL}", cuti_install)

        # Insert tools setup before the final CMD if it exists
        if tools_setup:
            dockerfile = dockerfile.replace("# Set the default command", tools_setup + "\n# Set the default command")
        
        return dockerfile
    
    def _setup_claude_host_config(self):
        """Setup Claude configuration on host for container usage."""
        # Create Linux-specific Claude config directory (separate from macOS)
        linux_claude_dir = Path.home() / ".cuti" / "claude-linux"
        linux_claude_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories that Claude CLI expects
        for subdir in ["plugins", "plugins/repos", "todos", "sessions", "projects", 
                       "statsig", "shell-snapshots", "ide"]:
            (linux_claude_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Set permissions to be writable for all users and files
        import stat
        try:
            # Make the directory world-writable to avoid UID/GID issues
            dir_mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
            file_mode = (
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
            )
            linux_claude_dir.chmod(dir_mode)
            for item in linux_claude_dir.rglob("*"):
                if not item.exists():
                    continue
                if item.is_dir():
                    item.chmod(dir_mode)
                else:
                    # Make files readable and writable by all
                    item.chmod(file_mode)
        except Exception as e:
            print(f"⚠️  Could not set permissions: {e}")
        
        # Copy non-credential files from host .claude if Linux dir is empty
        host_claude_dir = Path.home() / ".claude"
        
        # Only copy configuration files, not credentials (to avoid conflicts)
        if host_claude_dir.exists() and not any(linux_claude_dir.iterdir()):
            print("📋 Initializing Linux Claude config from host settings...")
            import shutil
            
            # Copy CLAUDE.md if it exists
            host_claude_md = host_claude_dir / "CLAUDE.md"
            if host_claude_md.exists():
                shutil.copy2(host_claude_md, linux_claude_dir / "CLAUDE.md")
                print("📄 Copied CLAUDE.md from host")
            
            # Copy settings if they exist
            host_settings = host_claude_dir / "settings.json"
            if host_settings.exists():
                shutil.copy2(host_settings, linux_claude_dir / "settings.json")
                print("⚙️  Copied settings from host")
            
            # Copy plugins config if it exists
            host_plugins_config = host_claude_dir / "plugins" / "config.json"
            if host_plugins_config.exists():
                dest_plugins_dir = linux_claude_dir / "plugins"
                dest_plugins_dir.mkdir(exist_ok=True)
                shutil.copy2(host_plugins_config, dest_plugins_dir / "config.json")
                print("🔌 Copied plugins config from host")
        
        # Create or update Linux-specific .claude.json
        linux_claude_json = linux_claude_dir / ".claude.json"
        config = {}
        if linux_claude_json.exists():
            try:
                with open(linux_claude_json, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        
        # Always ensure bypassPermissionsModeAccepted is set
        # Ensure bypass permissions mode is accepted
        config['bypassPermissionsModeAccepted'] = True
        with open(linux_claude_json, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Check if credentials already exist from previous container sessions
        linux_credentials = linux_claude_dir / ".credentials.json"
        if linux_credentials.exists():
            print(f"✅ Linux Claude config ready at {linux_claude_dir}")
            print("🔑 Found existing Linux credentials - no login needed!")
            print("📌 Credentials persist across all containers")
        else:
            print(f"📋 Linux Claude config initialized at {linux_claude_dir}")
            print("⚠️  No credentials found. You'll need to authenticate once:")
            print("   Run 'claude login' inside the container")
            print("   Credentials will persist for all future containers")
        
        print("📋 macOS Claude config mounted read-only for reference")
        
        return linux_claude_dir
    
    def _build_container_image(self, image_name: str, rebuild: bool = False) -> bool:
        """Build the container image with retry logic."""
        import time
        
        if rebuild:
            print("🔨 Rebuilding container (forced rebuild)...")
            self._run_command(["docker", "rmi", "-f", image_name])
        else:
            # Check if image exists
            result = self._run_command(["docker", "images", "-q", image_name])
            if result.stdout.strip():
                return True
            print("🔨 Building container (first time setup)...")
        
        # Retry logic for build
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
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
                            shutil.copytree(self.working_dir / "docs", Path(tmpdir) / "docs", dirs_exist_ok=True)
                    
                    # Build image
                    build_cmd = ["docker", "build", "-t", image_name, "-f", str(dockerfile_path)]
                    if rebuild:
                        build_cmd.append("--no-cache")
                    build_cmd.append(build_context)
                    
                    result = self._run_command(build_cmd, timeout=1800, show_output=True)
                    if result.returncode == 0:
                        print("✅ Container built successfully")
                        return True
                    else:
                        # Check both stderr and stdout for connection issues
                        error_output = str(result.stderr or "") + str(result.stdout or "")
                        if any(err in error_output.lower() for err in ["broken pipe", "closed pipe", "connection", "socket"]):
                            if attempt < max_retries - 1:
                                print(f"⚠️  Build failed due to connection issue. Retrying in {retry_delay} seconds... (attempt {attempt + 2}/{max_retries})")
                                time.sleep(retry_delay)
                                # Try to restart Docker daemon
                                print("🔄 Restarting Colima...")
                                self._run_command(["colima", "restart"], timeout=120)
                                time.sleep(10)  # Give Docker more time to stabilize
                                continue
                        print(f"❌ Container build failed: {result.stderr}")
                        return False
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Build failed with error: {e}. Retrying... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"❌ Container build failed after {max_retries} attempts: {e}")
                    return False
        
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

    @staticmethod
    def _extract_mount_target(volume_spec: str) -> Optional[str]:
        """Extract target path from a docker -v/--volume spec."""
        parts = volume_spec.split(":")
        if len(parts) < 2:
            return None
        return parts[1]

    def _collect_mount_targets(self, docker_args: List[str]) -> Set[str]:
        """Collect all bind mount targets from docker args."""
        targets: Set[str] = set()
        for idx, arg in enumerate(docker_args):
            if arg in ("-v", "--volume") and idx + 1 < len(docker_args):
                target = self._extract_mount_target(docker_args[idx + 1])
                if target:
                    targets.add(target)
        return targets

    @staticmethod
    def _remove_flag_value_pair(args: List[str], flag: str, value: str) -> List[str]:
        """Return args with the first matching flag/value pair removed."""
        new_args = list(args)
        for idx in range(len(new_args) - 1):
            if new_args[idx] == flag and new_args[idx + 1] == value:
                del new_args[idx: idx + 2]
                break
        return new_args

    @staticmethod
    def _flag_has_value(docker_args: List[str], flag: str, expected: str) -> bool:
        """Return True if docker args contain a flag with the expected value."""
        for idx, arg in enumerate(docker_args[:-1]):
            if arg == flag and docker_args[idx + 1] == expected:
                return True
        return False

    @staticmethod
    def _security_opt_values(docker_args: List[str]) -> List[str]:
        """Return all --security-opt values in docker args."""
        values: List[str] = []
        for idx, arg in enumerate(docker_args[:-1]):
            if arg == "--security-opt":
                values.append(docker_args[idx + 1])
        return values

    def _repository_seccomp_profile_path(self) -> Optional[Path]:
        """Locate repository seccomp profile when available."""
        try:
            repo_root = Path(__file__).resolve().parents[3]
        except IndexError:
            return None

        candidate = repo_root / "docker" / "seccomp" / self.CLAWDBOT_SECCOMP_FILENAME
        if candidate.exists():
            return candidate
        return None

    def _ensure_clawdbot_seccomp_profile(self) -> Optional[Path]:
        """Ensure the clawdbot seccomp profile exists and return an absolute host path."""
        override = os.environ.get("CUTI_CLAWDBOT_SECCOMP_PROFILE")
        if override:
            override_path = Path(override).expanduser().resolve()
            if override_path.exists():
                return override_path
            print(f"❌ CUTI_CLAWDBOT_SECCOMP_PROFILE does not exist: {override_path}")
            return None

        self.CLAWDBOT_SECCOMP_DIR.mkdir(parents=True, exist_ok=True)
        target_path = (self.CLAWDBOT_SECCOMP_DIR / self.CLAWDBOT_SECCOMP_FILENAME).resolve()

        source_path = self._repository_seccomp_profile_path()
        if source_path:
            content = source_path.read_text(encoding="utf-8")
        else:
            content = json.dumps(self.DEFAULT_CLAWDBOT_SECCOMP_PROFILE, indent=2) + "\n"

        if not target_path.exists() or target_path.read_text(encoding="utf-8") != content:
            target_path.write_text(content, encoding="utf-8")

        return target_path

    def _validate_runtime_profile_args(self, runtime_profile: str, docker_args: List[str]) -> List[str]:
        """Validate runtime args against the profile security checklist."""
        checklist = self.RUNTIME_SECURITY_CHECKLIST.get(runtime_profile)
        if not checklist:
            return []

        errors: List[str] = []
        mount_targets = self._collect_mount_targets(docker_args)

        required_flags = checklist.get("required_flags", [])
        for flag, expected in required_flags:
            if expected is None:
                if flag not in docker_args:
                    errors.append(f"missing required flag '{flag}'")
                continue
            if not self._flag_has_value(docker_args, flag, expected):
                errors.append(f"missing required flag/value '{flag} {expected}'")

        required_tmpfs_prefixes = checklist.get("required_tmpfs_prefixes", [])
        tmpfs_values = []
        for idx, arg in enumerate(docker_args[:-1]):
            if arg == "--tmpfs":
                tmpfs_values.append(docker_args[idx + 1])
        for prefix in required_tmpfs_prefixes:
            if not any(value.startswith(prefix) for value in tmpfs_values):
                errors.append(f"missing required tmpfs mount with prefix '{prefix}'")

        required_security_opt_prefixes = checklist.get("required_security_opt_prefixes", [])
        security_opt_values = self._security_opt_values(docker_args)
        for prefix in required_security_opt_prefixes:
            if not any(value.startswith(prefix) for value in security_opt_values):
                errors.append(f"missing required --security-opt value with prefix '{prefix}'")

        forbidden_network_values = checklist.get("forbidden_network_values", set())
        for idx, arg in enumerate(docker_args[:-1]):
            if arg == "--network" and docker_args[idx + 1] in forbidden_network_values:
                errors.append(f"forbidden network mode '{docker_args[idx + 1]}'")

        forbidden_targets = checklist.get("forbidden_mount_targets", set())
        for target in sorted(mount_targets):
            if target in forbidden_targets:
                errors.append(f"forbidden mount target '{target}'")

        allowed_targets = checklist.get("allowed_mount_targets")
        if allowed_targets is not None:
            allowed = set(allowed_targets)
            for target in sorted(mount_targets):
                if target not in allowed:
                    errors.append(f"mount target '{target}' is not allowed for profile '{runtime_profile}'")

        if checklist.get("require_workspace_mount", False) and "/workspace" not in mount_targets:
            errors.append("missing required workspace mount '/workspace'")

        return errors
    
    def run_in_container(
        self,
        command: Optional[str] = None,
        rebuild: bool = False,
        interactive: bool = False,
        *,
        mount_docker_socket: bool = True,
        runtime_profile: str = RUNTIME_PROFILE_CLOUD,
        published_ports: Optional[List[int]] = None,
    ) -> int:
        """Run command in dev container.

        Args:
            command: Command to run in the container
            rebuild: Force rebuild of the container image
            interactive: Run in interactive mode with TTY
            mount_docker_socket: Whether to mount host docker socket
            runtime_profile: Runtime profile (`cloud` or `clawdbot_sandbox`)
            published_ports: Host/container ports to publish (same port number)
        """
        if runtime_profile not in {
            self.RUNTIME_PROFILE_CLOUD,
            self.RUNTIME_PROFILE_CLAWDBOT_SANDBOX,
        }:
            print(f"❌ Unknown runtime profile: {runtime_profile}")
            return 1

        if runtime_profile == self.RUNTIME_PROFILE_CLAWDBOT_SANDBOX and mount_docker_socket:
            print("❌ Security policy violation: clawdbot sandbox profile cannot mount docker socket")
            return 1

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
        
        primary_provider = self._primary_provider()
        _linux_claude_dir: Optional[Path] = None
        provider_mount_args: List[str] = []
        if runtime_profile == self.RUNTIME_PROFILE_CLOUD:
            _linux_claude_dir, provider_mount_args = self._prepare_cloud_provider_mounts()

        clawdbot_enabled = False
        clawdbot_config_subpath: Optional[str] = None
        clawdbot_workspace_subpath: Optional[str] = None
        clawdbot_config_dir: Optional[Path] = None
        clawdbot_workspace_dir: Optional[Path] = None
        if runtime_profile == self.RUNTIME_PROFILE_CLAWDBOT_SANDBOX:
            clawdbot_enabled = True
            # Ensure host-side config/workspace directories exist
            clawdbot_config_dir, clawdbot_workspace_dir = self._prepare_clawdbot_storage()
            cuti_root = Path.home() / ".cuti"
            try:
                clawdbot_config_subpath = str(clawdbot_config_dir.relative_to(cuti_root))
                clawdbot_workspace_subpath = str(clawdbot_workspace_dir.relative_to(cuti_root))
            except ValueError:
                clawdbot_config_subpath = clawdbot_workspace_subpath = None

        if runtime_profile == self.RUNTIME_PROFILE_CLOUD:
            docker_args = [
                "docker", "run", "--rm", "--init",
                "-v", f"{current_dir}:/workspace:{mount_options}",  # Dynamic mount options
                "-v", f"{Path.home() / '.cuti'}:/home/cuti/.cuti-shared:rw",  # Mount to cuti-accessible location
                "--label", f"cuti.runtime_profile={runtime_profile}",
                "--label", f"cuti.workspace={current_dir}",
                "-w", "/workspace",
                "--env", "CUTI_IN_CONTAINER=true",
                "--env", f"CUTI_RUNTIME_PROFILE={runtime_profile}",
                # Don't set CLAUDE_QUEUE_STORAGE_DIR here - let the init script decide based on writability
                "--env", "IS_SANDBOX=1",
                "--env", "CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true",
                # Don't set CLAUDE_CONFIG_DIR here - let the init script decide based on writability
                "--env", "PYTHONUNBUFFERED=1",
                "--env", "PYTHONPATH=/workspace/src",
                "--env", "TERM=xterm-256color",
                "--env", "PATH=/home/cuti/.opencode/bin:/home/cuti/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
                "--env", "NODE_PATH=/usr/lib/node_modules:/usr/local/lib/node_modules",
                "--env", "CODEX_HOME=/home/cuti/.codex",
                "--env", "XDG_CONFIG_HOME=/home/cuti/.config",
                "--env", "XDG_DATA_HOME=/home/cuti/.local/share",
                "--env", f"CUTI_AGENT_PROVIDERS={self._selected_providers_env_value()}",
                "--env", f"CUTI_PRIMARY_AGENT_PROVIDER={primary_provider or ''}",
                "--network", "host",
            ]
            docker_args.extend(provider_mount_args)

            if mount_docker_socket:
                docker_args.extend([
                    "-v",
                    "/var/run/docker.sock:/var/run/docker.sock",  # Allow Docker-in-Docker when explicitly requested
                ])

            if clawdbot_config_subpath and clawdbot_workspace_subpath:
                docker_args.extend(
                    [
                        "--env",
                        f"CUTI_CLAWDBOT_CONFIG_SUBPATH={clawdbot_config_subpath}",
                        "--env",
                        f"CUTI_CLAWDBOT_WORKSPACE_SUBPATH={clawdbot_workspace_subpath}",
                    ]
                )
        else:
            # Hardened clawdbot sandbox runtime: workspace + explicit clawdbot mounts only.
            if not clawdbot_config_dir or not clawdbot_workspace_dir:
                print("❌ Failed to initialize Clawdbot config/workspace directories")
                return 1

            seccomp_profile_path = self._ensure_clawdbot_seccomp_profile()
            if not seccomp_profile_path:
                print("❌ Failed to prepare clawdbot seccomp profile")
                return 1

            docker_args = [
                "docker", "run", "--rm", "--init",
                "-v", f"{current_dir}:/workspace:{mount_options}",
                "-v", f"{clawdbot_config_dir}:/home/cuti/.clawdbot:rw",
                "-v", f"{clawdbot_workspace_dir}:/home/cuti/clawd:rw",
                "--label", f"cuti.runtime_profile={runtime_profile}",
                "--label", f"cuti.workspace={current_dir}",
                "--label", "cuti.mode=clawdbot",
                "-w", "/workspace",
                "--env", "CUTI_IN_CONTAINER=true",
                "--env", f"CUTI_RUNTIME_PROFILE={runtime_profile}",
                "--env", "CUTI_ENABLE_CLAWDBOT_ADDON=true",
                "--env", "IS_SANDBOX=1",
                "--env", "PYTHONUNBUFFERED=1",
                "--env", "TERM=xterm-256color",
                "--env", "PATH=/home/cuti/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
                "--env", "NODE_PATH=/usr/lib/node_modules:/usr/local/lib/node_modules",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges:true",
                "--security-opt", f"seccomp={seccomp_profile_path}",
                "--pids-limit", "256",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,nodev",
                "--tmpfs", "/run:rw,nosuid,nodev",
            ]

            unique_ports = sorted(set(published_ports or []))
            for port in unique_ports:
                docker_args.extend(["-p", f"127.0.0.1:{port}:{port}"])

        security_errors = self._validate_runtime_profile_args(runtime_profile, docker_args)
        if security_errors:
            print(f"❌ Runtime security policy validation failed for profile '{runtime_profile}'.")
            for error in security_errors:
                print(f"   - {error}")
            print("🛑 Refusing to start container (fail-closed).")
            return 1

        docker_args.append(image_name)
        
        # Setup initialization command for mounted directory
        init_script = """
# Set up signal handlers to ensure clean exit
trap 'echo "Container exiting cleanly..."; exit 0' SIGTERM SIGINT

# Test if workspace is writable
if touch /workspace/.test_write 2>/dev/null; then
    rm /workspace/.test_write
    WORKSPACE_WRITABLE=true
    echo "✅ Workspace is writable"
    # Use workspace directories when writable
    export CLAUDE_QUEUE_STORAGE_DIR=/workspace/.cuti
    export CLAUDE_CONFIG_DIR=/home/cuti/.claude-linux
else
    WORKSPACE_WRITABLE=false
    echo "⚠️  WARNING: Workspace mounted as read-only!"
    echo "    This prevents agent providers from editing your code."
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
    export CLAUDE_CONFIG_DIR=/home/cuti/.claude-linux
fi

cuti_provider_selected() {
    case ",${CUTI_AGENT_PROVIDERS:-}," in
        *,"$1",*) return 0 ;;
        *) return 1 ;;
    esac
}

if [ -n "${CUTI_AGENT_PROVIDERS:-}" ]; then
    echo "🧩 Selected providers: ${CUTI_AGENT_PROVIDERS}"
else
    echo "🧩 No agent providers selected"
fi

# The .claude-linux directory is mounted for Linux-specific credentials
# Ensure proper ownership for the mounted directories

# Fix Docker socket permissions if needed
if [ -e /var/run/docker.sock ]; then
    # Get the GID of the docker socket
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
    
    # Check if we need to update the docker group GID
    CURRENT_DOCKER_GID=$(getent group docker | cut -d: -f3)
    if [ "$DOCKER_GID" != "$CURRENT_DOCKER_GID" ]; then
        echo "📦 Updating docker group GID to match socket ($DOCKER_GID)..."
        sudo groupmod -g $DOCKER_GID docker
    fi
    
    # Ensure user is in docker group (compare numeric GIDs to avoid missing-name warnings)
    USER_GROUPS=$(id -G 2>/dev/null || echo "")
    if ! echo "$USER_GROUPS" | tr ' ' '\n' | grep -qx "$DOCKER_GID"; then
        echo "📦 Adding user to docker group..."
        sudo usermod -aG docker $USER
        # Apply group changes in current session
        newgrp docker
    fi
    
    # Test Docker access
    if docker version &>/dev/null; then
        echo "✅ Docker is accessible"
    else
        echo "⚠️  Docker socket mounted but not accessible"
        echo "   You may need to restart the container"
    fi
else
    echo "⚠️  Docker socket not mounted - Docker-in-Docker features unavailable"
fi
if [ -d /home/cuti/.claude-linux ]; then
    # Fix ownership if needed (container user might have different UID/GID)
    sudo chown -R cuti:cuti /home/cuti/.claude-linux 2>/dev/null || true
    echo "🔗 Linux Claude config mounted from host"
fi

if cuti_provider_selected claude; then
    if [ ! -x /home/cuti/.local/bin/claude ]; then
        echo "🧠 Installing Claude Code native build..."
        export HOME=/home/cuti
        if /usr/local/bin/cuti-install-claude > /tmp/claude-install.log 2>&1; then
            echo "✅ Claude Code installed"
        else
            echo "⚠️  Failed to install Claude Code"
            cat /tmp/claude-install.log
        fi
    fi
fi

if cuti_provider_selected codex; then
    if [ -x /home/cuti/.local/bin/codex ]; then
        echo "✅ Codex CLI already installed"
    else
        echo "🤖 Installing Codex CLI..."
        export HOME=/home/cuti
        export CODEX_INSTALL_DIR=/home/cuti/.local/bin
        export CODEX_HOME=/home/cuti/.codex
        if /usr/local/bin/cuti-install-codex > /tmp/codex-install.log 2>&1; then
            echo "✅ Codex CLI installed"
            hash -r 2>/dev/null || true
        else
            echo "⚠️  Failed to install Codex CLI"
            cat /tmp/codex-install.log
        fi
    fi
fi

if cuti_provider_selected opencode; then
    mkdir -p /home/cuti/.opencode /home/cuti/.config/opencode /home/cuti/.local/share/opencode
    if [ -x /home/cuti/.opencode/bin/opencode ]; then
        echo "✅ OpenCode CLI already installed"
    else
        echo "🪄 Installing OpenCode CLI..."
        export HOME=/home/cuti
        if /usr/local/bin/cuti-install-opencode > /tmp/opencode-install.log 2>&1; then
            echo "✅ OpenCode CLI installed"
            hash -r 2>/dev/null || true
        else
            echo "⚠️  Failed to install OpenCode CLI"
            cat /tmp/opencode-install.log
        fi
    fi
fi

if cuti_provider_selected openclaw; then
    mkdir -p /home/cuti/.openclaw /home/cuti/.agents/skills
    OPENCLAW_PACKAGE_ROOT="$(npm-original root -g 2>/dev/null || true)/openclaw"
    if [ -f "$OPENCLAW_PACKAGE_ROOT/openclaw.mjs" ]; then
        echo "✅ OpenClaw CLI already installed"
    else
        echo "🦞 Installing OpenClaw CLI..."
        export HOME=/home/cuti
        if sudo /usr/local/bin/cuti-install-openclaw > /tmp/openclaw-install.log 2>&1; then
            echo "✅ OpenClaw CLI installed"
            hash -r 2>/dev/null || true
        else
            echo "⚠️  Failed to install OpenClaw CLI"
            cat /tmp/openclaw-install.log
        fi
    fi

    if [ ! -e /home/cuti/.openclaw/workspace ]; then
        ln -s /workspace /home/cuti/.openclaw/workspace 2>/dev/null || true
        if [ -L /home/cuti/.openclaw/workspace ]; then
            echo "🔗 OpenClaw workspace bootstrapped to /workspace"
        fi
    fi
fi

# Setup symlink for cuti account management to access global .cuti directory
if [ -d /home/cuti/.cuti-shared ]; then
    # Fix ownership of the shared directory to ensure cuti user can access it
    sudo chown -R cuti:cuti /home/cuti/.cuti-shared 2>/dev/null || true
    
    # Create symlink from .cuti to .cuti-shared if it doesn't exist or isn't a symlink
    if [ ! -L /home/cuti/.cuti ]; then
        # Remove if it's a regular directory
        if [ -d /home/cuti/.cuti ]; then
            sudo rm -rf /home/cuti/.cuti
        fi
        ln -sf /home/cuti/.cuti-shared /home/cuti/.cuti
    fi
    echo "🔗 Global .cuti directory mounted and accessible for account management"
fi

# Ensure Clawdbot config/workspace point to the host-persistent ~/.cuti storage
if [ "${CUTI_ENABLE_CLAWDBOT_ADDON:-false}" = "true" ] && [ -d /home/cuti/.cuti ]; then
    CLAWDBOT_CONFIG_SUBPATH=${CUTI_CLAWDBOT_CONFIG_SUBPATH:-clawdbot/config}
    CLAWDBOT_WORKSPACE_SUBPATH=${CUTI_CLAWDBOT_WORKSPACE_SUBPATH:-clawdbot/workspace}
    CLAWDBOT_CONFIG_TARGET=/home/cuti/.cuti/$CLAWDBOT_CONFIG_SUBPATH
    CLAWDBOT_WORKSPACE_TARGET=/home/cuti/.cuti/$CLAWDBOT_WORKSPACE_SUBPATH

    mkdir -p "$CLAWDBOT_CONFIG_TARGET" "$CLAWDBOT_WORKSPACE_TARGET" 2>/dev/null || true
    sudo chown -R cuti:cuti "$CLAWDBOT_CONFIG_TARGET" "$CLAWDBOT_WORKSPACE_TARGET" 2>/dev/null || true

    cuti_link_clawdbot_path() {
        local LINK_PATH="$1"
        local TARGET_PATH="$2"
        if [ -e "$LINK_PATH" ] && [ ! -L "$LINK_PATH" ]; then
            if rm -rf "$LINK_PATH" 2>/dev/null; then
                :
            else
                sudo rm -rf "$LINK_PATH" 2>/dev/null || true
            fi
        fi

        ln -sfn "$TARGET_PATH" "$LINK_PATH" 2>/dev/null || \
            sudo ln -sfn "$TARGET_PATH" "$LINK_PATH" 2>/dev/null || true

        if [ ! -L "$LINK_PATH" ]; then
            echo "⚠️  Failed to link $LINK_PATH -> $TARGET_PATH (check permissions)"
            return 1
        fi
    }

    cuti_link_clawdbot_path "/home/cuti/.clawdbot" "$CLAWDBOT_CONFIG_TARGET"
    cuti_link_clawdbot_path "/home/cuti/clawd" "$CLAWDBOT_WORKSPACE_TARGET"

    echo "🔗 Clawdbot config linked to ~/.cuti/$CLAWDBOT_CONFIG_SUBPATH"
    echo "🔗 Clawdbot workspace linked to ~/.cuti/$CLAWDBOT_WORKSPACE_SUBPATH"
fi

# Ensure the cuti CLI is available inside the container via `uv tool install`
ensure_cuti_cli() {
    if command -v cuti >/dev/null 2>&1; then
        if python3 - <<'PY' >/dev/null 2>&1
import importlib
import sys

try:
    importlib.import_module("cuti")
except Exception:
    sys.exit(1)
PY
        then
            return
        fi
        echo "⚠️  cuti executable found but module import failed - reinstalling via uv tool"
    else
        echo "⚙️  cuti CLI missing inside container - installing via uv tool"
    fi

    UV_BIN=${UV_BIN:-/home/cuti/.local/bin/uv}
    if [ ! -x "$UV_BIN" ]; then
        echo "❌ uv tool not found at $UV_BIN"
        return
    fi

    if [ -d /workspace/src/cuti ] && [ -f /workspace/pyproject.toml ]; then
        echo "   ↪︎ Installing editable cuti from workspace source"
        if "$UV_BIN" tool install --force --editable /workspace > /tmp/cuti-install.log 2>&1; then
            echo "✅ cuti installed from workspace via uv tool"
        else
            echo "⚠️  Failed to install cuti from workspace"
            cat /tmp/cuti-install.log
        fi
    else
        echo "   ↪︎ Installing latest cuti from PyPI"
        if "$UV_BIN" tool install --force cuti > /tmp/cuti-install.log 2>&1; then
            echo "✅ cuti installed from PyPI via uv tool"
        else
            echo "⚠️  Failed to install cuti from PyPI"
            cat /tmp/cuti-install.log
        fi
    fi

    hash -r 2>/dev/null || true
}

ensure_cuti_cli

# Keep runtime-installed CLIs ahead of system paths in the login shell.
export PATH="/home/cuti/.opencode/bin:/home/cuti/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
hash -r 2>/dev/null || true

# Copy settings from macOS config if available (read-only mount)
if cuti_provider_selected claude && [ -d /home/cuti/.claude-macos ] && [ ! -f /home/cuti/.claude-linux/CLAUDE.md ]; then
    if [ -f /home/cuti/.claude-macos/CLAUDE.md ]; then
        cp /home/cuti/.claude-macos/CLAUDE.md /home/cuti/.claude-linux/CLAUDE.md 2>/dev/null || true
        echo "📄 Copied CLAUDE.md from macOS config"
    fi
fi

# Handle workspace directories based on writability
if [ "$WORKSPACE_WRITABLE" = "true" ]; then
    # Create workspace directories if they don't exist
    mkdir -p /workspace/.cuti 2>/dev/null || true
    if cuti_provider_selected claude; then
        mkdir -p /workspace/.claude-linux 2>/dev/null || true
        sudo chown -R cuti:cuti /workspace/.claude-linux 2>/dev/null || true
    fi
    
    # Ensure proper ownership for workspace directories
    sudo chown -R cuti:cuti /workspace/.cuti 2>/dev/null || true
    
    echo "📁 Using workspace-scoped cuti state"
fi

# Check authentication status
if cuti_provider_selected claude; then
    if [ -f /home/cuti/.claude-linux/.credentials.json ]; then
        echo "🔑 Found Linux Claude credentials - authentication ready!"
    else
        echo "⚠️  No Claude credentials found. Authenticate once with: claude login"
        echo "   Your credentials will persist across all containers."
        echo "   Note: Linux credentials are separate from macOS keychain."
    fi

    if [ -x /home/cuti/.local/bin/claude ]; then
        echo "✅ Claude CLI is available at: $(which claude)"
        if claude --version > /dev/null 2>&1; then
            echo "✅ Claude CLI verified: $(claude --version 2>&1 | head -n1)"
        else
            echo "⚠️  Claude CLI found but cannot execute --version"
            echo "   Queue inspection and provider validation may be incomplete until this is fixed"
        fi
    else
        echo "❌ Claude CLI not found in PATH!"
        echo "   Expected at /usr/local/bin/claude"
        echo "   This will prevent queue execution and limit ops console visibility"
    fi
fi

# Ensure PYTHONPATH includes workspace source for local development
export PYTHONPATH="/workspace/src:$PYTHONPATH"
echo "🐍 Python path: $PYTHONPATH"

# Setup Docker access in container
if [ -S /var/run/docker.sock ]; then
    echo "🐳 Docker socket mounted - setting up access..."
    
    # Ensure Docker socket permissions are accessible
    sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
    
    # Test if we can access Docker directly
    if docker version > /dev/null 2>&1; then
        echo "✅ Docker access confirmed - direct access enabled"
    else
        # Fallback: Create wrappers that use sudo
        cat > /home/cuti/.local/bin/docker << 'DOCKER_EOF'
#!/bin/bash
# Docker wrapper to handle permission issues
if [ -S /var/run/docker.sock ]; then
    sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
fi
exec sudo /usr/bin/docker "$@"
DOCKER_EOF
        chmod +x /home/cuti/.local/bin/docker
        
        # Also create docker-compose wrapper with proper permissions
        cat > /home/cuti/.local/bin/docker-compose << 'COMPOSE_EOF'
#!/bin/bash
# Docker-compose wrapper for compatibility
if [ -S /var/run/docker.sock ]; then
    sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
fi
# Try docker compose v2 first, fallback to docker-compose
if command -v docker >/dev/null 2>&1; then
    exec sudo docker compose "$@"
else
    exec sudo /usr/bin/docker-compose "$@"
fi
COMPOSE_EOF
        chmod +x /home/cuti/.local/bin/docker-compose
        
        # Ensure our local bin is first in PATH
        export PATH="/home/cuti/.local/bin:$PATH"
        
        if sudo docker version > /dev/null 2>&1; then
            echo "✅ Docker configured with sudo wrapper"
            echo "📝 Note: Docker commands will use sudo automatically"
        else
            echo "⚠️  Docker socket mounted but not accessible even with sudo"
        fi
    fi
    
    # Verify docker-compose is working
    if docker-compose version > /dev/null 2>&1 || docker compose version > /dev/null 2>&1; then
        echo "✅ docker-compose command available"
    else
        echo "⚠️  docker-compose not working properly"
    fi
else
    echo "⚠️  Docker socket not found - Docker commands won't work in container"
fi
"""

        if runtime_profile == self.RUNTIME_PROFILE_CLAWDBOT_SANDBOX:
            init_script = """
# Set up signal handlers to ensure clean exit
trap 'echo "Container exiting cleanly..."; exit 0' SIGTERM SIGINT

if [ ! -d /home/cuti/.clawdbot ]; then
    echo "❌ Clawdbot config mount missing at /home/cuti/.clawdbot"
    exit 1
fi

if [ ! -d /home/cuti/clawd ]; then
    echo "❌ Clawdbot workspace mount missing at /home/cuti/clawd"
    exit 1
fi

if ! command -v clawdbot >/dev/null 2>&1; then
    echo "🦞 Installing legacy Clawdbot CLI for sandbox mode..."
    if sudo npm-original install -g clawdbot@latest >/tmp/clawdbot-install.log 2>&1; then
        echo "✅ Clawdbot CLI installed"
        hash -r 2>/dev/null || true
    else
        echo "❌ Failed to install Clawdbot CLI"
        cat /tmp/clawdbot-install.log
        exit 1
    fi
fi

echo "🔒 Running clawdbot sandbox profile"
echo "📁 Workspace: /workspace"
echo "🗂️  Clawdbot config: /home/cuti/.clawdbot"
echo "🦞 Clawdbot CLI: $(command -v clawdbot)"
"""
        
        # Add interactive flags when needed
        zsh_bin = "/usr/bin/zsh"
        needs_tty = not command or interactive
        if not command:
            docker_args.insert(2, "-it")
            full_command = f"{init_script}\nexec {zsh_bin} -l"
            docker_args.extend([zsh_bin, "-c", full_command])
        else:
            if needs_tty:
                docker_args.insert(2, "-it")
            full_command = f"{init_script}\n{command}"
            docker_args.extend([zsh_bin, "-lc", full_command])

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
            linux_claude_dir = Path.home() / ".cuti" / "claude-linux"
            if linux_claude_dir.exists():
                shutil.rmtree(linux_claude_dir)
                print(f"✅ Removed Linux Claude config at {linux_claude_dir}")
                print("   Note: You'll need to authenticate again in future containers")
        else:
            print("💡 Tip: Linux Claude credentials preserved. Use --clean-credentials to remove them.")
        
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
