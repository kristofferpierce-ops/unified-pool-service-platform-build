from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.services.routing_bridge_network_transport_contract_schema import (
    BridgeRoutingNetworkTransportContractPacket,
    build_sample_contract_packet,
)
from app.services.routing_bridge_network_transport_guard_envelope import (
    BridgeRoutingNetworkTransportGuardEnvelope,
    BridgeRoutingNetworkTransportGuardEnvelopeDecisionResult,
    build_bridge_routing_network_transport_guard_envelope,
)


ROUTING_BRIDGE_NETWORK_TRANSPORT_READINESS_REPORT_VERSION = "phase20_step38_readiness_report_v1"

ReadinessReportStatus = Literal["ready_for_review_no_execution", "blocked_no_write"]


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportReadinessReportResult:
    """No-write readiness report for future bridge routing network transport.

    This result summarizes the Step 37 guard decision and keeps every live
    transport, socket, bridge POST, response-capture, audit, rollback, mutation,
    and LACRM flag false.
    """

    readiness_report_id: str
    transport_execution_id: str
    request_id: str
    readiness_status: ReadinessReportStatus = "ready_for_review_no_execution"
    readiness_report_only: bool = True
    readiness_preview_created: bool = True
    guard_decision_seen: str = "preview_allowed_no_execution"
    guard_preview_created: bool = True
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
    cutover_approval_recorded: bool = False
    operator_approval_recorded: bool = False
    confirmation_record_created: bool = False
    environment_variables_set: bool = False
    bridge_mutation_performed: bool = False
    platform_db_mutation_performed: bool = False
    lacrm_call_performed: bool = False
    live_write_enabled: bool = False
    future_execution_allowed: bool = False
    future_network_boundary_allowed: bool = False
    future_bridge_post_allowed: bool = False
    report_message: str = (
        "Readiness report preview only. This packet is ready for review but does not "
        "authorize execution implementation, network transport, socket opening, bridge POST, "
        "response capture, database writes, LACRM calls, or live writes."
    )

    def __post_init__(self) -> None:
        if self.readiness_report_only is not True:
            raise ValueError("readiness_report_only must remain True in Phase 20 Step 38.")
        if self.readiness_preview_created is not True:
            raise ValueError("readiness_preview_created must remain True in Phase 20 Step 38.")
        if self.future_execution_allowed is True:
            raise ValueError("future_execution_allowed must remain False in Phase 20 Step 38.")
        if self.future_network_boundary_allowed is True:
            raise ValueError("future_network_boundary_allowed must remain False in Phase 20 Step 38.")
        if self.future_bridge_post_allowed is True:
            raise ValueError("future_bridge_post_allowed must remain False in Phase 20 Step 38.")

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
            "cutover_approval_recorded",
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
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 38.")


@dataclass(frozen=True)
class BridgeRoutingNetworkTransportReadinessReport:
    """Readiness report wrapper around the Step 37 guard envelope.

    Phase 20 Step 38 produces a no-write report. It does not call interface
    execution methods and does not cross any network boundary.
    """

    report_version: str = ROUTING_BRIDGE_NETWORK_TRANSPORT_READINESS_REPORT_VERSION
    readiness_report_only: bool = True
    guard_envelope_required: bool = True
    preview_only_report_created: bool = True
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
    cutover_approval_recorded: bool = False
    operator_approval_recorded: bool = False
    confirmation_record_created: bool = False
    environment_variables_set: bool = False
    bridge_mutation_performed: bool = False
    platform_db_mutation_performed: bool = False
    lacrm_call_performed: bool = False
    live_write_enabled: bool = False

    def __post_init__(self) -> None:
        if self.readiness_report_only is not True:
            raise ValueError("readiness_report_only must remain True in Phase 20 Step 38.")
        if self.guard_envelope_required is not True:
            raise ValueError("guard_envelope_required must remain True in Phase 20 Step 38.")
        if self.preview_only_report_created is not True:
            raise ValueError("preview_only_report_created must remain True in Phase 20 Step 38.")

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
            "cutover_approval_recorded",
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
                raise ValueError(f"{field_name} must remain False in Phase 20 Step 38.")

    def build_report(
        self,
        packet: BridgeRoutingNetworkTransportContractPacket,
        guard: BridgeRoutingNetworkTransportGuardEnvelope | None = None,
    ) -> BridgeRoutingNetworkTransportReadinessReportResult:
        guard_envelope = guard or build_bridge_routing_network_transport_guard_envelope()
        decision = guard_envelope.evaluate_preview(packet)
        self._validate_guard_decision(decision)

        return BridgeRoutingNetworkTransportReadinessReportResult(
            readiness_report_id=f"readiness-report:{packet.request.transport_execution_id}",
            transport_execution_id=packet.request.transport_execution_id,
            request_id=packet.request.request_id,
            guard_decision_seen=decision.guard_decision,
            guard_preview_created=decision.guard_preview_created,
        )

    def _validate_guard_decision(
        self,
        decision: BridgeRoutingNetworkTransportGuardEnvelopeDecisionResult,
    ) -> None:
        if decision.future_execution_allowed:
            raise ValueError("Guard decision unexpectedly allowed future execution.")
        if decision.future_network_boundary_allowed:
            raise ValueError("Guard decision unexpectedly allowed future network boundary.")
        if decision.future_bridge_post_allowed:
            raise ValueError("Guard decision unexpectedly allowed future bridge POST.")
        if decision.execution_implementation_created:
            raise ValueError("Guard decision reported execution implementation.")
        if decision.network_transport_implemented:
            raise ValueError("Guard decision reported network transport.")
        if decision.network_socket_opened:
            raise ValueError("Guard decision reported socket opening.")
        if decision.bridge_post_called:
            raise ValueError("Guard decision reported bridge POST.")
        if decision.bridge_response_captured:
            raise ValueError("Guard decision reported bridge response capture.")
        if decision.platform_db_mutation_performed:
            raise ValueError("Guard decision reported platform DB mutation.")
        if decision.bridge_mutation_performed:
            raise ValueError("Guard decision reported bridge mutation.")
        if decision.lacrm_call_performed:
            raise ValueError("Guard decision reported LACRM call.")


