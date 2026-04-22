from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROUTING_BRIDGE_NETWORK_TRANSPORT_INTERFACE_SCAFFOLD_VERSION = "phase20-step14-v1"
REQUIRED_TRANSPORT_CONFIRMATION = "ENABLE BRIDGE TRANSPORT DESIGN"


@dataclass(frozen=True)
class BridgeRoutingTransportRequest:
    phone: str
    mode: str = "dry_run"
    owner_type: str = "unknown"
    label: str = ""
    default_contact_ids: list[str] = field(default_factory=list)
    notes: str = ""
    idempotency_key: str = ""


@dataclass(frozen=True)
class BridgeRoutingTransportResult:
    ok: bool = False
    status_code: int = 0
    transport_mode: str = "dry_run_no_network"
    would_open_socket: bool = False
    would_send_http_request: bool = False
    would_call_bridge: bool = False
    would_mutate_bridge: bool = False
    message: str = "Interface scaffold only. No network transport is implemented."


class BridgeRoutingTransportAdapterInterface:
    """Future adapter shape only. It intentionally cannot perform transport."""

    adapter_name = "BridgeRoutingTransportAdapterInterface"
    implementation_kind = "interface_scaffold_only"
    network_transport_implemented = False
    bridge_post_call_implemented = False

    def validate_request(self, request: BridgeRoutingTransportRequest) -> list[str]:
        errors: list[str] = []
        if not request.phone.strip():
            errors.append("phone is required")
        if request.mode != "dry_run":
            errors.append("only dry_run mode is accepted by the interface scaffold")
        if not request.idempotency_key.strip():
            errors.append("idempotency_key is required for future transport design")
        return errors

    def simulate(self, request: BridgeRoutingTransportRequest) -> BridgeRoutingTransportResult:
        errors = self.validate_request(request)
        if errors:
            return BridgeRoutingTransportResult(message="Validation failed: " + "; ".join(errors))
        return BridgeRoutingTransportResult(message="Dry-run interface scaffold accepted the shape without opening a socket.")

    def execute(self, request: BridgeRoutingTransportRequest) -> BridgeRoutingTransportResult:
        raise RuntimeError("Bridge network transport execution is not implemented in Phase 20 Step 14.")


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_network_transport_interface_scaffold_status() -> dict[str, Any]:
    return {
        "scaffold_version": ROUTING_BRIDGE_NETWORK_TRANSPORT_INTERFACE_SCAFFOLD_VERSION,
        "safe_default": "interface_scaffold_only_no_network",
        "bridge_routing_network_transport_interface_scaffold_only": True,
        "bridge_network_transport_design_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ENABLED")),
        "bridge_network_transport_design_armed": _truthy(os.getenv("PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ARMED")),
        "bridge_routing_write_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED")),
        "bridge_routing_write_armed": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED")),
        "bridge_admin_token_configured": bool(str(os.getenv("PLATFORM_BRIDGE_ADMIN_TOKEN") or "").strip()),
        "required_transport_design_confirmation_phrase": REQUIRED_TRANSPORT_CONFIRMATION,
        "interface_scaffold_endpoint_available": True,
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


