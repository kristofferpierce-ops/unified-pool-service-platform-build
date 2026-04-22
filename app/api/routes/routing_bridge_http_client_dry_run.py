from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_bridge_http_client_dry_run import (
    bridge_routing_http_client_dry_run_status,
    build_bridge_routing_http_client_dry_run,
)

router = APIRouter(prefix="/front-desk/routing/bridge-http-client-dry-run", tags=["front-desk-routing-bridge-http-client-dry-run"])


class BridgeRoutingHttpClientDryRunRequest(BaseModel):
    stub_report_path: str
    operator_name: str = ""
    confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_http_client_dry_run_status() -> dict:
    return bridge_routing_http_client_dry_run_status()


@router.post("/simulate")
def post_bridge_routing_http_client_dry_run_simulate(request: BridgeRoutingHttpClientDryRunRequest) -> dict:
    return build_bridge_routing_http_client_dry_run(
        stub_report_path=request.stub_report_path,
        operator_name=request.operator_name,
        confirmation_phrase=request.confirmation_phrase,
    )
