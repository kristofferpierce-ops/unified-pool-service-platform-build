from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROUTING_BRIDGE_WRITE_DRY_RUN_BUNDLE_VERSION = "phase19-step46-v1"
REQUIRED_BRIDGE_WRITE_CONFIRMATION = "WRITE BRIDGE ROUTING"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_write_dry_run_bundle_status() -> dict[str, Any]:
    return {
        "bundle_version": ROUTING_BRIDGE_WRITE_DRY_RUN_BUNDLE_VERSION,
        "safe_default": "dry_run_bundle_only",
        "dry_run_bundle_only": True,
        "bridge_routing_write_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED")),
        "bridge_routing_write_armed": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED")),
        "required_confirmation_phrase": REQUIRED_BRIDGE_WRITE_CONFIRMATION,
        "bundle_builder_endpoint_available": True,
        "bridge_http_client_implemented": False,
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


def _json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalized(value: Any) -> str:
    return str(value or "").strip()


def _extract_payload_template(scaffold: dict[str, Any]) -> dict[str, Any]:
    preview = scaffold.get("preview") or {}
    envelope = preview.get("request_envelope_preview") or {}
    request_shape = envelope.get("future_request_shape") or {}
    body = request_shape.get("body") or {}
    if isinstance(body, dict):
        return body
    return {}


def _extract_headers_template(scaffold: dict[str, Any]) -> dict[str, Any]:
    preview = scaffold.get("preview") or {}
    envelope = preview.get("request_envelope_preview") or {}
    request_shape = envelope.get("future_request_shape") or {}
    headers = request_shape.get("headers") or {}
    if isinstance(headers, dict):
        return headers
    return {}


def _extract_contract(scaffold: dict[str, Any]) -> dict[str, Any]:
    preview = scaffold.get("preview") or {}
    envelope = preview.get("request_envelope_preview") or {}
    contract = envelope.get("contract") or {}
    if isinstance(contract, dict):
        return contract
    return {}


def build_bridge_routing_write_dry_run_bundle(
    *,
    scaffold_report_path: str | Path,
    cutover_packet_path: str | Path | None = None,
    implementation_plan_path: str | Path | None = None,
) -> dict[str, Any]:
    status = bridge_routing_write_dry_run_bundle_status()
    scaffold = load_json_artifact(scaffold_report_path)
    cutover = load_json_artifact(cutover_packet_path) if cutover_packet_path else None
    implementation_plan = load_json_artifact(implementation_plan_path) if implementation_plan_path else None

    safety_errors: list[str] = []
    blockers: list[str] = []

    scaffold_safety = scaffold.get("safety") or {}
    scaffold_preview = scaffold.get("preview") or {}
    scaffold_counts = scaffold.get("counts") or {}

    if scaffold_safety.get("bridge_routing_write_scaffold_only") is not True:
        safety_errors.append("scaffold report is not marked bridge_routing_write_scaffold_only=true")
    if scaffold_safety.get("bridge_post_called") is not False:
        safety_errors.append("scaffold report does not confirm bridge_post_called=false")
    if scaffold_safety.get("bridge_post_call_implemented") is not False:
        safety_errors.append("scaffold report does not confirm bridge_post_call_implemented=false")
    if scaffold_safety.get("platform_db_mutation_performed") is not False:
        safety_errors.append("scaffold report does not confirm platform_db_mutation_performed=false")
    if scaffold_preview.get("would_call_bridge") is not False:
        safety_errors.append("scaffold preview does not confirm would_call_bridge=false")
    if scaffold_preview.get("blocked") is not True:
        blockers.append("scaffold preview is not blocked")

    if cutover is not None:
        cutover_safety = cutover.get("safety") or {}
        packet = cutover.get("cutover_packet") or {}
        if cutover_safety.get("bridge_post_called") is not False:
            safety_errors.append("cutover packet does not confirm bridge_post_called=false")
        if packet.get("can_execute_bridge_write_now") is not False:
            blockers.append("cutover packet does not explicitly block bridge write execution now")

    if implementation_plan is not None:
        plan_safety = implementation_plan.get("safety") or {}
        plan = implementation_plan.get("implementation_plan") or {}
        if plan_safety.get("bridge_post_called") is not False:
            safety_errors.append("implementation plan does not confirm bridge_post_called=false")
        if plan.get("can_execute_bridge_write_now") is not False:
            blockers.append("implementation plan does not explicitly block bridge write execution now")

    contract = _extract_contract(scaffold)
    payload_template = _extract_payload_template(scaffold)
    headers_template = _extract_headers_template(scaffold)

    required_payload_fields = ["phone", "mode", "owner_type", "label", "default_contact_ids", "notes"]
    missing_fields = [field for field in required_payload_fields if field not in payload_template]
    if missing_fields:
        blockers.append("payload template missing fields: " + ", ".join(missing_fields))

    bundle_row = {
        "bundle_row_type": "request_template_only",
        "target_bridge_endpoint": contract.get("target_bridge_endpoint") or "/api/routing-rules",
        "http_method": contract.get("http_method") or "POST",
        "headers_template": headers_template,
        "payload_template": payload_template,
        "idempotency_key_template": headers_template.get("Idempotency-Key") or "<audit/rehearsal idempotency key>",
        "payload_hash": _json_hash(payload_template),
        "would_call_bridge": False,
        "would_mutate_platform": False,
        "would_call_lacrm": False,
        "ready_for_live_execution": False,
        "reason": "Step 46 is dry-run bundle only and does not implement a bridge HTTP client.",
    }

    bundle = {
        "bundle_version": ROUTING_BRIDGE_WRITE_DRY_RUN_BUNDLE_VERSION,
        "phase": "Phase 19 Step 46",
        "source_scaffold_report": str(scaffold_report_path),
        "source_cutover_packet": str(cutover_packet_path or ""),
        "source_implementation_plan": str(implementation_plan_path or ""),
        "dry_run": True,
        "preview_only": True,
        "dry_run_bundle_only": True,
        "blocked": True,
        "blockers": blockers + ["Bridge HTTP client and bridge POST call are not implemented in Step 46."],
        "safety_errors": safety_errors,
        "bundle_rows": [bundle_row],
        "counts": {
            "bundle_rows": 1,
            "scaffold_blocker_count": int(scaffold_counts.get("blocker_count") or 0),
            "scaffold_review_item_count": int(scaffold_counts.get("review_item_count") or 0),
            "safety_error_count": len(safety_errors),
        },
        "gate_status": status,
        "safety": {
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "bridge_http_client_implemented": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
            "live_write_enabled": False,
        },
    }

    return bundle
