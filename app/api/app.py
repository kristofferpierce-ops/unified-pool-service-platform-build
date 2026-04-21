from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import baseline, commercial, expenses, invoices, properties, reports, tools
from app.api.routes.bootstrap_admin import router as bootstrap_router
from app.api.routes.connectors import router as connectors_router
from app.api.routes.estimates import router as estimates_router
from app.api.routes.front_desk import router as front_desk_router
from app.api.routes.routing_candidates import router as routing_candidates_router
from app.api.routes.routing_candidate_import import router as routing_candidate_import_router
from app.api.routes.routing_candidate_workbench import router as routing_candidate_workbench_router
from app.api.routes.routing_preference_drafts import router as routing_preference_drafts_router
from app.api.routes.routing_bridge_apply_preview import router as routing_bridge_apply_preview_router
from app.api.routes.routing_bridge_write_rehearsal import router as routing_bridge_write_rehearsal_router
from app.api.routes.routing_bridge_write_audit import router as routing_bridge_write_audit_router
from app.api.routes.routing_bridge_write_audit_writer import router as routing_bridge_write_audit_writer_router
from app.api.routes.routing_bridge_write_executor import router as routing_bridge_write_executor_router
from app.api.routes.routing_bridge_write_dry_run_bundle import router as routing_bridge_write_dry_run_bundle_router
from app.api.routes.routing_bridge_http_client_stub import router as routing_bridge_http_client_stub_router
from app.api.routes.freshbooks_oauth import router as freshbooks_oauth_router
from app.api.routes.health import router as health_router
from app.api.routes.quote_workflow import router as quote_workflow_router
from app.api.routes.heater_quotes import router as heater_quotes_router
from app.api.routes.system_settings import router as system_settings_router
from app.core.config import APP_NAME, STATIC_DIR
from app.core.database import create_db_and_tables, get_session
import app.models.quote_tables as _quote_tables
import app.models.heater_quote_tables as _heater_quote_tables
import app.models.routing_candidates as _routing_candidate_tables
import app.models.routing_preference_drafts as _routing_preference_draft_tables
import app.models.routing_bridge_write_audit as _routing_bridge_write_audit_tables
from app.services.bootstrap import seed_defaults

app = FastAPI(title=APP_NAME)
app.include_router(health_router)
app.include_router(bootstrap_router)
app.include_router(system_settings_router)
app.include_router(estimates_router)
app.include_router(connectors_router)
app.include_router(front_desk_router)
app.include_router(routing_candidates_router)
app.include_router(routing_candidate_import_router)
app.include_router(routing_candidate_workbench_router)
app.include_router(routing_preference_drafts_router)
app.include_router(routing_bridge_apply_preview_router)
app.include_router(routing_bridge_write_rehearsal_router)
app.include_router(routing_bridge_write_audit_router)
app.include_router(routing_bridge_write_audit_writer_router)
app.include_router(routing_bridge_write_executor_router)
app.include_router(routing_bridge_write_dry_run_bundle_router)
app.include_router(routing_bridge_http_client_stub_router)
app.include_router(freshbooks_oauth_router)
app.include_router(quote_workflow_router)
app.include_router(heater_quotes_router)

# Legacy platform routes kept active
app.include_router(expenses.router)
app.include_router(baseline.router)
app.include_router(properties.router)
app.include_router(commercial.router)
app.include_router(invoices.router)
app.include_router(reports.router)
app.include_router(tools.router)

app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


@app.on_event('startup')
def startup() -> None:
    create_db_and_tables()
    with get_session() as session:
        seed_defaults(session)


@app.get('/')
def front_page():
    dashboard = Path(STATIC_DIR) / 'frontdesk.html'
    if dashboard.exists():
        return FileResponse(dashboard)
    return {'message': APP_NAME}











