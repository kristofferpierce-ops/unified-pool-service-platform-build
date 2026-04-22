from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUTING_BRIDGE_NETWORK_TRANSPORT_DRY_RUN_ADAPTER_VERSION = "phase20-step8-v1"
REQUIRED_TRANSPORT_CONFIRMATION = "ENABLE BRIDGE TRANSPORT DESIGN"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_network_transport_dry_run_adapter_status() -> dict[str, Any]:
    return {
        "adapter_version": ROUTING_BRIDGE_NETWORK_TRANSPORT_DRY_RUN_ADAPTER_VERSION,
        "safe_default": "dry_run_adapter_no_network",
        "bridge_routing_network_transport_dry_run_adapter_only": True,
        "bridge_network_transport_design_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ENABLED")),
        "bridge_network_transport_design_armed": _truthy(os.getenv("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ARMED")),
        "bridge_routing_write_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED")),
        "bridge_routing_write_armed": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED")),
        "bridge_admin_token_configured": bool(str(os.getenv("PLATFORM_BRIDGE_ADMIN_TOKEN") or "").strip()),
        "required_transport_design_confirmation_phrase": REQUIRED_TRANSPORT_CONFIRMATION,
        "dry_run_adapter_endpoint_available": True,
        "real_bridge_http_client_implemented": False,
        "network_transport_implemented": False,
        "network_transport_enabled": False,
        "network_transport_armed": False,
        "network_socket_opened": False,
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


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _extract_guard_preview(guard_report: dict[str, Any]) -> dict[str, Any]:
    preview = guard_report.get("preview") or {}
    return preview if isinstance(preview, dict) else {}


def _extract_transport_design_contract(guard_report: dict[str, Any]) -> dict[str, Any]:
    preview = _extract_guard_preview(guard_report)
    contract = preview.get("transport_design_contract") or {}
    return contract if isinstance(contract, dict) else {}


