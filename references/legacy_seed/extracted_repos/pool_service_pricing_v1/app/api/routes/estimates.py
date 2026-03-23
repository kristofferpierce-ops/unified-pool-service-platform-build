from fastapi import APIRouter

from app.core.database import get_session
from app.services.estimator import EstimateInputs, run_estimate

router = APIRouter()


@router.post("/run")
def estimate(payload: EstimateInputs):
    with get_session() as session:
        return run_estimate(session, payload)
