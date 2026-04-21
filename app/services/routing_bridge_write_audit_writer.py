from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.models.routing_bridge_write_audit import RoutingBridgeWriteAudit


ROUTING_BRIDGE_WRITE_AUDIT_WRITER_VERSION = "phase19-step40-v1"
REQUIRED_AUDIT_WRITE_CONFIRMATION = "CREATE BRIDGE ROUTING AUDIT ROWS"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_audit_writer_gate() -> dict[str, Any]:
    enabled = _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ENABLED"))
    armed = _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ARMED"))
    return {
        "writer_version": ROUTING_BRIDGE_WRITE_AUDIT_WRITER_VERSION,
        "safe_default": "dry_run",
        "audit_write_enabled": enabled,
        "audit_write_armed": armed,
        "required_confirmation_phrase": REQUIRED_AUDIT_WRITE_CONFIRMATION,
        "audit_writer_endpoint_available": True,
        "bridge_post_enabled": False,
        "bridge_post_call_implemented": False,
        "bridge_post_called": False,
        "bridge_mutation_performed": False,
        "lacrm_call_enabled": False,
        "lacrm_call_performed": False,
        "routing_write_endpoint_implemented": False,
    }


def load_bridge_routing_audit_plan(plan_path: str | Path) -> dict[str, Any]:
    path = Path(plan_path)
    if not path.exists():
        raise FileNotFoundError(f"Bridge routing write audit plan not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, sort_keys=True, default=str)


def _normalized(value: Any) -> str:
    return str(value or "").strip()


def _audit_payload_from_plan_row(row: dict[str, Any]) -> dict[str, Any] | None:
    preview = row.get("preview") or {}
    if not isinstance(preview, dict):
        return None

    audit_preview = preview.get("audit_preview") or {}
    if not isinstance(audit_preview, dict):
        return None

    audit_key = _normalized(audit_preview.get("audit_key"))
    if not audit_key:
        return None

    now = datetime.now(timezone.utc)

    return {
        "audit_key": audit_key,
        "rehearsal_idempotency_key": _normalized(audit_preview.get("rehearsal_idempotency_key")),
        "draft_id": audit_preview.get("draft_id"),
        "draft_key": _normalized(audit_preview.get("draft_key")),
        "preference_key": _normalized(audit_preview.get("preference_key")),
        "phone": _normalized(audit_preview.get("phone")),
        "mode": _normalized(audit_preview.get("mode") or "manual"),
        "owner_type": _normalized(audit_preview.get("owner_type") or "unknown"),
        "label": _normalized(audit_preview.get("label")),
        "bridge_endpoint": _normalized(audit_preview.get("bridge_endpoint") or "/api/routing-rules"),
        "bridge_method": _normalized(audit_preview.get("bridge_method") or "POST"),
        "status": "planned_not_executed",
        "request_payload_json": _as_json(audit_preview.get("request_payload")),
        "previous_bridge_rule_json": _as_json(audit_preview.get("previous_bridge_rule")),
        "response_payload_json": _as_json(audit_preview.get("response_payload")),
        "rollback_payload_json": _as_json(audit_preview.get("rollback_payload")),
        "bridge_post_called": False,
        "bridge_mutation_performed": False,
        "platform_db_mutation_performed": False,
        "lacrm_call_performed": False,
        "updated_at": now,
    }


def _classify_plan_row(session: Session, row: dict[str, Any]) -> dict[str, Any]:
    payload = _audit_payload_from_plan_row(row)
    plan_action = _normalized(row.get("plan_action"))
    issues = list(row.get("issues") or [])

    if payload is None:
        return {
            "audit_key": _normalized(row.get("audit_key")),
            "action": "would_block",
            "reason": "missing_audit_preview_payload",
            "existing_audit_id": None,
            "issues": ["missing_audit_preview_payload"],
        }

    existing = session.exec(
        select(RoutingBridgeWriteAudit).where(RoutingBridgeWriteAudit.audit_key == payload["audit_key"])
    ).first()

    if existing is not None:
        return {
            "audit_key": payload["audit_key"],
            "action": "would_skip_existing_audit_row",
            "reason": "matching audit row already exists",
            "existing_audit_id": existing.id,
            "issues": [],
        }

    if plan_action != "would_create_audit_row":
        return {
            "audit_key": payload["audit_key"],
            "action": "would_block",
            "reason": plan_action or "plan row is not eligible to create an audit row",
            "existing_audit_id": None,
            "issues": issues,
        }

    if issues:
        return {
            "audit_key": payload["audit_key"],
            "action": "would_block",
            "reason": "audit preview has issues",
            "existing_audit_id": None,
            "issues": issues,
        }

    return {
        "audit_key": payload["audit_key"],
        "action": "would_create_audit_row",
        "reason": "eligible audit row does not exist",
        "existing_audit_id": None,
        "issues": [],
    }


def preview_bridge_routing_audit_write(session: Session, *, plan_path: str | Path) -> dict[str, Any]:
    plan = load_bridge_routing_audit_plan(plan_path)
    rows = plan.get("plan_rows") or []

    write_rows: list[dict[str, Any]] = []
    for row in rows:
        row_dict = row if isinstance(row, dict) else {}
        classified = _classify_plan_row(session, row_dict)
        payload = _audit_payload_from_plan_row(row_dict)
        classified["payload_preview"] = payload
        write_rows.append(classified)

    action_counts: dict[str, int] = {}
    for row in write_rows:
        action = str(row.get("action") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1

    gate = bridge_routing_audit_writer_gate()

    return {
        "phase": "Phase 19 Step 40",
        "source_audit_plan": str(plan_path),
        "dry_run": True,
        "preview_only": True,
        "blocked": False,
        "blockers": [],
        "safety": {
            "audit_write_enabled": gate["audit_write_enabled"],
            "audit_write_armed": gate["audit_write_armed"],
            "audit_write_performed": False,
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
        },
        "counts": {
            "plan_rows": len(rows),
            "write_rows": len(write_rows),
            "action_counts": action_counts,
        },
        "write_rows": write_rows,
    }


def run_bridge_routing_audit_write(
    session: Session,
    *,
    plan_path: str | Path,
    dry_run: bool = True,
    confirmation_phrase: str = "",
) -> dict[str, Any]:
    gate = bridge_routing_audit_writer_gate()
    preview = preview_bridge_routing_audit_write(session, plan_path=plan_path)

    blockers: list[str] = []
    if not gate["audit_write_enabled"]:
        blockers.append("PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ENABLED is not true.")
    if not gate["audit_write_armed"]:
        blockers.append("PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ARMED is not true.")
    if confirmation_phrase != REQUIRED_AUDIT_WRITE_CONFIRMATION:
        blockers.append("Typed bridge routing audit write confirmation phrase is required.")

    if dry_run or blockers:
        preview["dry_run"] = bool(dry_run)
        preview["preview_only"] = True
        preview["blocked"] = bool(blockers and not dry_run)
        preview["blockers"] = blockers
        preview["safety"].update(
            {
                "audit_write_enabled": gate["audit_write_enabled"],
                "audit_write_armed": gate["audit_write_armed"],
                "audit_write_performed": False,
                "platform_db_mutation_performed": False,
                "bridge_mutation_performed": False,
                "bridge_post_called": False,
                "lacrm_call_performed": False,
            }
        )
        return preview

    plan = load_bridge_routing_audit_plan(plan_path)
    created = 0
    skipped = 0
    blocked = 0

    for row in plan.get("plan_rows") or []:
        row_dict = row if isinstance(row, dict) else {}
        classified = _classify_plan_row(session, row_dict)
        if classified["action"] == "would_create_audit_row":
            payload = _audit_payload_from_plan_row(row_dict)
            if payload is None:
                blocked += 1
                continue
            audit = RoutingBridgeWriteAudit(**payload)
            session.add(audit)
            created += 1
        elif classified["action"] == "would_skip_existing_audit_row":
            skipped += 1
        else:
            blocked += 1

    session.commit()

    result = preview_bridge_routing_audit_write(session, plan_path=plan_path)
    result["dry_run"] = False
    result["preview_only"] = False
    result["blocked"] = False
    result["blockers"] = []
    result["safety"].update(
        {
            "audit_write_enabled": gate["audit_write_enabled"],
            "audit_write_armed": gate["audit_write_armed"],
            "audit_write_performed": True,
            "platform_db_mutation_performed": True,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
        }
    )
    result["execution"] = {
        "created": created,
        "skipped_existing": skipped,
        "blocked": blocked,
    }
    return result
