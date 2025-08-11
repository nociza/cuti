"""
Main web routes for the cuti web interface.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

main_router = APIRouter()


@main_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main terminal chat interface."""
    templates = request.app.state.templates
    
    nav_items = [
        {"label": "Chat", "onclick": "activeTab = 'chat'", "tab_id": "chat"},
        {"label": "History", "onclick": "activeTab = 'history'", "tab_id": "history"},
        {"label": "Settings", "onclick": "activeTab = 'settings'", "tab_id": "settings"},
        {"url": "/agents", "label": "Agent Status", "active": False}
    ]
    
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
    
    nav_items = [
        {"url": "/", "label": "Chat", "active": False},
        {"url": "/agents", "label": "Agent Status", "active": True}
    ]
    
    return templates.TemplateResponse("agents.html", {
        "request": request,
        "working_directory": "System Monitor",
        "nav_items": nav_items
    })