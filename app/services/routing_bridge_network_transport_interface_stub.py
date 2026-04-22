from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.services.routing_bridge_network_transport_contract_schema import (
    BridgeRoutingNetworkTransportContractPacket,
    BridgeRoutingTransportRequestContract,
    BridgeRoutingTransportResponseContract,
    build_sample_contract_packet,
)


ROUTING_BRIDGE_NETWORK_TRANSPORT_INTERFACE_STUB_VERSION = "phase20_step35_non_network_interface_stub_v1"


class BridgeRoutingNetworkTransportNotImplemented(NotImplementedError):
    """Raised when a future bridge routing transport execution path is requested too early."""


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportInterfaceStub:
    """Non-network interface stub for future bridge routing transport.

    Phase 20 Step 35 intentionally provides interface shape only. The execution,
    network boundary, and bridge POST methods raise NotImplementedError so the
    future implementation boundary is explicit and testable.
    """

    interface_version: str = ROUTING_BRIDGE_NETWORK_TRANSPORT_INTERFACE_STUB_VERSION
    interface_stub_scaffold_only: bool = True
    non_network_interface_stub_created: bool = True
    execution_implementation_created: bool = False
    real_bridge_http_client_implemented: bool = False
    network_transport_implemented: bool = False
    network_transport_enabled: bool = False
    network_transport_armed: bool = False
    network_socket_opened: bool = False
    bridge_post_call_implemented: bool = False
    bridge_post_called: bool = False
    routing_write_endpoint_implemented: bool = False
    bridge_mutation_performed: bool = False
    platform_db_mutation_performed: bool = False
    lacrm_call_performed: bool = False
    audit_row_created: bool = False
    rollback_row_created: bool = False
    rollback_snapshot_created: bool = False
    cutover_packet_created: bool = False
    operator_approval_recorded: bool = False
    confirmation_record_created: bool = False
    environment_variables_set: bool = False
    live_write_enabled: bool = False

    def __post_init__(self) -> None:
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
            "bridge_mutation_performed",
            "platform_db_mutation_performed",
            "lacrm_call_performed",
            "audit_row_created",
            "rollback_row_created",
            "rollback_snapshot_created",
            "cutover_packet_created",
            "operator_approval_recorded",
            "confirmation_record_created",
            "environment_variables_set",
            "live_write_enabled",
        )
        if self.interface_stub_scaffold_only is not True:
            raise ValueError("interface_stub_scaffold_only must remain True in Phase 20 Step 35.")
        if self.non_network_interface_stub_created is not True:
            raise ValueError("non_network_interface_stub_created must remain True in Phase 20 Step 35.")
        for field_name in required_false_fields:
            if getattr(self, field_name) is True:
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 35.")

    def validate_contract_packet_shape(
        self,
        packet: BridgeRoutingNetworkTransportContractPacket,
    ) -> dict[str, Any]:
        """Validate only the schema shape and hard no-execution flags."""

        if not isinstance(packet, BridgeRoutingNetworkTransportContractPacket):
            raise TypeError("packet must be a BridgeRoutingNetworkTransportContractPacket.")

        return {
            "valid_contract_packet_shape": True,
            "schema_version": packet.schema_version,
            "contract_schema_scaffold_only": packet.contract_schema_scaffold_only,
            "can_execute_bridge_write_now": packet.can_execute_bridge_write_now,
            "can_open_network_boundary_now": packet.can_open_network_boundary_now,
            "can_call_bridge_post_now": packet.can_call_bridge_post_now,
            "execution_implementation_created": False,
            "network_transport_implemented": False,
            "bridge_post_called": False,
        }

    def execute_bridge_routing_transport(
        self,
        request: BridgeRoutingTransportRequestContract,
    ) -> BridgeRoutingTransportResponseContract:
        raise BridgeRoutingNetworkTransportNotImplemented(
            "Bridge routing network transport execution is not implemented in Phase 20 Step 35."
        )

    def open_network_boundary(self, request: BridgeRoutingTransportRequestContract) -> None:
        raise BridgeRoutingNetworkTransportNotImplemented(
            "Opening a bridge routing network socket is not implemented in Phase 20 Step 35."
        )

    def call_bridge_post(self, request: BridgeRoutingTransportRequestContract) -> None:
        raise BridgeRoutingNetworkTransportNotImplemented(
            "Calling bridge POST endpoints is not implemented in Phase 20 Step 35."
        )

    def create_audit_row(self, packet: BridgeRoutingNetworkTransportContractPacket) -> None:
        raise BridgeRoutingNetworkTransportNotImplemented(
            "Creating bridge routing transport audit rows is not implemented in Phase 20 Step 35."
        )

    def create_rollback_snapshot(self, packet: BridgeRoutingNetworkTransportContractPacket) -> None:
        raise BridgeRoutingNetworkTransportNotImplemented(
            "Creating bridge routing transport rollback snapshots is not implemented in Phase 20 Step 35."
        )


