from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session

from app.core.database import engine
from app.services.property_verification import create_verification_case, list_verification_cases
from app.services.tools import list_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
def get_tools():
    with Session(engine) as session:
        return [tool.model_dump() for tool in list_tools(session)]


@router.get("/property-verification")
def get_property_verifications(limit: int = 25):
    with Session(engine) as session:
        return [case.model_dump() for case in list_verification_cases(session, limit=limit)]


@router.post("/property-verification")
def post_property_verification(payload: dict):
    with Session(engine) as session:
        case = create_verification_case(
            session=session,
            property_id=payload.get("property_id"),
            account_type=payload.get("account_type", "residential"),
            input_address=payload.get("input_address", ""),
            caller_name=payload.get("caller_name", ""),
            caller_phone=payload.get("caller_phone", ""),
            caller_role=payload.get("caller_role", ""),
            owner_name=payload.get("owner_name", ""),
            owner_mailing_address=payload.get("owner_mailing_address", ""),
            parcel_id=payload.get("parcel_id", ""),
            sunbiz_entity_name=payload.get("sunbiz_entity_name", ""),
            sunbiz_role_matches=payload.get("sunbiz_role_matches", ""),
            source_mode=payload.get("source_mode", "manual"),
            raw_payload=payload,
            notes=payload.get("notes", ""),
        )
        return case.model_dump()
