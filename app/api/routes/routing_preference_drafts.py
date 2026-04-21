from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session

from app.core.database import engine
from app.services.routing_preference_drafts import (
    get_routing_preference_draft,
    list_routing_preference_drafts,
    preview_draft_from_candidate,
    routing_preference_draft_status,
)

router = APIRouter(prefix="/front-desk/routing/preference-drafts", tags=["front-desk-routing-drafts"])


@router.get("/status")
def get_preference_draft_status() -> dict:
    with Session(engine) as session:
        return routing_preference_draft_status(session)


@router.get("")
def get_preference_drafts(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with Session(engine) as session:
        return list_routing_preference_drafts(session, limit=limit, offset=offset)


@router.get("/{draft_id}")
def get_preference_draft_detail(draft_id: int) -> dict:
    with Session(engine) as session:
        draft = get_routing_preference_draft(session, draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Routing preference draft not found")
        return draft


@router.post("/from-candidate-preview/{candidate_id}")
def post_preference_draft_from_candidate_preview(candidate_id: int) -> dict:
    with Session(engine) as session:
        return preview_draft_from_candidate(session, candidate_id=candidate_id)
