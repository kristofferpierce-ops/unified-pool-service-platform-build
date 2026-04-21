from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.models.routing_candidates import RoutingPreferenceCandidate


REQUIRED_IMPORT_CONFIRMATION = "IMPORT ROUTING CANDIDATES"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def routing_candidate_import_gate() -> dict[str, Any]:
    enabled = _truthy(os.getenv("PLATFORM_ROUTING_CANDIDATE_IMPORT_ENABLED"))
    armed = _truthy(os.getenv("PLATFORM_ROUTING_CANDIDATE_IMPORT_ARMED"))
    return {
        "candidate_import_enabled": enabled,
        "candidate_import_armed": armed,
        "required_confirmation_phrase": REQUIRED_IMPORT_CONFIRMATION,
        "bridge_post_enabled": False,
        "lacrm_call_enabled": False,
        "routing_write_endpoint_implemented": False,
    }


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _candidate_payload_from_row(row: dict[str, Any], *, source_plan_path: str) -> dict[str, Any]:
    source_json = json.dumps(row, sort_keys=True, default=str)
    now = datetime.now(timezone.utc)
    return {
        "preference_key": _normalize(row.get("preference_key")),
        "phone": _normalize(row.get("phone")),
        "proposed_mode": _normalize(row.get("proposed_mode") or "manual"),
        "proposed_owner_type": _normalize(row.get("proposed_owner_type") or "unknown"),
        "risk_level": _normalize(row.get("risk_level") or "unknown"),
        "proposed_action": _normalize(row.get("proposed_action")),
        "operator_decision": _normalize(row.get("operator_decision") or "unreviewed"),
        "import_blocker": _normalize(row.get("import_blocker")),
        "eligible_for_future_dry_run_import": bool(row.get("eligible_for_future_dry_run_import")),
        "write_status": "imported_from_plan_disabled_by_default",
        "source_plan_path": source_plan_path,
        "source_preference_key": _normalize(row.get("preference_key")),
        "source_row_json": source_json,
        "updated_at": now,
    }


