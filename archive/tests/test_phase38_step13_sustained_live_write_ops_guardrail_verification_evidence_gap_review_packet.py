from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase38_step13_sustained_live_write_ops_guardrail_verification_evidence_gap_review_packet.ps1"
UI = ROOT / "ui/pages/1949_Phase38_Step13_Sustained_Live_Write_Ops_Guardrail_Verification_Evidence_Gap_Review.py"
DOC = ROOT / "docs/PHASE38_STEP13_SUSTAINED_LIVE_WRITE_OPS_GUARDRAIL_VERIFICATION_EVIDENCE_GAP_REVIEW_PACKET.md"
TEST = ROOT / "tests/test_phase38_step13_sustained_live_write_ops_guardrail_verification_evidence_gap_review_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase38_step13_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase38_step13_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert not text.startswith("\ufeff")
    assert text.lstrip().startswith("param(")
    assert '[string]$RepoRoot = ""' in text
    assert '[ValidateSet("status", "apply", "smoke", "packet", "all")]' in text


def test_phase38_step13_required_safety_markers_present() -> None:
    combined = "\n".join(read(path) for path in (SCRIPT, UI, DOC))
    for marker in [
        'planning_only',
        'no_real_bridge_http_client',
        'no_network_transport_implementation',
        'no_bridge_post',
        'no_network_sockets',
        'phase38_execution_start',
        'phase38_implementation_start',
        'implementation_phase_start',
        'trusted_production_sustained_live_write_operations_start',
        'trusted_production_sustained_live_write_operations_execution_start',
        'sustained_live_write_operations_start',
        'sustained_live_write_operations_execution_start',
        'live_write_activation_start',
        'live_write_apply_start',
        'live_user_access_start',
        'no_live_user_access',
        'no_live_write_activation',
        'no_live_write_apply',
        'phase39_start',
        'phase39_boundary_creation',
        'lacrm_default_mode',
        'live_write_disabled',
        'live_write_unarmed',
    ]:
        assert marker in combined


def test_phase38_step13_next_phase_guards_present() -> None:
    combined = "\n".join(read(path) for path in (SCRIPT, UI, DOC)).replace(" ", "").lower()
    assert "phase39_start=false" in combined
    assert "phase39_boundary_creation=false" in combined


def test_phase38_step13_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    forbidden_true = [
        'phase39_start=true',
        'phase39_boundary_creation=true',
        'phase38_execution_start=true',
        'phase38_implementation_start=true',
        'implementation_phase_start=true',
        'trusted_production_sustained_live_write_operations_start=true',
        'trusted_production_sustained_live_write_operations_execution_start=true',
        'sustained_live_write_operations_start=true',
        'sustained_live_write_operations_execution_start=true',
        'live_write_activation_start=true',
        'live_write_apply_start=true',
        'live_user_access_start=true',
        'no_live_user_access=false',
        'no_live_write_activation=false',
        'no_live_write_apply=false',
    ]
    for marker in forbidden_true:
        assert marker not in compact


def test_phase38_step13_literal_pass_markers_present() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text


def test_phase38_step13_ui_is_planning_only_page() -> None:
    text = read(UI)
    assert "Planning-only packet page" in text
    assert "st.set_page_config" in text
    assert "phase39_start=false" in text


def test_phase38_step13_doc_records_no_runtime_boundary() -> None:
    text = read(DOC)
    assert "does not launch a server" in text
    assert "does not" in text
    assert "phase39_boundary_creation=false" in text


def test_phase38_step13_no_phase39_files_created_by_payload() -> None:
    assert "phase39" in read(SCRIPT).lower()
    assert "phase39_start=false" in read(DOC).replace(" ", "").lower()
    hits = []
    for folder in ["scripts", "docs", "tests", "ui/pages"]:
        hits.extend((ROOT / folder).glob("*phase39*"))
        hits.extend((ROOT / folder).glob("*Phase39*"))
        hits.extend((ROOT / folder).glob("*PHASE39*"))
    assert not hits
