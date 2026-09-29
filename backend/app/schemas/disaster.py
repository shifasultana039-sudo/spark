"""
Schemas for disaster reports, locations, relief inventory, and AI recommendations.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class ReportCreate(BaseModel):
    source: str
    location: str
    sub_zone: Optional[str] = None
    latitude: float
    longitude: float
    description: str
    people_affected: int = 0
    severity: str
    required_resources: List[str]
    evidence_available: Optional[str] = "None"

class RecommendationOverride(BaseModel):
    modified_quantity: int
    override_reason: str
    supervisor_name: str
    supervisor_role: str = "RELIEF_COORDINATOR"

class RecommendationAction(BaseModel):
    actor_name: str
    actor_role: str = "RELIEF_COORDINATOR"
    wallet_address: Optional[str] = None

class ResourceDispatchPayload(BaseModel):
    resource_type: str
    quantity: int
    location_name: Optional[str] = "General Dispatch"
    actor_name: Optional[str] = "Relief Coordinator"
    actor_role: Optional[str] = "RELIEF_COORDINATOR"
