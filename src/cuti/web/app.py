"""
FastAPI web application for cuti.
"""

import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from ..services.queue_service import QueueManager
from ..services.aliases import PromptAliasManager
from ..services.history import PromptHistoryManager
from ..services.task_expansion import TaskExpansionEngine
from ..services.monitoring import SystemMonitor
from ..core.claude_interface import ClaudeCodeInterface
from ..services.claude_usage_monitor import ClaudeUsageMonitor
from ..services.claude_agent_manager import ClaudeCodeAgentManager
from ..services.claude_settings_manager import ClaudeSettingsManager
from ..services.claude_logs_reader import ClaudeLogsReader
from ..services.workspace_manager import WorkspaceManager
from ..services.log_sync import LogSyncService
from ..services.claude_orchestration import ClaudeOrchestrationManager
from ..services.usage_sync_service import UsageSyncManager
from ..services.global_data_manager import GlobalDataManager
from .api.queue import queue_router
from .api.agents import agents_router, get_orchestration_manager
from .api.monitoring import monitoring_router
from .api.websocket import websocket_router
from .api.claude_code_agents import claude_code_agents_router
from .api.claude_settings import claude_settings_router
from .api.claude_logs import claude_logs_router
from .api.workspace import workspace_router
from .api.claude_status import router as claude_status_router
try:
    from .api.enhanced_chat import enhanced_chat_router
except ImportError:
    enhanced_chat_router = None
try:
    from .api.improved_chat import improved_chat_router
except ImportError:
    improved_chat_router = None
try:
    from .api.streaming_chat import streaming_chat_router
except ImportError:
    streaming_chat_router = None
try:
    from .api.todos import router as todos_router
except ImportError:
    todos_router = None
try:
    from .api.global_settings import router as global_settings_router
except ImportError:
    global_settings_router = None
from .utils import WebSocketManager


def create_app(
    storage_dir: str = "~/.cuti",
    working_directory: Optional[str] = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="cuti Web Interface",
        description="Production-ready Claude Code utils with web interface",
        version="0.1.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize workspace manager first
    workspace_manager = WorkspaceManager(working_directory=working_directory)
    
    # Use workspace-specific storage
    workspace_storage = str(workspace_manager.cuti_dir)
    
    # Initialize managers with workspace storage
    try:
        queue_manager = QueueManager(storage_dir=workspace_storage)
        claude_interface = ClaudeCodeInterface()
    except RuntimeError as e:
        # Handle case where Claude CLI is not available
        print(f"Warning: {e}")
        print("Web interface will start in demo mode.")
        queue_manager = None
        claude_interface = None
    
    alias_manager = PromptAliasManager(workspace_storage)
    history_manager = PromptHistoryManager(workspace_storage)
    task_engine = TaskExpansionEngine(workspace_storage)
    system_monitor = SystemMonitor(base_dir=workspace_storage)
    websocket_manager = WebSocketManager()
    
    # Initialize Claude usage monitor
    usage_monitor = ClaudeUsageMonitor(plan='pro', storage_dir=workspace_storage)
    
    # Initialize log sync service
    log_sync_service = LogSyncService(workspace_manager)
    # Perform initial sync
    log_sync_service.sync_all()
    # Start auto-sync in background
    log_sync_service.auto_sync(interval=300)  # Sync every 5 minutes
    
    # Initialize global data manager and usage sync
    global_data_manager = GlobalDataManager()
    if global_data_manager.settings.usage_tracking_enabled:
        # Start background usage sync service
        UsageSyncManager.start_service()
        # Perform initial sync
        UsageSyncManager.sync_now()
    
    # Initialize Claude Code agent manager (reads from .claude/agents)
    claude_code_agent_manager = ClaudeCodeAgentManager(
        working_directory=working_directory
    )
    
    # Initialize Claude settings manager
    claude_settings_manager = ClaudeSettingsManager(
        working_directory=working_directory
    )
    
    # Initialize Claude logs reader for ground truth data
    claude_logs_reader = ClaudeLogsReader(
        working_directory=working_directory
    )
    
    # Initialize project settings if needed
    if not (Path(working_directory or Path.cwd()) / ".claude").exists():
        claude_settings_manager.initialize_project_settings()
    
    # Initialize orchestration manager
    orchestration_manager = ClaudeOrchestrationManager(Path(working_directory or Path.cwd()))
    
    # Store managers in app state
    app.state.queue_manager = queue_manager
    app.state.claude_interface = claude_interface
    app.state.alias_manager = alias_manager
    app.state.history_manager = history_manager
    app.state.task_engine = task_engine
    app.state.system_monitor = system_monitor
    app.state.websocket_manager = websocket_manager
    app.state.usage_monitor = usage_monitor
    app.state.claude_code_agent_manager = claude_code_agent_manager
    app.state.claude_settings_manager = claude_settings_manager
    app.state.claude_logs_reader = claude_logs_reader
    app.state.workspace_manager = workspace_manager
    app.state.log_sync_service = log_sync_service
    app.state.orchestration_manager = orchestration_manager
    app.state.storage_dir = workspace_storage
    app.state.working_directory = Path(working_directory or Path.cwd()).resolve()
    
    # Static files and templates
    web_dir = Path(__file__).parent
    templates = Jinja2Templates(directory=str(web_dir / "templates"))
    app.state.templates = templates
    
    try:
        app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
    except RuntimeError:
        pass  # Directory might not exist
    
    # Include API routers
    app.include_router(queue_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    app.include_router(monitoring_router, prefix="/api")
    app.include_router(claude_code_agents_router, prefix="/api")
    app.include_router(claude_settings_router, prefix="/api")
    app.include_router(claude_logs_router, prefix="/api")
    app.include_router(workspace_router, prefix="/api")
    app.include_router(claude_status_router)
    app.include_router(websocket_router)
    
    # Include enhanced chat router if available
    if enhanced_chat_router:
        app.include_router(enhanced_chat_router)
    
    # Include improved chat router if available
    if improved_chat_router:
        app.include_router(improved_chat_router)
    
    # Include streaming chat router if available
    if streaming_chat_router:
        app.include_router(streaming_chat_router)
    
    # Include todos router if available
    if todos_router:
        app.include_router(todos_router)
    
    # Include global settings router if available
    if global_settings_router:
        app.include_router(global_settings_router)
    
    # Include main routes
    from .routes import main_router
    app.include_router(main_router)
    
    # Start queue processor in the background on app startup
    @app.on_event("startup")
    async def _start_background_processor():
        # Initialize orchestration manager
        await orchestration_manager.initialize()
        
        # Set the global orchestration manager for the API
        from .api import agents as agents_api
        agents_api.orchestration_manager = orchestration_manager
        
        if not queue_manager:
            return
            
        # Avoid double-start in hot-reload or multiple workers
        if getattr(app.state, "queue_thread", None) is not None:
            return

        def _run_queue():
            try:
                queue_manager.start()
            finally:
                # Reflect stopped state
                app.state.queue_running = False

        thread = threading.Thread(target=_run_queue, name="cuti-queue", daemon=True)
        app.state.queue_thread = thread
        app.state.queue_running = True
        thread.start()

    @app.on_event("shutdown")
    async def _stop_background_processor():
        if not queue_manager:
            return
            
        try:
            queue_manager.stop()
        except Exception:
            pass
        thread = getattr(app.state, "queue_thread", None)
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
    
    return app


def main():
    """Main entry point for the web application."""
    import argparse
    import os
    import sys
    import uvicorn
    
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