from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .schemas import EstimateRequest, EstimateResult, HealthResponse
from .service import PoolVolumeService

router = APIRouter(prefix="/tools/pool-volume", tags=["pool-volume"])
service = PoolVolumeService.build_default()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse()


@router.post("/inspect-live")
def inspect_live(request: EstimateRequest) -> dict:
    try:
        return service.inspect_live(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/estimate", response_model=EstimateResult)
def estimate_pool_volume(request: EstimateRequest) -> EstimateResult:
    try:
        return service.estimate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
