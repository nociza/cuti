"""
Main web routes for the cuti web interface.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

main_router = APIRouter()


def get_nav_items(current_page: str = "chat"):
    """Get navigation items with proper active state."""
    nav_items = [
        {"url": "/", "label": "Chat", "active": current_page == "chat"},
        {"url": "/todos", "label": "Todos", "active": current_page == "todos"},
        {"url": "/agents", "label": "Agent Manager", "active": current_page == "agents"},
        {"url": "/statistics", "label": "Statistics", "active": current_page == "statistics"},
        {"url": "/global-settings", "label": "Global Settings", "active": current_page == "settings"}
    ]
    return nav_items


@main_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main terminal chat interface."""
    templates = request.app.state.templates
    
    nav_items = get_nav_items("chat")
    
    status_info = {
        "left": ["0 messages"],
        "right": [
            {"text": "Ready", "indicator": "ready"},
            {"text": "0 active tasks", "indicator": None}
        ]
    }
    
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "working_directory": str(request.app.state.working_directory),
        "nav_items": nav_items,
        "status_info": status_info
    })


@main_router.get("/agents", response_class=HTMLResponse)
async def agents_dashboard(request: Request):
    """Agent status dashboard page."""
    templates = request.app.state.templates
    
    nav_items = get_nav_items("agents")
    
    return templates.TemplateResponse("agents.html", {
        "request": request,
        "working_directory": str(request.app.state.working_directory),
        "nav_items": nav_items
    })


@main_router.get("/todos", response_class=HTMLResponse)
async def todos_dashboard(request: Request):
    """Todo list management page."""
    templates = request.app.state.templates
    
    nav_items = get_nav_items("todos")
    
    # Check if todos.html template exists, fallback to a simple page if not
    try:
        return templates.TemplateResponse("todos.html", {
            "request": request,
            "working_directory": str(request.app.state.working_directory),
            "nav_items": nav_items
        })
    except Exception:
        # Fallback for older versions without todos.html template
        from fastapi.responses import HTMLResponse
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Todos - cuti</title>
            <style>
                body {{ font-family: system-ui, sans-serif; padding: 20px; background: #f9fafb; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .title {{ font-size: 2rem; color: #1f2937; margin: 0 0 10px 0; }}
                .subtitle {{ color: #6b7280; margin: 0; }}
                .message {{ text-align: center; padding: 60px 20px; color: #6b7280; }}
                .icon {{ font-size: 3rem; margin-bottom: 20px; }}
                .nav {{ margin-bottom: 20px; }}
                .nav a {{ display: inline-block; padding: 8px 16px; margin-right: 10px; text-decoration: none; color: #374151; background: #f3f4f6; border-radius: 4px; }}
                .nav a.active {{ background: #3b82f6; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav">
                    <a href="/">Chat</a>
                    <a href="/todos" class="active">Todos</a>
                    <a href="/agents">Agents</a>
                    <a href="/statistics">Statistics</a>
                </div>
                <div class="header">
                    <h1 class="title">Todo Manager</h1>
                    <p class="subtitle">Task management coming soon</p>
                </div>
                <div class="message">
                    <div class="icon">📝</div>
                    <h3>Todo Management</h3>
                    <p>This feature is available in the latest version of cuti.</p>
                    <p>Use the CLI commands for now:</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li><code>cuti todo add "Task description"</code></li>
                        <li><code>cuti todo list</code></li>
                        <li><code>cuti todo complete &lt;id&gt;</code></li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=fallback_html)


@main_router.get("/statistics", response_class=HTMLResponse)
async def statistics_dashboard(request: Request):
    """Usage statistics dashboard page."""
    templates = request.app.state.templates
    
    nav_items = get_nav_items("statistics")
    
    return templates.TemplateResponse("statistics.html", {
        "request": request,
        "working_directory": str(request.app.state.working_directory),
        "nav_items": nav_items
    })


@main_router.get("/orchestration", response_class=HTMLResponse)
async def orchestration_dashboard(request: Request):
    """Agent orchestration control page."""
    templates = request.app.state.templates
    
    nav_items = get_nav_items("orchestration")
    
    return templates.TemplateResponse("agents_orchestration.html", {
        "request": request,
        "working_directory": str(request.app.state.working_directory),
        "nav_items": nav_items
    })


@main_router.get("/enhanced-chat", response_class=HTMLResponse)
async def enhanced_chat_page(request: Request):
    """Enhanced chat interface with execution control and detailed streaming."""
    templates = request.app.state.templates
    
    nav_items = get_nav_items("chat")
    
    status_info = {
        "left": ["Enhanced Mode"],
        "right": [
            {"text": "Ready", "indicator": "ready"},
            {"text": "Stop Enabled", "indicator": "success"}
        ]
    }
    
    return templates.TemplateResponse("enhanced_chat.html", {
        "request": request,
        "working_directory": str(request.app.state.working_directory),
        "nav_items": nav_items,
        "status_info": status_info
    })


@main_router.get("/global-settings", response_class=HTMLResponse)
async def global_settings(request: Request):
    """Global settings page."""
    templates = request.app.state.templates
    
    nav_items = get_nav_items("settings")
    
    return templates.TemplateResponse("global_settings.html", {
        "request": request,
        "nav_items": nav_items
    })