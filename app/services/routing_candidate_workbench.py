from __future__ import annotations

from typing import Any

from sqlmodel import Session, func, select

from app.models.routing_candidates import RoutingPreferenceCandidate
from app.services.routing_candidates import routing_candidate_to_dict


ROUTING_CANDIDATE_WORKBENCH_VERSION = "phase19-step32-v1"

ALLOWED_REVIEW_DECISIONS = [
    "unreviewed",
    "candidate_keep_manual",
    "needs_contact_verification",
    "needs_scope_review",
    "block_until_reviewed",
    "approved_for_future_dry_run_only",
    "skip",
]


def routing_candidate_workbench_status(session: Session) -> dict[str, Any]:
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

    blocker_counts: dict[str, int] = {}
    for blocker, count in session.exec(
        select(RoutingPreferenceCandidate.import_blocker, func.count(RoutingPreferenceCandidate.id)).group_by(
            RoutingPreferenceCandidate.import_blocker
        )
    ).all():
        blocker_counts[str(blocker or "blank")] = int(count or 0)

    return {
        "workbench_version": ROUTING_CANDIDATE_WORKBENCH_VERSION,
        "read_only": True,
        "review_preview_available": True,
        "review_write_endpoint_implemented": False,
        "candidate_review_write_enabled": False,
        "candidate_import_enabled": False,
        "bridge_post_enabled": False,
        "lacrm_call_enabled": False,
        "allowed_review_decisions": ALLOWED_REVIEW_DECISIONS,
        "total_candidates": int(total),
        "eligible_for_future_dry_run_import": int(eligible),
        "blocked_or_review_required": int(blocked),
        "risk_counts": risk_counts,
        "operator_decision_counts": decision_counts,
        "import_blocker_counts": blocker_counts,
    }


def list_candidate_workbench_queue(
    session: Session,
    *,
    limit: int = 250,
    offset: int = 0,
    only_eligible: bool | None = None,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    statement = select(RoutingPreferenceCandidate)

    if only_eligible is not None:
        statement = statement.where(RoutingPreferenceCandidate.eligible_for_future_dry_run_import == only_eligible)

    statement = statement.order_by(
        RoutingPreferenceCandidate.eligible_for_future_dry_run_import.desc(),
        RoutingPreferenceCandidate.risk_level.asc(),
        RoutingPreferenceCandidate.updated_at.desc(),
        RoutingPreferenceCandidate.id.desc(),
    ).offset(offset).limit(limit)

    rows = session.exec(statement).all()

    return {
        "workbench_version": ROUTING_CANDIDATE_WORKBENCH_VERSION,
        "read_only": True,
        "limit": limit,
        "offset": offset,
        "only_eligible": only_eligible,
        "candidates": [routing_candidate_to_dict(row) for row in rows],
    }


def preview_candidate_review(
    session: Session,
    *,
    candidate_id: int,
    operator_decision: str,
    operator_note: str = "",
) -> dict[str, Any]:
    candidate = session.get(RoutingPreferenceCandidate, candidate_id)
    decision = str(operator_decision or "").strip()

    issues: list[str] = []
    if candidate is None:
        issues.append("candidate_not_found")
    if decision not in ALLOWED_REVIEW_DECISIONS:
        issues.append("invalid_operator_decision")

    if candidate is not None and candidate.risk_level == "high" and decision == "approved_for_future_dry_run_only":
        issues.append("high_risk_candidate_cannot_be_approved_in_workbench")

    if candidate is not None and candidate.import_blocker == "auto_attach_missing_contact" and decision == "approved_for_future_dry_run_only":
        issues.append("auto_attach_missing_contact_cannot_be_approved_in_workbench")

    return {
        "workbench_version": ROUTING_CANDIDATE_WORKBENCH_VERSION,
        "read_only": True,
        "preview_only": True,
        "candidate_review_write_enabled": False,
        "platform_db_mutation_performed": False,
        "bridge_mutation_performed": False,
        "bridge_post_called": False,
        "lacrm_call_performed": False,
        "candidate_id": candidate_id,
        "operator_decision": decision,
        "operator_note_present": bool(str(operator_note or "").strip()),
        "would_accept_for_future_review_step": len(issues) == 0,
        "issues": issues,
        "candidate": routing_candidate_to_dict(candidate) if candidate is not None else None,
    }
