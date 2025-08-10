#!/bin/bash

echo "Starting cuti with new modern UI design..."
echo "======================================"
echo ""
echo "Features of the new design:"
echo "✨ Modern gradient background with animated effects"
echo "✨ Glassmorphism header with professional navigation"
echo "✨ Terminal-style chat area (preserved as requested)"
echo "✨ Beautiful sidebar with task tracking"
echo "✨ Sophisticated color palette (purple/blue gradients)"
echo "✨ Smooth animations and transitions"
echo "✨ Modern input area with processing indicators"
echo "✨ Clean status bar with real-time indicators"
echo ""
echo "Opening browser at http://localhost:8000"
echo ""

# Try to run the web server
if command -v python3 &> /dev/null; then
    python3 src/cuti/web/main.py
elif command -v python &> /dev/null; then
    python src/cuti/web/main.py
else
    echo "Error: Python not found. Please install Python to run the web interface."
    exit 1
fi