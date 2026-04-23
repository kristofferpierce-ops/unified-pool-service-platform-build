from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.services.routing_bridge_network_transport_contract_schema import (
    BridgeRoutingNetworkTransportContractPacket,
    build_sample_contract_packet,
)
from app.services.routing_bridge_network_transport_dry_run_adapter_wrapper import (
    BridgeRoutingNetworkTransportDryRunAdapterWrapper,
    BridgeRoutingNetworkTransportDryRunAdapterWrapperResult,
    build_bridge_routing_network_transport_dry_run_adapter_wrapper,
)


ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_ENVELOPE_VERSION = "phase20_step37_guard_envelope_v1"

GuardEnvelopeDecision = Literal["preview_allowed_no_execution", "blocked_no_write"]


class BridgeRoutingNetworkTransportGuardBlocked(RuntimeError):
    """Raised when a guarded future execution attempt is requested too early."""


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportGuardEnvelopeDecisionResult:
    """Guard-envelope decision for future bridge routing network transport.

    This result is guard-only. It intentionally records that no execution
    implementation ran, no socket opened, no bridge POST call happened, and no
    bridge response was captured.
    """

    guard_run_id: str
    transport_execution_id: str
    request_id: str
    guard_decision: GuardEnvelopeDecision = "preview_allowed_no_execution"
    guard_envelope_only: bool = True
    guard_preview_created: bool = True
    dry_run_preview_allowed: bool = True
    future_execution_allowed: bool = False
    future_network_boundary_allowed: bool = False
    future_bridge_post_allowed: bool = False
    execution_implementation_created: bool = False
    real_bridge_http_client_implemented: bool = False
    network_transport_implemented: bool = False
    network_transport_enabled: bool = False
    network_transport_armed: bool = False
    network_socket_opened: bool = False
    bridge_post_call_implemented: bool = False
    bridge_post_called: bool = False
    routing_write_endpoint_implemented: bool = False
    bridge_response_captured: bool = False
    response_capture_record_created: bool = False
    audit_row_created: bool = False
    rollback_row_created: bool = False
    rollback_snapshot_created: bool = False
    cutover_packet_created: bool = False
    operator_approval_recorded: bool = False
    confirmation_record_created: bool = False
    environment_variables_set: bool = False
    bridge_mutation_performed: bool = False
    platform_db_mutation_performed: bool = False
    lacrm_call_performed: bool = False
    live_write_enabled: bool = False
    guard_message: str = (
        "Guard envelope preview only. No execution implementation, network transport, "
        "socket opening, bridge POST, database write, LACRM call, or live write occurred."
    )

    def __post_init__(self) -> None:
        if self.guard_envelope_only is not True:
            raise ValueError("guard_envelope_only must remain True in Phase 20 Step 37.")
        if self.guard_preview_created is not True:
            raise ValueError("guard_preview_created must remain True in Phase 20 Step 37.")
        if self.future_execution_allowed is True:
            raise ValueError("future_execution_allowed must remain False in Phase 20 Step 37.")
        if self.future_network_boundary_allowed is True:
            raise ValueError("future_network_boundary_allowed must remain False in Phase 20 Step 37.")
        if self.future_bridge_post_allowed is True:
            raise ValueError("future_bridge_post_allowed must remain False in Phase 20 Step 37.")

        required_false_fields = (
            "execution_implementation_created",
            "real_bridge_http_client_implemented",
            "network_transport_implemented",
            "network_transport_enabled",
            "network_transport_armed",
            "network_socket_opened",
            "bridge_post_call_implemented",
            "bridge_post_called",
            "routing_write_endpoint_implemented",
            "bridge_response_captured",
            "response_capture_record_created",
            "audit_row_created",
            "rollback_row_created",
            "rollback_snapshot_created",
            "cutover_packet_created",
            "operator_approval_recorded",
            "confirmation_record_created",
            "environment_variables_set",
            "bridge_mutation_performed",
            "platform_db_mutation_performed",
            "lacrm_call_performed",
            "live_write_enabled",
        )
        for field_name in required_false_fields:
            if getattr(self, field_name) is True:
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 37.")


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportGuardEnvelope:
    """Guard envelope around the preview-only dry-run adapter wrapper.

    Phase 20 Step 37 validates the dry-run wrapper preview and returns a guard
    decision. It does not call interface execution methods and does not cross any
    network boundary.
    """

    guard_version: str = ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_ENVELOPE_VERSION
    guard_envelope_only: bool = True
    dry_run_adapter_wrapper_required: bool = True
    preview_only_guard_created: bool = True
    execution_implementation_created: bool = False
    real_bridge_http_client_implemented: bool = False
    network_transport_implemented: bool = False
    network_transport_enabled: bool = False
    network_transport_armed: bool = False
    network_socket_opened: bool = False
    bridge_post_call_implemented: bool = False
    bridge_post_called: bool = False
    routing_write_endpoint_implemented: bool = False
    bridge_response_captured: bool = False
    response_capture_record_created: bool = False
    audit_row_created: bool = False
    rollback_row_created: bool = False
    rollback_snapshot_created: bool = False
    cutover_packet_created: bool = False
    operator_approval_recorded: bool = False
    confirmation_record_created: bool = False
    environment_variables_set: bool = False
    bridge_mutation_performed: bool = False
    platform_db_mutation_performed: bool = False
    lacrm_call_performed: bool = False
    live_write_enabled: bool = False

    def __post_init__(self) -> None:
        if self.guard_envelope_only is not True:
            raise ValueError("guard_envelope_only must remain True in Phase 20 Step 37.")
        if self.dry_run_adapter_wrapper_required is not True:
            raise ValueError("dry_run_adapter_wrapper_required must remain True in Phase 20 Step 37.")
        if self.preview_only_guard_created is not True:
            raise ValueError("preview_only_guard_created must remain True in Phase 20 Step 37.")

        required_false_fields = (
            "execution_implementation_created",
            "real_bridge_http_client_implemented",
            "network_transport_implemented",
            "network_transport_enabled",
            "network_transport_armed",
            "network_socket_opened",
            "bridge_post_call_implemented",
            "bridge_post_called",
            "routing_write_endpoint_implemented",
            "bridge_response_captured",
            "response_capture_record_created",
            "audit_row_created",
            "rollback_row_created",
            "rollback_snapshot_created",
            "cutover_packet_created",
            "operator_approval_recorded",
            "confirmation_record_created",
            "environment_variables_set",
            "bridge_mutation_performed",
            "platform_db_mutation_performed",
            "lacrm_call_performed",
            "live_write_enabled",
        )
        for field_name in required_false_fields:
            if getattr(self, field_name) is True:
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 37.")

    def evaluate_preview(
        self,
        packet: BridgeRoutingNetworkTransportContractPacket,
        wrapper: BridgeRoutingNetworkTransportDryRunAdapterWrapper | None = None,
    ) -> BridgeRoutingNetworkTransportGuardEnvelopeDecisionResult:
        adapter = wrapper or build_bridge_routing_network_transport_dry_run_adapter_wrapper()
        preview = adapter.build_preview(packet)
        self._validate_preview_safety(preview)

        return BridgeRoutingNetworkTransportGuardEnvelopeDecisionResult(
            guard_run_id=f"guard-envelope:{packet.request.transport_execution_id}",
            transport_execution_id=packet.request.transport_execution_id,
            request_id=packet.request.request_id,
        )

    def _validate_preview_safety(
        self,
        preview: BridgeRoutingNetworkTransportDryRunAdapterWrapperResult,
    ) -> None:
        if preview.execution_implementation_created:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported execution implementation.")
        if preview.network_transport_implemented:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported network transport.")
        if preview.network_socket_opened:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported socket opening.")
        if preview.bridge_post_called:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported bridge POST.")
        if preview.bridge_response_captured:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported bridge response capture.")
        if preview.platform_db_mutation_performed:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported platform DB mutation.")
        if preview.bridge_mutation_performed:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported bridge mutation.")
        if preview.lacrm_call_performed:
            raise BridgeRoutingNetworkTransportGuardBlocked("Preview reported LACRM call.")

    def block_future_execution_attempt(self) -> None:
        raise BridgeRoutingNetworkTransportGuardBlocked(
            "Bridge routing network transport execution remains blocked in Phase 20 Step 37."
        )


