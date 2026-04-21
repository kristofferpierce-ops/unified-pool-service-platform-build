from __future__ import annotations

import os
from typing import Any


ROUTING_BRIDGE_WRITE_REHEARSAL_VERSION = "phase19-step37-v1"
REQUIRED_BRIDGE_WRITE_CONFIRMATION = "WRITE BRIDGE ROUTING"

EXPECTED_TARGET_ENDPOINT = "/api/routing-rules"
EXPECTED_HTTP_METHOD = "POST"
EXPECTED_PAYLOAD_FIELDS = [
    "phone",
    "mode",
    "owner_type",
    "label",
    "default_contact_ids",
    "notes",
]


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def bridge_routing_write_rehearsal_status() -> dict[str, Any]:
    enabled = _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED"))
    armed = _truthy(os.getenv("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED"))
    admin_token_configured = bool(str(os.getenv("PLATFORM_BRIDGE_ADMIN_TOKEN") or "").strip())

    return {
        "rehearsal_version": ROUTING_BRIDGE_WRITE_REHEARSAL_VERSION,
        "safe_default": "blocked",
        "rehearsal_only": True,
        "bridge_routing_write_enabled": enabled,
        "bridge_routing_write_armed": armed,
        "bridge_admin_token_configured": admin_token_configured,
        "required_confirmation_phrase": REQUIRED_BRIDGE_WRITE_CONFIRMATION,
        "expected_target_endpoint": EXPECTED_TARGET_ENDPOINT,
        "expected_http_method": EXPECTED_HTTP_METHOD,
        "expected_payload_fields": EXPECTED_PAYLOAD_FIELDS,
        "bridge_post_call_implemented": False,
        "bridge_post_called": False,
        "platform_db_mutation_performed": False,
        "bridge_mutation_performed": False,
        "lacrm_call_performed": False,
        "routing_write_endpoint_implemented": False,
    }


def _normalized(value: Any) -> str:
    return str(value or "").strip()


def _payload_field_issues(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in EXPECTED_PAYLOAD_FIELDS:
        if field not in payload:
            issues.append(f"missing_payload_field:{field}")

    if not _normalized(payload.get("phone")):
        issues.append("missing_payload_phone")

    if _normalized(payload.get("mode")) not in {"manual", "auto"}:
        issues.append("invalid_payload_mode")

    if _normalized(payload.get("owner_type")) not in {"unknown", "homeowner", "property_manager"}:
        issues.append("invalid_payload_owner_type")

    if "default_contact_ids" in payload and not isinstance(payload.get("default_contact_ids"), list):
        issues.append("default_contact_ids_must_be_list")

    return issues


def rehearse_bridge_routing_write(
    *,
    preview_row: dict[str, Any],
    confirmation_phrase: str = "",
) -> dict[str, Any]:
    status = bridge_routing_write_rehearsal_status()

    target_endpoint = _normalized(preview_row.get("target_bridge_endpoint"))
    http_method = _normalized(preview_row.get("http_method")).upper()
    payload = preview_row.get("bridge_payload_preview") or {}
    if not isinstance(payload, dict):
        payload = {}

    blockers: list[str] = []

    if not status["bridge_routing_write_enabled"]:
        blockers.append("PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED is not true.")

    if not status["bridge_routing_write_armed"]:
        blockers.append("PLATFORM_BRIDGE_ROUTING_WRITE_ARMED is not true.")

    if confirmation_phrase != REQUIRED_BRIDGE_WRITE_CONFIRMATION:
        blockers.append("Typed bridge routing write confirmation phrase is required.")

    if not status["bridge_admin_token_configured"]:
        blockers.append("PLATFORM_BRIDGE_ADMIN_TOKEN is not configured.")

    if preview_row.get("previewable") is not True:
        blockers.append("Bridge apply preview row is not previewable.")

    if target_endpoint != EXPECTED_TARGET_ENDPOINT:
        blockers.append(f"Target endpoint must be {EXPECTED_TARGET_ENDPOINT}.")

    if http_method != EXPECTED_HTTP_METHOD:
        blockers.append(f"HTTP method must be {EXPECTED_HTTP_METHOD}.")

    blockers.extend(_payload_field_issues(payload))

    # Step 37 deliberately does not implement the outbound bridge POST call yet.
    blockers.append("Bridge POST call is not implemented in Step 37; this is rehearsal only.")

    return {
        "rehearsal_version": ROUTING_BRIDGE_WRITE_REHEARSAL_VERSION,
        "safe_default": "blocked",
        "rehearsal_only": True,
        "blocked": True,
        "would_call_bridge": False,
        "would_mutate_platform": False,
        "target_bridge_endpoint": target_endpoint,
        "http_method": http_method,
        "idempotency_key": _normalized(preview_row.get("idempotency_key")),
        "previewable": bool(preview_row.get("previewable")),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "payload_preview": payload,
        "source_preview_row": preview_row,
        "safety": {
            "platform_db_mutation_performed": False,
            "bridge_mutation_performed": False,
            "bridge_post_called": False,
            "lacrm_call_performed": False,
            "bridge_post_call_implemented": False,
            "routing_write_endpoint_implemented": False,
            "live_write_enabled": False,
        },
        "gate_status": status,
    }
