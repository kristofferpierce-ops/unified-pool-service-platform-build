from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_VERSION = "phase20-step7-v1"
REQUIRED_BRIDGE_WRITE_CONFIRMATION = "WRITE BRIDGE ROUTING"
REQUIRED_TRANSPORT_CONFIRMATION = "ENABLE BRIDGE TRANSPORT DESIGN"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_network_transport_guard_status() -> dict[str, Any]:
    return {
        "guard_version": ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_VERSION,
        "safe_default": "network_transport_guard_blocked",
        "bridge_routing_network_transport_guard_only": True,
        "bridge_routing_write_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED")),
        "bridge_routing_write_armed": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED")),
        "bridge_network_transport_design_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ENABLED")),
        "bridge_network_transport_design_armed": _truthy(os.getenv("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ARMED")),
        "bridge_admin_token_configured": bool(str(os.getenv("PLATFORM_BRIDGE_ADMIN_TOKEN") or "").strip()),
        "required_bridge_write_confirmation_phrase": REQUIRED_BRIDGE_WRITE_CONFIRMATION,
        "required_transport_design_confirmation_phrase": REQUIRED_TRANSPORT_CONFIRMATION,
        "guard_endpoint_available": True,
        "real_bridge_http_client_implemented": False,
        "network_transport_implemented": False,
        "network_transport_enabled": False,
        "network_transport_armed": False,
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


def _artifact_summary(release_checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = release_checkpoint.get("artifacts") or []
    return [item for item in artifacts if isinstance(item, dict)]


def _checkpoint_blockers(release_checkpoint: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    safety = release_checkpoint.get("safety") or {}
    checkpoint = release_checkpoint.get("release_checkpoint") or {}

    expected_false = [
        "platform_db_mutation_performed",
        "bridge_mutation_performed",
        "bridge_post_called",
        "lacrm_call_performed",
        "real_bridge_http_client_implemented",
        "network_transport_implemented",
        "bridge_http_client_implemented",
        "bridge_post_call_implemented",
        "routing_write_endpoint_implemented",
        "live_write_enabled",
    ]
    for key in expected_false:
        if safety.get(key) is not False:
            blockers.append(f"release checkpoint safety flag {key} is not false")

    if safety.get("bridge_routing_http_client_release_checkpoint_only") is not True:
        blockers.append("release checkpoint is not marked bridge_routing_http_client_release_checkpoint_only=true")

    if checkpoint.get("can_execute_bridge_write_now") is not False:
        blockers.append("release checkpoint must explicitly say can_execute_bridge_write_now=false")
    if checkpoint.get("can_add_network_transport_now") is not False:
        blockers.append("release checkpoint must explicitly say can_add_network_transport_now=false")
    if checkpoint.get("can_add_real_bridge_http_client_now") is not False:
        blockers.append("release checkpoint must explicitly say can_add_real_bridge_http_client_now=false")

    for issue in release_checkpoint.get("issues") or []:
        if isinstance(issue, dict) and str(issue.get("severity") or "").lower() == "blocker":
            blockers.append(f"release checkpoint blocker: {issue.get('code') or 'unknown'}")

    return blockers


def build_bridge_routing_network_transport_guard_preview(
    *,
    release_checkpoint_path: str | Path,
    operator_name: str = "",
    transport_confirmation_phrase: str = "",
    bridge_write_confirmation_phrase: str = "",
) -> dict[str, Any]:
    release_checkpoint = load_json_artifact(release_checkpoint_path)
    gate = bridge_routing_network_transport_guard_status()

    blockers = _checkpoint_blockers(release_checkpoint)

    if not str(operator_name or "").strip():
        blockers.append("Operator name is required for future transport design review.")

    if transport_confirmation_phrase != REQUIRED_TRANSPORT_CONFIRMATION:
        blockers.append("Typed transport design confirmation phrase is required for future design review.")

    if bridge_write_confirmation_phrase == REQUIRED_BRIDGE_WRITE_CONFIRMATION:
        blockers.append("Bridge write confirmation phrase must not be used at this design-only guard step.")

    if not gate["bridge_network_transport_design_enabled"]:
        blockers.append("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ENABLED is not true.")
    if not gate["bridge_network_transport_design_armed"]:
        blockers.append("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ARMED is not true.")

    # Critical invariant: Phase 20 Step 7 still does not implement transport.
    blockers.append("Real bridge network transport is not implemented in Phase 20 Step 7.")

    transport_design_contract = {
        "adapter_name": "BridgeRoutingNetworkTransport",
        "intended_method": "POST",
        "intended_endpoint": "/api/routing-rules",
        "base_url_env": "PLATFORM_BRIDGE_BASE_URL",
        "admin_token_env": "PLATFORM_BRIDGE_ADMIN_TOKEN",
        "idempotency_header": "Idempotency-Key",
        "allowed_default_mode": "dry_run",
        "live_mode_default": False,
        "must_require_pre_audit_row": True,
        "must_require_rollback_snapshot": True,
        "must_require_operator_confirmation": True,
        "must_record_response_before_returning": True,
        "must_not_call_lacrm": True,
    }

    return {
        "guard_version": ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_VERSION,
        "phase": "Phase 20 Step 7",
        "source_release_checkpoint": str(release_checkpoint_path),
        "operator_name": str(operator_name or "").strip(),
        "preview_only": True,
        "guard_only": True,
        "blocked": True,
        "would_add_network_transport": False,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "would_mutate_platform": False,
        "would_call_lacrm": False,
        "blockers": blockers,
        "transport_design_contract": transport_design_contract,
        "transport_design_contract_hash": _hash_json(transport_design_contract),
        "release_checkpoint_status": (release_checkpoint.get("release_checkpoint") or {}).get("status", "unknown"),
        "release_checkpoint_artifacts": _artifact_summary(release_checkpoint),
        "gate_status": gate,
        "safety": {
            "bridge_routing_network_transport_guard_only": True,
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "real_bridge_http_client_implemented": False,
            "network_transport_implemented": False,
            "network_transport_enabled": False,
            "network_transport_armed": False,
            "bridge_http_client_implemented": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
            "live_write_enabled": False,
        },
    }
