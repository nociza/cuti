# Claude API Key Management

## Overview

The Claude account management system now supports both **OAuth credentials** (Claude Code CLI) and **API keys** from:
- **Anthropic API** - Direct API access with `sk-ant-` keys
- **AWS Bedrock** - Claude via AWS with access keys and model IDs

This allows you to manage different types of Claude access in one unified system.

## Credential Types

### 1. OAuth (Claude Code CLI)
- Default for `cuti container` workflows
- Uses browser-based authentication
- Stored in `.credentials.json`
- Type shown as: `Max`, `Pro`, etc.

### 2. Anthropic API
- Direct API access
- Requires API key from https://console.anthropic.com/
- Stored in `.api_keys.json` (600 permissions)
- Type shown as: `API (Anthropic)`

### 3. AWS Bedrock
- Claude via AWS Bedrock service
- Requires AWS access keys and region
- Supports all Bedrock Claude models
- Type shown as: `API (Bedrock)`

## Quick Start

### Adding an Anthropic API Key

```bash
# Add API key to an account
cuti claude add-api-key "my-api-account" \
  --api-key "sk-ant-api03-xxxxx" \
  --provider anthropic

# Verify it was added
cuti claude list-api-keys "my-api-account"

# View the key (masked)
cuti claude show-api-key "my-api-account" --provider anthropic
```

### Adding AWS Bedrock Credentials

```bash
# Add Bedrock credentials
cuti claude add-api-key "bedrock-prod" \
  --api-key "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --provider bedrock \
  --region us-east-1 \
  --access-key "AKIAXXXXXXXXXXXXXXXX" \
  --secret-key "your-secret-access-key"

# View the credentials (masked)
cuti claude show-api-key "bedrock-prod" --provider bedrock
```

## Commands

### `add-api-key`

Add API key credentials to an account.

**Syntax:**
```bash
cuti claude add-api-key <account> --api-key <key> [options]
```

**Options:**
- `--api-key, -k` - API key (required)
- `--provider, -p` - Provider: `anthropic` or `bedrock` (default: `anthropic`)
- `--region, -r` - AWS region (Bedrock only)
- `--access-key` - AWS access key ID (Bedrock only)
- `--secret-key` - AWS secret access key (Bedrock only)

**Examples:**

Anthropic API:
```bash
cuti claude add-api-key "prod-api" \
  --api-key "sk-ant-api03-your-key-here"
```

AWS Bedrock:
```bash
cuti claude add-api-key "bedrock-us" \
  --api-key "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --provider bedrock \
  --region us-east-1 \
  --access-key "AKIAIOSFODNN7EXAMPLE" \
  --secret-key "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

### `show-api-key`

Display API key credentials (masked by default).

**Syntax:**
```bash
cuti claude show-api-key <account> [options]
```

**Options:**
- `--provider, -p` - Provider: `anthropic` or `bedrock` (default: `anthropic`)
- `--show-secret` - Reveal full credentials (default: masked)

**Example:**
```bash
# Show masked key
cuti claude show-api-key "prod-api"

# Show full key
cuti claude show-api-key "prod-api" --show-secret
```

**Output (masked):**
```
╭────────────────────── Anthropic API Key - prod-api ──────────────────────────╮
│ Provider: anthropic                                                          │
│ Created: 2025-10-01T00:31:34.953588                                          │
│ API Key: sk-ant-a...key                                                      │
│                                                                              │
│ Use --show-secret to reveal full credentials                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `list-api-keys`

List all API key providers for an account.

**Syntax:**
```bash
cuti claude list-api-keys <account>
```

**Example:**
```bash
cuti claude list-api-keys "multi-provider"
```

**Output:**
```
API Keys for account: multi-provider

  • anthropic - Added: 2025-10-01 00:31
  • bedrock - Added: 2025-10-01 00:35
```

### `delete-api-key`

Delete an API key from an account.

**Syntax:**
```bash
cuti claude delete-api-key <account> --provider <provider> [options]
```

**Options:**
- `--provider, -p` - Provider: `anthropic` or `bedrock` (required)
- `--force, -f` - Skip confirmation

**Example:**
```bash
# Delete with confirmation
cuti claude delete-api-key "old-account" --provider anthropic

# Delete without confirmation
cuti claude delete-api-key "old-account" --provider bedrock --force
```

## Account Management

### Viewing Accounts

API key accounts appear in the main list:

```bash
$ cuti claude list
                               Claude Accounts                                
╭──────────────┬─────────────────┬────────────┬──────────────────┬───────────╮
│ Name         │ Type            │ Created    │ Last Used        │ Status    │
├──────────────┼─────────────────┼────────────┼──────────────────┼───────────┤
│ api-prod     │ API (Anthropic) │ 2025-10-01 │ never            │           │
│ bedrock-us   │ API (Bedrock)   │ 2025-10-01 │ never            │           │
│ default      │ Max             │ 2025-09-30 │ 2025-10-01 07:24 │ 🟢 Active │
╰──────────────┴─────────────────┴────────────┴──────────────────┴───────────╯
```

