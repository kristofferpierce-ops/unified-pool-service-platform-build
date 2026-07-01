from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase34_step69_trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_closeout_index_packet.ps1"
UI_PAGE = ROOT / "ui/pages/1525_Phase34_Step69_Shadow_Run_Result_Disposition_Closeout_Index.py"
DOCS = ROOT / "docs/PHASE34_STEP69_TRUSTED_PRODUCTION_SHADOW_RUN_VALIDATION_NO_WRITE_DRY_RUN_RESULT_DISPOSITION_PLANNING_CLOSEOUT_INDEX_PACKET.md"
TEST = ROOT / "tests/test_phase34_step69_trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_closeout_index_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase34_step69_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOCS.exists()
    assert TEST.exists()


def test_phase34_step69_uses_short_ui_filename():
    assert UI_PAGE.name == "1525_Phase34_Step69_Shadow_Run_Result_Disposition_Closeout_Index.py"
    assert len(str(UI_PAGE)) < 245
    assert "Implementation_Trusted_Production_Shadow_Run_Validation_No_Write_Dry_Run_Result_Disposition_Planning" not in UI_PAGE.name


def test_phase34_step69_launcher_actions_and_markers():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 34 Step 69" in script
    assert "SMOKE TEST PASS: Phase 34 Step 69" in script
    assert "planning_only = $true" in script
    assert "phase35_start = $false" in script
    assert "phase35_boundary_creation = $false" in script


def test_phase34_step69_operational_text_is_safe():
    combined = "\n".join(read(path) for path in (SCRIPT, UI_PAGE, DOCS)).lower()
    assert "planning_only=true" in combined or "planning_only = $true" in combined
    assert "no_network_transport_implementation=true" in combined or "no_network_transport_implementation = $true" in combined
    unsafe = [
        ("phase35_start", "true"),
        ("phase35_boundary_creation", "true"),
        ("phase34_execution_start", "true"),
        ("phase34_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("trusted_production_shadow_run_validation_start", "true"),
        ("trusted_production_shadow_run_validation_execution_start", "true"),
        ("shadow_run_execution_start", "true"),
        ("live_read_activation_start", "true"),
        ("live_user_access_start", "true"),
        ("live_write_disabled", "false"),
        ("live_write_unarmed", "false"),
    ]
    compact = "".join(ch for ch in combined if ch.isalnum())
    for key, value in unsafe:
        assert f"{key}{value}" not in compact


def test_phase34_step69_docs_and_page_reference_title():
    assert "Phase 20 Network Transport Implementation Trusted Production Shadow Run Validation No-Write Dry Run Result Disposition Planning Closeout Index Packet" in read(DOCS)
    assert "Phase 20 Network Transport Implementation Trusted Production Shadow Run Validation No-Write Dry Run Result Disposition Planning Closeout Index Packet" in read(UI_PAGE)
    assert "trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_closeout_index" in read(SCRIPT)


def test_phase34_step69_does_not_start_runtime_or_live_write():
    script = read(SCRIPT).lower()
    assert "network_transport_runtime_start = $false" in script
    assert "live_write_disabled = $true" in script
    assert "live_write_unarmed = $true" in script


def test_phase34_step69_test_file_is_self_reference_only():
    assert TEST.name.startswith("test_phase34_step69")


def test_phase34_step69_old_long_ui_name_not_used():
    assert "Implementation_Trusted_Production_Shadow_Run_Validation_No_Write_Dry_Run_Result_Disposition_Planning" not in read(SCRIPT)

