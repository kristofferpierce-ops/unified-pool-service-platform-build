from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Literal


ROUTING_BRIDGE_NETWORK_TRANSPORT_CONTRACT_SCHEMA_VERSION = "phase20_step34_contract_schema_scaffold_v1"

BridgeRoutingResultKind = Literal[
    "not_implemented",
    "dry_run",
    "blocked",
    "success",
    "timeout",
    "connection_error",
    "auth_error",
    "parse_error",
    "unknown",
]


def _as_tuple(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(str(value) for value in values)


def _require_text(value: str, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required for the bridge routing transport contract schema.")
    return normalized


@dataclass(frozen=True)
class BridgeRoutingTransportRequestContract:
    """Schema-only future bridge routing transport request contract.

    This dataclass is a design contract only. It does not execute bridge writes,
    does not create a bridge HTTP client, and does not open a network boundary.
    """

    request_id: str
    transport_execution_id: str
    idempotency_key: str
    phone: str
    mode: str
    owner_type: str
    label: str = ""
    default_contact_ids: tuple[str, ...] = ()
    notes: str = ""
    source_checkpoint_hash: str = ""
    audit_prerequisite_gate_hash: str = ""
    rollback_snapshot_prerequisite_gate_hash: str = ""
    environment_gate_hash: str = ""
    operator_confirmation_gate_hash: str = ""
    response_capture_gate_hash: str = ""
    cutover_packet_hash: str = ""
    dry_run: bool = True
    design_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _require_text(self.request_id, "request_id"))
        object.__setattr__(self, "transport_execution_id", _require_text(self.transport_execution_id, "transport_execution_id"))
        object.__setattr__(self, "idempotency_key", _require_text(self.idempotency_key, "idempotency_key"))
        object.__setattr__(self, "phone", _require_text(self.phone, "phone"))
        object.__setattr__(self, "mode", _require_text(self.mode, "mode"))
        object.__setattr__(self, "owner_type", _require_text(self.owner_type, "owner_type"))
        object.__setattr__(self, "default_contact_ids", _as_tuple(self.default_contact_ids))

        if self.dry_run is not True:
            raise ValueError("BridgeRoutingTransportRequestContract must remain dry_run=True in Phase 20 Step 34.")
        if self.design_only is not True:
            raise ValueError("BridgeRoutingTransportRequestContract must remain design_only=True in Phase 20 Step 34.")


@dataclass(frozen=True)
class BridgeRoutingTransportResponseContract:
    """Schema-only future bridge routing transport response contract."""

    response_capture_id: str
    transport_execution_id: str
    bridge_result_kind: BridgeRoutingResultKind = "not_implemented"
    response_status_code: int | None = None
    response_headers_hash: str = ""
    response_body_hash: str = ""
    response_body_redaction_status: str = "not_applicable"
    transport_error_code: str = ""
    transport_error_message: str = ""
    retry_allowed: bool = False
    bridge_response_captured: bool = False
    bridge_post_called: bool = False
    network_transport_implemented: bool = False
    network_transport_enabled: bool = False
    network_transport_armed: bool = False
    network_socket_opened: bool = False
    bridge_mutation_performed: bool = False
    platform_db_mutation_performed: bool = False
    lacrm_call_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "response_capture_id", _require_text(self.response_capture_id, "response_capture_id"))
        object.__setattr__(self, "transport_execution_id", _require_text(self.transport_execution_id, "transport_execution_id"))

        forbidden_true_fields = (
            "bridge_response_captured",
            "bridge_post_called",
            "network_transport_implemented",
            "network_transport_enabled",
            "network_transport_armed",
            "network_socket_opened",
            "bridge_mutation_performed",
            "platform_db_mutation_performed",
            "lacrm_call_performed",
        )
        for field_name in forbidden_true_fields:
            if getattr(self, field_name) is True:
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 34.")


@dataclass(frozen=True)
class BridgeRoutingAuditContract:
    """Schema-only future audit linkage contract."""

    audit_contract_id: str
    transport_execution_id: str
    request_hash: str
    idempotency_key: str
    audit_row_id: str = ""
    audit_row_created: bool = False
    append_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "audit_contract_id", _require_text(self.audit_contract_id, "audit_contract_id"))
        object.__setattr__(self, "transport_execution_id", _require_text(self.transport_execution_id, "transport_execution_id"))
        object.__setattr__(self, "request_hash", _require_text(self.request_hash, "request_hash"))
        object.__setattr__(self, "idempotency_key", _require_text(self.idempotency_key, "idempotency_key"))
        if self.audit_row_created is True:
            raise ValueError("audit_row_created must remain False in Phase 20 Step 34.")


@dataclass(frozen=True)
class BridgeRoutingRollbackContract:
    """Schema-only future rollback linkage contract."""

    rollback_contract_id: str
    transport_execution_id: str
    rollback_snapshot_id: str = ""
    rollback_plan_hash: str = ""
    rollback_snapshot_created: bool = False
    rollback_row_created: bool = False
    append_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "rollback_contract_id", _require_text(self.rollback_contract_id, "rollback_contract_id"))
        object.__setattr__(self, "transport_execution_id", _require_text(self.transport_execution_id, "transport_execution_id"))
        if self.rollback_snapshot_created is True:
            raise ValueError("rollback_snapshot_created must remain False in Phase 20 Step 34.")
        if self.rollback_row_created is True:
            raise ValueError("rollback_row_created must remain False in Phase 20 Step 34.")


