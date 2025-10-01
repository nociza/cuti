#!/bin/bash
# Automatic workspace tools activation for cuti containers
# This script should be sourced in shell initialization files

# Function to automatically activate workspace tools
cuti_auto_activate_tools() {
    # Check if we're in a workspace with tools configuration
    if [ -f "$PWD/.cuti/tools.json" ]; then
        # Check if tools are already activated for this workspace
        if [ "$CUTI_WORKSPACE_TOOLS_ACTIVE" != "$PWD" ]; then
            # Activate workspace tools silently
            eval $(cuti tools activate 2>/dev/null)
            if [ $? -eq 0 ]; then
                export CUTI_WORKSPACE_TOOLS_ACTIVE="$PWD"
                echo "✅ Workspace tools activated for: $(basename $PWD)"
            fi
        fi
    fi
}

# Function to handle directory changes
cuti_cd() {
    # Call the original cd command
    builtin cd "$@"
    local result=$?
    
    # If cd was successful, check for workspace tools
    if [ $result -eq 0 ]; then
        cuti_auto_activate_tools
    fi
    
    return $result
}

# Override cd command with our wrapper
alias cd='cuti_cd'

# Activate tools for current directory on shell start
cuti_auto_activate_tools

# Also hook into prompt command for additional safety
# This ensures tools are activated even if directory is changed by other means
if [ -n "$PROMPT_COMMAND" ]; then
    # Append to existing PROMPT_COMMAND
    PROMPT_COMMAND="${PROMPT_COMMAND}; cuti_auto_activate_tools >/dev/null 2>&1"
else
    PROMPT_COMMAND="cuti_auto_activate_tools >/dev/null 2>&1"
fi