def build_bridge_routing_network_transport_readiness_report() -> BridgeRoutingNetworkTransportReadinessReport:
    return BridgeRoutingNetworkTransportReadinessReport()


def bridge_routing_network_transport_readiness_report_status() -> dict[str, Any]:
    report = build_bridge_routing_network_transport_readiness_report()
    return {
        "version": ROUTING_BRIDGE_NETWORK_TRANSPORT_READINESS_REPORT_VERSION,
        "readiness_report_only": report.readiness_report_only,
        "guard_envelope_required": report.guard_envelope_required,
        "preview_only_report_created": report.preview_only_report_created,
        "execution_implementation_created": report.execution_implementation_created,
        "real_bridge_http_client_implemented": report.real_bridge_http_client_implemented,
        "network_transport_implemented": report.network_transport_implemented,
        "network_transport_enabled": report.network_transport_enabled,
        "network_transport_armed": report.network_transport_armed,
        "network_socket_opened": report.network_socket_opened,
        "bridge_post_call_implemented": report.bridge_post_call_implemented,
        "bridge_post_called": report.bridge_post_called,
        "routing_write_endpoint_implemented": report.routing_write_endpoint_implemented,
        "bridge_response_captured": report.bridge_response_captured,
        "response_capture_record_created": report.response_capture_record_created,
        "audit_row_created": report.audit_row_created,
        "rollback_row_created": report.rollback_row_created,
        "rollback_snapshot_created": report.rollback_snapshot_created,
        "cutover_packet_created": report.cutover_packet_created,
        "cutover_approval_recorded": report.cutover_approval_recorded,
        "operator_approval_recorded": report.operator_approval_recorded,
        "confirmation_record_created": report.confirmation_record_created,
        "environment_variables_set": report.environment_variables_set,
        "bridge_mutation_performed": report.bridge_mutation_performed,
        "platform_db_mutation_performed": report.platform_db_mutation_performed,
        "lacrm_call_performed": report.lacrm_call_performed,
        "live_write_enabled": report.live_write_enabled,
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
        "can_create_cutover_packets_now": False,
        "message": (
            "Phase 20 Step 38 is a readiness report only. It summarizes the Step 37 "
            "guard envelope decision and returns a no-execution readiness report without "
            "bridge HTTP, network transport, sockets, bridge POST, response capture, "
            "database writes, LACRM calls, or live writes."
        ),
    }


def bridge_routing_network_transport_readiness_report_packet_dict() -> dict[str, Any]:
    report = build_bridge_routing_network_transport_readiness_report()
    sample_packet = build_sample_contract_packet()
    readiness = report.build_report(sample_packet)
    return {
        "status": bridge_routing_network_transport_readiness_report_status(),
        "report": asdict(report),
        "sample_readiness_report": asdict(readiness),
        "sample_contract_packet": asdict(sample_packet),
    }