### Account Information

View detailed account info including API keys:

```bash
cuti claude info "api-prod"
```

## Directory Structure

API keys are stored separately from OAuth credentials:

```
~/.cuti/claude-accounts/
├── my-api-account/
│   └── .api_keys.json           # API keys (600 permissions)
├── default/
│   ├── .credentials.json        # OAuth credentials
│   ├── .claude.json
│   └── settings.json
```

### API Keys File Format

**Anthropic:**
```json
{
  "anthropic": {
    "api_key": "sk-ant-api03-your-key",
    "provider": "anthropic",
    "created": "2025-10-01T00:31:34.953588"
  }
}
```

**Bedrock:**
```json
{
  "bedrock": {
    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "region": "us-east-1",
    "access_key_id": "AKIAXXXXXXXXXXXXXXXX",
    "secret_access_key": "your-secret-key",
    "provider": "bedrock",
    "created": "2025-10-01T00:31:55.556156"
  }
}
```

## Multiple Providers Per Account

An account can have both Anthropic and Bedrock credentials:

```bash
# Add Anthropic key
cuti claude add-api-key "multi" \
  --api-key "sk-ant-api03-key1"

# Add Bedrock key to same account
cuti claude add-api-key "multi" \
  --api-key "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --provider bedrock \
  --region us-east-1 \
  --access-key "AKIATEST" \
  --secret-key "secret"

# List both
cuti claude list-api-keys "multi"
```

Output:
```
API Keys for account: multi

  • anthropic - Added: 2025-10-01 00:31
  • bedrock - Added: 2025-10-01 00:35
```

## Security

### File Permissions

API keys are stored with restricted permissions:
- **File mode:** 600 (user read/write only)
- **Location:** `~/.cuti/claude-accounts/<account>/.api_keys.json`
- **Encryption:** None (rely on OS file permissions)

### Best Practices

1. **Use separate accounts** for different environments:
   ```bash
   cuti claude add-api-key "dev-api" --api-key "sk-ant-dev-key"
   cuti claude add-api-key "prod-api" --api-key "sk-ant-prod-key"
   ```

2. **Mask keys by default** - Only use `--show-secret` when necessary

3. **Delete old keys** when rotated:
   ```bash
   cuti claude delete-api-key "old" --provider anthropic
   ```

4. **Never commit** `.api_keys.json` files to version control

## Use Cases

### Development Workflow

```bash
# Development with API keys
cuti claude add-api-key "dev" --api-key "sk-ant-dev-key"

# Production with different key
cuti claude add-api-key "prod" --api-key "sk-ant-prod-key"

# Switch between them as needed
cuti claude show-api-key "dev"
cuti claude show-api-key "prod"
```

### Multi-Region Bedrock

```bash
# US East region
cuti claude add-api-key "bedrock-us-east" \
  --api-key "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --provider bedrock \
  --region us-east-1 \
  --access-key "AKIAEAST" \
  --secret-key "secret-east"

# EU West region
cuti claude add-api-key "bedrock-eu-west" \
  --api-key "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --provider bedrock \
  --region eu-west-1 \
  --access-key "AKIAWEST" \
  --secret-key "secret-west"
```

### Team Sharing

```bash
# Each team member has their own API key
cuti claude add-api-key "alice" --api-key "sk-ant-alice-key"
cuti claude add-api-key "bob" --api-key "sk-ant-bob-key"

# View whose key is being used
cuti claude list
cuti claude show-api-key "alice"
```

## Troubleshooting

### API Key Not Found

```bash
$ cuti claude show-api-key "test" --provider anthropic
⚠  No anthropic API key found for account: test

Add one with: cuti claude add-api-key test --api-key YOUR_KEY --provider anthropic
```

**Solution:** Add the API key first

### Missing Bedrock Parameters

```bash
$ cuti claude add-api-key "test" --api-key "model-id" --provider bedrock
✗ Bedrock requires --region, --access-key, and --secret-key
```

**Solution:** Provide all required Bedrock parameters

### Permission Denied

If you can't read `.api_keys.json`:

```bash
# Fix permissions
chmod 600 ~/.cuti/claude-accounts/<account>/.api_keys.json
```

## API Key Sources

### Getting an Anthropic API Key

1. Visit https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to API Keys section
4. Create a new key
5. Copy the `sk-ant-` key

### Getting AWS Bedrock Access

1. Sign in to AWS Console
2. Enable Bedrock service in your region
3. Request model access for Claude models
4. Create IAM user with Bedrock permissions
5. Generate access key and secret key
6. Note your preferred region (e.g., `us-east-1`)

## Related Documentation

- [Claude Account Switching](claude-account-switching.md) - Main account management guide
- [Quick Start](claude-account-quick-start.md) - Getting started guide
- [Container Authentication](claude-container-auth.md) - OAuth container setup

---

**Note:** API key support is in addition to OAuth-based Claude Code authentication. You can use both types in the same cuti installation.

