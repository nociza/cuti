#!/bin/bash

# Claude Code version switcher

set -e

VERSION="$1"
CURRENT_VERSION=$(npm list -g @anthropic-ai/claude-code 2>/dev/null | grep @anthropic-ai/claude-code | sed 's/.*@//')

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

show_usage() {
    echo "Usage: claude-switch <version|list|current>"
    echo ""
    echo "Commands:"
    echo "  <version>  - Switch to a specific version (e.g., 1.0.110)"
    echo "  list       - Show available versions from npm"
    echo "  current    - Show currently installed version"
    echo "  latest     - Switch to the latest version"
    echo ""
    echo "Examples:"
    echo "  claude-switch 1.0.110"
    echo "  claude-switch latest"
    echo "  claude-switch list"
}

if [ -z "$1" ]; then
    show_usage
    exit 1
fi

case "$1" in
    current)
        echo -e "${GREEN}Current Claude Code version: ${YELLOW}${CURRENT_VERSION}${NC}"
        ;;
    
    list)
        echo -e "${GREEN}Fetching available Claude Code versions...${NC}"
        npm view @anthropic-ai/claude-code versions --json | jq -r '.[]' | tail -20
        echo -e "\n${YELLOW}Showing last 20 versions. For all versions, use: npm view @anthropic-ai/claude-code versions${NC}"
        ;;
    
    latest)
        echo -e "${GREEN}Switching to latest Claude Code version...${NC}"
        sudo npm uninstall -g @anthropic-ai/claude-code 2>/dev/null || true
        sudo npm install -g @anthropic-ai/claude-code@latest
        NEW_VERSION=$(npm list -g @anthropic-ai/claude-code 2>/dev/null | grep @anthropic-ai/claude-code | sed 's/.*@//')
        echo -e "${GREEN}✓ Successfully switched to Claude Code ${YELLOW}${NEW_VERSION}${NC}"
        ;;
    
    help|--help|-h)
        show_usage
        ;;
    
    *)
        # Assume it's a version number
        echo -e "${GREEN}Switching from Claude Code ${YELLOW}${CURRENT_VERSION}${GREEN} to ${YELLOW}${VERSION}${NC}..."
        
        # Uninstall current version
        sudo npm uninstall -g @anthropic-ai/claude-code 2>/dev/null || true
        
        # Install specified version
        if sudo npm install -g @anthropic-ai/claude-code@"${VERSION}"; then
            NEW_VERSION=$(npm list -g @anthropic-ai/claude-code 2>/dev/null | grep @anthropic-ai/claude-code | sed 's/.*@//')
            echo -e "${GREEN}✓ Successfully switched to Claude Code ${YELLOW}${NEW_VERSION}${NC}"
        else
            echo -e "${RED}✗ Failed to install Claude Code version ${VERSION}${NC}"
            echo -e "${YELLOW}Use 'claude-switch list' to see available versions${NC}"
            exit 1
        fi
        ;;
esac