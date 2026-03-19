"""Provider-oriented web API endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...services.provider_host import ProviderHostService
from ...services.providers import ProviderManager

router = APIRouter(prefix="/api/providers", tags=["providers"])


class ProviderSelectionRequest(BaseModel):
    """Requested enabled state for a provider."""

    enabled: bool


def _provider_service(request: Request) -> ProviderHostService:
    return ProviderHostService(working_directory=str(request.app.state.working_directory))


@router.get("")
async def list_providers(request: Request) -> Dict[str, Any]:
    """Return host-side provider status for all known providers."""

    service = _provider_service(request)
    manager = service.provider_manager
    return {
        "primary_provider": manager.primary_provider(),
        "selected_providers": manager.selected_providers(),
        "items": [status.to_dict() for status in service.list_statuses()],
    }


@router.get("/{provider_name}")
async def get_provider(provider_name: str, request: Request) -> Dict[str, Any]:
    """Return host-side provider status for one provider."""

    service = _provider_service(request)
    try:
        status = service.get_status(provider_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return status.to_dict()


@router.put("/{provider_name}/selection")
async def update_provider_selection(
    provider_name: str,
    selection: ProviderSelectionRequest,
    request: Request,
) -> Dict[str, Any]:
    """Enable or disable a provider for future container runs."""

    manager = ProviderManager()
    try:
        canonical = manager.get_metadata(provider_name).name
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    manager.set_enabled(canonical, selection.enabled, source="web-ui")
    service = _provider_service(request)
    status = service.get_status(canonical)
    return {
        "provider": canonical,
        "enabled": status.enabled,
        "primary_provider": service.provider_manager.primary_provider(),
        "selected_providers": service.provider_manager.selected_providers(),
        "status": status.to_dict(),
    }
