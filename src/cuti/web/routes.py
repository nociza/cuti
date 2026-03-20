"""Routes for the lightweight cuti ops console."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

main_router = APIRouter()



def _render(request: Request, template_name: str, page_id: str, **context: object) -> HTMLResponse:
    templates = request.app.state.templates
    payload = {
        "request": request,
        "page_id": page_id,
        "working_directory": str(request.app.state.working_directory),
    }
    payload.update(context)
    return templates.TemplateResponse(request, template_name, payload)


@main_router.get("/", response_class=HTMLResponse)
async def ops_console(request: Request) -> HTMLResponse:
    """Read-only workspace operations console."""

    return _render(
        request,
        "ops.html",
        "ops",
        page_title="Workspace Ops Console",
        page_description="Inspect provider readiness, queue state, recent activity, and workspace drift. Use the CLI for changes.",
    )


@main_router.get("/providers")
@main_router.get("/tasks")
@main_router.get("/tools")
@main_router.get("/agents")
@main_router.get("/todos")
@main_router.get("/statistics")
@main_router.get("/global-settings")
@main_router.get("/orchestration")
@main_router.get("/enhanced-chat")
async def legacy_redirect() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)
