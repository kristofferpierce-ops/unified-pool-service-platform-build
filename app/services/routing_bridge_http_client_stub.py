from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROUTING_BRIDGE_HTTP_CLIENT_STUB_VERSION = "phase20-step1-v1"
REQUIRED_BRIDGE_WRITE_CONFIRMATION = "WRITE BRIDGE ROUTING"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_http_client_stub_status() -> dict[str, Any]:
    return {
        "stub_version": ROUTING_BRIDGE_HTTP_CLIENT_STUB_VERSION,
        "safe_default": "stub_preview_only",
        "bridge_routing_http_client_stub_only": True,
        "bridge_routing_write_enabled": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED")),
        "bridge_routing_write_armed": _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED")),
        "bridge_admin_token_configured": bool(str(os.getenv("PLATFORM_BRIDGE_ADMIN_TOKEN") or "").strip()),
        "required_confirmation_phrase": REQUIRED_BRIDGE_WRITE_CONFIRMATION,
        "stub_endpoint_available": True,
        "real_bridge_http_client_implemented": False,
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
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _safe_get(mapping: Any, *keys: str) -> Any:
    value = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _artifact_summary(release_checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = release_checkpoint.get("artifacts") or []
    return [item for item in artifacts if isinstance(item, dict)]


def _release_has_no_post_violations(release_checkpoint: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    safety = release_checkpoint.get("safety") or {}
    if safety.get("bridge_routing_write_release_checkpoint_only") is not True:
        issues.append("release checkpoint is not marked bridge_routing_write_release_checkpoint_only=true")
    if safety.get("bridge_post_called") is not False:
        issues.append("release checkpoint does not confirm bridge_post_called=false")
    if safety.get("bridge_mutation_performed") is not False:
        issues.append("release checkpoint does not confirm bridge_mutation_performed=false")
    if safety.get("platform_db_mutation_performed") is not False:
        issues.append("release checkpoint does not confirm platform_db_mutation_performed=false")
    if safety.get("lacrm_call_performed") is not False:
        issues.append("release checkpoint does not confirm lacrm_call_performed=false")
    if safety.get("bridge_http_client_implemented") is not False:
        issues.append("release checkpoint does not confirm bridge_http_client_implemented=false")
    if safety.get("routing_write_endpoint_implemented") is not False:
        issues.append("release checkpoint does not confirm routing_write_endpoint_implemented=false")

    checkpoint = release_checkpoint.get("release_checkpoint") or {}
    if checkpoint.get("can_execute_bridge_write_now") is not False:
        issues.append("release checkpoint must explicitly say can_execute_bridge_write_now=false")
    if checkpoint.get("can_add_bridge_http_client_now") is not False:
        issues.append("release checkpoint must explicitly say can_add_bridge_http_client_now=false")

    for issue in release_checkpoint.get("issues") or []:
        if isinstance(issue, dict) and str(issue.get("severity") or "").lower() == "blocker":
            issues.append(f"release checkpoint blocker: {issue.get('code') or 'unknown'}")

    return issues


def build_bridge_routing_http_client_stub_preview(
    *,
    release_checkpoint_path: str | Path,
    operator_name: str = "",
    confirmation_phrase: str = "",
) -> dict[str, Any]:
    release_checkpoint = load_json_artifact(release_checkpoint_path)
    gate = bridge_routing_http_client_stub_status()

    release_issues = _release_has_no_post_violations(release_checkpoint)
    blockers: list[str] = list(release_issues)

    if confirmation_phrase != REQUIRED_BRIDGE_WRITE_CONFIRMATION:
        blockers.append("Typed bridge routing confirmation phrase is required for future design review.")

    if not str(operator_name or "").strip():
        blockers.append("Operator name is required for future design review.")

    # Critical invariant for Phase 20 Step 1: this is still only a stub and cannot call the bridge.
    blockers.append("Real bridge HTTP client and bridge POST call are not implemented in Phase 20 Step 1.")

    request_template = {
        "target_bridge_base_url": "http://127.0.0.1:8000",
        "target_bridge_endpoint": "/api/routing-rules",
        "http_method": "POST",
        "headers_template": {
            "Authorization": "Bearer <PLATFORM_BRIDGE_ADMIN_TOKEN>",
            "Idempotency-Key": "<audit/rehearsal idempotency key>",
            "Content-Type": "application/json",
        },
        "payload_template": {
            "phone": "<phone>",
            "mode": "<manual|auto>",
            "owner_type": "<unknown|homeowner|property_manager>",
            "label": "<optional label>",
            "default_contact_ids": [],
            "notes": "<operator/audit note>",
        },
    }

    return {
        "stub_version": ROUTING_BRIDGE_HTTP_CLIENT_STUB_VERSION,
        "phase": "Phase 20 Step 1",
        "source_release_checkpoint": str(release_checkpoint_path),
        "operator_name": str(operator_name or "").strip(),
        "preview_only": True,
        "stub_only": True,
        "blocked": True,
        "would_call_bridge": False,
        "would_mutate_bridge": False,
        "would_mutate_platform": False,
        "would_call_lacrm": False,
        "blockers": blockers,
        "request_template": request_template,
        "request_template_hash": _json_hash(request_template),
        "release_checkpoint_status": _safe_get(release_checkpoint, "release_checkpoint", "status") or "unknown",
        "release_checkpoint_artifacts": _artifact_summary(release_checkpoint),
        "gate_status": gate,
        "safety": {
            "bridge_routing_http_client_stub_only": True,
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "real_bridge_http_client_implemented": False,
            "bridge_http_client_implemented": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
            "live_write_enabled": False,
        },
    }
