from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUTING_BRIDGE_HTTP_CLIENT_DRY_RUN_VERSION = "phase20-step2-v1"
REQUIRED_BRIDGE_WRITE_CONFIRMATION = "WRITE BRIDGE ROUTING"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_http_client_dry_run_status() -> dict[str, Any]:
    return {
        "dry_run_version": ROUTING_BRIDGE_HTTP_CLIENT_DRY_RUN_VERSION,
        "safe_default": "dry_run_transport_only",
        "bridge_routing_http_client_dry_run_only": True,
        "bridge_routing_write_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED")),
        "bridge_routing_write_armed": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED")),
        "bridge_admin_token_configured": bool(str(os.getenv("PLATFORM_BRIDGE_ADMIN_TOKEN") or "").strip()),
        "required_confirmation_phrase": REQUIRED_BRIDGE_WRITE_CONFIRMATION,
        "dry_run_transport_endpoint_available": True,
        "real_bridge_http_client_implemented": False,
        "network_transport_implemented": False,
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


def _extract_stub_preview(stub_report: dict[str, Any]) -> dict[str, Any]:
    preview = stub_report.get("preview") or {}
    return preview if isinstance(preview, dict) else {}


def _extract_request_template(stub_report: dict[str, Any]) -> dict[str, Any]:
    preview = _extract_stub_preview(stub_report)
    template = preview.get("request_template") or {}
    return template if isinstance(template, dict) else {}


def _check_stub_safety(stub_report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    safety = stub_report.get("safety") or {}
    preview = _extract_stub_preview(stub_report)

    if safety.get("bridge_routing_http_client_stub_only") is not True:
        blockers.append("source stub report is not marked bridge_routing_http_client_stub_only=true")
    if safety.get("real_bridge_http_client_implemented") is not False:
        blockers.append("source stub report does not confirm real_bridge_http_client_implemented=false")
    if safety.get("bridge_post_call_implemented") is not False:
        blockers.append("source stub report does not confirm bridge_post_call_implemented=false")
    if safety.get("bridge_post_called") is not False:
        blockers.append("source stub report does not confirm bridge_post_called=false")
    if safety.get("bridge_mutation_performed") is not False:
        blockers.append("source stub report does not confirm bridge_mutation_performed=false")
    if safety.get("platform_db_mutation_performed") is not False:
        blockers.append("source stub report does not confirm platform_db_mutation_performed=false")
    if safety.get("lacrm_call_performed") is not False:
        blockers.append("source stub report does not confirm lacrm_call_performed=false")

    if preview.get("would_call_bridge") is not False:
        blockers.append("source stub preview does not confirm would_call_bridge=false")
    if preview.get("would_mutate_bridge") is not False:
        blockers.append("source stub preview does not confirm would_mutate_bridge=false")
    if preview.get("would_mutate_platform") is not False:
        blockers.append("source stub preview does not confirm would_mutate_platform=false")
    if preview.get("would_call_lacrm") is not False:
        blockers.append("source stub preview does not confirm would_call_lacrm=false")

    return blockers


def build_bridge_routing_http_client_dry_run(
    *,
    stub_report_path: str | Path,
    operator_name: str = "",
    confirmation_phrase: str = "",
) -> dict[str, Any]:
    stub_report = load_json_artifact(stub_report_path)
    gate = bridge_routing_http_client_dry_run_status()
    request_template = _extract_request_template(stub_report)

    blockers = _check_stub_safety(stub_report)

    if not str(operator_name or "").strip():
        blockers.append("Operator name is required for future design review.")

    if confirmation_phrase != REQUIRED_BRIDGE_WRITE_CONFIRMATION:
        blockers.append("Typed bridge routing confirmation phrase is required for future design review.")

    if not isinstance(request_template, dict) or not request_template:
        blockers.append("Source stub report does not contain a request_template.")

    headers_template = request_template.get("headers_template") if isinstance(request_template, dict) else {}
    payload_template = request_template.get("payload_template") if isinstance(request_template, dict) else {}

    if not isinstance(headers_template, dict):
        headers_template = {}
    if not isinstance(payload_template, dict):
        payload_template = {}

    for field in ["Authorization", "Idempotency-Key", "Content-Type"]:
        if field not in headers_template:
            blockers.append(f"headers_template is missing {field}")

    for field in ["phone", "mode", "owner_type", "label", "default_contact_ids", "notes"]:
        if field not in payload_template:
            blockers.append(f"payload_template is missing {field}")

    # Critical invariant for Phase 20 Step 2: this is still a dry-run transport simulator.
    blockers.append("Real bridge network transport and bridge POST call are not implemented in Phase 20 Step 2.")

    simulated_request = {
        "request_id": _hash_json({"source": str(stub_report_path), "template": request_template}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_bridge_base_url": request_template.get("target_bridge_base_url", "http://127.0.0.1:8000"),
        "target_bridge_endpoint": request_template.get("target_bridge_endpoint", "/api/routing-rules"),
        "http_method": request_template.get("http_method", "POST"),
        "headers_template": headers_template,
        "payload_template": payload_template,
        "payload_hash": _hash_json(payload_template),
        "transport": "dry_run_no_network",
    }

    simulated_response = {
        "status_code": 0,
        "ok": False,
        "transport": "dry_run_no_network",
        "would_send": False,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "message": "Dry-run transport only. No network request was created or sent.",
    }

    return {
        "dry_run_version": ROUTING_BRIDGE_HTTP_CLIENT_DRY_RUN_VERSION,
        "phase": "Phase 20 Step 2",
        "source_stub_report": str(stub_report_path),
        "operator_name": str(operator_name or "").strip(),
        "dry_run": True,
        "preview_only": True,
        "transport_only": True,
        "blocked": True,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "would_mutate_platform": False,
        "would_call_lacrm": False,
        "blockers": blockers,
        "simulated_request": simulated_request,
        "simulated_response": simulated_response,
        "gate_status": gate,
        "safety": {
            "bridge_routing_http_client_dry_run_only": True,
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "real_bridge_http_client_implemented": False,
            "network_transport_implemented": False,
            "bridge_http_client_implemented": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
            "live_write_enabled": False,
        },
    }
