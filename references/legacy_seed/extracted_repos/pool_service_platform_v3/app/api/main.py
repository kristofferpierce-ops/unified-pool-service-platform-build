from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import baseline, commercial, expenses, invoices, properties, reports, tools

app = FastAPI(title="Pool Service Pricing Platform API")
app.include_router(expenses.router)
app.include_router(baseline.router)
app.include_router(properties.router)
app.include_router(commercial.router)
app.include_router(invoices.router)
app.include_router(reports.router)

app.include_router(tools.router)
