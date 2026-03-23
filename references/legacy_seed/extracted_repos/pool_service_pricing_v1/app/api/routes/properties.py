from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.database import get_session
from app.models.tables import Property

router = APIRouter()


@router.get("")
def list_properties():
    with get_session() as session:
        return list(session.exec(select(Property).order_by(Property.property_name)).all())


@router.post("")
def create_property(payload: Property):
    with get_session() as session:
        row = Property(**payload.model_dump(exclude={"id"}))
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


@router.get("/{property_id}")
def get_property(property_id: int):
    with get_session() as session:
        row = session.get(Property, property_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Property not found")
        return row
