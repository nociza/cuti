#!/bin/bash
# Quick rebuild script for cuti

echo "🔨 Rebuilding cuti package..."
rm -rf dist/ build/ *.egg-info
uv build
echo "✅ Build complete!"
echo ""
echo "📦 To test locally:"
echo "   uvx --from . cuti"
echo ""
echo "🚀 To publish to PyPI:"
echo "   uv publish"