from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROUTING_BRIDGE_WRITE_EXECUTOR_VERSION = "phase19-step45-v1"
REQUIRED_BRIDGE_WRITE_CONFIRMATION = "WRITE BRIDGE ROUTING"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_write_executor_gate() -> dict[str, Any]:
    enabled = _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED"))
    armed = _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED"))
    admin_token_configured = bool(str(os.getenv("PLATFORM_BRIDGE_ADMIN_TOKEN") or "").strip())

    return {
        "executor_version": ROUTING_BRIDGE_WRITE_EXECUTOR_VERSION,
        "safe_default": "dry_run_blocked",
        "bridge_routing_write_enabled": enabled,
        "bridge_routing_write_armed": armed,
        "bridge_admin_token_configured": admin_token_configured,
        "required_confirmation_phrase": REQUIRED_BRIDGE_WRITE_CONFIRMATION,
        "default_dry_run": True,
        "bridge_post_call_implemented": False,
        "bridge_post_called": False,
        "bridge_mutation_performed": False,
        "platform_db_mutation_performed": False,
        "lacrm_call_performed": False,
        "routing_write_endpoint_implemented": False,
        "live_write_enabled": False,
    }


def load_json_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")
    return json.loads(artifact_path.read_text(encoding="utf-8-sig"))


def _normalized(value: Any) -> str:
    return str(value or "").strip()


def _extract_plan_items(implementation_plan: dict[str, Any]) -> list[dict[str, Any]]:
    items = implementation_plan.get("plan_items") or []
    return [item for item in items if isinstance(item, dict)]


def _extract_future_gates(implementation_plan: dict[str, Any]) -> list[str]:
    plan = implementation_plan.get("implementation_plan") or {}
    gates = plan.get("required_future_gates") or []
    return [str(gate) for gate in gates]


def _readiness_allows_scaffold(implementation_plan: dict[str, Any]) -> bool:
    plan = implementation_plan.get("implementation_plan") or {}
    return bool(plan.get("can_add_guarded_write_scaffold_next"))


def _build_request_envelope(implementation_plan: dict[str, Any], cutover_packet: dict[str, Any] | None) -> dict[str, Any]:
    contract = {
        "target_bridge_endpoint": "/api/routing-rules",
        "http_method": "POST",
        "payload_fields": [
            "phone",
            "mode",
            "owner_type",
            "label",
            "default_contact_ids",
            "notes",
        ],
    }

    if cutover_packet:
        packet = cutover_packet.get("cutover_packet") or {}
        contract["future_confirmation_phrase"] = packet.get("future_confirmation_phrase") or REQUIRED_BRIDGE_WRITE_CONFIRMATION
        contract["operator_signoff_required"] = bool(packet.get("operator_signoff_required", True))

    return {
        "contract": contract,
        "future_request_shape": {
            "headers": {
                "Authorization": "Bearer <PLATFORM_BRIDGE_ADMIN_TOKEN>",
                "Idempotency-Key": "<audit/rehearsal idempotency key>",
                "Content-Type": "application/json",
            },
            "body": {
                "phone": "<phone>",
                "mode": "<manual|auto>",
                "owner_type": "<unknown|homeowner|property_manager>",
                "label": "<optional label>",
                "default_contact_ids": [],
                "notes": "<operator/audit note>",
            },
        },
        "source_plan_status": (implementation_plan.get("implementation_plan") or {}).get("status", "unknown"),
    }


def preview_bridge_routing_write_execution(
    *,
    implementation_plan_path: str | Path,
    cutover_packet_path: str | Path | None = None,
    dry_run: bool = True,
    confirmation_phrase: str = "",
) -> dict[str, Any]:
    gate = bridge_routing_write_executor_gate()
    implementation_plan = load_json_artifact(implementation_plan_path)
    cutover_packet = load_json_artifact(cutover_packet_path) if cutover_packet_path else None

    blockers: list[str] = []
    review_items: list[str] = []

    if not dry_run:
        blockers.append("Step 45 does not permit non-dry-run execution.")

    if not gate["bridge_routing_write_enabled"]:
        blockers.append("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED is not true.")

    if not gate["bridge_routing_write_armed"]:
        blockers.append("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED is not true.")

    if not gate["bridge_admin_token_configured"]:
        blockers.append("PLATFORM_BRIDGE_ADMIN_TOKEN is not configured.")

    if confirmation_phrase != REQUIRED_BRIDGE_WRITE_CONFIRMATION:
        blockers.append("Typed bridge routing write confirmation phrase is required.")

    if not _readiness_allows_scaffold(implementation_plan):
        blockers.append("Implementation plan does not allow guarded scaffold design.")

    plan = implementation_plan.get("implementation_plan") or {}
    if plan.get("can_execute_bridge_write_now") is not False:
        blockers.append("Implementation plan must explicitly say can_execute_bridge_write_now=false.")

    if implementation_plan.get("safety", {}).get("bridge_post_called") is not False:
        blockers.append("Implementation plan safety does not confirm bridge_post_called=false.")

    if implementation_plan.get("safety", {}).get("bridge_write_implementation_added") is not False:
        blockers.append("Implementation plan safety does not confirm bridge_write_implementation_added=false.")

    if cutover_packet:
        packet = cutover_packet.get("cutover_packet") or {}
        if packet.get("can_execute_bridge_write_now") is not False:
            blockers.append("Cutover packet must explicitly say can_execute_bridge_write_now=false.")
        if packet.get("approved_for_live_bridge_write") is True:
            blockers.append("Cutover packet unexpectedly indicates live bridge write approval.")
        if cutover_packet.get("operator_signoff", {}).get("approved_for_future_design_only") is not True:
            review_items.append("Operator signoff for future design only is not marked true.")

    # Critical safety invariant: Step 45 deliberately has no bridge HTTP client and no outbound POST implementation.
    blockers.append("Bridge POST call is not implemented in Step 45; scaffold is preview-only.")

    return {
        "executor_version": ROUTING_BRIDGE_WRITE_EXECUTOR_VERSION,
        "phase": "Phase 19 Step 45",
        "source_implementation_plan": str(implementation_plan_path),
        "source_cutover_packet": str(cutover_packet_path or ""),
        "dry_run": True,
        "preview_only": True,
        "blocked": True,
        "would_call_bridge": False,
        "would_mutate_platform": False,
        "would_call_lacrm": False,
        "blockers": blockers,
        "review_items": review_items,
        "request_envelope_preview": _build_request_envelope(implementation_plan, cutover_packet),
        "plan_items_seen": _extract_plan_items(implementation_plan),
        "future_gates_seen": _extract_future_gates(implementation_plan),
        "gate_status": gate,
        "safety": {
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
            "live_write_enabled": False,
            "bridge_write_implementation_added": False,
        },
    }
