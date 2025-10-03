#!/usr/bin/env bash
set -euo pipefail

echo "📦 Building website for deployment..."
echo ""

# Check if we're in the website directory or root
if [ -d "../docs" ]; then
    DOCS_SOURCE="../docs"
    WEBSITE_DIR="."
elif [ -d "docs" ] && [ -d "website" ]; then
    DOCS_SOURCE="docs"
    WEBSITE_DIR="website"
else
    echo "❌ Cannot find docs directory"
    echo "This script should be run from either:"
    echo "  - The website/ directory (with ../docs available)"
    echo "  - The project root (with docs/ and website/ available)"
    exit 1
fi

echo "📄 Syncing documentation files..."

# Create docs directory in website if needed
mkdir -p "$WEBSITE_DIR/docs"

# Copy all markdown files from docs to website/docs
rsync -av --delete --include='*.md' --exclude='*' "$DOCS_SOURCE/" "$WEBSITE_DIR/docs/" 2>/dev/null || \
    cp -r "$DOCS_SOURCE"/*.md "$WEBSITE_DIR/docs/" 2>/dev/null || \
    echo "⚠️  Warning: Could not sync docs (may not exist or already synced)"

doc_count=$(find "$WEBSITE_DIR/docs" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "✅ Synced $doc_count documentation files"

echo ""
echo "🔍 Validating website..."

# Check if required files exist
required_files=("index.html" "docs.html" "styles.css" "script.js" "docs.js")
for file in "${required_files[@]}"; do
    if [ ! -f "$WEBSITE_DIR/$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

echo "✅ All required files present"
echo ""
echo "✅ Website build complete!"
echo ""
echo "📂 Output directory: $WEBSITE_DIR"

