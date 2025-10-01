# Workspace-Specific Tools Architecture

## Current Problem

When tools like Playwright are installed via `cuti tools install`, they are installed:
- **In the container's filesystem** at `/usr/local/bin/`
- **Per-container basis** - not shared across containers
- **Not workspace-specific** - all workspaces in the same container share the same tools

This means:
1. **Tools are NOT shared across containers** even if they mount the same workspace
2. **Tools cannot be different per workspace** within the same container
3. **No hot-swapping** - requires container restart or manual PATH manipulation

## Solution: Three-Tier Tool Management

### 1. **System Tools** (Container Image Level)
- Location: `/usr/local/bin/`, `/usr/bin/`
- Scope: All workspaces in this container
- Installation: During container build or system package managers
- Persistence: Lost when container is destroyed
- Use case: Base tools that every workspace needs

### 2. **Container Tools** (Container-Wide)
- Location: `~/.cuti/container-tools/bin/`
- Scope: All workspaces in this container instance
- Installation: `cuti tools install --scope container`
- Persistence: Lost when container is destroyed
- Use case: Tools shared across all your workspaces in this session

### 3. **Workspace Tools** (Workspace-Specific)
- Location: `/workspace/.cuti/tools/bin/`
- Scope: Only this specific workspace
- Installation: `cuti tools install --scope workspace`
- Persistence: **Persisted in workspace** - survives container restarts!
- Use case: Project-specific tools and versions

## Implementation Details

### Workspace Tools Manager
Located in `/workspace/src/cuti/services/workspace_tools.py`

Key features:
- **Per-workspace configuration** in `/workspace/.cuti/tools.json`
- **Local installation** of npm/pip packages to workspace directory
- **PATH management** with precedence order
- **Hot-swappable** via activation scripts
- **Inheritance control** - can disable system or container tools

### Installation Scopes

```bash
# Install for this workspace only (persisted)
cuti tools install playwright --scope workspace

# Install for all workspaces in this container (temporary)
cuti tools install ripgrep --scope container

# Install system-wide (requires sudo, temporary)
cuti tools install tree --scope system
```

### Tool Precedence
When looking for a tool, the search order is:
1. Workspace tools (`/workspace/.cuti/tools/bin`)
2. Container tools (`~/.cuti/container-tools/bin`)
3. System tools (`/usr/local/bin`, `/usr/bin`)

### Configuration File
Each workspace has `/workspace/.cuti/tools.json`:

```json
{
  "workspace": "/workspace",
  "enabled_tools": ["playwright", "cypress"],
  "workspace_tools": {
    "playwright": {
      "installed": true,
      "install_dir": "/workspace/.cuti/tools/bin",
      "lib_dir": "/workspace/.cuti/tools/lib"
    }
  },
  "inherit_container": true,
  "inherit_system": true,
  "tool_paths": [],
  "environment": {}
}
```

## Benefits

### 1. **Persistence Across Containers**
- Workspace tools are stored in `/workspace/.cuti/tools/`
- This directory is part of the mounted workspace
- Tools survive container destruction and recreation
- Different containers mounting the same workspace share tools

### 2. **Workspace Isolation**
- Each workspace can have different tool versions
- No conflicts between project requirements
- Tools don't pollute other workspaces

### 3. **Hot-Swapping**
- Activate workspace tools: `source /workspace/.cuti/activate_tools.sh`
- Switch between workspaces without container restart
- Dynamic PATH updates per workspace

### 4. **Efficient Storage**
- Tools installed once per workspace, not per container
- Shared across all containers mounting that workspace
- Reduces redundant installations

## Usage Examples

### Setting Up a Testing Workspace

```bash
# Install testing tools for this workspace only
cuti tools install playwright --scope workspace
cuti tools install cypress --scope workspace
cuti tools install k6 --scope workspace

# Check workspace tools
cuti tools workspace

# Activate workspace tools
cuti tools workspace --activate
source /workspace/.cuti/activate_tools.sh
```

### Container-Wide Development Tools

```bash
# Install for all workspaces in this container
cuti tools install ripgrep --scope container
cuti tools install fd --scope container
cuti tools install bat --scope container
```

### Switching Between Workspaces

```bash
# In workspace A
cd /workspace-a
source /workspace-a/.cuti/activate_tools.sh
playwright --version  # Shows workspace A's version

# Switch to workspace B
cd /workspace-b
source /workspace-b/.cuti/activate_tools.sh
playwright --version  # Shows workspace B's version (or not found)
```

## Current Limitations

1. **APT packages** cannot be installed at workspace scope (require system-wide installation)
2. **Binary tools** that require specific system libraries may not work in workspace scope
3. **PATH activation** requires manual sourcing of activation script

## Future Enhancements

1. **Automatic activation** when entering a workspace directory
2. **Tool version management** - specify exact versions per workspace
3. **Tool sharing** - share tool configurations between workspaces
4. **Cloud sync** - backup and restore tool configurations
5. **Container image optimization** - pre-install common workspace tools in image