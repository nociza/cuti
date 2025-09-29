# CLI Tools Management

## Overview

The `cuti tools` command provides a comprehensive CLI interface for managing development tools within cuti containers. This allows you to easily install, enable, and manage various CLI tools to enhance your development environment.

## Available Commands

### List Tools
View all available tools and their current status:

```bash
# List all tools
cuti tools list

# Filter by category
cuti tools list --category Testing
cuti tools list --category "Code Analysis"

# Show only installed tools
cuti tools list --installed

# Show only enabled tools
cuti tools list --enabled
```

### Install Tools
Install a new CLI tool in your container:

```bash
# Basic installation
cuti tools install playwright

# Install and enable
cuti tools install tree --enable

# Install with auto-install on container start
cuti tools install ripgrep --auto

# Install without enabling
cuti tools install httpie --no-enable
```

### Enable/Disable Tools
Manage which tools are marked as available:

```bash
# Enable a tool
cuti tools enable playwright

# Enable with auto-install
cuti tools enable tree --auto

# Disable a tool
cuti tools disable httpie
```

### Get Tool Information
View detailed information about a specific tool:

```bash
cuti tools info playwright
cuti tools info "GitHub CLI"
```

### Check Tool Status
Check which tools are installed and their versions:

```bash
cuti tools check
```

## Available Tools

The system includes a curated list of development tools across various categories:

### Testing Tools
- **Playwright** - Browser automation and testing framework
- **Cypress** - JavaScript end-to-end testing framework  
- **k6** - Modern load testing tool

### Code Analysis
- **AST Grep** - Structural search and replace tool for code
- **Tokei** - Count lines of code quickly

### Search Tools
- **Ripgrep (rg)** - Fast recursive grep with smart defaults
- **fd** - Fast and user-friendly alternative to find

### File Management
- **Tree** - Display directory structure as a tree
- **NCurses Disk Usage (ncdu)** - Interactive disk usage analyzer

### Data Processing
- **jq** - Command-line JSON processor

### Version Control
- **GitHub CLI (gh)** - GitHub's official command line tool
- **LazyGit** - Terminal UI for git commands

### Network
- **HTTPie** - Modern command-line HTTP client

### Documentation
- **TLDR Pages** - Simplified man pages with practical examples

### File Viewing
- **Bat** - Cat clone with syntax highlighting

## How It Works

1. **Installation**: Tools are installed using their native package managers (apt, npm, pip, etc.)
2. **Configuration**: Tool status is saved in `~/.cuti/tools_config.json`
3. **Auto-install**: Tools marked with `--auto` are automatically installed when new containers start
4. **Documentation**: Enabled tools are documented in `/workspace/CLAUDE.md` for AI assistance
5. **Integration**: Works seamlessly with both CLI and web UI

## Examples

### Setting Up a Testing Environment

```bash
# Install testing tools
cuti tools install playwright --auto
cuti tools install cypress --enable
cuti tools install k6

# Check what's installed
cuti tools list --category Testing
```

### Setting Up Code Analysis Tools

```bash
# Install and enable code analysis tools
cuti tools install ast-grep --enable --auto
cuti tools install ripgrep --enable --auto
cuti tools install tokei --enable

# Verify installation
cuti tools check | grep -E "(AST|Ripgrep|Tokei)"
```

### Quick Setup for Common Tools

```bash
# Install essential tools with auto-install
cuti tools install tree --auto
cuti tools install jq --auto
cuti tools install ripgrep --auto
cuti tools install fd --auto
cuti tools install bat --auto
```

## Features

- **Category-based organization**: Tools are grouped by their primary use case
- **Status tracking**: See at a glance which tools are installed, enabled, and set to auto-install
- **Version checking**: Verify installed versions with `cuti tools check`
- **Usage instructions**: Each tool includes helpful usage examples
- **Progress indicators**: Visual feedback during installation
- **Error handling**: Clear error messages if installation fails
- **Auto-install**: Configure tools to automatically install in new containers

## Configuration

Tool configuration is stored in `~/.cuti/tools_config.json`:

```json
{
  "enabled_tools": ["playwright", "tree", "jq"],
  "auto_install": ["tree", "ripgrep"]
}
```

For containers with auto-install enabled, a setup script is generated at `/workspace/.cuti/container_tools.sh`.

## Integration with Web UI

The CLI commands work in harmony with the web UI at `http://localhost:8000/tools`. Changes made via CLI are reflected in the web interface and vice versa.

## Tips

1. Use `--auto` flag for tools you want in every container
2. Group related tools by installing them together
3. Check tool compatibility before installation
4. Use `cuti tools info <tool>` to learn about a tool before installing
5. Run `cuti tools check` periodically to verify tool health