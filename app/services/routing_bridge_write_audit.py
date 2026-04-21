from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, func, select

from app.models.routing_bridge_write_audit import RoutingBridgeWriteAudit


ROUTING_BRIDGE_WRITE_AUDIT_SCHEMA_VERSION = "phase19-step38-v1"

ALLOWED_AUDIT_STATUSES = [
    "audit_schema_only",
    "planned_not_executed",
    "blocked",
    "dry_run",
    "future_live_write",
    "future_rollback",
]


def routing_bridge_write_audit_to_dict(audit: RoutingBridgeWriteAudit) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": audit.id,
        "audit_key": audit.audit_key,
        "rehearsal_idempotency_key": audit.rehearsal_idempotency_key,
        "draft_id": audit.draft_id,
        "draft_key": audit.draft_key,
        "preference_key": audit.preference_key,
        "phone": audit.phone,
        "mode": audit.mode,
        "owner_type": audit.owner_type,
        "label": audit.label,
        "bridge_endpoint": audit.bridge_endpoint,
        "bridge_method": audit.bridge_method,
        "status": audit.status,
        "bridge_post_called": audit.bridge_post_called,
        "bridge_mutation_performed": audit.bridge_mutation_performed,
        "platform_db_mutation_performed": audit.platform_db_mutation_performed,
        "lacrm_call_performed": audit.lacrm_call_performed,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "updated_at": audit.updated_at.isoformat() if audit.updated_at else None,
    }

    for field in (
        "request_payload_json",
        "previous_bridge_rule_json",
        "response_payload_json",
        "rollback_payload_json",
    ):
        target_name = field.replace("_json", "")
        try:
            payload[target_name] = json.loads(getattr(audit, field) or "{}")
        except json.JSONDecodeError:
            payload[target_name] = {"raw": getattr(audit, field)}

    return payload


def routing_bridge_write_audit_status(session: Session) -> dict[str, Any]:
    total = session.exec(select(func.count(RoutingBridgeWriteAudit.id))).one() or 0

    status_counts: dict[str, int] = {}
    for status, count in session.exec(
        select(RoutingBridgeWriteAudit.status, func.count(RoutingBridgeWriteAudit.id)).group_by(
            RoutingBridgeWriteAudit.status
        )
    ).all():
        status_counts[str(status or "unknown")] = int(count or 0)

    bridge_post_called = (
        session.exec(
            select(func.count(RoutingBridgeWriteAudit.id)).where(
                RoutingBridgeWriteAudit.bridge_post_called == True  # noqa: E712
            )
        ).one()
        or 0
    )

    bridge_mutations = (
        session.exec(
            select(func.count(RoutingBridgeWriteAudit.id)).where(
                RoutingBridgeWriteAudit.bridge_mutation_performed == True  # noqa: E712
            )
        ).one()
        or 0
    )

    return {
        "schema_version": ROUTING_BRIDGE_WRITE_AUDIT_SCHEMA_VERSION,
        "table": "routing_bridge_write_audits",
        "read_only": True,
        "audit_write_enabled": False,
        "audit_write_endpoint_implemented": False,
        "rollback_write_enabled": False,
        "rollback_write_endpoint_implemented": False,
        "bridge_post_enabled": False,
        "bridge_write_endpoint_implemented": False,
        "lacrm_call_enabled": False,
        "allowed_audit_statuses": ALLOWED_AUDIT_STATUSES,
        "total_audit_rows": int(total),
        "bridge_post_called_rows": int(bridge_post_called),
        "bridge_mutation_rows": int(bridge_mutations),
        "status_counts": status_counts,
    }


def list_routing_bridge_write_audits(session: Session, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    statement = (
        select(RoutingBridgeWriteAudit)
        .order_by(RoutingBridgeWriteAudit.updated_at.desc(), RoutingBridgeWriteAudit.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = session.exec(statement).all()

    return {
        "schema_version": ROUTING_BRIDGE_WRITE_AUDIT_SCHEMA_VERSION,
        "read_only": True,
        "limit": limit,
        "offset": offset,
        "audit_rows": [routing_bridge_write_audit_to_dict(row) for row in rows],
    }


def get_routing_bridge_write_audit(session: Session, audit_id: int) -> dict[str, Any] | None:
    audit = session.get(RoutingBridgeWriteAudit, audit_id)
    if audit is None:
        return None

    payload = routing_bridge_write_audit_to_dict(audit)
    payload["schema_version"] = ROUTING_BRIDGE_WRITE_AUDIT_SCHEMA_VERSION
    payload["read_only"] = True
    return payload


def preview_audit_from_rehearsal(rehearsal_row: dict[str, Any]) -> dict[str, Any]:
    payload = rehearsal_row.get("payload_preview") or {}
    source = rehearsal_row.get("source_preview_row") or {}

    if not isinstance(payload, dict):
        payload = {}
    if not isinstance(source, dict):
        source = {}

    issues: list[str] = []
    if rehearsal_row.get("blocked") is not True:
        issues.append("rehearsal_row_not_blocked")
    if rehearsal_row.get("would_call_bridge") is not False:
        issues.append("rehearsal_row_would_call_bridge")
    if rehearsal_row.get("target_bridge_endpoint") != "/api/routing-rules":
        issues.append("unexpected_bridge_endpoint")
    if rehearsal_row.get("http_method") != "POST":
        issues.append("unexpected_bridge_method")

    audit_preview = {
        "audit_key": f"{rehearsal_row.get('idempotency_key') or 'missing-idempotency'}|audit",
        "rehearsal_idempotency_key": rehearsal_row.get("idempotency_key") or "",
        "draft_id": source.get("draft_id"),
        "draft_key": source.get("draft_key") or "",
        "preference_key": source.get("preference_key") or "",
        "phone": payload.get("phone") or "",
        "mode": payload.get("mode") or "manual",
        "owner_type": payload.get("owner_type") or "unknown",
        "label": payload.get("label") or "",
        "bridge_endpoint": rehearsal_row.get("target_bridge_endpoint") or "/api/routing-rules",
        "bridge_method": rehearsal_row.get("http_method") or "POST",
        "status": "planned_not_executed",
        "request_payload": payload,
        "previous_bridge_rule": {},
        "response_payload": {},
        "rollback_payload": {
            "status": "not_available_until_previous_bridge_rule_is_captured",
            "reason": "Step 38 does not call bridge or capture live previous rule state.",
        },
    }

    return {
        "schema_version": ROUTING_BRIDGE_WRITE_AUDIT_SCHEMA_VERSION,
        "read_only": True,
        "preview_only": True,
        "audit_write_enabled": False,
        "audit_write_endpoint_implemented": False,
        "platform_db_mutation_performed": False,
        "bridge_mutation_performed": False,
        "bridge_post_called": False,
        "lacrm_call_performed": False,
        "would_create_future_audit_row": len(issues) == 0,
        "issues": issues,
        "audit_preview": audit_preview,
    }
