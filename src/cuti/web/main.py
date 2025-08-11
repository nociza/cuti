"""
Main entry point for the web application.
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

from .app import create_app


def main():
    """Main entry point for the web application."""
    parser = argparse.ArgumentParser(
        description="cuti Web Interface",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1", 
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to"
    )
    parser.add_argument(
        "--storage-dir",
        default="~/.cuti",
        help="Storage directory"
    )
    parser.add_argument(
        "--working-directory",
        default=None,
        help="Working directory for Claude Code"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    args = parser.parse_args()
    
    # Override with environment variables if set
    host = os.getenv("CLAUDE_QUEUE_WEB_HOST", args.host)
    port_env = os.getenv("CLAUDE_QUEUE_WEB_PORT")
    port = int(port_env) if port_env else args.port
    storage_dir = os.getenv("CLAUDE_QUEUE_STORAGE_DIR", args.storage_dir)
    working_dir = os.getenv("CUTI_WORKING_DIR", args.working_directory)
    
    # Create the FastAPI app
    app = create_app(
        storage_dir=storage_dir,
        working_directory=working_dir
    )
    
    print(f"🚀 Starting cuti web interface...")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"💾 Storage: {Path(storage_dir).expanduser()}")
    if working_dir:
        print(f"📁 Working Directory: {working_dir}")
    print(f"🌐 Dashboard: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print()
    
    # Run the server
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=args.reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down cuti web interface...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()