def _guard_blockers(guard_report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []

    safety = guard_report.get("safety") or {}
    preview = _extract_guard_preview(guard_report)

    expected_false = [
        "platform_db_mutation_performed",
        "bridge_mutation_performed",
        "bridge_post_called",
        "lacrm_call_performed",
        "real_bridge_http_client_implemented",
        "network_transport_implemented",
        "network_transport_enabled",
        "network_transport_armed",
        "bridge_http_client_implemented",
        "bridge_post_call_implemented",
        "routing_write_endpoint_implemented",
        "live_write_enabled",
    ]

    if safety.get("bridge_routing_network_transport_guard_only") is not True:
        blockers.append("source guard report is not marked bridge_routing_network_transport_guard_only=true")

    for key in expected_false:
        if safety.get(key) is not False:
            blockers.append(f"source guard safety flag {key} is not false")

    if preview.get("would_add_network_transport") is not False:
        blockers.append("source guard preview does not confirm would_add_network_transport=false")
    if preview.get("would_call_bridge") is not False:
        blockers.append("source guard preview does not confirm would_call_bridge=false")
    if preview.get("would_mutate_bridge") is not False:
        blockers.append("source guard preview does not confirm would_mutate_bridge=false")
    if preview.get("would_mutate_platform") is not False:
        blockers.append("source guard preview does not confirm would_mutate_platform=false")
    if preview.get("would_call_lacrm") is not False:
        blockers.append("source guard preview does not confirm would_call_lacrm=false")

    for item in guard_report.get("safety_errors") or []:
        blockers.append(f"source guard safety error: {item}")

    return blockers


def build_bridge_routing_network_transport_dry_run_adapter(
    *,
    guard_report_path: str | Path,
    operator_name: str = "",
    transport_confirmation_phrase: str = "",
) -> dict[str, Any]:
    guard_report = load_json_artifact(guard_report_path)
    gate = bridge_routing_network_transport_dry_run_adapter_status()
    contract = _extract_transport_design_contract(guard_report)

    blockers = _guard_blockers(guard_report)

    if not str(operator_name or "").strip():
        blockers.append("Operator name is required for future transport design review.")

    if transport_confirmation_phrase != REQUIRED_TRANSPORT_CONFIRMATION:
        blockers.append("Typed transport design confirmation phrase is required for future design review.")

    required_contract_fields = [
        "adapter_name",
        "intended_method",
        "intended_endpoint",
        "base_url_env",
        "admin_token_env",
        "idempotency_header",
        "allowed_default_mode",
        "live_mode_default",
        "must_require_pre_audit_row",
        "must_require_rollback_snapshot",
        "must_require_operator_confirmation",
        "must_record_response_before_returning",
        "must_not_call_lacrm",
    ]

    for field in required_contract_fields:
        if field not in contract:
            blockers.append(f"transport_design_contract is missing {field}")

    if contract.get("allowed_default_mode") != "dry_run":
        blockers.append("transport_design_contract allowed_default_mode must be dry_run")

    if contract.get("live_mode_default") is not False:
        blockers.append("transport_design_contract live_mode_default must be false")

    # Critical invariant for Phase 20 Step 8.
    blockers.append("Real bridge network transport and bridge POST call are not implemented in Phase 20 Step 8.")

    adapter_dry_run_contract = {
        "adapter_name": contract.get("adapter_name", "BridgeRoutingNetworkTransport"),
        "implementation_kind": "dry_run_adapter_harness",
        "transport_mode": "dry_run_no_network",
        "network_socket_opened": False,
        "would_open_socket": False,
        "would_send_http_request": False,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "request_shape": {
            "method": contract.get("intended_method", "POST"),
            "endpoint": contract.get("intended_endpoint", "/api/routing-rules"),
            "base_url_env": contract.get("base_url_env", "PLATFORM_BRIDGE_BASE_URL"),
            "admin_token_env": contract.get("admin_token_env", "PLATFORM_BRIDGE_ADMIN_TOKEN"),
            "idempotency_header": contract.get("idempotency_header", "Idempotency-Key"),
            "payload_template": {
                "phone": "<phone>",
                "mode": "<manual|auto>",
                "owner_type": "<unknown|homeowner|property_manager>",
                "label": "<optional label>",
                "default_contact_ids": [],
                "notes": "<operator/audit note>",
            },
        },
        "required_gates": {
            "pre_audit_row": True,
            "rollback_snapshot": True,
            "operator_confirmation": True,
            "response_recording": True,
            "lacrm_forbidden": True,
        },
    }

    simulated_adapter_result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "adapter_contract_hash": _hash_json(adapter_dry_run_contract),
        "transport_mode": "dry_run_no_network",
        "status_code": 0,
        "ok": False,
        "would_open_socket": False,
        "would_send_http_request": False,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "message": "Dry-run adapter harness only. No network transport was created or called.",
    }

    return {
        "adapter_version": ROUTING_BRIDGE_NETWORK_TRANSPORT_DRY_RUN_ADAPTER_VERSION,
        "phase": "Phase 20 Step 8",
        "source_guard_report": str(guard_report_path),
        "operator_name": str(operator_name or "").strip(),
        "preview_only": True,
        "dry_run": True,
        "adapter_harness_only": True,
        "blocked": True,
        "would_add_network_transport": False,
        "would_open_socket": False,
        "would_send_http_request": False,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "would_mutate_platform": False,
        "would_call_lacrm": False,
        "blockers": blockers,
        "source_transport_design_contract": contract,
        "adapter_dry_run_contract": adapter_dry_run_contract,
        "simulated_adapter_result": simulated_adapter_result,
        "gate_status": gate,
        "safety": {
            "bridge_routing_network_transport_dry_run_adapter_only": True,
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "real_bridge_http_client_implemented": False,
            "network_transport_implemented": False,
            "network_transport_enabled": False,
            "network_transport_armed": False,
            "network_socket_opened": False,
            "bridge_http_client_implemented": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
            "live_write_enabled": False,
        },
    }
