from fastapi import FastAPI

from app.api.routes import admin, estimates, properties
from app.core.database import create_db_and_tables

create_db_and_tables()

app = FastAPI(title="Pool Service Pricing Platform", version="1.0.0")
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(properties.router, prefix="/properties", tags=["properties"])
app.include_router(estimates.router, prefix="/estimates", tags=["estimates"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
