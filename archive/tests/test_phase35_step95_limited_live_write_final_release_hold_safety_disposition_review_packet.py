from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / 'scripts/phase35_step95_limited_live_write_final_release_hold_safety_disposition_review_packet.ps1'
UI = REPO_ROOT / 'ui/pages/1671_Phase35_Step95_Live_Write_Final_Release_Hold_Safety_Review.py'
DOC = REPO_ROOT / 'docs/PHASE35_STEP95_LIMITED_LIVE_WRITE_FINAL_RELEASE_HOLD_SAFETY_DISPOSITION_REVIEW_PACKET.md'
TEST = REPO_ROOT / 'tests/test_phase35_step95_limited_live_write_final_release_hold_safety_disposition_review_packet.py'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def compact(text: str) -> str:
    return text.lower().replace(" ", "").replace("\r", "").replace("\n", "")


def test_phase35_step95_files_exist():
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase35_step95_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'param(' in script
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 35 Step 95" in script
    assert "SMOKE TEST PASS: Phase 35 Step 95" in script


def test_phase35_step95_planning_only_safety_markers():
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


def test_phase35_step95_does_not_start_runtime_or_next_phase():
    operational = "\n".join(read(path) for path in (SCRIPT, UI, DOC))
    squashed = compact(operational)
    forbidden_true_keys = [
        "phase36_start",
        "phase36_boundary_creation",
        "phase35_execution_start",
        "phase35_implementation_start",
        "implementation_phase_start",
        "trusted_production_limited_live_write_pilot_start",
        "trusted_production_limited_live_write_pilot_execution_start",
        "limited_live_write_pilot_start",
        "limited_live_write_pilot_execution_start",
        "live_write_activation_start",
        "live_write_apply_start",
        "live_user_access_start",
        "network_transport_runtime_start",
        "bridge_transport_runtime_start",
    ]
    for key in forbidden_true_keys:
        assert f"{key}=true" not in squashed
        assert f"{key}:$true" not in squashed


def test_phase35_step95_has_correct_title_and_context():
    doc = read(DOC)
    script = read(SCRIPT)
    assert 'Phase 35 Step 95 - Phase 20 Network Transport Implementation Trusted Production Limited Live Write Pilot Final Release Hold Planning Safety Disposition Review Packet' in doc
    assert 'Phase 35 Step 95 - Phase 20 Network Transport Implementation Trusted Production Limited Live Write Pilot Final Release Hold Planning Safety Disposition Review Packet' in script
    assert "trusted-production limited live-write pilot" in doc.lower()
    assert "final-release-hold planning" in doc.lower()


def test_phase35_step95_ui_is_streamlit_page():
    ui = read(UI)
    assert "import streamlit as st" in ui
    assert "st.set_page_config" in ui
    assert "Phase 35 Step 95" in ui


def test_phase35_step95_forbidden_operational_literals_are_absent_from_launcher_and_doc():
    operational = "\n".join(read(path) for path in (SCRIPT, DOC))
    squashed = compact(operational)
    for key in ("phase36_start", "phase36_boundary_creation", "live_write_activation_start", "live_write_apply_start"):
        assert f"{key}=true" not in squashed


def test_phase35_step95_test_file_has_path_constants():
    test_source = read(TEST)
    assert "Path(__file__)" in test_source
    assert "SCRIPT =" in test_source
    assert "UI =" in test_source
    assert "DOC =" in test_source

