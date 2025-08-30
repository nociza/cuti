# Claude Container Authentication Guide

## Overview

This guide explains how Claude authentication works in cuti containers and how to set it up for persistent credentials across container sessions.

## The Problem

Claude Code stores credentials differently on macOS vs Linux:
- **macOS**: Uses Keychain (not accessible to containers)
- **Linux**: Uses `~/.claude/.credentials.json` file
- **Conflict**: macOS Claude deletes Linux credential files when switching between host and container

## The Solution

Cuti uses separate credential storage for Linux containers:
- **Linux credentials**: `~/.cuti/claude-linux/`
- **macOS config**: Mounted read-only for settings reference
- **No conflicts**: Both systems work independently

## Setup Instructions

### First-Time Setup

1. **Start the container**:
   ```bash
   cuti container
   ```

2. **Authenticate once inside the container**:
   ```bash
   # Inside container
   claude login
   # Follow the browser authentication flow
   ```

3. **Verify authentication**:
   ```bash
   # Test Claude
   claude "What is 2+2?"
   # Output: 4
   ```

### Subsequent Uses

Authentication persists automatically:
```bash
# Start container - already authenticated!
cuti container

# Claude works immediately
claude "Hello, how can I help?"
```

## How It Works

### Directory Structure

```
Host (macOS):
~/.cuti/claude-linux/           # Linux container credentials
├── .credentials.json           # Linux auth tokens (persistent)
├── .claude.json               # Configuration
├── CLAUDE.md                  # Copied from macOS
├── settings.json              # Copied from macOS
└── plugins/                   # Plugin configs

~/.claude/                     # macOS credentials (unchanged)
├── [Keychain storage]         # macOS auth (not files)
├── CLAUDE.md                  # Your settings
└── settings.json              # Your preferences
```

### Container Mounts

| Host Path | Container Path | Purpose | Mode |
|-----------|---------------|---------|------|
| `~/.cuti/claude-linux/` | `/home/cuti/.claude-linux` | Linux credentials | Read-Write |
| `~/.claude/` | `/home/cuti/.claude-macos` | macOS settings | Read-Only |

### Environment Variables

- `CLAUDE_CONFIG_DIR=/home/cuti/.claude-linux` - Linux config location
- `IS_SANDBOX=1` - Enables container mode
- `CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=true` - Allows container user

## Benefits

✅ **No conflicts**: macOS and Linux credentials never interfere  
✅ **Persistent**: Survives container rebuilds  
✅ **Multi-workspace**: Works across all projects  
✅ **One-time setup**: Authenticate once, use forever  
✅ **Settings sync**: Inherits CLAUDE.md and settings from macOS  

## Troubleshooting

### "No credentials found" on first run
This is normal. Run `claude login` once inside the container to authenticate.

### Credentials not persisting
Check that the credentials file exists:
```bash
ls -la ~/.cuti/claude-linux/.credentials.json
```

### Reset credentials
To start fresh:
```bash
cuti devcontainer clean --clean-credentials
```

### Copy settings from macOS
Settings are automatically copied on first run. To manually update:
```bash
cp ~/.claude/CLAUDE.md ~/.cuti/claude-linux/
cp ~/.claude/settings.json ~/.cuti/claude-linux/
```

## Technical Details

### Why Separate Directories?

1. **macOS Keychain**: Credentials stored in Keychain aren't accessible to containers
2. **File conflicts**: macOS Claude deletes `.credentials.json` files it doesn't need
3. **Clean separation**: Each OS uses its native authentication method

### Implementation

The container:
1. Sets `CLAUDE_CONFIG_DIR` to the Linux-specific directory
2. Mounts macOS config as read-only for reference
3. Copies non-credential files on first run
4. Preserves Linux credentials between sessions

### Security Notes

- Credentials are stored in `~/.cuti/claude-linux/` with user-only permissions
- macOS config is mounted read-only to prevent modification
- Each container workspace has isolated credentials

## Related Documentation

- [Dev Container Documentation](devcontainer.md) - Complete container setup guide
- [Container Management](container.md) - Basic container commands
- [Main README](../README.md) - Project overview