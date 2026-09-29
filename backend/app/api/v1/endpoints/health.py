"""
Health check endpoints for system observability and uptime monitoring.
"""

from fastapi import APIRouter, status
from ....core.database import check_db_health, get_db_telemetry
from ....core.config import STORAGE_DIR
from ....schemas.common import HealthResponse
from ....utils.helpers import get_current_utc_iso

router = APIRouter(tags=["Health"])

@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Diagnostic Telemetry"
)
def get_health() -> HealthResponse:
    """
    Returns operational health status across core components:
    - Application server runtime
    - Database connectivity (PostgreSQL or SQLite)
    - Evidence storage directory accessibility
    """
    db_ok = check_db_health()
    storage_ok = STORAGE_DIR.exists()

    overall_status = "HEALTHY" if (db_ok and storage_ok) else "DEGRADED"

    return HealthResponse(
        status=overall_status,
        database="CONNECTED" if db_ok else "DISCONNECTED",
        storage="ACCESSIBLE" if storage_ok else "UNAVAILABLE",
        version="1.0.0",
        timestamp=get_current_utc_iso()
    )

@router.get(
    "/health/db",
    status_code=status.HTTP_200_OK,
    summary="Database Engine & Telemetry Diagnostics"
)
def get_db_health_diagnostic():
    """
    Detailed database diagnostics:
    - Active engine (postgresql vs sqlite)
    - Connection status
    - Driver availability (psycopg)
    - Target host and database
    """
    telemetry = get_db_telemetry()
    return {
        "status": telemetry["status"],
        "telemetry": telemetry,
        "timestamp": get_current_utc_iso()
    }

