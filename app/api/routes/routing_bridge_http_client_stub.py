from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_bridge_http_client_stub import (
    bridge_routing_http_client_stub_status,
    build_bridge_routing_http_client_stub_preview,
)

router = APIRouter(prefix="/front-desk/routing/bridge-http-client-stub", tags=["front-desk-routing-bridge-http-client-stub"])


class BridgeRoutingHttpClientStubPreviewRequest(BaseModel):
    release_checkpoint_path: str
    operator_name: str = ""
    confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_http_client_stub_status() -> dict:
    return bridge_routing_http_client_stub_status()


@router.post("/preview")
def post_bridge_routing_http_client_stub_preview(request: BridgeRoutingHttpClientStubPreviewRequest) -> dict:
    return build_bridge_routing_http_client_stub_preview(
        release_checkpoint_path=request.release_checkpoint_path,
        operator_name=request.operator_name,
        confirmation_phrase=request.confirmation_phrase,
    )
