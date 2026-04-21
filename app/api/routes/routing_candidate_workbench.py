from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Query
from sqlmodel import Session

from app.core.database import engine
from app.services.routing_candidate_workbench import (
    list_candidate_workbench_queue,
    preview_candidate_review,
    routing_candidate_workbench_status,
)

router = APIRouter(prefix="/front-desk/routing/candidate-workbench", tags=["front-desk-routing-workbench"])


class CandidateReviewPreviewRequest(BaseModel):
    operator_decision: str
    operator_note: str = ""


@router.get("/status")
def get_routing_candidate_workbench_status() -> dict:
    with Session(engine) as session:
        return routing_candidate_workbench_status(session)


@router.get("/queue")
def get_routing_candidate_workbench_queue(
    limit: int = Query(default=250, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    only_eligible: bool | None = Query(default=None),
) -> dict:
    with Session(engine) as session:
        return list_candidate_workbench_queue(session, limit=limit, offset=offset, only_eligible=only_eligible)


@router.post("/{candidate_id}/review-preview")
def post_routing_candidate_review_preview(candidate_id: int, request: CandidateReviewPreviewRequest) -> dict:
    with Session(engine) as session:
        return preview_candidate_review(
            session,
            candidate_id=candidate_id,
            operator_decision=request.operator_decision,
            operator_note=request.operator_note,
        )