def build_bridge_routing_network_transport_interface_stub() -> BridgeRoutingNetworkTransportInterfaceStub:
    return BridgeRoutingNetworkTransportInterfaceStub()


def bridge_routing_network_transport_interface_stub_status() -> dict[str, Any]:
    stub = build_bridge_routing_network_transport_interface_stub()
    return {
        "version": ROUTING_BRIDGE_NETWORK_TRANSPORT_INTERFACE_STUB_VERSION,
        "interface_stub_scaffold_only": stub.interface_stub_scaffold_only,
        "non_network_interface_stub_created": stub.non_network_interface_stub_created,
        "execution_implementation_created": stub.execution_implementation_created,
        "real_bridge_http_client_implemented": stub.real_bridge_http_client_implemented,
        "network_transport_implemented": stub.network_transport_implemented,
        "network_transport_enabled": stub.network_transport_enabled,
        "network_transport_armed": stub.network_transport_armed,
        "network_socket_opened": stub.network_socket_opened,
        "bridge_post_call_implemented": stub.bridge_post_call_implemented,
        "bridge_post_called": stub.bridge_post_called,
        "routing_write_endpoint_implemented": stub.routing_write_endpoint_implemented,
        "bridge_mutation_performed": stub.bridge_mutation_performed,
        "platform_db_mutation_performed": stub.platform_db_mutation_performed,
        "lacrm_call_performed": stub.lacrm_call_performed,
        "audit_row_created": stub.audit_row_created,
        "rollback_row_created": stub.rollback_row_created,
        "rollback_snapshot_created": stub.rollback_snapshot_created,
        "cutover_packet_created": stub.cutover_packet_created,
        "operator_approval_recorded": stub.operator_approval_recorded,
        "confirmation_record_created": stub.confirmation_record_created,
        "environment_variables_set": stub.environment_variables_set,
        "live_write_enabled": stub.live_write_enabled,
        "can_execute_bridge_write_now": False,
        "can_add_network_transport_now": False,
        "can_enable_network_transport_now": False,
        "can_arm_network_transport_now": False,
        "can_open_network_socket_now": False,
        "can_add_real_bridge_http_client_now": False,
        "can_add_bridge_post_now": False,
        "can_create_audit_rows_now": False,
        "can_create_rollback_rows_now": False,
        "can_create_rollback_snapshots_now": False,
        "not_implemented_methods": [
            "execute_bridge_routing_transport",
            "open_network_boundary",
            "call_bridge_post",
            "create_audit_row",
            "create_rollback_snapshot",
        ],
        "message": (
            "Phase 20 Step 35 is a non-network interface stub only. It defines future "
            "method boundaries with explicit NotImplementedError behavior but does not "
            "implement bridge HTTP, network transport, sockets, bridge POST, database "
            "writes, LACRM calls, or live writes."
        ),
    }


def bridge_routing_network_transport_interface_stub_packet_dict() -> dict[str, Any]:
    stub = build_bridge_routing_network_transport_interface_stub()
    sample_packet = build_sample_contract_packet()
    return {
        "status": bridge_routing_network_transport_interface_stub_status(),
        "stub": asdict(stub),
        "sample_contract_validation": stub.validate_contract_packet_shape(sample_packet),
        "sample_contract_packet": asdict(sample_packet),
    }
