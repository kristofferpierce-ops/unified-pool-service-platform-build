from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter
from sqlmodel import Session

from app.core.database import engine
from app.services.routing_candidate_import import (
    preview_routing_candidate_import,
    routing_candidate_import_gate,
    run_routing_candidate_import,
)

router = APIRouter(prefix="/front-desk/routing", tags=["front-desk-routing-import"])


class RoutingCandidateImportRequest(BaseModel):
    plan_path: str
    dry_run: bool = True
    confirmation_phrase: str = ""


@router.get("/candidates/import/status")
def get_routing_candidate_import_status() -> dict:
    gate = routing_candidate_import_gate()
    return {
        **gate,
        "default_dry_run": True,
        "import_endpoint_available": True,
        "safe_default": "dry_run",
    }


@router.post("/candidates/import-plan")
def post_routing_candidate_import_plan(request: RoutingCandidateImportRequest) -> dict:
    with Session(engine) as session:
        if request.dry_run:
            return preview_routing_candidate_import(session, plan_path=request.plan_path)
        return run_routing_candidate_import(
            session,
            plan_path=request.plan_path,
            dry_run=False,
            confirmation_phrase=request.confirmation_phrase,
        )
