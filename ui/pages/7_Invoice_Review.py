from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from sqlmodel import Session, select

from app.core.config import UPLOAD_DIR
from app.core.database import engine
from app.models.tables import InvoiceLineStaging
from app.services.invoice_ingestion import approve_staged_line, bucket_counts, ingest_invoice_document, reject_staged_line
from app.utils.serialization import loads

st.title("Invoice Review")

with Session(engine) as session:
    vendor_name = st.text_input("Vendor name")
    uploaded = st.file_uploader("Invoice document", type=["pdf", "txt", "csv"])
    if uploaded is not None:
        temp_path = UPLOAD_DIR / uploaded.name
        temp_path.write_bytes(uploaded.read())
        if st.button("Ingest uploaded invoice", type="primary"):
            doc = ingest_invoice_document(session, temp_path, vendor_name=vendor_name)
            st.success(f"Invoice ingested: {doc.original_filename}")

    counts = bucket_counts(session)
    c1, c2, c3 = st.columns(3)
    c1.metric("High confidence", counts.get("high_confidence", 0))
    c2.metric("Assisted match", counts.get("assisted_match", 0))
    c3.metric("Exception", counts.get("exception", 0))

    bucket = st.selectbox("Review bucket", ["high_confidence", "assisted_match", "exception"])
    rows = list(session.exec(select(InvoiceLineStaging).where(InvoiceLineStaging.bucket == bucket, InvoiceLineStaging.review_status == "pending")).all())
    for row in rows[:50]:
        with st.expander(f"Line {row.id} | {row.product_text[:80]}"):
            st.write(row.raw_line_text)
            st.write(f"Confidence: {row.confidence:.2f}")
            st.write(f"Matched product ID: {row.matched_product_id}")
            st.write(f"Matched property ID: {row.matched_property_id}")
            st.json(loads(row.suggestion_json, {}))
            col1, col2 = st.columns(2)
            if col1.button(f"Approve {row.id}"):
                approve_staged_line(session, row.id)
                st.success("Approved")
            if col2.button(f"Reject {row.id}"):
                reject_staged_line(session, row.id, notes="Rejected in UI")
                st.warning("Rejected")
