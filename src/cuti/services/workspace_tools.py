"""
Workspace-specific tools management service.
Enables per-workspace tool configuration with hot-swappable capabilities.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class WorkspaceToolsManager:
    """Manages tools configuration per workspace with hot-reload capabilities."""
    
    def __init__(self, workspace_path: Optional[str] = None):
        """Initialize workspace tools manager."""
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.workspace_config_dir = self.workspace_path / ".cuti"
        self.workspace_tools_config = self.workspace_config_dir / "tools.json"
        self.workspace_tools_bin = self.workspace_config_dir / "tools" / "bin"
        self.workspace_tools_lib = self.workspace_config_dir / "tools" / "lib"
        
        # Global tools location (shared across workspaces in same container)
        self.container_tools_dir = Path.home() / ".cuti" / "container-tools"
        self.container_tools_bin = self.container_tools_dir / "bin"
        
        # System-wide tools (installed in container image)
        self.system_tools_dir = Path("/usr/local/bin")
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        self.workspace_config_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_tools_bin.mkdir(parents=True, exist_ok=True)
        self.workspace_tools_lib.mkdir(parents=True, exist_ok=True)
        self.container_tools_bin.mkdir(parents=True, exist_ok=True)
    
    def get_workspace_config(self) -> Dict[str, Any]:
        """Get workspace-specific tool configuration."""
        if self.workspace_tools_config.exists():
            try:
                with open(self.workspace_tools_config, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default configuration
        return {
            "workspace": str(self.workspace_path),
            "enabled_tools": [],
            "workspace_tools": {},  # Tools installed in this workspace
            "inherit_container": True,  # Whether to inherit container-wide tools
            "inherit_system": True,  # Whether to inherit system tools
            "tool_paths": [],  # Additional tool paths
            "environment": {},  # Environment variables for tools
            "last_updated": datetime.now().isoformat()
        }
    
    def save_workspace_config(self, config: Dict[str, Any]):
        """Save workspace-specific configuration."""
        config["last_updated"] = datetime.now().isoformat()
        with open(self.workspace_tools_config, 'w') as f:
            json.dump(config, f, indent=2)
    
    def install_tool_for_workspace(self, tool_name: str, tool_config: Dict[str, Any], 
                                   scope: str = "workspace") -> Dict[str, Any]:
        """
        Install a tool with specified scope.
        
        Scopes:
        - workspace: Install only for this workspace
        - container: Install for all workspaces in this container
        - image: Would require rebuilding the image (not supported at runtime)
        """
        result = {"success": False, "message": "", "scope": scope}
        
        if scope == "workspace":
            install_dir = self.workspace_tools_bin
            lib_dir = self.workspace_tools_lib
        elif scope == "container":
            install_dir = self.container_tools_bin
            lib_dir = self.container_tools_dir / "lib"
            lib_dir.mkdir(parents=True, exist_ok=True)
        else:
            result["message"] = f"Unsupported scope: {scope}"
            return result
        
        # Modify install command to use local directories
        install_cmd = tool_config.get("install_command", "")
        
        # Handle different package managers
        if "npm install -g" in install_cmd:
            # Install npm packages locally
            package_name = install_cmd.split("@")[-1] if "@" in install_cmd else tool_name
            local_install_cmd = f"cd {install_dir.parent} && npm install {package_name} --prefix ."
            install_cmd = local_install_cmd
        elif "pip install" in install_cmd:
            # Install Python packages to local directory
            package_name = tool_name
            if "playwright" in install_cmd:
                package_name = "playwright"
            local_install_cmd = f"pip install --target={lib_dir} {package_name}"
            install_cmd = local_install_cmd
        elif "apt-get install" in install_cmd:
            # APT packages need container or system-wide installation
            if scope == "workspace":
                result["message"] = "APT packages cannot be installed at workspace scope. Use container or rebuild image."
                return result
        
        try:
            # Run installation
            env = os.environ.copy()
            env["PATH"] = f"{install_dir}:{env.get('PATH', '')}"
            env["PYTHONPATH"] = f"{lib_dir}:{env.get('PYTHONPATH', '')}"
            
            result_proc = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            if result_proc.returncode == 0:
                # Create wrapper script if needed
                self._create_tool_wrapper(tool_name, tool_config, install_dir, lib_dir)
                
                # Update workspace configuration
                config = self.get_workspace_config()
                if scope == "workspace":
                    config["workspace_tools"][tool_name] = {
                        "installed": True,
                        "install_dir": str(install_dir),
                        "lib_dir": str(lib_dir),
                        "timestamp": datetime.now().isoformat()
                    }
                config["enabled_tools"].append(tool_name)
                self.save_workspace_config(config)
                
                result["success"] = True
                result["message"] = f"Tool {tool_name} installed successfully in {scope}"
            else:
                result["message"] = f"Installation failed: {result_proc.stderr}"
        
        except subprocess.TimeoutExpired:
            result["message"] = "Installation timed out"
        except Exception as e:
            result["message"] = str(e)
        
        return result
    
    def _create_tool_wrapper(self, tool_name: str, tool_config: Dict[str, Any], 
                            bin_dir: Path, lib_dir: Path):
        """Create a wrapper script for the tool to set proper paths."""
        wrapper_path = bin_dir / tool_name
        
        # Determine the actual binary location
        if "npm" in tool_config.get("install_command", ""):
            actual_bin = bin_dir.parent / "node_modules" / ".bin" / tool_name
        elif "pip" in tool_config.get("install_command", ""):
            actual_bin = lib_dir / "bin" / tool_name
            if not actual_bin.exists():
                # For Python modules that don't create bin scripts
                wrapper_content = f"""#!/bin/bash
