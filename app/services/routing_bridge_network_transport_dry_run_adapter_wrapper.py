from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.services.routing_bridge_network_transport_contract_schema import (
    BridgeRoutingNetworkTransportContractPacket,
    build_sample_contract_packet,
)
from app.services.routing_bridge_network_transport_interface_stub import (
    BridgeRoutingNetworkTransportInterfaceStub,
    build_bridge_routing_network_transport_interface_stub,
)


ROUTING_BRIDGE_NETWORK_TRANSPORT_DRY_RUN_ADAPTER_WRAPPER_VERSION = "phase20_step36_dry_run_adapter_wrapper_v1"


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportDryRunAdapterWrapperResult:
    """Dry-run preview result for future bridge routing network transport.

    This result is preview-only. It intentionally records that no bridge response
    was captured, no execution implementation ran, no socket opened, and no bridge
    POST call happened.
    """

    adapter_run_id: str
    transport_execution_id: str
    request_id: str
    dry_run_adapter_wrapper_only: bool = True
    dry_run_preview_created: bool = True
    interface_stub_used: bool = True
    contract_packet_validated: bool = True
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
    would_execute_future_transport: bool = False
    would_open_future_socket: bool = False
    would_call_future_bridge_post: bool = False
    preview_message: str = (
        "Dry-run adapter wrapper preview only. No execution implementation, network "
        "transport, socket opening, bridge POST, database write, LACRM call, or live write occurred."
    )

    def __post_init__(self) -> None:
        if self.dry_run_adapter_wrapper_only is not True:
            raise ValueError("dry_run_adapter_wrapper_only must remain True in Phase 20 Step 36.")
        if self.dry_run_preview_created is not True:
            raise ValueError("dry_run_preview_created must remain True in Phase 20 Step 36.")

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
            "would_execute_future_transport",
            "would_open_future_socket",
            "would_call_future_bridge_post",
        )
        for field_name in required_false_fields:
            if getattr(self, field_name) is True:
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 36.")


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportDryRunAdapterWrapper:
    """Adapter wrapper around the non-network interface stub.

    Phase 20 Step 36 validates contract shape and produces a preview-only result.
    It does not call the interface execution methods and does not cross any network
    boundary.
    """

    wrapper_version: str = ROUTING_BRIDGE_NETWORK_TRANSPORT_DRY_RUN_ADAPTER_WRAPPER_VERSION
    dry_run_adapter_wrapper_only: bool = True
    non_network_interface_stub_required: bool = True
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
        if self.dry_run_adapter_wrapper_only is not True:
            raise ValueError("dry_run_adapter_wrapper_only must remain True in Phase 20 Step 36.")
        if self.non_network_interface_stub_required is not True:
            raise ValueError("non_network_interface_stub_required must remain True in Phase 20 Step 36.")

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
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 36.")

    def build_preview(
        self,
        packet: BridgeRoutingNetworkTransportContractPacket,
        interface_stub: BridgeRoutingNetworkTransportInterfaceStub | None = None,
    ) -> BridgeRoutingNetworkTransportDryRunAdapterWrapperResult:
        stub = interface_stub or build_bridge_routing_network_transport_interface_stub()
        validation = stub.validate_contract_packet_shape(packet)
        if validation.get("valid_contract_packet_shape") is not True:
            raise ValueError("Contract packet shape validation failed.")

        return BridgeRoutingNetworkTransportDryRunAdapterWrapperResult(
            adapter_run_id=f"dry-run-wrapper:{packet.request.transport_execution_id}",
            transport_execution_id=packet.request.transport_execution_id,
            request_id=packet.request.request_id,
        )


def build_bridge_routing_network_transport_dry_run_adapter_wrapper() -> BridgeRoutingNetworkTransportDryRunAdapterWrapper:
    return BridgeRoutingNetworkTransportDryRunAdapterWrapper()


def bridge_routing_network_transport_dry_run_adapter_wrapper_status() -> dict[str, Any]:
    wrapper = build_bridge_routing_network_transport_dry_run_adapter_wrapper()
    return {
        "version": ROUTING_BRIDGE_NETWORK_TRANSPORT_DRY_RUN_ADAPTER_WRAPPER_VERSION,
        "dry_run_adapter_wrapper_only": wrapper.dry_run_adapter_wrapper_only,
        "non_network_interface_stub_required": wrapper.non_network_interface_stub_required,
        "execution_implementation_created": wrapper.execution_implementation_created,
        "real_bridge_http_client_implemented": wrapper.real_bridge_http_client_implemented,
        "network_transport_implemented": wrapper.network_transport_implemented,
        "network_transport_enabled": wrapper.network_transport_enabled,
        "network_transport_armed": wrapper.network_transport_armed,
        "network_socket_opened": wrapper.network_socket_opened,
        "bridge_post_call_implemented": wrapper.bridge_post_call_implemented,
        "bridge_post_called": wrapper.bridge_post_called,
        "routing_write_endpoint_implemented": wrapper.routing_write_endpoint_implemented,
        "bridge_response_captured": wrapper.bridge_response_captured,
        "response_capture_record_created": wrapper.response_capture_record_created,
        "audit_row_created": wrapper.audit_row_created,
        "rollback_row_created": wrapper.rollback_row_created,
        "rollback_snapshot_created": wrapper.rollback_snapshot_created,
        "cutover_packet_created": wrapper.cutover_packet_created,
        "operator_approval_recorded": wrapper.operator_approval_recorded,
        "confirmation_record_created": wrapper.confirmation_record_created,
        "environment_variables_set": wrapper.environment_variables_set,
        "bridge_mutation_performed": wrapper.bridge_mutation_performed,
        "platform_db_mutation_performed": wrapper.platform_db_mutation_performed,
        "lacrm_call_performed": wrapper.lacrm_call_performed,
        "live_write_enabled": wrapper.live_write_enabled,
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
            "Phase 20 Step 36 is a dry-run adapter wrapper only. It validates the "
            "contract packet shape through the non-network interface stub and returns "
            "a preview result without execution implementation, bridge HTTP, network "
            "transport, sockets, bridge POST, database writes, LACRM calls, or live writes."
        ),
    }


def bridge_routing_network_transport_dry_run_adapter_wrapper_packet_dict() -> dict[str, Any]:
    wrapper = build_bridge_routing_network_transport_dry_run_adapter_wrapper()
    sample_packet = build_sample_contract_packet()
    preview = wrapper.build_preview(sample_packet)
    return {
        "status": bridge_routing_network_transport_dry_run_adapter_wrapper_status(),
        "wrapper": asdict(wrapper),
        "sample_preview": asdict(preview),
        "sample_contract_packet": asdict(sample_packet),
    }
