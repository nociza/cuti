# Automatic Tools Activation

## Overview

Workspace tools are now **automatically activated** when:
1. Installing a tool with `--scope workspace`
2. Entering a workspace directory (after setup)
3. Starting a new shell in a workspace

## Commands

### Setup Automatic Activation (One-time)

```bash
# Setup auto-activation for all shells
cuti tools activate --setup
```

This adds hooks to `.bashrc` and `.zshrc` to automatically activate workspace tools.

### Manual Activation

```bash
# Activate workspace tools in current shell
eval $(cuti tools activate)

# Or source the activation script directly
source /workspace/.cuti/activate_tools.sh
```

### Install with Auto-Activation

```bash
# Install tool for workspace - automatically activated!
cuti tools install playwright --scope workspace

# The tool is immediately available in current session
playwright --version
```

## How It Works

### 1. **Installation Auto-Activation**
When you install a tool with `--scope workspace`:
- Tool is installed to `/workspace/.cuti/tools/`
- Environment is updated for current session
- Tool is immediately usable

### 2. **Directory Change Auto-Activation**
After running `cuti tools activate --setup`:
- Shell monitors directory changes
- When entering a workspace with `.cuti/tools.json`
- Tools are automatically activated
- Shows: "✅ Workspace tools activated: <workspace-name>"

### 3. **Shell Startup Auto-Activation**
When starting a new shell:
- Checks if current directory has workspace tools
- Automatically activates them
- No manual intervention needed

## Implementation Details

### Shell Integration
The auto-activation works by:
1. **Overriding `cd` command** - Checks for workspace tools after directory change
2. **PROMPT_COMMAND hook** - Additional safety check on each prompt
3. **Shell initialization** - Activates tools when shell starts

### Activation Script Location
- Per-workspace: `/workspace/.cuti/activate_tools.sh`
- Global auto-activate: `~/.cuti/auto_activate.sh`

### Environment Variables
- `CUTI_WORKSPACE_TOOLS_ACTIVE` - Tracks current active workspace
- `PATH` - Updated to include workspace tool directories
- `PYTHONPATH` - Updated for Python tools

## Usage Examples

### First-Time Setup

```bash
# 1. Setup auto-activation (once per container)
cuti tools activate --setup

# 2. Install workspace tools
cuti tools install playwright --scope workspace
cuti tools install cypress --scope workspace

# 3. Tools are immediately available!
playwright --version
cypress --version
```

### Switching Between Workspaces

```bash
# In workspace A with playwright
cd /workspace-a
# Automatic: "✅ Workspace tools activated: workspace-a"
playwright --version  # Works!

# Switch to workspace B without playwright
cd /workspace-b
# Automatic: "✅ Workspace tools activated: workspace-b"
playwright --version  # Not found (unless installed here too)
```

### New Shell Sessions

```bash
# Open new terminal in workspace with tools
# Tools are automatically activated on shell start
# No need to run any activation commands!
```

## Benefits

1. **Zero Manual Activation** - Tools just work when you need them
2. **Workspace Isolation** - Each workspace has its own tools
3. **Hot-Swapping** - Seamlessly switch between workspaces
4. **Persistent** - Tools survive container restarts
5. **Immediate Availability** - No restart needed after install

## Troubleshooting

### Tools Not Activating?

1. Check setup was completed:
   ```bash
   grep cuti_auto_activate ~/.zshrc
   ```

2. Manually activate once:
   ```bash
   eval $(cuti tools activate)
   ```

3. Verify workspace has tools:
   ```bash
   cuti tools workspace
   ```

### Path Issues?

Check current tool paths:
```bash
echo $PATH | tr ':' '\n' | grep cuti
```

### Reset Activation

Re-run setup:
```bash
cuti tools activate --setup
source ~/.zshrc  # or restart shell
```

## Technical Notes

- Tools installed with `--scope workspace` are stored in `/workspace/.cuti/tools/`
- This directory is part of the mounted workspace volume
- Tools persist across container destruction/recreation
- Multiple containers can share the same workspace tools
- Activation modifies PATH and PYTHONPATH dynamically