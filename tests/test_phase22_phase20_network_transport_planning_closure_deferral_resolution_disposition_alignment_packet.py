from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STEP_FILES = [
    REPO_ROOT / "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_alignment_packet.ps1",
    REPO_ROOT / "ui/pages/152_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Alignment_Packet.py",
    REPO_ROOT / "docs/PHASE22_STEP46_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_ALIGNMENT_PACKET.md",
    REPO_ROOT / "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_alignment_packet.py",
]

STEP_SCRIPT = STEP_FILES[0]
UI_PAGE = STEP_FILES[1]
DOC_FILE = STEP_FILES[2]
TEST_FILE = STEP_FILES[3]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step46_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_phase22_step46_doc_identifies_phase_and_step():
    text = read(DOC_FILE)
    assert "Phase 22 Step 46" in text
    assert "Closure Deferral Resolution Disposition Alignment Packet" in text


def test_phase22_step46_ui_identifies_planning_only_status():
    text = read(UI_PAGE)
    assert "Planning-only alignment packet" in text
    assert "closure-deferral resolution" in text


def test_phase22_step46_launcher_supports_action_all():
    text = read(STEP_SCRIPT)
    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]' in text
    assert '"all"' in text


def test_phase22_step46_launcher_uses_literal_path_handling():
    text = read(STEP_SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Get-Content -LiteralPath" in text
    assert "Set-Content -LiteralPath" in text


def test_phase22_step46_launcher_is_idempotent_for_same_source_and_target():
    text = read(STEP_SCRIPT)
    assert "source and target are the same file" in text
    assert "Test-SameFile" in text


def test_phase22_step46_planning_only_safety_flags_are_present():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "planning_only = $true" in text or "planning_only: true" in text
    assert "no_platform_db_mutation" in text
    assert "no_bridge_mutation" in text


def test_phase22_step46_network_transport_remains_disabled():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "no_real_bridge_http_client" in text
    assert "no_network_transport_implementation" in text
    assert "no_bridge_post" in text
    assert "no_network_sockets" in text


def test_phase22_step46_closure_and_approval_records_are_not_created():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "operator_signoff_creation" in text
    assert "operator_approval_creation" in text
    assert "final_approval_creation" in text
    assert "design_closure_record_creation" in text
    assert "closure_decision_creation" in text


def test_phase22_step46_lacrm_write_lane_is_unarmed():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "lacrm_default_mode" in text
    assert "dry_run" in text
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_phase22_step46_packet_generation_is_backup_only():
    text = read(STEP_SCRIPT)
    assert "backups\\phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_alignment_packet_" in text
    assert "packet_json=" in text


def test_phase22_step46_source_bucket_alignment_is_documented():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "raw_normalized_matched_approved_applied" in text
    assert "source buckets" in text or "source_bucket" in text


def test_phase22_step46_bridge_absorption_guardrail_is_documented():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "connector_package_not_separate_product" in text or "connector-package" in text


def test_phase22_step46_resolution_disposition_is_planned_only():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "closure_deferral_resolution_disposition" in text
    assert "planned_only" in text
    assert "closure_resolution_disposition_creation" in text


def test_phase22_step46_does_not_create_backlog_or_applied_layer_mutation():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "closure_deferral_backlog_mutation" in text
    assert "applied_layer_mutation" in text


def test_phase22_step46_test_file_tracks_all_public_files():
    text = read(TEST_FILE)
    for expected in [
        "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_alignment_packet.ps1",
        "ui/pages/152_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Alignment_Packet.py",
        "docs/PHASE22_STEP46_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_ALIGNMENT_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_alignment_packet.py",
    ]:
        assert expected in text


def test_phase22_step46_public_files_do_not_contain_forbidden_runtime_tokens():
    forbidden = [
        "planning" + "_only: False",
        "no_network" + "_sockets: False",
        "no_bridge" + "_post: False",
        "lacrm_live" + "_write=true",
        "live_write" + "_disabled=false",
        "live_write" + "_unarmed=false",
        "implementation_phase" + "_start=true",
        "operator_signoff" + "_creation=true",
        "operator_approval" + "_creation=true",
        "final_approval" + "_creation=true",
        "design_closure_record" + "_creation=true",
        "closure_resolution_disposition" + "_creation=true",
        "closure_resolution_approval" + "_creation=true",
        "closure_decision" + "_creation=true",
    ]
    for path in STEP_FILES:
        text = read(path)
        for token in forbidden:
            assert token not in text


def test_phase22_step46_does_not_reference_runtime_server_start():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "Server startup is intentionally disabled" in text
    assert "No FastAPI, Streamlit, bridge server, ngrok, webhook listener, or network socket is started here." in text


def test_phase22_step46_disposition_record_creation_remains_false():
    text = read(STEP_SCRIPT) + read(DOC_FILE)
    assert "disposition_record_creation" in text
    assert "closure_resolution_disposition_approval_creation" in text
