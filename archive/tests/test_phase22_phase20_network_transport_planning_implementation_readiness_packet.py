from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP16_FILES = [
    ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_implementation_readiness_packet.ps1",
    ROOT / "ui" / "pages" / "122_Phase20_Network_Transport_Planning_Implementation_Readiness_Packet.py",
    ROOT / "docs" / "PHASE22_STEP16_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_READINESS_PACKET.md",
    ROOT / "tests" / "test_phase22_phase20_network_transport_planning_implementation_readiness_packet.py",
]

PUBLIC_FILES = STEP16_FILES[:3]
STEP_SCRIPT = STEP16_FILES[0]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step16_files_exist() -> None:
    missing = [str(path.relative_to(ROOT)) for path in STEP16_FILES if not path.exists()]
    assert not missing, f"Missing Step 16 files: {missing}"


def test_phase22_step16_declares_planning_only_safety_posture() -> None:
    combined = "\n".join(_read(path) for path in PUBLIC_FILES)
    required_tokens = [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "implementation_phase_start",
        "authorization_record_creation",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "dry_run",
        "lacrm_live_write",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for token in required_tokens:
        assert token in combined, f"Missing required safety token: {token}"


def test_phase22_step16_does_not_add_transport_or_live_write_implementation() -> None:
    combined = "\n".join(_read(path) for path in PUBLIC_FILES)
    forbidden_tokens = [
        "Invoke-" + "WebRequest",
        "Invoke-" + "RestMethod",
        "requests" + ".post(",
        "http" + "x.",
        "socket" + ".socket",
        "create" + "_engine(",
        "Session" + "(",
        ".commit" + "(",
        "live_write_enabled" + " = True",
        "lacrm_live_write" + " = True",
    ]
    for token in forbidden_tokens:
        assert token not in combined, f"Forbidden implementation or live-write token found: {token}"


def test_phase22_step16_expected_operator_outputs_are_documented() -> None:
    doc = _read(ROOT / "docs" / "PHASE22_STEP16_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_READINESS_PACKET.md")
    assert "SMOKE TEST PASS: Phase 22 Step 16 Phase 20 Network Transport Planning Implementation Readiness Packet is present and planning-only." in doc
    expected_lines = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: authorization_record_creation=false",
    ]
    for line in expected_lines:
        assert line in doc, f"Expected output line missing: {line}"


def test_phase22_step16_git_staging_guidance_is_narrow() -> None:
    doc = _read(ROOT / "docs" / "PHASE22_STEP16_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_READINESS_PACKET.md")
    assert "git add scripts\\phase22_generate_phase20_network_transport_planning_implementation_readiness_packet.ps1" in doc
    assert "data/unified_pool_service_platform.db" in doc
    assert ".env" in doc
    assert ".venv" in doc
    assert "backups" in doc



def test_step16_launcher_is_idempotent_for_same_source_and_target():
    script_text = STEP_SCRIPT.read_text(encoding="utf-8")
    assert "Test-SameLiteralPathSafe" in script_text
    assert "source and target are the same file" in script_text
    assert "copied or already present" in script_text

