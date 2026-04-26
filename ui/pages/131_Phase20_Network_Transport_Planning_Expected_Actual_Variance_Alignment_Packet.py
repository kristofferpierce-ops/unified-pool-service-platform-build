"""Phase 22 Step 25 expected actual variance alignment page.

This Streamlit page is intentionally read-only. It records planning alignment
between Phase 20 network transport planning and the expected vs actual variance
layer needed for operating intelligence, without starting runtime work.
"""

from __future__ import annotations

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


TITLE = "Phase 22 Step 25 - Phase 20 Network Transport Planning Expected Actual Variance Alignment Packet"

SAFETY_FLAGS = {
    "planning_only": True,
    "no_platform_db_mutation": True,
    "no_bridge_mutation": True,
    "no_real_bridge_http_client": True,
    "no_network_transport_implementation": True,
    "no_bridge_post": True,
    "no_network_sockets": True,
    "no_execution_implementation": True,
    "implementation_phase_start": False,
    "operator_signoff_creation": False,
    "operator_approval_creation": False,
    "final_approval_creation": False,
    "design_closure_record_creation": False,
    "lacrm_default_mode": "dry_run",
    "live_write_disabled": True,
    "live_write_unarmed": True,
    "source_bucket_writes": False,
    "canonical_event_ledger_writes": False,
    "expected_actual_alignment_mode": "planning_variance_traceability_only",
    "expected_actual_writes": False,
    "expected_actual_runtime": False,
    "variance_analysis_runtime": False,
    "probability_update_runtime": False,
    "operating_intelligence_runtime": False,
}

EXPECTED_ACTUAL_VARIANCE_ALIGNMENT = {
    "read_only_status": "Read-only planning checkpoint",
    "connector_first_operating_core": True,
    "source_bucket_alignment": "raw_normalized_matched_approved_applied",
    "canonical_event_ledger_dependency": "events_must_be_time_stamped_and_entity_tied",
    "expected_actual_alignment": "variance_confidence_driver_attribution",
    "required_future_estimate_fields": [
        "entity_id",
        "event_id",
        "model_name",
        "model_version",
        "input_snapshot",
        "expected_output",
        "actual_output",
        "variance",
        "confidence_score",
        "driver_attribution",
        "business_result",
    ],
    "expected_actual_domains": [
        "chemical_usage",
        "labor_minutes",
        "drive_time",
        "parts_material_cost",
        "billing_collection_speed",
        "quote_accuracy",
        "route_profitability",
        "account_margin",
    ],
    "blocked_runtime_outcomes": [
        "creating expected actual tables",
        "writing expected values",
        "writing actual values",
        "running variance analysis",
        "running probability updates",
        "starting recommendation engine",
    ],
}


DRIVER_MODELS_FOR_LATER = [
    "climate_baseline",
    "chemical_usage_baseline",
    "labor_baseline",
    "overhead_baseline",
    "branch_prior",
    "seasonal_prior",
    "tech_prior",
    "account_class_prior",
]


def render() -> None:
    """Render the planning-only page when Streamlit is available."""
    if st is None:
        return

    st.set_page_config(page_title="Phase 22 Step 25", layout="wide")
    st.title(TITLE)
    st.info("Read-only planning checkpoint. No transport, bridge, database, variance engine, or LACRM write is enabled here.")

    left, right = st.columns(2)
    with left:
        st.subheader("Safety posture")
        st.json(SAFETY_FLAGS)
    with right:
        st.subheader("Expected actual variance alignment")
        st.json(EXPECTED_ACTUAL_VARIANCE_ALIGNMENT)

    st.subheader("Driver models reserved for later implementation planning")
    st.write(DRIVER_MODELS_FOR_LATER)


if __name__ == "__main__":
    render()
