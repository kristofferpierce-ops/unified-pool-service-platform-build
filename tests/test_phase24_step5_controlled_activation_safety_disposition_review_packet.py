from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE = 24
STEP = 5
STEP_TITLE = "Phase 24 Step 5 - Phase 20 Network Transport Implementation Controlled Activation Safety Disposition Review Packet"
PRIOR_STEP = "Phase 24 Step 4 - Phase 20 Network Transport Implementation Controlled Activation Safety Disposition Planning Packet"
BRANCH = "phase24-step5-controlled-activation-safety-disposition-review"
MODE_KEY = "implementation_controlled_activation_safety_disposition_review_mode"
WRITE_KEY = "implementation_controlled_activation_safety_disposition_review_write"
RECORD_KEY = "implementation_controlled_activation_safety_disposition_review_record_creation"
CONTEXT = "implementation_controlled_activation_safety_disposition_review_planning_only"

STEP_SCRIPT = ROOT / "scripts/phase24_step5_controlled_activation_safety_disposition_review_packet.ps1"
UI_PAGE = ROOT / "ui/pages/261_Phase24_Step5_Implementation_Controlled_Activation_Safety_Disposition_Review_Packet.py"
DOC = ROOT / "docs/PHASE24_STEP5_CONTROLLED_ACTIVATION_SAFETY_DISPOSITION_REVIEW_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase24_step5_controlled_activation_safety_disposition_review_packet.py"
STEP_FILES = [STEP_SCRIPT, UI_PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase24_step_file_set_exists():
    for path in STEP_FILES:
        assert path.exists(), f"missing {path}"


def test_phase24_step_identity_markers_are_present():
    combined = "\n".join(read(path) for path in STEP_FILES)
    assert STEP_TITLE in combined
    assert PRIOR_STEP in combined
    assert BRANCH in combined
    assert f"Step {STEP}" in combined


def test_phase24_step_launcher_has_menu_and_optimized_actions():
    text = read(STEP_SCRIPT)
    assert "Phase 24 Step 5 menu" in text
    assert 'ValidateSet("menu", "status", "apply", "smoke", "packet", "all")' in text
    assert "Show server start placeholder only" in text
    assert "Server startup is intentionally disabled" in text
    assert "APPLY PASS: Phase 24 Step 5 files copied or already present." in text


def test_phase24_step_planning_only_safety_guards_are_present():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC])
    required = [
        "planning_only",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "phase24_boundary",
        "phase24_execution_start",
        "phase24_implementation_start",
        "implementation_phase_start",
        "controlled_activation_runtime_start",
        "cross_repo_write",
        "cross_repo_mutation",
        "external_repo_push",
        "lacrm_default_mode",
        "dry_run",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for marker in required:
        assert marker in combined


def test_phase24_step_specific_change_isolation_markers_are_present():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC])
    assert MODE_KEY in combined
    assert WRITE_KEY in combined
    assert RECORD_KEY in combined
    assert CONTEXT in combined
    assert "reference_only" in combined
    assert "controlled_activation_decision_creation" in combined
    assert "controlled_activation_approval_creation" in combined
    assert "phase23_reopen" in combined
    assert "phase25_start" in combined
    assert "phase25_boundary_creation" in combined


def test_phase24_step_forbidden_runtime_language_is_not_introduced():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC]).lower()
    forbidden_phrases = [
        "requests.post(",
        "httpx.post(",
        "socket.socket(",
        "uvicorn.run(",
        "streamlit run",
        "real bridge http client",
        "network transport implementation=true",
        "phase24_execution_start=true",
        "phase24_implementation_start=true",
        "implementation_phase_start=true",
        "controlled_activation_runtime_start=true",
        "live_write_disabled=false",
        "live_write_unarmed=false",
        "phase25_start=true",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in combined


def test_phase24_step_packet_output_markers_are_documented():
    doc = read(DOC)
    script = read(STEP_SCRIPT)
    expected = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        f"PASS: {MODE_KEY}=reference_only",
        f"PASS: {WRITE_KEY}=false",
        f"PASS: {RECORD_KEY}=false",
        "PASS: phase25_start=false",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: network_transport_runtime_start=not_started",
        "CHECK: parent_workspace_launcher=safe",
        "CHECK: packet_json=",
    ]
    for marker in expected:
        assert marker in doc
        assert marker in script


def test_phase24_step_safe_staging_reminder_is_documented():
    doc = read(DOC)
    assert "Only these four files belong to this step" in doc
    assert "data/unified_pool_service_platform.db" in doc
    assert ".env" in doc
    assert "backups" in doc
    assert "bridge folders" in doc
    assert "extractor folders" in doc
    assert "Streamlit temporary launcher files" in doc
