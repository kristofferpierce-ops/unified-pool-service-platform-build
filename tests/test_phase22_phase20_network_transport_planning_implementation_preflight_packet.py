from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP17_FILES = [
    ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_implementation_preflight_packet.ps1",
    ROOT / "ui" / "pages" / "123_Phase20_Network_Transport_Planning_Implementation_Preflight_Packet.py",
    ROOT / "docs" / "PHASE22_STEP17_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_PREFLIGHT_PACKET.md",
    ROOT / "tests" / "test_phase22_phase20_network_transport_planning_implementation_preflight_packet.py",
]

PUBLIC_FILES = STEP17_FILES[:3]
STEP_SCRIPT = STEP17_FILES[0]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step17_files_exist() -> None:
    missing = [str(path.relative_to(ROOT)) for path in STEP17_FILES if not path.exists()]
    assert not missing, f"Missing Step 17 files: {missing}"


def test_phase22_step17_declares_planning_only_safety_posture() -> None:
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
        "operator_signoff_creation",
        "operator_approval_creation",
        "final_approval_creation",
        "design_closure_record_creation",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "dry_run",
        "lacrm_live_write",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for token in required_tokens:
        assert token in combined, f"Missing required safety token: {token}"


def test_phase22_step17_does_not_add_transport_or_live_write_implementation() -> None:
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


def test_phase22_step17_expected_operator_outputs_are_documented() -> None:
    doc = _read(ROOT / "docs" / "PHASE22_STEP17_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_PREFLIGHT_PACKET.md")
    assert "SMOKE TEST PASS: Phase 22 Step 17 Phase 20 Network Transport Planning Implementation Preflight Packet is present and planning-only." in doc
    expected_lines = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: authorization_record_creation=false",
        "CHECK: operator_signoff_creation=false",
        "CHECK: operator_approval_creation=false",
        "CHECK: final_approval_creation=false",
        "CHECK: design_closure_record_creation=false",
    ]
    for line in expected_lines:
        assert line in doc, f"Expected output line missing: {line}"


def test_phase22_step17_git_staging_guidance_is_parent_workspace_safe_and_narrow() -> None:
    doc = _read(ROOT / "docs" / "PHASE22_STEP17_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_PREFLIGHT_PACKET.md")
    assert "git -C $Repo add \"scripts\\phase22_generate_phase20_network_transport_planning_implementation_preflight_packet.ps1\"" in doc
    assert "git -C $Repo add \"ui\\pages\\123_Phase20_Network_Transport_Planning_Implementation_Preflight_Packet.py\"" in doc
    assert "data/unified_pool_service_platform.db" in doc
    assert ".env" in doc
    assert ".venv" in doc
    assert "backups" in doc


def test_step17_launcher_is_idempotent_for_same_source_and_target() -> None:
    script_text = STEP_SCRIPT.read_text(encoding="utf-8")
    assert "Test-SameLiteralPathSafe" in script_text
    assert "source and target are the same file" in script_text
    assert "copied or already present" in script_text


def test_step17_launcher_supports_fast_noninteractive_action_all() -> None:
    script_text = STEP_SCRIPT.read_text(encoding="utf-8")
    assert "ValidateSet" in script_text
    assert "-Action all" in _read(ROOT / "docs" / "PHASE22_STEP17_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_PREFLIGHT_PACKET.md")
    assert "Invoke-Step17Action" in script_text
    assert '"all"' in script_text


def test_step17_packet_keeps_approval_and_closure_records_disabled() -> None:
    combined = "\n".join(_read(path) for path in PUBLIC_FILES)
    assert "operator_signoff_creation = $false" in combined or '"operator_signoff_creation": False' in combined or '"operator_signoff_creation"' in combined
    assert "operator_approval_creation = $false" in combined or '"operator_approval_creation": False' in combined or '"operator_approval_creation"' in combined
    assert "final_approval_creation = $false" in combined or '"final_approval_creation": False' in combined or '"final_approval_creation"' in combined
    assert "design_closure_record_creation = $false" in combined or '"design_closure_record_creation": False' in combined or '"design_closure_record_creation"' in combined
