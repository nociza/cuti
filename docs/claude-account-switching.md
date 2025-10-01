# Claude Account Switching

## Overview

The Claude account switching feature allows you to manage multiple Claude Code accounts within cuti containers. This is useful when you need to:

- Switch between different Claude subscription tiers (Pro, Max 5, Max 20)
- Use separate accounts for different projects
- Test with different Claude accounts
- Maintain work and personal accounts separately

## Quick Start

### Creating Your First Account

1. **Start the container**:
   ```bash
   cuti container
   ```

2. **Authenticate with Claude** (inside container):
   ```bash
   claude login
   # Follow the browser authentication flow
   ```

3. **Save the account** (can be run inside or outside container):
   ```bash
   cuti claude save -n "My Work Account"
   ```

### Switching Between Accounts

```bash
# List all accounts
cuti claude list

# Switch to a different account
cuti claude use "My Work Account"

# Start container with the active account
cuti container
```

## Commands

### `cuti claude list`

List all saved Claude accounts with their details.

```bash
cuti claude list

# Show detailed information
cuti claude list --verbose
```

**Output includes:**
- Account name
- Subscription type (Pro, Max 5, Max 20)
- Creation date
- Last used date
- Active status

### `cuti claude use <account>`

Switch to a different Claude account.

```bash
cuti claude use "Personal Account"
```

The credentials from the specified account will be loaded and become active in your next container session.

### `cuti claude save -n <name>`

Save current credentials as a named account.

```bash
# Save with a new name
cuti claude save -n "Project X Account"

# Overwrite an existing account
cuti claude save -n "My Account" --force
```

**Requirements:**
- You must have authenticated with `claude login` first
- The credentials file must exist in `~/.cuti/claude-linux/`

### `cuti claude new`

Prepare to create a new Claude account.

```bash
cuti claude new
```

This command:
1. Backs up your current credentials automatically
2. Clears the active credentials
3. Prepares the environment for a fresh login

**Next steps after running `cuti claude new`:**
1. Start a container: `cuti container`
2. Inside the container: `claude login`
3. Save the new account: `cuti claude save -n "New Account"`

### `cuti claude delete <account>`

Delete a saved account.

```bash
# Delete with confirmation
cuti claude delete "Old Account"

# Delete without confirmation
cuti claude delete "Old Account" --force
```

**Note:** Deleting the active account will clear the active account status. You'll need to use another account to authenticate again.

### `cuti claude info <account>`

Show detailed information about a specific account.

```bash
cuti claude info "Work Account"
```

**Output includes:**
- Account name and type
- Creation and last used dates
- Credential status
- Subscription type
- Email (if available)
- File path

### `cuti claude current`

Show the currently active account.

```bash
cuti claude current
```

## How It Works

### Directory Structure

```
~/.cuti/
├── claude-linux/              # Active credentials (mounted in containers)
│   ├── .credentials.json      # Current active credentials
│   ├── .claude.json
│   ├── settings.json
│   └── plugins/
├── claude-accounts/           # Saved accounts
│   ├── accounts.json          # Account metadata
│   ├── Work Account/          # Saved account
│   │   ├── .credentials.json
│   │   └── ...
│   └── Personal Account/      # Another saved account
│       ├── .credentials.json
│       └── ...
```

### Container Mounting

When you start a container with `cuti container`, the directories are mounted:

- **Host:** `~/.cuti/` → **Container:** `/home/cuti/.cuti-shared` (symlinked to `~/.cuti`)
- **Host:** `~/.cuti/claude-linux/` → **Container:** `/home/cuti/.claude-linux`
- **Environment:** `CLAUDE_CONFIG_DIR=/home/cuti/.claude-linux`

This means:
- The active account is available in all containers
- Changes persist across container sessions
- Switching accounts affects all future container sessions
- Account management commands work inside containers with proper permissions

### Account Metadata

Each account stores:
- **Creation date** - When the account was first saved
- **Last used date** - When the account was last activated
- **Account type** - Subscription tier (Pro, Max 5, Max 20)
- **Credentials** - All Claude authentication tokens and config

## Workflows

### Multiple Projects Workflow

If you work on different projects with different Claude accounts:

```bash
# Switch to project-specific account
cuti claude use "Client A Account"

# Start container for that project
cd ~/projects/client-a
cuti container

# Work with Claude in the container
# ...
```

### Testing Multiple Accounts

Test features with different subscription tiers:

```bash
# Save your current account
cuti claude save -n "Main Pro Account"

# Create and test with a Max 20 account
cuti claude new
# ... login with Max 20 account in container ...
cuti claude save -n "Max 20 Test"

# Switch back to original
cuti claude use "Main Pro Account"
```

### Backup and Restore

Automatically backs up credentials when creating new accounts:

```bash
# Your current credentials are automatically backed up
cuti claude new

# The backup is named with a timestamp
cuti claude list
# Shows: backup_20251001_143022
```

## Best Practices

### 1. Name Your Accounts Clearly

Use descriptive names that indicate the account's purpose:
```bash
cuti claude save -n "Work - Max 20"
cuti claude save -n "Personal - Pro"
cuti claude save -n "Project X - Client Account"
```

### 2. Verify Active Account

Before starting important work, check which account is active:
```bash
cuti claude current
```

### 3. Regular Backups

Save your current setup before experimenting:
```bash
cuti claude save -n "Stable Config - $(date +%Y%m%d)"
```

### 4. Clean Up Old Accounts

Remove accounts you no longer use:
```bash
cuti claude delete "Old Test Account"
```

## Troubleshooting

### "No credentials found" Error

**Problem:** Trying to save an account but no credentials exist.

**Solution:**
1. Start a container: `cuti container`
2. Inside container: `claude login`
3. Then save: `cuti claude save -n "Account Name"`

### Account Switch Doesn't Work

**Problem:** Switched accounts but container still uses old credentials.

**Solution:**
- Exit any running containers
- Switch account: `cuti claude use "Other Account"`
- Start a fresh container: `cuti container`

### Lost Credentials

**Problem:** Accidentally cleared credentials.

**Solution:**
Check for automatic backups:
```bash
cuti claude list
# Look for backup_YYYYMMDD_HHMMSS entries
cuti claude use "backup_20251001_143022"
```

### Account Name Already Exists

**Problem:** Trying to save with a name that's already used.

**Solution:**
```bash
# Either delete the old account first
cuti claude delete "Account Name"

# Or use --force to overwrite
cuti claude save -n "Account Name" --force
```

## Security Notes

- Account credentials are stored in `~/.cuti/claude-accounts/` with user-only permissions
- Each account is isolated in its own directory
- The active credentials in `claude-linux/` are what containers use
- Credentials are never transmitted or shared externally
- All account operations happen locally on your machine

## Integration with Other Features

### With Container Management

```bash
# Switch account before starting container
cuti claude use "Work Account"
cuti container

# The container automatically uses the active account
```

### With Web Interface

The web interface uses the currently active account's credentials. Switch accounts before starting the web interface:

```bash
cuti claude use "My Account"
cuti web
```

### With DevContainer

DevContainers automatically mount the active account:

```bash
cuti claude use "Development Account"
cuti devcontainer start
```

## Related Documentation

- [Claude Container Authentication](claude-container-auth.md) - How Claude auth works in containers
- [Container Management](container.md) - Container commands and usage
- [DevContainer Documentation](devcontainer.md) - DevContainer setup and configuration

