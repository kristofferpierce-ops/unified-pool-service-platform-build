from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP_SCRIPT = ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_pattern_detection_alignment_packet.ps1"
STEP_UI = ROOT / "ui" / "pages" / "134_Phase20_Network_Transport_Planning_Pattern_Detection_Alignment_Packet.py"
STEP_DOC = ROOT / "docs" / "PHASE22_STEP28_PHASE20_NETWORK_TRANSPORT_PLANNING_PATTERN_DETECTION_ALIGNMENT_PACKET.md"
STEP_TEST = ROOT / "tests" / "test_phase22_phase20_network_transport_planning_pattern_detection_alignment_packet.py"

STEP_FILES = [STEP_SCRIPT, STEP_UI, STEP_DOC, STEP_TEST]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step28_files_exist():
    missing = [str(path) for path in STEP_FILES if not path.exists()]
    assert not missing


def test_phase22_step28_document_labels_phase_and_step():
    text = read(STEP_DOC)
    assert "Phase 22 Step 28" in text
    assert "Pattern Detection Alignment Packet" in text
    assert "planning-only" in text


def test_phase22_step28_launcher_supports_optimized_actions():
    text = read(STEP_SCRIPT)
    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]' in text
    assert "Optimized launcher actions" in text
    assert '-Action status, apply, smoke, packet, all' in text


def test_phase22_step28_launcher_is_path_safe_and_idempotent():
    text = read(STEP_SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Copy-Item -LiteralPath" in text
    assert "source and target are the same file" in text
    assert "Remove-ControlCharacters" in text


def test_phase22_step28_safety_flags_present():
    combined = "\n".join(read(path) for path in STEP_FILES)
    required = [
        "planning_only",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "lacrm_default_mode",
        "dry_run",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for token in required:
        assert token in combined


def test_phase22_step28_no_forbidden_runtime_tokens():
    combined = "\n".join(read(path).lower() for path in STEP_FILES)
    forbidden_parts = [
        ("planning", "_", "only", "=", "false"),
        ("lacrm", "_", "live", "_", "write", "=", "true"),
        ("live", "_", "write", "_", "disabled", "=", "false"),
        ("live", "_", "write", "_", "unarmed", "=", "false"),
        ("implementation", "_", "phase", "_", "start", "=", "true"),
        ("authorization", "_", "record", "_", "creation", "=", "true"),
        ("operator", "_", "signoff", "_", "creation", "=", "true"),
        ("operator", "_", "approval", "_", "creation", "=", "true"),
        ("final", "_", "approval", "_", "creation", "=", "true"),
        ("design", "_", "closure", "_", "record", "_", "creation", "=", "true"),
        ("requests", ".", "post"),
        ("urllib", ".", "request"),
        ("http", ".", "client"),
        ("socket", ".", "create", "_", "connection"),
        ("fast", "api", "("),
        ("uvicorn", ".", "run"),
    ]
    for parts in forbidden_parts:
        assert "".join(parts) not in combined


def test_phase22_step28_packet_outputs_expected_checks():
    text = read(STEP_SCRIPT)
    expected = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "PASS: pattern_detection_runtime=false",
        "CHECK: pattern_detection_stage=planning_alignment_only",
        "CHECK: anomaly_detection_runtime=false",
        "CHECK: recommendation_engine_runtime=false",
        "CHECK: connector_first_operating_core=true",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
    ]
    for token in expected:
        assert token in text


def test_phase22_step28_source_bucket_alignment_preserved():
    combined = "\n".join(read(path) for path in STEP_FILES)
    assert "raw_normalized_matched_approved_applied" in combined
    assert "connector_first_operating_core" in combined
    assert "connector_package_not_separate_product" in combined


def test_phase22_step28_pattern_detection_is_planning_only():
    combined = "\n".join(read(path) for path in STEP_FILES)
    assert "pattern_detection_stage" in combined
    assert "planning_alignment_only" in combined
    assert "pattern_detection_runtime" in combined
    assert "anomaly_detection_runtime" in combined
    assert "recommendation_engine_runtime" in combined


def test_phase22_step28_ui_is_planning_page_only():
    text = read(STEP_UI)
    assert "st.set_page_config" in text
    assert "Planning-only packet" in text
    assert "does not start network transport" in text
    assert "does not mutate the platform DB" in text


def test_phase22_step28_branch_and_prior_step_are_recorded():
    text = read(STEP_SCRIPT)
    assert "phase22-step28-phase20-network-transport-planning-pattern-detection-alignment-packet" in text
    assert "Phase 22 Step 27 - Phase 20 Network Transport Planning Probabilistic Calibration Alignment Packet" in text
