#!/usr/bin/env python3
"""
Main entry point for ccutils when run with uvx or python -m ccutils.
Starts the web server by default.
"""

import sys
import argparse
import os
from pathlib import Path

from .web.main import main as web_main


def main():
    """Main entry point for uvx ccutils command."""
    parser = argparse.ArgumentParser(
        prog="ccutils",
        description="Production-ready ccutils system with web interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uvx ccutils                    # Start web interface on default port (8000)
  uvx ccutils --port 3000        # Start web interface on port 3000
  uvx ccutils --host 0.0.0.0     # Bind to all interfaces
  
The web interface will automatically start the queue processor in the background.
Access the dashboard at http://localhost:8000
        """
    )
    
    parser.add_argument(
        "--host", 
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--storage-dir", 
        default="~/.claude-queue",
        help="Storage directory (default: ~/.claude-queue)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ccutils 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Allow environment variables to override CLI
    host = os.getenv("CLAUDE_QUEUE_WEB_HOST", args.host)
    port_str = os.getenv("CLAUDE_QUEUE_WEB_PORT")
    port = int(port_str) if port_str else args.port
    storage_dir = os.getenv("CLAUDE_QUEUE_STORAGE_DIR", args.storage_dir)
    
    print(f"🚀 Starting ccutils web interface...")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"💾 Storage: {Path(storage_dir).expanduser()}")
    print(f"🌐 Dashboard: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print()
    
    # Override sys.argv for the web main function
    sys.argv = [
        "ccutils-web", 
        "--host", host, 
        "--port", str(port), 
        "--storage-dir", storage_dir
    ]
    
    try:
        web_main()
    except KeyboardInterrupt:
        print("\n👋 Shutting down ccutils...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting ccutils: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()