export PYTHONPATH="{lib_dir}:$PYTHONPATH"
python -m {tool_name} "$@"
"""
                wrapper_path.write_text(wrapper_content)
                wrapper_path.chmod(0o755)
                return
        else:
            actual_bin = bin_dir / tool_name
        
        if actual_bin.exists():
            # Create symlink or wrapper
            wrapper_content = f"""#!/bin/bash
export PATH="{bin_dir}:$PATH"
export PYTHONPATH="{lib_dir}:$PYTHONPATH"
exec "{actual_bin}" "$@"
"""
            wrapper_path.write_text(wrapper_content)
            wrapper_path.chmod(0o755)
    
    def get_tool_paths(self) -> List[str]:
        """Get all tool paths for this workspace (for PATH environment variable)."""
        paths = []
        config = self.get_workspace_config()
        
        # Workspace-specific tools
        if self.workspace_tools_bin.exists():
            paths.append(str(self.workspace_tools_bin))
        
        # Container-wide tools
        if config.get("inherit_container", True) and self.container_tools_bin.exists():
            paths.append(str(self.container_tools_bin))
        
        # Additional configured paths
        paths.extend(config.get("tool_paths", []))
        
        return paths
    
    def get_environment(self) -> Dict[str, str]:
        """Get environment variables for tools in this workspace."""
        env = {}
        config = self.get_workspace_config()
        
        # Set up PATH
        tool_paths = self.get_tool_paths()
        if tool_paths:
            current_path = os.environ.get("PATH", "")
            env["PATH"] = ":".join(tool_paths + [current_path])
        
        # Set up PYTHONPATH for workspace Python tools
        if self.workspace_tools_lib.exists():
            current_pythonpath = os.environ.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{self.workspace_tools_lib}:{current_pythonpath}"
        
        # Add custom environment variables
        env.update(config.get("environment", {}))
        
        return env
    
    def activate_workspace_tools(self):
        """Activate tools for current workspace (updates environment)."""
        env = self.get_environment()
        for key, value in env.items():
            os.environ[key] = value
        
        # Create activation script for shell
        activation_script = self.workspace_config_dir / "activate_tools.sh"
        script_content = "#!/bin/bash\n"
        script_content += "# Workspace tools activation script\n"
        script_content += f"# Generated for: {self.workspace_path}\n\n"
        
        for key, value in env.items():
            script_content += f'export {key}="{value}"\n'
        
        script_content += '\necho "Workspace tools activated for: ' + str(self.workspace_path) + '"\n'
        
        activation_script.write_text(script_content)
        activation_script.chmod(0o755)
        
        return str(activation_script)
    
    def list_workspace_tools(self) -> Dict[str, Any]:
        """List all tools available in this workspace."""
        config = self.get_workspace_config()
        tools = {
            "workspace": str(self.workspace_path),
            "workspace_tools": config.get("workspace_tools", {}),
            "enabled_tools": config.get("enabled_tools", []),
            "tool_paths": self.get_tool_paths(),
            "inherit_container": config.get("inherit_container", True),
            "inherit_system": config.get("inherit_system", True)
        }
        
        # Check actual availability
        for tool_name in config.get("enabled_tools", []):
            tool_path = self.workspace_tools_bin / tool_name
            if tool_path.exists():
                tools["workspace_tools"][tool_name] = tools.get("workspace_tools", {}).get(tool_name, {})
                tools["workspace_tools"][tool_name]["available"] = True
                tools["workspace_tools"][tool_name]["path"] = str(tool_path)
        
        return tools
    
    def sync_with_container(self):
        """Sync workspace tools with container-wide tools."""
        # This would handle syncing tools between workspace and container scope
        pass
    
    def export_tools_config(self) -> Dict[str, Any]:
        """Export tools configuration for backup or sharing."""
        config = self.get_workspace_config()
        config["export_timestamp"] = datetime.now().isoformat()
        config["workspace_path"] = str(self.workspace_path)
        return config
    
    def import_tools_config(self, config: Dict[str, Any]):
        """Import tools configuration from another workspace."""
        # Validate and adapt the configuration for current workspace
        imported_config = self.get_workspace_config()
        imported_config["enabled_tools"] = config.get("enabled_tools", [])
        imported_config["tool_paths"] = config.get("tool_paths", [])
        imported_config["environment"] = config.get("environment", {})
        imported_config["imported_from"] = config.get("workspace_path", "unknown")
        imported_config["imported_at"] = datetime.now().isoformat()
        
        self.save_workspace_config(imported_config)


def setup_workspace_tools_on_container_start():
    """Set up workspace tools when container starts."""
    workspace_path = os.environ.get("WORKSPACE_PATH", "/workspace")
    manager = WorkspaceToolsManager(workspace_path)
    
    # Activate workspace tools
    activation_script = manager.activate_workspace_tools()
    
    # Setup auto-activation for all shells
    setup_shell_auto_activation()
    
    return manager


def setup_shell_auto_activation():
    """Setup automatic workspace tools activation in shell."""
    auto_activate_content = '''
# Cuti workspace tools auto-activation
cuti_auto_activate_tools() {
    if [ -f "$PWD/.cuti/tools.json" ]; then
        if [ "$CUTI_WORKSPACE_TOOLS_ACTIVE" != "$PWD" ]; then
            eval $(cuti tools activate 2>/dev/null)
            if [ $? -eq 0 ]; then
                export CUTI_WORKSPACE_TOOLS_ACTIVE="$PWD"
                echo "✅ Workspace tools activated: $(basename $PWD)"
            fi
        fi
    fi
}

# Activate on directory change
cuti_cd() {
    builtin cd "$@"
    local result=$?
    [ $result -eq 0 ] && cuti_auto_activate_tools
    return $result
}
alias cd='cuti_cd'

# Activate for current directory
cuti_auto_activate_tools
'''
    
    # Add to shell initialization files
    for shell_rc in [Path.home() / ".bashrc", Path.home() / ".zshrc"]:
        if shell_rc.exists():
            content = shell_rc.read_text()
            if "cuti_auto_activate_tools" not in content:
                shell_rc.write_text(content + "\n" + auto_activate_content)