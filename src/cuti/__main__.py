#!/usr/bin/env python3
"""
Main entry point for cuti when run with uvx or python -m cuti.
Starts the ops console by default.
"""

import sys
import argparse
import os
from pathlib import Path

from .web.app import main as web_main


def main():
    """Main entry point for uvx cuti command."""
    parser = argparse.ArgumentParser(
        prog="cuti",
        description="Production-ready cuti system with a read-only ops console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uvx cuti                    # Start ops console for current directory
  uvx cuti --port 3000        # Start ops console on port 3000
  uvx cuti --host 0.0.0.0     # Bind to all interfaces
  uvx cuti /path/to/project   # Start ops console for specific directory
  
The ops console is read-only. Use the CLI for provider changes, auth, and queue execution.
Claude workspace state will be inspected from the working directory you specify (or current directory).
Access the console at http://localhost:8000
        """
    )
    
    parser.add_argument(
        "working_directory",
        nargs="?",
        default=None,
        help="Working directory for Claude Code (default: current directory)"
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
        default="~/.cuti",
        help="Storage directory (default: ~/.cuti)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="cuti 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Determine working directory
    if args.working_directory:
        working_dir = Path(args.working_directory).resolve()
        if not working_dir.exists():
            print(f"❌ Error: Directory '{working_dir}' does not exist")
            sys.exit(1)
    else:
        working_dir = Path.cwd()
    
    # Allow environment variables to override CLI
    host = os.getenv("CLAUDE_QUEUE_WEB_HOST", args.host)
    port_str = os.getenv("CLAUDE_QUEUE_WEB_PORT")
    port = int(port_str) if port_str else args.port
    storage_dir = os.getenv("CLAUDE_QUEUE_STORAGE_DIR", args.storage_dir)
    if os.getenv("CLAUDE_QUEUE_STORAGE_DIR"):
        display_storage = Path(storage_dir).expanduser()
    elif args.storage_dir != "~/.cuti":
        display_storage = Path(args.storage_dir).expanduser()
    else:
        display_storage = working_dir / ".cuti"
    
    print("🚀 Starting cuti ops console...")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"📁 Working Directory: {working_dir}")
    print(f"💾 Storage: {display_storage}")
    print(f"🌐 Ops Console: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print("📝 This UI is read-only. Use the CLI for changes.")
    print()
    
    # Set environment variable for working directory
    os.environ["CUTI_WORKING_DIR"] = str(working_dir)
    
    # Override sys.argv for the web main function
    sys.argv = [
        "cuti-web", 
        "--host", host, 
        "--port", str(port), 
        "--storage-dir", storage_dir
    ]
    
    try:
        web_main()
    except KeyboardInterrupt:
        print("\n👋 Shutting down cuti...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting cuti: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
