# Phase 22 Step 63 - Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Index Packet

## Prior completed step

Phase 22 Step 62 - Phase 20 Network Transport Planning Cross-Repo Handoff Verification Packet

## Purpose

This packet adds a planning-only evidence index after the Step 62 cross-repo handoff verification packet.

It indexes the handoff evidence references without collecting evidence from sibling repositories, mutating any repository outside the platform working tree, starting Phase 23, or introducing network transport implementation work.

## Evidence index scope

- Index the Step 61 cross-repo handoff reference by name only.
- Index the Step 62 cross-repo handoff verification reference by name only.
- Keep parent-workspace commands runnable from `C:\Users\krist\Desktop\unified_pool_service_platform_build` by using `git -C $Repo` and absolute pytest paths.
- Keep the one-file installer flow using `INSTALL_PHASE22_STEP63_SINGLE_FILE.ps1`.
- Confirm no platform database mutation, bridge mutation, live LACRM write, bridge POST, socket, runtime execution, or evidence collection execution is introduced.
- Confirm no external repo branch, push, validation write, or file write is requested.
- Confirm Phase 23 remains not started.

## Cross-repo posture

- Platform repo: `unified_pool_service_platform_build`
- Extractor repo: `start_here_extractor_m1_completion`
- Bridge repo: `front_desk_bridge` or equivalent local bridge folder
- Evidence index mode: reference only
- Cross-repo write: false
- Cross-repo mutation: false
- External repo push: false
- Sibling repo mutation: false
- Handoff evidence index write: false
- Phase 23 start: false

## Safety posture

- planning_only: true
- no_platform_db_mutation: true
- no_bridge_mutation: true
- no_real_bridge_http_client: true
- no_network_transport_implementation: true
- no_bridge_post: true
- no_network_sockets: true
- no_execution_implementation: true
- implementation_phase_start: false
- phase23_start: false
- phase23_branch_creation: false
- implementation_queue_creation: false
- authorization_record_creation: false
- operator_signoff_creation: false
- operator_approval_creation: false
- final_approval_creation: false
- design_closure_record_creation: false
- closure_review_record_creation: false
- closure_decision_creation: false
- cross_repo_write: false
- cross_repo_mutation: false
- external_repo_push: false
- cross_repo_branch_change: false
- cross_repo_file_write: false
- sibling_repo_mutation: false
- cross_repo_validation_write: false
- handoff_record_creation: false
- handoff_queue_creation: false
- handoff_verification_record_creation: false
- handoff_evidence_index_record_creation: false
- handoff_evidence_collection_execution: false
- handoff_evidence_index_write: false
- evidence_capture_mutation: false
- bridge_absorption_execution: false
- phase22_reopen: false
- phase23_start_boundary_creation: false
- source_bucket_writes: false
- applied_layer_mutation: false
- review_gate_mutation: false
- lacrm_default_mode: dry_run
- lacrm_live_write: false
- live_write_disabled: true
- live_write_unarmed: true

## Files added

- `scripts/phase22_step63_cross_repo_handoff_evidence_index_packet.ps1`
- `ui/pages/169_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Evidence_Index_Packet.py`
- `docs/PHASE22_STEP63_CROSS_REPO_HANDOFF_EVIDENCE_INDEX_PACKET.md`
- `tests/test_phase22_step63_cross_repo_handoff_evidence_index_packet.py`

## Expected launcher smoke text

```text
SMOKE TEST PASS: Phase 22 Step 63 Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Index Packet is present and planning-only.
```

## Expected option 5 PASS/CHECK output

```text
PASS: planning_only=true
PASS: no_real_bridge_http_client=true
PASS: no_network_transport_implementation=true
PASS: no_bridge_post=true
PASS: no_network_sockets=true
PASS: cross_repo_write=false
PASS: cross_repo_mutation=false
PASS: external_repo_push=false
PASS: evidence_index_mode=reference_only
PASS: handoff_evidence_index_write=false
PASS: phase23_start=false
PASS: lacrm_default_mode=dry_run
PASS: live_write_disabled=true
PASS: live_write_unarmed=true
CHECK: prior_step=Phase 22 Step 62
CHECK: phase23_start=not_started
CHECK: implementation_phase_start=not_started
CHECK: evidence_index_mode=reference_only
CHECK: parent_workspace_launcher=safe
CHECK: packet_json=<path>
```

## One-file parent workspace install command

```powershell
$Parent = "C:\Users\krist\Desktop\unified_pool_service_platform_build"
Set-Location $Parent
$Installer = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "INSTALL_PHASE22_STEP63_SINGLE_FILE*.ps1" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Installer.FullName
```

## Parent workspace command to open the menu only

```powershell
$Parent = "C:\Users\krist\Desktop\unified_pool_service_platform_build"
Set-Location $Parent
$Installer = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "INSTALL_PHASE22_STEP63_SINGLE_FILE*.ps1" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Installer.FullName -Parent $Parent -Action menu
```

## Parent workspace pytest command

```powershell
$Parent = "C:\Users\krist\Desktop\unified_pool_service_platform_build"
$Repo = Join-Path $Parent "unified_pool_service_platform_build"
Set-Location $Parent
python -m pytest (Join-Path $Repo "tests\test_phase22_step63_cross_repo_handoff_evidence_index_packet.py") -q
git -C $Repo status
```

## Safe git add, commit, backup push commands

The single-file installer already performs these commands safely, but the manual version is preserved here for review.

```powershell
$Parent = "C:\Users\krist\Desktop\unified_pool_service_platform_build"
$Repo = Join-Path $Parent "unified_pool_service_platform_build"
$Branch = "phase22-step63-cross-repo-handoff-evidence-index"
Set-Location $Parent

if (git -C $Repo show-ref --verify --quiet "refs/heads/$Branch") {
    git -C $Repo checkout $Branch
} else {
    git -C $Repo checkout -b $Branch
}

python -m pytest (Join-Path $Repo "tests\test_phase22_step63_cross_repo_handoff_evidence_index_packet.py") -q

git -C $Repo status --short

git -C $Repo add -- `
  scripts/phase22_step63_cross_repo_handoff_evidence_index_packet.ps1 `
  ui/pages/169_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Evidence_Index_Packet.py `
  docs/PHASE22_STEP63_CROSS_REPO_HANDOFF_EVIDENCE_INDEX_PACKET.md `
  tests/test_phase22_step63_cross_repo_handoff_evidence_index_packet.py

git -C $Repo commit -m "Phase 22 Step 63 - cross-repo handoff evidence index packet"
git -C $Repo push -u origin $Branch
```

## Do not stage

- `data/unified_pool_service_platform.db`
- `.env`
- `.venv`
- `backups`
- bridge folders
- extractor folders
- unrelated files

## Server launch note

You do not need to launch the server to validate this planning-only packet. Option 4 intentionally confirms that server startup is disabled and no FastAPI, Streamlit, bridge server, network socket, cross-repo write, evidence collection execution, or runtime execution is started.

