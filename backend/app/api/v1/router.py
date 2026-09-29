"""
Central API v1 router aggregator.
"""

from fastapi import APIRouter
from .endpoints import health, kpis, disasters, audit, assets, claims, evidence, certificates, auth, inspections

api_v1_router = APIRouter()

# Authentication & User identity
api_v1_router.include_router(auth.router)

# Core system endpoints
api_v1_router.include_router(health.router)
api_v1_router.include_router(kpis.router)

# Disaster operations domain
api_v1_router.include_router(disasters.router)
api_v1_router.include_router(audit.router)

# Foundation modules for Digital Asset Verification & Disaster Claims
api_v1_router.include_router(assets.router)
api_v1_router.include_router(evidence.router)
api_v1_router.include_router(claims.router)
api_v1_router.include_router(certificates.router)
api_v1_router.include_router(inspections.router)


