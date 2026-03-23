from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

from sqlmodel import Session, select

from app.models.tables import ApprovedAgent, Property, PropertyVerificationCase
from app.services.tools import log_tool_run
from app.utils.serialization import dumps, loads


def normalize_name(value: str) -> str:
    cleaned = " ".join((value or "").strip().lower().replace(",", " ").replace(".", " ").split())
    suffixes = {"llc", "inc", "corp", "corporation", "co", "ltd", "lp", "llp", "pllc"}
    parts = [part for part in cleaned.split() if part not in suffixes]
    return " ".join(parts)


def looks_like_entity(name: str) -> bool:
    lowered = (name or "").lower()
    markers = ["llc", "inc", "corp", "corporation", "management", "holdings", "properties", "trust", "company", "partners", "association"]
    return any(marker in lowered for marker in markers)


def person_name_match(a: str, b: str) -> bool:
    na = normalize_name(a)
    nb = normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    set_a = set(na.split())
    set_b = set(nb.split())
    if len(set_a.intersection(set_b)) >= 2:
        return True
    return False


def build_property_search_url(address: str = "") -> str:
    base = "https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946&PageTypeID=4&PageID=4575"
    return f"{base}&KeyValue={quote_plus(address)}" if address else base


def build_gis_url(address: str = "") -> str:
    base = "https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946&PageTypeID=1&PageID=3846"
    return f"{base}&KeyValue={quote_plus(address)}" if address else base


def build_sunbiz_entity_search_url(entity_name: str = "") -> str:
    base = "https://search.sunbiz.org/Inquiry/CorporationSearch/ByName"
    return f"{base}?searchTerm={quote_plus(entity_name)}" if entity_name else base


def build_source_links(address: str, entity_name: str = "") -> dict[str, str]:
    return {
        "property_search": build_property_search_url(address),
        "gis_maps": build_gis_url(address),
        "sunbiz_entity_search": build_sunbiz_entity_search_url(entity_name),
    }


def list_approved_agents(session: Session, property_id: int) -> list[ApprovedAgent]:
    return list(session.exec(
        select(ApprovedAgent)
        .where(ApprovedAgent.property_id == property_id)
        .where(ApprovedAgent.is_active == True)
        .order_by(ApprovedAgent.full_name)
    ).all())


