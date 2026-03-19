"""Main web routes for the redesigned cuti interface."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

main_router = APIRouter()


def get_nav_items(current_page: str) -> list[dict[str, object]]:
    """Return primary navigation items with active state."""

    items = [
        {"url": "/", "label": "Overview", "key": "dashboard"},
        {"url": "/providers", "label": "Providers", "key": "providers"},
        {"url": "/tasks", "label": "Tasks", "key": "tasks"},
        {"url": "/tools", "label": "Tools", "key": "tools"},
        {"url": "/agents", "label": "Agents", "key": "agents"},
    ]
    for item in items:
        item["active"] = item["key"] == current_page
    return items


def _render(request: Request, template_name: str, page_id: str, **context: object) -> HTMLResponse:
    templates = request.app.state.templates
    payload = {
        "request": request,
        "page_id": page_id,
        "working_directory": str(request.app.state.working_directory),
        "nav_items": get_nav_items(page_id),
    }
    payload.update(context)
    return templates.TemplateResponse(request, template_name, payload)


@main_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Operational overview for the current workspace."""

    return _render(
        request,
        "dashboard.html",
        "dashboard",
        page_title="Workspace Control Room",
        page_description="Track provider readiness, dispatch work, and keep the project state visible in one place.",
    )


@main_router.get("/providers", response_class=HTMLResponse)
async def providers_page(request: Request) -> HTMLResponse:
    """Provider selection and readiness page."""

    return _render(
        request,
        "providers.html",
        "providers",
        page_title="Provider Fleet",
        page_description="Select the agent CLIs you want available in the container and inspect their setup state before you start work.",
    )


@main_router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request) -> HTMLResponse:
    """Queue and todo management page."""

    return _render(
        request,
        "tasks.html",
        "tasks",
        page_title="Dispatch and Work Queue",
        page_description="Submit work into the queue, track prompt execution, and keep the active todo list aligned with what the agents are doing.",
    )


@main_router.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request) -> HTMLResponse:
    """CLI tool catalog page."""

    return _render(
        request,
        "tools.html",
        "tools",
        page_title="Workspace Toolbelt",
        page_description="Choose which supporting CLI tools should be documented, installed, and carried into the container runtime.",
    )


@main_router.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request) -> HTMLResponse:
    """Workspace agent inventory page."""

    return _render(
        request,
        "agents.html",
        "agents",
        page_title="Agent Inventory",
        page_description="Inspect Claude agent files and orchestration state so the workspace instructions stay legible and predictable.",
    )


@main_router.get("/todos")
async def legacy_todos_redirect() -> RedirectResponse:
    return RedirectResponse(url="/tasks", status_code=307)


@main_router.get("/statistics")
async def legacy_statistics_redirect() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)


@main_router.get("/global-settings")
async def legacy_settings_redirect() -> RedirectResponse:
    return RedirectResponse(url="/providers", status_code=307)


@main_router.get("/orchestration")
async def legacy_orchestration_redirect() -> RedirectResponse:
    return RedirectResponse(url="/agents", status_code=307)


@main_router.get("/enhanced-chat")
async def legacy_chat_redirect() -> RedirectResponse:
    return RedirectResponse(url="/tasks", status_code=307)
