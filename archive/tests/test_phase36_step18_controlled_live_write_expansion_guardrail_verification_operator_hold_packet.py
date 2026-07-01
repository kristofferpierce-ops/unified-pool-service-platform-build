from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/phase36_step18_controlled_live_write_expansion_guardrail_verification_operator_hold_packet.ps1"
UI = REPO_ROOT / "ui/pages/1714_Phase36_Step18_Guardrail_Verification_Operator_Hold.py"
DOC = REPO_ROOT / "docs/PHASE36_STEP18_CONTROLLED_LIVE_WRITE_EXPANSION_GUARDRAIL_VERIFICATION_OPERATOR_HOLD_PACKET.md"
TEST = REPO_ROOT / "tests/test_phase36_step18_controlled_live_write_expansion_guardrail_verification_operator_hold_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compact(text: str) -> str:
    return text.lower().replace(" ", "").replace("\r", "").replace("\n", "")


def test_phase36_step18_files_exist():
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase36_step18_launcher_supports_expected_actions_and_pass_markers():
    script = read(SCRIPT)
    assert 'param(' in script
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 36 Step 18" in script
    assert "SMOKE TEST PASS: Phase 36 Step 18" in script


def test_phase36_step18_planning_only_safety_markers_are_present():
    combined = "\n".join(read(path) for path in (SCRIPT, UI, DOC))
    lowered = combined.lower()
    for marker in (
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_live_user_access",
        "no_live_write_activation",
        "no_live_write_apply",
        "live_write_disabled",
        "live_write_unarmed",
        "lacrm_default_mode",
        "dry_run",
    ):
        assert marker in lowered


def test_phase36_step18_does_not_start_runtime_live_write_or_next_phase():
    operational = "\n".join(read(path) for path in (SCRIPT, UI, DOC))
    squashed = compact(operational)
    forbidden_true_keys = [
        "phase37_start",
        "phase37_boundary_creation",
        "phase36_execution_start",
        "phase36_implementation_start",
        "implementation_phase_start",
        "trusted_production_controlled_live_write_expansion_start",
        "trusted_production_controlled_live_write_expansion_execution_start",
        "controlled_live_write_expansion_start",
        "controlled_live_write_expansion_execution_start",
        "live_write_activation_start",
        "live_write_apply_start",
        "live_user_access_start",
        "network_transport_runtime_start",
        "bridge_transport_runtime_start",
    ]
    for key in forbidden_true_keys:
        assert f"{key}=true" not in squashed
        assert f"{key}:$true" not in squashed


def test_phase36_step18_has_correct_title_and_context():
    doc = read(DOC)
    script = read(SCRIPT)
    assert "Phase 36 Step 18 - Phase 20 Network Transport Implementation Trusted Production Controlled Live Write Expansion Guardrail Verification Operator Hold Point Packet" in doc
    assert "Phase 36 Step 18 - Phase 20 Network Transport Implementation Trusted Production Controlled Live Write Expansion Guardrail Verification Operator Hold Point Packet" in script
    assert "trusted-production controlled live-write expansion" in doc.lower()
    assert "guardrail verification" in doc.lower()


def test_phase36_step18_ui_is_streamlit_page():
    ui = read(UI)
    assert "import streamlit as st" in ui
    assert "st.set_page_config" in ui
    assert "Phase 36 Step 18" in ui


def test_phase36_step18_forbidden_operational_literals_absent_from_launcher_and_doc():
    operational = "\n".join(read(path) for path in (SCRIPT, DOC))
    squashed = compact(operational)
    for key in (
        "phase37_start",
        "phase37_boundary_creation",
        "live_write_activation_start",
        "live_write_apply_start",
    ):
        assert f"{key}=true" not in squashed


def test_phase36_step18_test_file_mentions_phase37_guard_without_creating_it():
    test_source = read(TEST)
    assert "phase37" in test_source.lower()
    assert "Path(" in test_source

