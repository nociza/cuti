"""FastAPI application for the lightweight cuti ops console."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..services.claude_logs_reader import ClaudeLogsReader
from ..services.history import PromptHistoryManager
from ..services.queue_service import QueueManager
from .api.ops import router as ops_router
from .routes import main_router



def _resolve_storage_dir(storage_dir: str, working_directory: Path) -> Path:
    override = os.getenv("CLAUDE_QUEUE_STORAGE_DIR")
    if override:
        return Path(override).expanduser()
    if storage_dir and storage_dir != "~/.cuti":
        return Path(storage_dir).expanduser()
    return working_directory / ".cuti"



def create_app(
    storage_dir: str = "~/.cuti",
    working_directory: Optional[str] = None,
) -> FastAPI:
    """Create the passive cuti ops console."""

    app = FastAPI(
        title="cuti Ops Console",
        description="Read-only workspace operations console for provider readiness, queue state, and drift.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    working_path = Path(working_directory or Path.cwd()).resolve()
    resolved_storage_dir = _resolve_storage_dir(storage_dir, working_path)

    queue_manager = None
    queue_warning = None
    try:
        queue_manager = QueueManager(storage_dir=str(resolved_storage_dir))
    except RuntimeError as exc:
        queue_warning = str(exc)
        print(f"Warning: {queue_warning}")
        print("The ops console will still load, but queue inspection is limited until Claude is available.")

    app.state.queue_manager = queue_manager
    app.state.queue_warning = queue_warning
    app.state.history_manager = PromptHistoryManager(str(resolved_storage_dir))
    app.state.claude_logs_reader = ClaudeLogsReader(working_directory=str(working_path))
    app.state.storage_dir = resolved_storage_dir
    app.state.working_directory = working_path

    web_dir = Path(__file__).parent
    app.state.templates = Jinja2Templates(directory=str(web_dir / "templates"))

    try:
        app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
    except RuntimeError:
        pass

    app.include_router(ops_router)
    app.include_router(main_router)
    return app



def main() -> None:
    """Main entry point for the web application."""

    parser = argparse.ArgumentParser(
        description="cuti Ops Console",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--storage-dir", default="~/.cuti", help="Storage directory")
    parser.add_argument("--working-directory", default=None, help="Workspace to inspect")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    host = os.getenv("CLAUDE_QUEUE_WEB_HOST", args.host)
    port_env = os.getenv("CLAUDE_QUEUE_WEB_PORT")
    port = int(port_env) if port_env else args.port
    storage_dir = os.getenv("CLAUDE_QUEUE_STORAGE_DIR", args.storage_dir)
    working_dir = os.getenv("CUTI_WORKING_DIR", args.working_directory)
    app = create_app(storage_dir=storage_dir, working_directory=working_dir)

    print("Starting cuti ops console...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Storage: {Path(app.state.storage_dir)}")
    if working_dir:
        print(f"Working Directory: {working_dir}")
    print(f"Ops Console: http://{host}:{port}")
    print(f"API Docs: http://{host}:{port}/docs")
    print("This UI is read-only. Use the CLI for provider changes, auth, and queue execution.")
    print()

    try:
        uvicorn.run(app, host=host, port=port, reload=args.reload, log_level="info")
    except KeyboardInterrupt:
        print("\nShutting down cuti ops console...")
        sys.exit(0)
    except Exception as exc:
        print(f"Error starting ops console: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
