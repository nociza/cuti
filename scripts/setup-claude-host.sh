#!/bin/bash
# Script to setup Claude configuration on host machine for container usage

echo "🔧 Setting up Claude configuration for container usage..."

CLAUDE_JSON="$HOME/.claude.json"

# Check if .claude.json exists
if [ -f "$CLAUDE_JSON" ]; then
    echo "📄 Found existing .claude.json"
    
    # Check if bypassPermissionsModeAccepted is already set
    if grep -q '"bypassPermissionsModeAccepted".*true' "$CLAUDE_JSON"; then
        echo "✅ bypassPermissionsModeAccepted is already set to true"
    else
        echo "⚙️  Adding bypassPermissionsModeAccepted setting..."
        
        # Backup the original file
        cp "$CLAUDE_JSON" "$CLAUDE_JSON.backup"
        
        # Use jq if available, otherwise use sed
        if command -v jq >/dev/null 2>&1; then
            jq '.bypassPermissionsModeAccepted = true' "$CLAUDE_JSON" > "$CLAUDE_JSON.tmp" && \
            mv "$CLAUDE_JSON.tmp" "$CLAUDE_JSON"
            echo "✅ Updated .claude.json with bypassPermissionsModeAccepted"
        else
            # Simple approach: add it before the last closing brace
            sed -i.bak 's/^}$/  ,"bypassPermissionsModeAccepted": true\n}/' "$CLAUDE_JSON"
            echo "✅ Added bypassPermissionsModeAccepted to .claude.json"
        fi
    fi
else
    echo "📝 Creating new .claude.json with required settings..."
    cat > "$CLAUDE_JSON" << 'EOF'
{
  "bypassPermissionsModeAccepted": true
}
EOF
    echo "✅ Created .claude.json"
fi

echo ""
echo "🎉 Claude configuration is ready for container usage!"
echo ""
echo "You can now run 'cuti container' and Claude should work automatically."
echo "If you haven't authenticated Claude yet, run 'claude login' first."