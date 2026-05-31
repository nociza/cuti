"""Routes for the lightweight cuti ops console."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

main_router = APIRouter()


def _render(
    request: Request, template_name: str, page_id: str, **context: object
) -> HTMLResponse:
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
        page_description="Inspect provider readiness, Claude sessions, tools, and "
        "workspace instruction-file drift. Use the CLI for changes.",
    )
