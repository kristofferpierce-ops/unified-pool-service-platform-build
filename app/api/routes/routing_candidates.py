from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session

from app.core.database import engine
from app.services.routing_candidates import (
    get_routing_candidate,
    list_routing_candidates,
    routing_candidate_status,
)

router = APIRouter(prefix="/front-desk/routing", tags=["front-desk-routing"])


@router.get("/candidates/status")
def get_candidate_status() -> dict:
    with Session(engine) as session:
        return routing_candidate_status(session)


@router.get("/candidates")
def get_candidates(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with Session(engine) as session:
        return list_routing_candidates(session, limit=limit, offset=offset)


@router.get("/candidates/{candidate_id}")
def get_candidate_detail(candidate_id: int) -> dict:
    with Session(engine) as session:
        candidate = get_routing_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Routing candidate not found")
        return candidate
