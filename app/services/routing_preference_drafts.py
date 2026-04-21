from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, func, select

from app.models.routing_candidates import RoutingPreferenceCandidate
from app.models.routing_preference_drafts import RoutingPreferenceDraft


ROUTING_PREFERENCE_DRAFT_SCHEMA_VERSION = "phase19-step34-v1"

ALLOWED_DRAFT_STATUSES = [
    "draft_schema_only",
    "candidate_ready_for_future_draft",
    "blocked_needs_review",
    "skipped",
]


def routing_preference_draft_to_dict(draft: RoutingPreferenceDraft) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": draft.id,
        "draft_key": draft.draft_key,
        "candidate_id": draft.candidate_id,
        "preference_key": draft.preference_key,
        "phone": draft.phone,
        "mode": draft.mode,
        "owner_type": draft.owner_type,
        "label": draft.label,
        "default_contact_count": draft.default_contact_count,
        "status": draft.status,
        "approval_source": draft.approval_source,
        "operator_decision": draft.operator_decision,
        "risk_level": draft.risk_level,
        "write_status": draft.write_status,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
    }

    for source_field in ("source_candidate_json", "source_reconciliation_json"):
        try:
            payload[source_field.replace("_json", "")] = json.loads(getattr(draft, source_field) or "{}")
        except json.JSONDecodeError:
            payload[source_field.replace("_json", "")] = {"raw": getattr(draft, source_field)}

    return payload


def routing_preference_draft_status(session: Session) -> dict[str, Any]:
    total = session.exec(select(func.count(RoutingPreferenceDraft.id))).one() or 0

    status_counts: dict[str, int] = {}
    for status, count in session.exec(
        select(RoutingPreferenceDraft.status, func.count(RoutingPreferenceDraft.id)).group_by(
            RoutingPreferenceDraft.status
        )
    ).all():
        status_counts[str(status or "unknown")] = int(count or 0)

    mode_counts: dict[str, int] = {}
    for mode, count in session.exec(
        select(RoutingPreferenceDraft.mode, func.count(RoutingPreferenceDraft.id)).group_by(
            RoutingPreferenceDraft.mode
        )
    ).all():
        mode_counts[str(mode or "unknown")] = int(count or 0)

    owner_type_counts: dict[str, int] = {}
    for owner_type, count in session.exec(
        select(RoutingPreferenceDraft.owner_type, func.count(RoutingPreferenceDraft.id)).group_by(
            RoutingPreferenceDraft.owner_type
        )
    ).all():
        owner_type_counts[str(owner_type or "unknown")] = int(count or 0)

    return {
        "schema_version": ROUTING_PREFERENCE_DRAFT_SCHEMA_VERSION,
        "table": "routing_preference_drafts",
        "read_only": True,
        "draft_creation_enabled": False,
        "draft_write_endpoint_implemented": False,
        "bridge_post_enabled": False,
        "lacrm_call_enabled": False,
        "routing_write_endpoint_implemented": False,
        "allowed_draft_statuses": ALLOWED_DRAFT_STATUSES,
        "total_drafts": int(total),
        "status_counts": status_counts,
        "mode_counts": mode_counts,
        "owner_type_counts": owner_type_counts,
    }


def list_routing_preference_drafts(session: Session, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    statement = (
        select(RoutingPreferenceDraft)
        .order_by(RoutingPreferenceDraft.updated_at.desc(), RoutingPreferenceDraft.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = session.exec(statement).all()

    return {
        "schema_version": ROUTING_PREFERENCE_DRAFT_SCHEMA_VERSION,
        "read_only": True,
        "limit": limit,
        "offset": offset,
        "drafts": [routing_preference_draft_to_dict(row) for row in rows],
    }


def get_routing_preference_draft(session: Session, draft_id: int) -> dict[str, Any] | None:
    draft = session.get(RoutingPreferenceDraft, draft_id)
    if draft is None:
        return None

    payload = routing_preference_draft_to_dict(draft)
    payload["schema_version"] = ROUTING_PREFERENCE_DRAFT_SCHEMA_VERSION
    payload["read_only"] = True
    return payload


def preview_draft_from_candidate(session: Session, *, candidate_id: int) -> dict[str, Any]:
    candidate = session.get(RoutingPreferenceCandidate, candidate_id)

    issues: list[str] = []
    if candidate is None:
        issues.append("candidate_not_found")
    else:
        if not candidate.eligible_for_future_dry_run_import:
            issues.append("candidate_not_eligible_for_future_dry_run_import")
        if candidate.operator_decision != "approved_for_future_dry_run_only":
            issues.append("candidate_not_approved_for_future_draft")
        if candidate.risk_level == "high":
            issues.append("high_risk_candidate_cannot_become_draft")

    draft_preview: dict[str, Any] | None = None
    if candidate is not None:
        draft_preview = {
            "draft_key": f"{candidate.preference_key}|draft",
            "candidate_id": candidate.id,
            "preference_key": candidate.preference_key,
            "phone": candidate.phone,
            "mode": candidate.proposed_mode,
            "owner_type": candidate.proposed_owner_type,
            "label": "",
            "default_contact_count": 0,
            "status": "candidate_ready_for_future_draft" if not issues else "blocked_needs_review",
            "approval_source": "routing_candidate_workbench",
            "operator_decision": candidate.operator_decision,
            "risk_level": candidate.risk_level,
            "write_status": "draft_preview_only_no_write",
        }

    return {
        "schema_version": ROUTING_PREFERENCE_DRAFT_SCHEMA_VERSION,
        "read_only": True,
        "preview_only": True,
        "draft_creation_enabled": False,
        "draft_write_endpoint_implemented": False,
        "platform_db_mutation_performed": False,
        "bridge_mutation_performed": False,
        "bridge_post_called": False,
        "lacrm_call_performed": False,
        "candidate_id": candidate_id,
        "would_create_future_draft": candidate is not None and len(issues) == 0,
        "issues": issues,
        "draft_preview": draft_preview,
    }
