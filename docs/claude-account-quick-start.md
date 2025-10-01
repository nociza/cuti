# Claude Account Switching - Quick Start

## 5-Minute Setup

### Creating Your First Account

```bash
# 1. Start the container
cuti container

# 2. Inside container - authenticate with Claude
claude login

# 3. Exit container and save the account
exit
cuti claude save -n "default"
```

Done! Your account is saved and will be available in all future containers.

### Switching Between Accounts

```bash
# List all saved accounts (hides backups by default)
cuti claude list

# Show backup accounts too
cuti claude list --backups

# Switch to a different account
cuti claude use "work"

# Verify which account is active
cuti claude current

# Start container with the active account
cuti container
```

### Adding a New Account

```bash
# 1. Prepare for new account (backs up current credentials)
cuti claude new

# 2. Start container and login with new account
cuti container
claude login

# 3. Save the new account
exit
cuti claude save -n "Client Project"
```

## Common Workflows

### Multiple Projects

```bash
# Switch account before starting work
cuti claude use "Client A"
cd ~/projects/client-a
cuti container

# Later, switch to different project
cuti claude use "Client B"
cd ~/projects/client-b
cuti container
```

### Testing Different Tiers

```bash
# Try features with different subscription levels
cuti claude use "Pro Account"
cuti container

# Switch to Max 20 for intensive tasks
cuti claude use "Max 20 Account"
cuti container
```

## Useful Commands

```bash
# Show detailed info about an account
cuti claude info "Account Name"

# Delete an old account
cuti claude delete "Old Account"

# List all accounts with details
cuti claude list --verbose
```

## Troubleshooting

**Problem:** "No credentials found" error when saving

**Solution:**
```bash
# Make sure you've logged in first
cuti container
claude login
exit
cuti claude save -n "My Account"
```

**Problem:** Container still shows old account

**Solution:**
```bash
# Exit the container first, then switch
exit
cuti claude use "Other Account"
cuti container  # Fresh container with new account
```

## Need More Help?

- Full documentation: [claude-account-switching.md](claude-account-switching.md)
- Container setup: [claude-container-auth.md](claude-container-auth.md)
- Report issues: [GitHub Issues](https://github.com/nociza/cuti/issues)

