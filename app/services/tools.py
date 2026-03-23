from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlmodel import Session, select

from app.models.tables import ToolCatalogEntry, ToolRun
from app.utils.serialization import dumps


@dataclass(frozen=True)
class ToolDefinition:
    slug: str
    name: str
    category: str
    description: str
    page_key: str


DEFAULT_TOOLS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        slug="property_authority_verification",
        name="Property Authority Verification",
        category="intake",
        description="Check whether a caller is an owner, likely authorized agent, or needs owner approval before scheduling.",
        page_key="tools_property_verification",
    ),
    ToolDefinition(
        slug="invoice_ingestion_review",
        name="Invoice Ingestion Review",
        category="operations",
        description="Review parsed invoices, approve high-confidence matches, and clear assisted-match backlogs.",
        page_key="invoice_review",
    ),
    ToolDefinition(
        slug="commercial_delivery_reporting",
        name="Commercial Delivery Reporting",
        category="billing",
        description="Review direct-delivery activity by property and export monthly billing reports.",
        page_key="commercial_deliveries",
    ),
)


def seed_tools(session: Session) -> None:
    existing = {tool.slug for tool in session.exec(select(ToolCatalogEntry)).all()}
    for tool in DEFAULT_TOOLS:
        if tool.slug not in existing:
            session.add(ToolCatalogEntry(
                slug=tool.slug,
                name=tool.name,
                category=tool.category,
                description=tool.description,
                page_key=tool.page_key,
                is_enabled=True,
            ))
    session.commit()


def list_tools(session: Session, enabled_only: bool = True) -> list[ToolCatalogEntry]:
    query = select(ToolCatalogEntry)
    if enabled_only:
        query = query.where(ToolCatalogEntry.is_enabled == True)
    return list(session.exec(query.order_by(ToolCatalogEntry.category, ToolCatalogEntry.name)).all())


def log_tool_run(session: Session, tool_slug: str, input_payload: dict, output_payload: dict, status: str = "completed", notes: str = "") -> ToolRun:
    run = ToolRun(
        tool_slug=tool_slug,
        status=status,
        input_json=dumps(input_payload),
        output_json=dumps(output_payload),
        notes=notes,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
