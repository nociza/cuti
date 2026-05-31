#!/usr/bin/env python3
"""Developer convenience shim for working on cuti from a source checkout.

This is NOT the user-facing entry point. Once installed, use the console
scripts instead:

    cuti              # the full CLI (containers, providers, accounts, ...)
    cuti-web          # the read-only ops console
    python -m cuti    # the ops console (same as cuti-web)

`run.py` only helps contributors bootstrap the editable install and delegate
into those commands without installing first.
"""

import subprocess
import sys
from pathlib import Path


def check_uv_available() -> bool:
    try:
        result = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def setup_environment() -> bool:
    """Install cuti in editable mode with uv."""
    if not check_uv_available():
        print("uv is not available. Install it first:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    try:
        subprocess.run(
            ["uv", "pip", "install", "-e", ".[dev]"],
            check=True,
            cwd=Path(__file__).parent,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Installation failed: {exc}")
        return False
    print("cuti installed in editable mode. Try: cuti --help")
    return True


def main() -> int:
    args = sys.argv[1:]
    command = args[0] if args else None

    if command in (None, "-h", "--help", "help"):
        print(__doc__)
        print("Usage:")
        print("  python run.py setup        # editable install with uv")
        print("  python run.py cli [args]   # run the cuti CLI from source")
        print("  python run.py web [args]   # run the ops console from source")
        return 0 if command else 1

    if command == "setup":
        return 0 if setup_environment() else 1

    # Make the source tree importable without an install.
    src_path = Path(__file__).parent / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))

    if command == "cli":
        from cuti.cli.app import app as cli_app

        sys.argv = ["cuti", *args[1:]] if len(args) > 1 else ["cuti", "--help"]
        cli_app()
        return 0

    if command == "web":
        from cuti.web.app import main as web_main

        sys.argv = ["cuti-web", *args[1:]]
        web_main()
        return 0

    print(f"Unknown command: {command}. Try 'python run.py --help'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
