#!/usr/bin/env python3
"""``python -m cuti`` / ``uvx cuti`` entry point — starts the read-only ops console.

For the full CLI (containers, providers, accounts, history, …) use the ``cuti``
command instead.
"""

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .web.app import main as web_main


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cuti",
        description="cuti read-only ops console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uvx cuti                    # Ops console for the current directory
  uvx cuti --port 3000        # Ops console on port 3000
  uvx cuti /path/to/project   # Ops console for a specific directory

The console is read-only. Use the `cuti` CLI for provider changes and auth.
""",
    )
    parser.add_argument(
        "working_directory",
        nargs="?",
        default=None,
        help="Workspace to inspect (default: current directory)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--storage-dir", default="~/.cuti", help="Storage directory")
    parser.add_argument("--version", action="version", version=f"cuti {__version__}")
    args = parser.parse_args()

    if args.working_directory:
        working_dir = Path(args.working_directory).resolve()
        if not working_dir.exists():
            print(f"Error: directory '{working_dir}' does not exist")
            sys.exit(1)
    else:
        working_dir = Path.cwd()

    host = os.getenv("CUTI_WEB_HOST", args.host)
    port_str = os.getenv("CUTI_WEB_PORT")
    port = int(port_str) if port_str else args.port
    storage_dir = os.getenv("CUTI_STORAGE_DIR", args.storage_dir)

    print("Starting cuti ops console...")
    print(f"Workspace: {working_dir}")
    print(f"Console:   http://{host}:{port}")
    print("This UI is read-only. Use the `cuti` CLI for changes.\n")

    os.environ["CUTI_WORKING_DIR"] = str(working_dir)
    sys.argv = [
        "cuti-web",
        "--host",
        host,
        "--port",
        str(port),
        "--storage-dir",
        storage_dir,
    ]

    try:
        web_main()
    except KeyboardInterrupt:
        print("\nShutting down cuti ops console...")
        sys.exit(0)


if __name__ == "__main__":
    main()