def load_routing_import_plan(plan_path: str | Path) -> dict[str, Any]:
    path = Path(plan_path)
    if not path.exists():
        raise FileNotFoundError(f"Routing import plan not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _classify_row(session: Session, row: dict[str, Any], *, source_plan_path: str) -> dict[str, Any]:
    key = _normalize(row.get("preference_key"))
    eligible = bool(row.get("eligible_for_future_dry_run_import"))

    if not eligible:
        return {
            "preference_key": key,
            "phone": _normalize(row.get("phone")),
            "eligible_for_future_dry_run_import": False,
            "action": "blocked",
            "reason": _normalize(row.get("import_blocker")) or "not eligible for future dry-run import",
            "existing_candidate_id": None,
            "diffs": [],
        }

    existing = session.exec(
        select(RoutingPreferenceCandidate).where(RoutingPreferenceCandidate.preference_key == key)
    ).first()

    payload = _candidate_payload_from_row(row, source_plan_path=source_plan_path)

    if existing is None:
        return {
            "preference_key": key,
            "phone": payload["phone"],
            "eligible_for_future_dry_run_import": True,
            "action": "would_create",
            "reason": "eligible row does not exist in platform candidate table",
            "existing_candidate_id": None,
            "diffs": [],
        }

    diffs: list[dict[str, Any]] = []
    for field in [
        "phone",
        "proposed_mode",
        "proposed_owner_type",
        "risk_level",
        "proposed_action",
        "operator_decision",
        "import_blocker",
        "eligible_for_future_dry_run_import",
    ]:
        existing_value = getattr(existing, field)
        planned_value = payload[field]
        if existing_value != planned_value:
            diffs.append({"field": field, "existing": existing_value, "planned": planned_value})

    if diffs:
        return {
            "preference_key": key,
            "phone": payload["phone"],
            "eligible_for_future_dry_run_import": True,
            "action": "would_update",
            "reason": "eligible row exists but differs from import plan",
            "existing_candidate_id": existing.id,
            "diffs": diffs,
        }

    return {
        "preference_key": key,
        "phone": payload["phone"],
        "eligible_for_future_dry_run_import": True,
        "action": "would_skip_existing",
        "reason": "eligible row already matches import plan",
        "existing_candidate_id": existing.id,
        "diffs": [],
    }


def preview_routing_candidate_import(session: Session, *, plan_path: str | Path) -> dict[str, Any]:
    plan = load_routing_import_plan(plan_path)
    rows = plan.get("import_plan_rows") or []
    source_path = str(plan_path)

    import_rows = [_classify_row(session, row, source_plan_path=source_path) for row in rows]

    action_counts: dict[str, int] = {}
    for row in import_rows:
        action = str(row.get("action") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "phase": "Phase 19 Step 31",
        "source_routing_import_plan": source_path,
        "dry_run": True,
        "preview_only": True,
        "safety": {
            "candidate_import_enabled": routing_candidate_import_gate()["candidate_import_enabled"],
            "candidate_import_armed": routing_candidate_import_gate()["candidate_import_armed"],
            "candidate_import_performed": False,
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "routing_write_endpoint_implemented": False,
        },
        "counts": {
            "plan_rows": len(rows),
            "import_rows": len(import_rows),
            "action_counts": action_counts,
        },
        "import_rows": import_rows,
    }


def run_routing_candidate_import(
    session: Session,
    *,
    plan_path: str | Path,
    dry_run: bool = True,
    confirmation_phrase: str = "",
) -> dict[str, Any]:
    gate = routing_candidate_import_gate()
    preview = preview_routing_candidate_import(session, plan_path=plan_path)

    blockers: list[str] = []
    if not gate["candidate_import_enabled"]:
        blockers.append("PLATFORM_ROUTING_CANDIDATE_IMPORT_ENABLED is not true.")
    if not gate["candidate_import_armed"]:
        blockers.append("PLATFORM_ROUTING_CANDIDATE_IMPORT_ARMED is not true.")
    if confirmation_phrase != REQUIRED_IMPORT_CONFIRMATION:
        blockers.append("Typed routing candidate import confirmation phrase is required.")

    if dry_run or blockers:
        preview["dry_run"] = bool(dry_run)
        preview["preview_only"] = True
        preview["blocked"] = bool(blockers and not dry_run)
        preview["blockers"] = blockers
        preview["safety"].update(
            {
                "candidate_import_enabled": gate["candidate_import_enabled"],
                "candidate_import_armed": gate["candidate_import_armed"],
                "candidate_import_performed": False,
                "platform_db_mutation_performed": False,
            }
        )
        return preview

    created = 0
    updated = 0
    skipped = 0
    plan = load_routing_import_plan(plan_path)
    source_path = str(plan_path)

    for row in plan.get("import_plan_rows") or []:
        classified = _classify_row(session, row, source_plan_path=source_path)
        if classified["action"] == "blocked":
            continue

        payload = _candidate_payload_from_row(row, source_plan_path=source_path)
        existing = session.exec(
            select(RoutingPreferenceCandidate).where(
                RoutingPreferenceCandidate.preference_key == payload["preference_key"]
            )
        ).first()

        if existing is None:
            candidate = RoutingPreferenceCandidate(**payload)
            session.add(candidate)
            created += 1
        else:
            changed = False
            for field, value in payload.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                updated += 1
            else:
                skipped += 1

    session.commit()

    result = preview_routing_candidate_import(session, plan_path=plan_path)
    result["dry_run"] = False
    result["preview_only"] = False
    result["blocked"] = False
    result["blockers"] = []
    result["safety"].update(
        {
            "candidate_import_enabled": gate["candidate_import_enabled"],
            "candidate_import_armed": gate["candidate_import_armed"],
            "candidate_import_performed": True,
            "platform_db_mutation_performed": True,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
        }
    )
    result["execution"] = {"created": created, "updated": updated, "skipped": skipped}
    return result