@dataclass(frozen=True)
class BridgeRoutingCutoverContract:
    """Schema-only future cutover linkage contract."""

    cutover_contract_id: str
    transport_execution_id: str
    cutover_packet_id: str = ""
    cutover_packet_hash: str = ""
    cutover_packet_created: bool = False
    cutover_approval_recorded: bool = False
    append_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "cutover_contract_id", _require_text(self.cutover_contract_id, "cutover_contract_id"))
        object.__setattr__(self, "transport_execution_id", _require_text(self.transport_execution_id, "transport_execution_id"))
        if self.cutover_packet_created is True:
            raise ValueError("cutover_packet_created must remain False in Phase 20 Step 34.")
        if self.cutover_approval_recorded is True:
            raise ValueError("cutover_approval_recorded must remain False in Phase 20 Step 34.")


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportContractPacket:
    """Schema-only packet composed of future contract surfaces."""

    request: BridgeRoutingTransportRequestContract
    response: BridgeRoutingTransportResponseContract
    audit: BridgeRoutingAuditContract
    rollback: BridgeRoutingRollbackContract
    cutover: BridgeRoutingCutoverContract
    schema_version: str = ROUTING_BRIDGE_NETWORK_TRANSPORT_CONTRACT_SCHEMA_VERSION
    contract_schema_scaffold_only: bool = True
    can_execute_bridge_write_now: bool = False
    can_open_network_boundary_now: bool = False
    can_call_bridge_post_now: bool = False

    def __post_init__(self) -> None:
        if self.contract_schema_scaffold_only is not True:
            raise ValueError("contract_schema_scaffold_only must remain True in Phase 20 Step 34.")
        if self.can_execute_bridge_write_now is True:
            raise ValueError("can_execute_bridge_write_now must remain False in Phase 20 Step 34.")
        if self.can_open_network_boundary_now is True:
            raise ValueError("can_open_network_boundary_now must remain False in Phase 20 Step 34.")
        if self.can_call_bridge_post_now is True:
            raise ValueError("can_call_bridge_post_now must remain False in Phase 20 Step 34.")


def contract_field_names(contract_type: type[Any]) -> list[str]:
    return [field.name for field in fields(contract_type)]


def build_sample_contract_packet() -> BridgeRoutingNetworkTransportContractPacket:
    request = BridgeRoutingTransportRequestContract(
        request_id="schema-only-request",
        transport_execution_id="schema-only-transport-execution",
        idempotency_key="schema-only-idempotency-key",
        phone="+10000000000",
        mode="manual",
        owner_type="unknown",
        label="schema only",
    )
    response = BridgeRoutingTransportResponseContract(
        response_capture_id="schema-only-response-capture",
        transport_execution_id=request.transport_execution_id,
    )
    audit = BridgeRoutingAuditContract(
        audit_contract_id="schema-only-audit-contract",
        transport_execution_id=request.transport_execution_id,
        request_hash="schema-only-request-hash",
        idempotency_key=request.idempotency_key,
    )
    rollback = BridgeRoutingRollbackContract(
        rollback_contract_id="schema-only-rollback-contract",
        transport_execution_id=request.transport_execution_id,
    )
    cutover = BridgeRoutingCutoverContract(
        cutover_contract_id="schema-only-cutover-contract",
        transport_execution_id=request.transport_execution_id,
    )
    return BridgeRoutingNetworkTransportContractPacket(
        request=request,
        response=response,
        audit=audit,
        rollback=rollback,
        cutover=cutover,
    )


def bridge_routing_network_transport_contract_schema_status() -> dict[str, Any]:
    return {
        "version": ROUTING_BRIDGE_NETWORK_TRANSPORT_CONTRACT_SCHEMA_VERSION,
        "contract_schema_scaffold_only": True,
        "schema_only_code_created": True,
        "execution_implementation_created": False,
        "real_bridge_http_client_implemented": False,
        "network_transport_implemented": False,
        "network_transport_enabled": False,
        "network_transport_armed": False,
        "network_socket_opened": False,
        "bridge_post_call_implemented": False,
        "bridge_post_called": False,
        "routing_write_endpoint_implemented": False,
        "bridge_mutation_performed": False,
        "platform_db_mutation_performed": False,
        "lacrm_call_performed": False,
        "audit_row_created": False,
        "rollback_row_created": False,
        "rollback_snapshot_created": False,
        "cutover_packet_created": False,
        "operator_approval_recorded": False,
        "confirmation_record_created": False,
        "environment_variables_set": False,
        "live_write_enabled": False,
        "can_execute_bridge_write_now": False,
        "can_open_network_boundary_now": False,
        "can_call_bridge_post_now": False,
        "contract_types": [
            "BridgeRoutingTransportRequestContract",
            "BridgeRoutingTransportResponseContract",
            "BridgeRoutingAuditContract",
            "BridgeRoutingRollbackContract",
            "BridgeRoutingCutoverContract",
            "BridgeRoutingNetworkTransportContractPacket",
        ],
        "message": (
            "Phase 20 Step 34 is schema-only. It defines future bridge routing transport "
            "contract surfaces but does not implement a bridge HTTP client, network transport, "
            "bridge POST, socket opening, database writes, LACRM calls, or live writes."
        ),
    }


def bridge_routing_network_transport_contract_schema_dict() -> dict[str, Any]:
    packet = build_sample_contract_packet()
    return {
        "status": bridge_routing_network_transport_contract_schema_status(),
        "schema": {
            "request_fields": contract_field_names(BridgeRoutingTransportRequestContract),
            "response_fields": contract_field_names(BridgeRoutingTransportResponseContract),
            "audit_fields": contract_field_names(BridgeRoutingAuditContract),
            "rollback_fields": contract_field_names(BridgeRoutingRollbackContract),
            "cutover_fields": contract_field_names(BridgeRoutingCutoverContract),
            "packet_fields": contract_field_names(BridgeRoutingNetworkTransportContractPacket),
        },
        "sample_packet": asdict(packet),
    }
