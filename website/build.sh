#!/usr/bin/env bash
set -euo pipefail

echo "📦 Building static website for deployment..."
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
    exit 1
fi

echo "📄 Syncing documentation files..."

# Create docs directory in website if needed
mkdir -p "$WEBSITE_DIR/docs"

# Copy all markdown files from docs to website/docs
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --include='*.md' --exclude='*' "$DOCS_SOURCE/" "$WEBSITE_DIR/docs/" 2>/dev/null
else
    rm -f "$WEBSITE_DIR/docs"/*.md 2>/dev/null
    cp "$DOCS_SOURCE"/*.md "$WEBSITE_DIR/docs/" 2>/dev/null
fi

doc_count=$(find "$WEBSITE_DIR/docs" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "✅ Synced $doc_count documentation files"

echo ""
echo "🔍 Validating website..."

# Check if required files exist
required_files=("index.html" "docs.html" "styles.css" "script.js" "docs.js" "favicon.svg" "robots.txt" "sitemap.xml")
for file in "${required_files[@]}"; do
    if [ ! -f "$WEBSITE_DIR/$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

echo "✅ All required files present (including SEO files)"
echo "✅ Static website build complete!"
echo ""
echo "📂 Deploy this directory: $WEBSITE_DIR"
echo "🌐 Website is ready for Cloudflare Pages, Netlify, Vercel, etc."

