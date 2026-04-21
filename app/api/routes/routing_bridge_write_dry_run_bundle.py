from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from app.services.routing_bridge_write_dry_run_bundle import (
    bridge_routing_write_dry_run_bundle_status,
    build_bridge_routing_write_dry_run_bundle,
)

router = APIRouter(prefix="/front-desk/routing/bridge-write-dry-run-bundle", tags=["front-desk-routing-bridge-dry-run-bundle"])


class BridgeRoutingWriteDryRunBundleRequest(BaseModel):
    scaffold_report_path: str
    cutover_packet_path: str | None = None
    implementation_plan_path: str | None = None


@router.get("/status")
def get_bridge_routing_write_dry_run_bundle_status() -> dict:
    return bridge_routing_write_dry_run_bundle_status()


@router.post("/build-preview")
def post_bridge_routing_write_dry_run_bundle_preview(request: BridgeRoutingWriteDryRunBundleRequest) -> dict:
    return build_bridge_routing_write_dry_run_bundle(
        scaffold_report_path=request.scaffold_report_path,
        cutover_packet_path=request.cutover_packet_path,
        implementation_plan_path=request.implementation_plan_path,
    )
