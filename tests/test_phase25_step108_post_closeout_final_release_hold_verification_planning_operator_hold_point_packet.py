from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/phase25_step108_post_closeout_final_release_hold_verification_planning_operator_hold_point_packet.ps1"
PAGE = REPO_ROOT / "ui/pages/484_Phase25_Step108_Implementation_PostCloseout_Final_Release_Hold_Verification_Planning_Operator_Hold_Point_Packet.py"
DOC = REPO_ROOT / "docs/PHASE25_STEP108_POST_CLOSEOUT_FINAL_RELEASE_HOLD_VERIFICATION_PLANNING_OPERATOR_HOLD_POINT_PACKET.md"
TEST = REPO_ROOT / "tests/test_phase25_step108_post_closeout_final_release_hold_verification_planning_operator_hold_point_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def operational_text() -> str:
    return "\n".join(read(path).lower() for path in (SCRIPT, PAGE, DOC))


def test_phase25_step108_files_are_present():
    for path in (SCRIPT, PAGE, DOC, TEST):
        assert path.exists(), f"missing {path}"


def test_phase25_step108_planning_only_markers_are_present():
    text = operational_text()
    assert "planning_only" in text
    assert "no_real_bridge_http_client" in text
    assert "no_network_transport_implementation" in text
    assert "no_bridge_post" in text
    assert "no_network_sockets" in text
    assert "phase25_execution_start" in text
    assert "phase25_implementation_start" in text
    assert "implementation_phase_start" in text
    assert "phase26_start" in text
    assert "phase26_boundary_creation" in text
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text
    assert "dry_run" in text


def test_phase25_step108_does_not_enable_runtime_or_next_phase():
    text = operational_text()
    forbidden = [
        "phase26_start" + "=true",
        "phase26_boundary_creation" + "=true",
        "phase25_execution_start" + "=true",
        "phase25_implementation_start" + "=true",
        "implementation_phase_start" + "=true",
        "post_closeout_runtime_start" + "=true",
        "network_transport_runtime_start" + "=true",
        "bridge_transport_runtime_start" + "=true",
        "no_network_sockets" + "=false",
        "no_bridge_post" + "=false",
        "live_write_disabled" + "=false",
        "live_write_unarmed" + "=false",
    ]
    for marker in forbidden:
        assert marker not in text


def test_phase25_step108_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert "ValidateSet(\"status\", \"apply\", \"smoke\", \"packet\", \"all\")" in script
    assert "APPLY PASS: Phase 25 Step 108" in script
    assert "SMOKE TEST PASS: Phase 25 Step 108" in script
    assert "CHECK: packet_json=" in script


def test_phase25_step108_known_powershell_generation_bugs_are_absent():
    script = read(SCRIPT)
    assert "$File:" not in script
    assert "Join-Path $RepoRoot \"scripts/phase25_step108_post_closeout_final_release_hold_verification_planning_operator_hold_point_packet.ps1\"," not in script
    assert "System.Object[]" not in script


def test_phase25_step108_ui_page_is_reference_only():
    page = read(PAGE).lower()
    assert "streamlit" in page
    assert "reference-only" in page
    assert "phase26_start" in page
    assert "phase26_boundary_creation" in page
    assert "live_write_disabled" in page


def test_phase25_step108_doc_records_no_write_safety():
    doc = read(DOC).lower()
    assert "planning-only" in doc
    assert "no-write" in doc
    assert "no phase 26 boundary creation" in doc
    assert "phase26_start=false" in doc
    assert "phase26_boundary_creation=false" in doc


def test_phase25_step108_file_names_match_step_number():
    assert "step108" in SCRIPT.name
    assert "Step108" in PAGE.name
    assert "STEP108" in DOC.name
    assert "step108" in TEST.name