def add_approved_agent(session: Session, property_id: int, full_name: str, role_label: str = "", company_name: str = "", phone: str = "", email: str = "", approval_source: str = "manual", notes: str = "") -> ApprovedAgent:
    agent = ApprovedAgent(
        property_id=property_id,
        full_name=full_name,
        role_label=role_label,
        company_name=company_name,
        phone=phone,
        email=email,
        approval_source=approval_source,
        notes=notes,
        is_active=True,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@dataclass
class VerificationDecision:
    status: str
    recommended_action: str
    owner_type: str
    matched_approved_agents: list[str]
    source_links: dict[str, str]


def evaluate_verification(
    caller_name: str,
    caller_role: str,
    input_address: str,
    owner_name: str,
    parcel_id: str = "",
    approved_agents: Optional[list[ApprovedAgent]] = None,
    sunbiz_entity_name: str = "",
    sunbiz_role_matches: str = "",
) -> VerificationDecision:
    approved_agents = approved_agents or []
    owner_type = "entity" if looks_like_entity(owner_name or sunbiz_entity_name) else "individual"
    links = build_source_links(input_address, sunbiz_entity_name or owner_name)

    if owner_name and person_name_match(caller_name, owner_name) and owner_type == "individual":
        return VerificationDecision(
            status="verified_owner",
            recommended_action="Caller matches the parcel owner. Proceed with normal intake and note the source record.",
            owner_type=owner_type,
            matched_approved_agents=[],
            source_links=links,
        )

    matched_agents = [agent.full_name for agent in approved_agents if person_name_match(caller_name, agent.full_name)]
    if matched_agents:
        return VerificationDecision(
            status="likely_authorized_agent",
            recommended_action="Caller matches an approved agent on file. Proceed, but keep owner-approval notes visible in the account record.",
            owner_type=owner_type,
            matched_approved_agents=matched_agents,
            source_links=links,
        )

    if owner_type == "entity" and (sunbiz_role_matches or caller_role):
        combined = f"{caller_role} {sunbiz_role_matches}".lower()
        if any(token in combined for token in ["manager", "member", "officer", "president", "registered agent", "authorized"]):
            return VerificationDecision(
                status="likely_authorized_agent",
                recommended_action="Entity ownership detected and caller appears tied to an authorized business role. Verify the relationship and document the source before scheduling non-emergency work.",
                owner_type=owner_type,
                matched_approved_agents=[],
                source_links=links,
            )

    role_lower = (caller_role or "").lower()
    if any(token in role_lower for token in ["property manager", "manager", "tenant rep", "caretaker", "family"]):
        return VerificationDecision(
            status="needs_owner_approval",
            recommended_action="Caller may be operationally involved, but ownership authority is not verified. Require owner confirmation, management agreement, or prior approved-agent record before non-emergency work.",
            owner_type=owner_type,
            matched_approved_agents=[],
            source_links=links,
        )

    return VerificationDecision(
        status="high_renter_guest_risk",
        recommended_action="Do not treat occupancy as authority. Require owner confirmation, management agreement, or approved-agent record before non-emergency work.",
        owner_type=owner_type,
        matched_approved_agents=[],
        source_links=links,
    )


def create_verification_case(
    session: Session,
    property_id: Optional[int],
    account_type: str,
    input_address: str,
    caller_name: str,
    caller_phone: str,
    caller_role: str,
    owner_name: str,
    owner_mailing_address: str = "",
    parcel_id: str = "",
    sunbiz_entity_name: str = "",
    sunbiz_role_matches: str = "",
    source_mode: str = "manual",
    raw_payload: Optional[dict] = None,
    notes: str = "",
) -> PropertyVerificationCase:
    approved_agents = list_approved_agents(session, property_id) if property_id else []
    decision = evaluate_verification(
        caller_name=caller_name,
        caller_role=caller_role,
        input_address=input_address,
        owner_name=owner_name,
        parcel_id=parcel_id,
        approved_agents=approved_agents,
        sunbiz_entity_name=sunbiz_entity_name,
        sunbiz_role_matches=sunbiz_role_matches,
    )
    run = log_tool_run(
        session,
        tool_slug="property_authority_verification",
        input_payload={
            "property_id": property_id,
            "account_type": account_type,
            "input_address": input_address,
            "caller_name": caller_name,
            "caller_role": caller_role,
            "owner_name": owner_name,
            "parcel_id": parcel_id,
            "source_mode": source_mode,
        },
        output_payload={
            "status": decision.status,
            "recommended_action": decision.recommended_action,
            "owner_type": decision.owner_type,
            "source_links": decision.source_links,
        },
    )
    case = PropertyVerificationCase(
        property_id=property_id,
        tool_run_id=run.id,
        account_type=account_type,
        input_address=input_address,
        caller_name=caller_name,
        caller_phone=caller_phone,
        caller_role=caller_role,
        parcel_id=parcel_id,
        owner_name=owner_name,
        owner_mailing_address=owner_mailing_address,
        owner_type=decision.owner_type,
        sunbiz_entity_name=sunbiz_entity_name,
        sunbiz_role_matches=sunbiz_role_matches,
        approved_agent_matches=", ".join(decision.matched_approved_agents),
        verification_status=decision.status,
        recommended_action=decision.recommended_action,
        source_mode=source_mode,
        raw_payload_json=dumps(raw_payload or {"source_links": decision.source_links}),
        notes=notes,
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def list_verification_cases(session: Session, limit: int = 50) -> list[PropertyVerificationCase]:
    return list(session.exec(select(PropertyVerificationCase).order_by(PropertyVerificationCase.created_at.desc()).limit(limit)).all())
