from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, func, select

from app.models.routing_candidates import RoutingPreferenceCandidate


ROUTING_CANDIDATE_SCHEMA_VERSION = "phase19-step29-v1"


def routing_candidate_to_dict(candidate: RoutingPreferenceCandidate) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": candidate.id,
        "preference_key": candidate.preference_key,
        "phone": candidate.phone,
        "proposed_mode": candidate.proposed_mode,
        "proposed_owner_type": candidate.proposed_owner_type,
        "risk_level": candidate.risk_level,
        "proposed_action": candidate.proposed_action,
        "operator_decision": candidate.operator_decision,
        "import_blocker": candidate.import_blocker,
        "eligible_for_future_dry_run_import": candidate.eligible_for_future_dry_run_import,
        "write_status": candidate.write_status,
        "source_plan_path": candidate.source_plan_path,
        "source_preference_key": candidate.source_preference_key,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
    }

    try:
        payload["source_row"] = json.loads(candidate.source_row_json or "{}")
    except json.JSONDecodeError:
        payload["source_row"] = {"raw": candidate.source_row_json}

    return payload


def routing_candidate_status(session: Session) -> dict[str, Any]:
    total = session.exec(select(func.count(RoutingPreferenceCandidate.id))).one() or 0
    eligible = (
        session.exec(
            select(func.count(RoutingPreferenceCandidate.id)).where(
                RoutingPreferenceCandidate.eligible_for_future_dry_run_import == True  # noqa: E712
            )
        ).one()
        or 0
    )
    blocked = int(total) - int(eligible)

    risk_counts: dict[str, int] = {}
    for risk, count in session.exec(
        select(RoutingPreferenceCandidate.risk_level, func.count(RoutingPreferenceCandidate.id)).group_by(
            RoutingPreferenceCandidate.risk_level
        )
    ).all():
        risk_counts[str(risk or "unknown")] = int(count or 0)

    decision_counts: dict[str, int] = {}
    for decision, count in session.exec(
        select(RoutingPreferenceCandidate.operator_decision, func.count(RoutingPreferenceCandidate.id)).group_by(
            RoutingPreferenceCandidate.operator_decision
        )
    ).all():
        decision_counts[str(decision or "unknown")] = int(count or 0)

    return {
        "schema_version": ROUTING_CANDIDATE_SCHEMA_VERSION,
        "table": "routing_preference_candidates",
        "read_only": True,
        "candidate_import_enabled": False,
        "routing_write_endpoint_implemented": False,
        "bridge_post_enabled": False,
        "lacrm_call_enabled": False,
        "total_candidates": int(total),
        "eligible_for_future_dry_run_import": int(eligible),
        "blocked_or_review_required": int(blocked),
        "risk_counts": risk_counts,
        "operator_decision_counts": decision_counts,
    }


def list_routing_candidates(session: Session, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    statement = (
        select(RoutingPreferenceCandidate)
        .order_by(RoutingPreferenceCandidate.updated_at.desc(), RoutingPreferenceCandidate.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = session.exec(statement).all()

    return {
        "schema_version": ROUTING_CANDIDATE_SCHEMA_VERSION,
        "read_only": True,
        "limit": limit,
        "offset": offset,
        "candidates": [routing_candidate_to_dict(row) for row in rows],
    }


def get_routing_candidate(session: Session, candidate_id: int) -> dict[str, Any] | None:
    candidate = session.get(RoutingPreferenceCandidate, candidate_id)
    if candidate is None:
        return None

    payload = routing_candidate_to_dict(candidate)
    payload["schema_version"] = ROUTING_CANDIDATE_SCHEMA_VERSION
    payload["read_only"] = True
    return payload
