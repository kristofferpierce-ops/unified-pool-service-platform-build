from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session, select

from app.core.database import engine
from app.models.tables import InvoiceDocument, InvoiceLineStaging

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/documents")
def get_invoice_documents() -> list[InvoiceDocument]:
    with Session(engine) as session:
        return list(session.exec(select(InvoiceDocument)).all())


@router.get("/staging")
def get_invoice_staging() -> list[InvoiceLineStaging]:
    with Session(engine) as session:
        return list(session.exec(select(InvoiceLineStaging)).all())
