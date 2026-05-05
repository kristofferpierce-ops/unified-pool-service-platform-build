import pathlib
import streamlit as st

st.set_page_config(page_title="KPS UI Stabilization Pass 1", layout="wide")

st.title("KPS UI Stabilization Pass 1")
st.caption("Persistent launcher and diagnostics for local backend + Streamlit UI inspection.")

st.subheader("Purpose")
st.write(
    "This page documents the local UI stabilization pass. It keeps phase work separate "
    "from runtime inspection while giving the repo a stable launcher for backend + Streamlit checks."
)

st.subheader("Safety posture")
st.code(
    "LACRM_DEFAULT_MODE=dry_run\n"
    "LACRM_LIVE_WRITE=false\n"
    "LIVE_WRITE_DISABLED=true\n"
    "LIVE_WRITE_UNARMED=true\n"
    "NO_BRIDGE_POST=true\n"
    "NO_NETWORK_TRANSPORT_IMPLEMENTATION=true\n"
    "NO_NETWORK_SOCKETS=true"
)

st.subheader("Recommended local commands")
st.code(
    r'''
$Parent = "C:\Users\krist\Desktop\unified_pool_service_platform_build"
$Repo = Join-Path $Parent "unified_pool_service_platform_build"
Set-Location $Parent

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File (Join-Path $Repo "scripts\kps_ui_stabilization_pass1_launcher.ps1") `
  -RepoRoot $Repo `
  -Action launch
'''.strip(),
    language="powershell",
)

st.subheader("What the launcher does")
st.write(
    "It verifies the repo venv, confirms app.api.main:app can import, launches FastAPI on 8000, "
    "launches the Streamlit multipage UI on 8501, writes proof logs under TEMP, and keeps live writes disabled."
)

repo_root = pathlib.Path(__file__).resolve().parents[2]
pages_root = repo_root / "ui" / "pages"
workflow_keywords = (
    "Quote", "Front", "Bridge", "LACRM", "Ring", "Customer", "Property",
    "Skimmer", "Fresh", "Heritage", "Replaster", "Tool", "Apply", "CRM",
    "Routing", "Review",
)

if pages_root.exists():
    pages = sorted(p.name for p in pages_root.glob("*.py"))
    workflow_pages = [p for p in pages if any(k in p for k in workflow_keywords)]
    st.metric("Total Streamlit page files", len(pages))
    st.metric("Likely workflow pages", len(workflow_pages))
    with st.expander("Likely workflow pages", expanded=False):
        for page in workflow_pages:
            st.write(page)
else:
    st.warning("ui/pages was not found from this page context.")

