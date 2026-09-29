"""
KPI telemetry endpoint for emergency operations.
"""

from fastapi import APIRouter
from ....repositories.disaster_repo import DisasterRepository
from ....utils.helpers import get_current_utc_iso

router = APIRouter(tags=["KPIs"])

@router.get("/kpis", summary="High-level Emergency Operations Metrics")
def get_kpis():
    data = DisasterRepository.get_kpis()
    data["timestamp"] = get_current_utc_iso()
    return data