def build_bridge_routing_network_transport_guard_envelope() -> BridgeRoutingNetworkTransportGuardEnvelope:
    return BridgeRoutingNetworkTransportGuardEnvelope()


def bridge_routing_network_transport_guard_envelope_status() -> dict[str, Any]:
    guard = build_bridge_routing_network_transport_guard_envelope()
    return {
        "version": ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_ENVELOPE_VERSION,
        "guard_envelope_only": guard.guard_envelope_only,
        "dry_run_adapter_wrapper_required": guard.dry_run_adapter_wrapper_required,
        "preview_only_guard_created": guard.preview_only_guard_created,
        "execution_implementation_created": guard.execution_implementation_created,
        "real_bridge_http_client_implemented": guard.real_bridge_http_client_implemented,
        "network_transport_implemented": guard.network_transport_implemented,
        "network_transport_enabled": guard.network_transport_enabled,
        "network_transport_armed": guard.network_transport_armed,
        "network_socket_opened": guard.network_socket_opened,
        "bridge_post_call_implemented": guard.bridge_post_call_implemented,
        "bridge_post_called": guard.bridge_post_called,
        "routing_write_endpoint_implemented": guard.routing_write_endpoint_implemented,
        "bridge_response_captured": guard.bridge_response_captured,
        "response_capture_record_created": guard.response_capture_record_created,
        "audit_row_created": guard.audit_row_created,
        "rollback_row_created": guard.rollback_row_created,
        "rollback_snapshot_created": guard.rollback_snapshot_created,
        "cutover_packet_created": guard.cutover_packet_created,
        "operator_approval_recorded": guard.operator_approval_recorded,
        "confirmation_record_created": guard.confirmation_record_created,
        "environment_variables_set": guard.environment_variables_set,
        "bridge_mutation_performed": guard.bridge_mutation_performed,
        "platform_db_mutation_performed": guard.platform_db_mutation_performed,
        "lacrm_call_performed": guard.lacrm_call_performed,
        "live_write_enabled": guard.live_write_enabled,
        "can_execute_bridge_write_now": False,
        "can_add_network_transport_now": False,
        "can_enable_network_transport_now": False,
        "can_arm_network_transport_now": False,
        "can_open_network_socket_now": False,
        "can_add_real_bridge_http_client_now": False,
        "can_add_bridge_post_now": False,
        "can_capture_bridge_response_now": False,
        "can_create_response_capture_records_now": False,
        "can_create_audit_rows_now": False,
        "can_create_rollback_rows_now": False,
        "can_create_rollback_snapshots_now": False,
        "message": (
            "Phase 20 Step 37 is a guard envelope only. It evaluates the dry-run "
            "adapter wrapper preview and returns a no-execution guard decision without "
            "bridge HTTP, network transport, sockets, bridge POST, database writes, "
            "LACRM calls, or live writes."
        ),
    }


def bridge_routing_network_transport_guard_envelope_packet_dict() -> dict[str, Any]:
    guard = build_bridge_routing_network_transport_guard_envelope()
    sample_packet = build_sample_contract_packet()
    decision = guard.evaluate_preview(sample_packet)
    return {
        "status": bridge_routing_network_transport_guard_envelope_status(),
        "guard": asdict(guard),
        "sample_guard_decision": asdict(decision),
        "sample_contract_packet": asdict(sample_packet),
    }
