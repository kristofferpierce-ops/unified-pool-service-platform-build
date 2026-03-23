from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader
from sqlmodel import Session, select

from app.core.config import UPLOAD_DIR
from app.models.tables import ChemicalProduct, InvoiceDocument, InvoiceLineStaging, Property, SupplierTrainingExample
from app.services.commercial import add_delivery_item, create_delivery
from app.services.expenses import create_price_history
from app.utils.matching import best_match
from app.utils.serialization import dumps

LINE_RE = re.compile(r"(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>gal|gallon|drum|lb|lbs|oz|ea)?\s+(?P<desc>.+?)\s+(?P<cost>\d+(?:\.\d+)?)$", re.I)
INVOICE_RE = re.compile(r"invoice\s*#?\s*[:\-]?\s*([A-Z0-9\-]+)", re.I)


def _extract_text(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return file_path.read_text(errors="ignore")


def ingest_invoice_document(session: Session, file_path: str | Path, vendor_name: str = "") -> InvoiceDocument:
    file_path = Path(file_path)
    destination = UPLOAD_DIR / file_path.name
    if file_path.resolve() != destination.resolve():
        destination.write_bytes(file_path.read_bytes())
    raw = destination.read_bytes()
    document_hash = hashlib.sha256(raw).hexdigest()
    extracted_text = _extract_text(destination)
    invoice_number_match = INVOICE_RE.search(extracted_text)
    invoice_number = invoice_number_match.group(1) if invoice_number_match else ""
    document = InvoiceDocument(
        vendor_name=vendor_name,
        original_filename=destination.name,
        file_path=str(destination),
        document_hash=document_hash,
        invoice_number=invoice_number,
        extracted_text=extracted_text,
        status="staged",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    stage_invoice_lines(session, document.id)
    return document


def _product_candidates(session: Session) -> list[tuple[int, str]]:
    products = session.exec(select(ChemicalProduct).where(ChemicalProduct.is_active == True)).all()
    candidates = []
    for product in products:
        labels = [product.name, product.sku, product.manufacturer_part_number]
        if product.aliases_csv:
            labels.extend([part.strip() for part in product.aliases_csv.split(",") if part.strip()])
        for label in labels:
            candidates.append((product.id, label))
    return candidates


def _property_candidates(session: Session) -> list[tuple[int, str]]:
    properties = session.exec(select(Property)).all()
    return [(prop.id, f"{prop.name} {prop.address_line_1} {prop.city}") for prop in properties]


def stage_invoice_lines(session: Session, document_id: int) -> list[InvoiceLineStaging]:
    document = session.get(InvoiceDocument, document_id)
    if not document:
        raise ValueError("Document not found")
    product_candidates = _product_candidates(session)
    property_candidates = _property_candidates(session)
    created = []
    for raw_line in document.extracted_text.splitlines():
        line = raw_line.strip()
        if not line or len(line) < 6:
            continue
        match = LINE_RE.search(line)
        quantity = float(match.group("qty")) if match else 0.0
        unit = (match.group("unit") if match else "") or ""
        product_text = (match.group("desc") if match else line).strip()
        unit_cost = float(match.group("cost")) if match else 0.0

        product_id, product_score, product_suggestions = best_match(product_text, product_candidates)
        property_id, property_score, property_suggestions = best_match(document.extracted_text[:500], property_candidates)

        confidence = max(product_score, 0.0)
        if product_score >= 0.95:
            bucket = "high_confidence"
        elif product_score >= 0.75:
            bucket = "assisted_match"
        else:
            bucket = "exception"

        staged = InvoiceLineStaging(
            document_id=document_id,
            raw_line_text=line,
            product_text=product_text,
            matched_product_id=product_id,
            matched_property_id=property_id if property_score >= 0.55 else None,
            quantity=quantity,
            unit=unit,
            unit_cost=unit_cost,
            confidence=confidence,
            bucket=bucket,
            suggestion_json=dumps({
                "product_suggestions": product_suggestions,
                "property_suggestions": property_suggestions,
            }),
        )
        session.add(staged)
        created.append(staged)
    document.status = "parsed"
    session.commit()
    return created


def bucket_counts(session: Session) -> dict[str, int]:
    rows = session.exec(select(InvoiceLineStaging)).all()
    counts = {"high_confidence": 0, "assisted_match": 0, "exception": 0}
    for row in rows:
        counts[row.bucket] = counts.get(row.bucket, 0) + 1
    return counts


def approve_staged_line(session: Session, staging_id: int, approved_by: str = "ui") -> InvoiceLineStaging:
    line = session.get(InvoiceLineStaging, staging_id)
    if not line:
        raise ValueError("Staged line not found")
    document = session.get(InvoiceDocument, line.document_id)
    if line.matched_product_id and line.unit_cost > 0:
        create_price_history(
            session,
            product_id=line.matched_product_id,
            vendor_name=document.vendor_name if document else "",
            invoice_number=document.invoice_number if document else "",
            unit_cost=line.unit_cost,
            pack_size=line.unit,
            confidence=line.confidence,
            approved_by=approved_by,
        )
    if line.matched_property_id:
        delivery = create_delivery(
            session,
            property_id=line.matched_property_id,
            vendor_name=document.vendor_name if document else "",
            invoice_number=document.invoice_number if document else "",
            delivery_ticket=document.original_filename if document else "",
            status="delivered",
            source_document_id=document.id if document else None,
        )
        add_delivery_item(
            session,
            delivery_id=delivery.id,
            product_name=line.product_text,
            quantity_ordered=line.quantity,
            quantity_delivered=line.quantity,
            quantity_confirmed=0.0,
            unit=line.unit or "ea",
            unit_cost=line.unit_cost,
            product_id=line.matched_product_id,
            confidence=line.confidence,
        )
    session.add(SupplierTrainingExample(
        vendor_name=document.vendor_name if document else "",
        source_document_id=document.id if document else None,
        raw_text=line.raw_line_text,
        approved_product_id=line.matched_product_id,
        approved_property_id=line.matched_property_id,
        outcome="approved",
    ))
    line.review_status = "approved"
    session.commit()
    session.refresh(line)
    return line


def reject_staged_line(session: Session, staging_id: int, notes: str = "") -> InvoiceLineStaging:
    line = session.get(InvoiceLineStaging, staging_id)
    if not line:
        raise ValueError("Staged line not found")
    document = session.get(InvoiceDocument, line.document_id)
    session.add(SupplierTrainingExample(
        vendor_name=document.vendor_name if document else "",
        source_document_id=document.id if document else None,
        raw_text=line.raw_line_text,
        approved_product_id=None,
        approved_property_id=None,
        correction_notes=notes,
        outcome="rejected",
    ))
    line.review_status = "rejected"
    session.commit()
    session.refresh(line)
    return line
