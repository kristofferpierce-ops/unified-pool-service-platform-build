from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STEP_SCRIPT = ROOT / "scripts/phase22_generate_phase20_network_transport_planning_probabilistic_calibration_alignment_packet.ps1"
UI_PAGE = ROOT / "ui/pages/133_Phase20_Network_Transport_Planning_Probabilistic_Calibration_Alignment_Packet.py"
DOC_FILE = ROOT / "docs/PHASE22_STEP27_PHASE20_NETWORK_TRANSPORT_PLANNING_PROBABILISTIC_CALIBRATION_ALIGNMENT_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_phase20_network_transport_planning_probabilistic_calibration_alignment_packet.py"

STEP_FILES = [
    STEP_SCRIPT,
    UI_PAGE,
    DOC_FILE,
    TEST_FILE,
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step27_files_exist():
    missing = [str(path.relative_to(ROOT)) for path in STEP_FILES if not path.exists()]
    assert not missing, f"Missing Phase 22 Step 27 files: {missing}"


def test_phase22_step27_launcher_supports_optimized_action_all():
    text = read(STEP_SCRIPT)
    assert 'ValidateSet("menu", "status", "apply", "smoke", "packet", "all")' in text
    assert '"all" { Show-Status $ResolvedRepoRoot; Apply-StepFiles $ResolvedRepoRoot; Invoke-SmokeTest $ResolvedRepoRoot; New-PlanningPacket $ResolvedRepoRoot }' in text


def test_phase22_step27_launcher_is_path_safe_and_idempotent():
    text = read(STEP_SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Copy-Item -LiteralPath" in text
    assert "source and target are the same file" in text
    assert "Remove-ControlCharacters" in text


def test_phase22_step27_safety_guardrails_are_present():
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


def test_phase22_step27_forbids_runtime_probabilistic_execution():
    combined = "\n".join(read(path) for path in STEP_FILES)
    required = [
        "probabilistic_calibration_writes",
        "bayesian_update_execution",
        "recommendation_engine_execution",
        "No Bayesian update execution",
        "No recommendation engine execution",
    ]
    for token in required:
        assert token in combined


def test_phase22_step27_has_rollout_calibration_sequence():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    required = [
        "rules first",
        "probabilistic calibration",
        "pattern detection",
        "recommendation engine",
    ]
    for token in required:
        assert token in combined


def test_phase22_step27_declares_planned_priors():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    required = [
        "account class",
        "seasonal",
        "branch",
        "tech",
        "route density",
        "equipment family",
    ]
    for token in required:
        assert token in combined


def test_phase22_step27_preserves_source_bucket_chain():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, DOC_FILE])
    assert "raw_normalized_matched_approved_applied" in combined
    assert "raw -> normalized -> matched -> approved -> applied" in combined


def test_phase22_step27_preserves_bridge_absorption_guardrail():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, DOC_FILE])
    assert "connector_package_not_separate_product" in combined
    assert "not a direct shared database merge" in combined or "not a separate product" in combined


def test_phase22_step27_does_not_contain_network_or_write_clients():
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    forbidden_patterns = [
        r"Invoke-WebRequest\b",
        r"Invoke-RestMethod\b",
        r"System\.Net\.Sockets",
        r"TcpClient\b",
        r"HttpClient\b",
        r"requests\.post",
        r"sqlite3\.connect",
        r"create_engine\(",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, combined), pattern


def test_phase22_step27_packet_expected_output_markers():
    text = read(STEP_SCRIPT)
    expected = [
        "PASS: planning_only=true",
        "PASS: probabilistic_calibration_writes=false",
        "PASS: bayesian_update_execution=false",
        "PASS: recommendation_engine_execution=false",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: calibration_sequence=rules_first_then_probabilistic_calibration_then_pattern_detection_then_recommendations",
    ]
    for marker in expected:
        assert marker in text
