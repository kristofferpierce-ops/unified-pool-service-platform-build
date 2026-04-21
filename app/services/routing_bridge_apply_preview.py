from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlmodel import Session, func, select

from app.models.routing_preference_drafts import RoutingPreferenceDraft
from app.services.routing_preference_drafts import routing_preference_draft_to_dict


ROUTING_BRIDGE_APPLY_PREVIEW_VERSION = "phase19-step35-v1"


def _idempotency_key_for_draft(draft: RoutingPreferenceDraft) -> str:
    seed = {
        "draft_key": draft.draft_key,
        "phone": draft.phone,
        "mode": draft.mode,
        "owner_type": draft.owner_type,
        "label": draft.label,
        "default_contact_count": draft.default_contact_count,
    }
    encoded = json.dumps(seed, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"routing-draft-{draft.id or 'new'}-{digest}"


def _draft_to_bridge_payload_preview(draft: RoutingPreferenceDraft) -> dict[str, Any]:
    return {
        "phone": draft.phone,
        "mode": draft.mode,
        "owner_type": draft.owner_type,
        "label": draft.label,
        "default_contact_ids": [],
        "notes": f"Preview only from platform draft {draft.draft_key}",
    }


def routing_bridge_apply_preview_status(session: Session) -> dict[str, Any]:
    total_drafts = session.exec(select(func.count(RoutingPreferenceDraft.id))).one() or 0
    previewable_drafts = (
        session.exec(
            select(func.count(RoutingPreferenceDraft.id)).where(
                RoutingPreferenceDraft.status == "candidate_ready_for_future_draft"
            )
        ).one()
        or 0
    )

    status_counts: dict[str, int] = {}
    for status, count in session.exec(
        select(RoutingPreferenceDraft.status, func.count(RoutingPreferenceDraft.id)).group_by(
            RoutingPreferenceDraft.status
        )
    ).all():
        status_counts[str(status or "unknown")] = int(count or 0)

    return {
        "preview_version": ROUTING_BRIDGE_APPLY_PREVIEW_VERSION,
        "read_only": True,
        "preview_only": True,
        "bridge_apply_preview_available": True,
        "bridge_apply_enabled": False,
        "bridge_apply_armed": False,
        "bridge_post_called": False,
        "bridge_write_endpoint_implemented": False,
        "platform_db_mutation_performed": False,
        "lacrm_call_enabled": False,
        "lacrm_call_performed": False,
        "total_drafts": int(total_drafts),
        "previewable_drafts": int(previewable_drafts),
        "status_counts": status_counts,
    }


def list_routing_bridge_apply_preview(
    session: Session,
    *,
    limit: int = 250,
    offset: int = 0,
    include_blocked: bool = True,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    statement = select(RoutingPreferenceDraft)
    if not include_blocked:
        statement = statement.where(RoutingPreferenceDraft.status == "candidate_ready_for_future_draft")

    statement = statement.order_by(
        RoutingPreferenceDraft.status.asc(),
        RoutingPreferenceDraft.updated_at.desc(),
        RoutingPreferenceDraft.id.desc(),
    ).offset(offset).limit(limit)

    drafts = session.exec(statement).all()
    rows: list[dict[str, Any]] = []

    for draft in drafts:
        issues: list[str] = []
        if draft.status != "candidate_ready_for_future_draft":
            issues.append("draft_status_not_ready")
        if draft.risk_level == "high":
            issues.append("high_risk_draft_not_previewable")
        if not draft.phone:
            issues.append("missing_phone")
        if draft.write_status not in {"draft_schema_only_no_write", "draft_preview_only_no_write"}:
            issues.append("unexpected_write_status")

        rows.append(
            {
                "draft_id": draft.id,
                "draft_key": draft.draft_key,
                "preference_key": draft.preference_key,
                "phone": draft.phone,
                "mode": draft.mode,
                "owner_type": draft.owner_type,
                "label": draft.label,
                "status": draft.status,
                "risk_level": draft.risk_level,
                "operator_decision": draft.operator_decision,
                "would_call_bridge": False,
                "would_write_platform": False,
                "previewable": len(issues) == 0,
                "issues": issues,
                "idempotency_key": _idempotency_key_for_draft(draft),
                "target_bridge_endpoint": "/api/routing-rules",
                "http_method": "POST",
                "bridge_payload_preview": _draft_to_bridge_payload_preview(draft),
                "source_draft": routing_preference_draft_to_dict(draft),
            }
        )

    action_counts: dict[str, int] = {"would_preview": 0, "blocked": 0}
    for row in rows:
        if row["previewable"]:
            action_counts["would_preview"] += 1
        else:
            action_counts["blocked"] += 1

    return {
        "preview_version": ROUTING_BRIDGE_APPLY_PREVIEW_VERSION,
        "read_only": True,
        "preview_only": True,
        "bridge_post_called": False,
        "bridge_write_endpoint_implemented": False,
        "platform_db_mutation_performed": False,
        "lacrm_call_performed": False,
        "limit": limit,
        "offset": offset,
        "include_blocked": include_blocked,
        "action_counts": action_counts,
        "preview_rows": rows,
    }