def _implementation_plan_blockers(plan_report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []

    safety = plan_report.get("safety") or {}
    implementation_plan = plan_report.get("implementation_plan") or {}

    expected_false = [
        "platform_db_mutation_performed",
        "bridge_mutation_performed",
        "bridge_post_called",
        "lacrm_call_performed",
        "real_bridge_http_client_implemented",
        "network_transport_implemented",
        "network_transport_enabled",
        "network_transport_armed",
        "network_socket_opened",
        "bridge_http_client_implemented",
        "bridge_post_call_implemented",
        "routing_write_endpoint_implemented",
        "live_write_enabled",
    ]

    if safety.get("bridge_routing_network_transport_implementation_plan_only") is not True:
        blockers.append("source implementation plan is not marked bridge_routing_network_transport_implementation_plan_only=true")

    for key in expected_false:
        if safety.get(key) is not False:
            blockers.append(f"source implementation plan safety flag {key} is not false")

    future_gate_false = [
        "can_execute_bridge_write_now",
        "can_add_network_transport_now",
        "can_enable_network_transport_now",
        "can_arm_network_transport_now",
        "can_open_network_socket_now",
        "can_add_real_bridge_http_client_now",
        "can_add_bridge_post_now",
    ]
    for key in future_gate_false:
        if implementation_plan.get(key) is not False:
            blockers.append(f"source implementation plan {key} must be false")

    for issue in plan_report.get("issues") or []:
        if isinstance(issue, dict) and str(issue.get("severity") or "").lower() == "blocker":
            blockers.append(f"source implementation plan blocker: {issue.get('code') or 'unknown'}")

    return blockers


def _stage_rows(plan_report: dict[str, Any]) -> list[dict[str, Any]]:
    stages = plan_report.get("stages") or []
    return [stage for stage in stages if isinstance(stage, dict)]


def build_bridge_routing_network_transport_interface_scaffold_preview(
    *,
    implementation_plan_path: str | Path,
    operator_name: str = "",
    transport_confirmation_phrase: str = "",
) -> dict[str, Any]:
    plan_report = load_json_artifact(implementation_plan_path)
    gate = bridge_routing_network_transport_interface_scaffold_status()

    blockers = _implementation_plan_blockers(plan_report)

    if not str(operator_name or "").strip():
        blockers.append("Operator name is required for future interface scaffold review.")

    if transport_confirmation_phrase != REQUIRED_TRANSPORT_CONFIRMATION:
        blockers.append("Typed transport design confirmation phrase is required for future interface scaffold review.")

    stage_names = {str(stage.get("stage") or "") for stage in _stage_rows(plan_report)}
    if "adapter_interface_scaffold" not in stage_names:
        blockers.append("source implementation plan does not include adapter_interface_scaffold stage")

    # Critical invariant for Phase 20 Step 14.
    blockers.append("Real bridge network transport, socket opening, and bridge POST are not implemented in Phase 20 Step 14.")

    sample_request = BridgeRoutingTransportRequest(
        phone="+13055550000",
        mode="dry_run",
        owner_type="unknown",
        label="interface scaffold sample",
        default_contact_ids=[],
        notes="No-network scaffold sample only.",
        idempotency_key="phase20-step14-interface-scaffold-sample",
    )
    adapter = BridgeRoutingTransportAdapterInterface()
    sample_result = adapter.simulate(sample_request)

    interface_scaffold = {
        "module": "app.services.routing_bridge_network_transport_interface_scaffold",
        "classes": [
            "BridgeRoutingTransportRequest",
            "BridgeRoutingTransportResult",
            "BridgeRoutingTransportAdapterInterface",
        ],
        "adapter_name": adapter.adapter_name,
        "implementation_kind": adapter.implementation_kind,
        "network_transport_implemented": False,
        "network_socket_opened": False,
        "bridge_post_call_implemented": False,
        "execute_method_behavior": "raises_runtime_error_no_transport",
        "simulate_method_behavior": "shape_only_no_network",
        "request_fields": list(asdict(sample_request).keys()),
        "result_fields": list(asdict(sample_result).keys()),
        "required_future_gates": [
            "audit_prerequisite_gate",
            "rollback_snapshot_gate",
            "environment_gate_design",
            "operator_confirmation_gate",
            "response_capture_design",
            "future_cutover_packet_prerequisite",
        ],
    }

    return {
        "scaffold_version": ROUTING_BRIDGE_NETWORK_TRANSPORT_INTERFACE_SCAFFOLD_VERSION,
        "phase": "Phase 20 Step 14",
        "source_implementation_plan": str(implementation_plan_path),
        "operator_name": str(operator_name or "").strip(),
        "preview_only": True,
        "interface_scaffold_only": True,
        "blocked": True,
        "would_add_network_transport": False,
        "would_enable_network_transport": False,
        "would_arm_network_transport": False,
        "would_open_socket": False,
        "would_send_http_request": False,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "would_mutate_platform": False,
        "would_call_lacrm": False,
        "blockers": blockers,
        "source_stage_count": len(_stage_rows(plan_report)),
        "interface_scaffold": interface_scaffold,
        "interface_scaffold_hash": _hash_json(interface_scaffold),
        "sample_request": asdict(sample_request),
        "sample_result": asdict(sample_result),
        "gate_status": gate,
        "safety": {
            "bridge_routing_network_transport_interface_scaffold_only": True,
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
