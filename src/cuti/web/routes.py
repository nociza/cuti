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
        {"url": "/agents", "label": "Agent Manager", "active": current_page == "agents"},
        {"url": "/statistics", "label": "Statistics", "active": current_page == "statistics"}
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