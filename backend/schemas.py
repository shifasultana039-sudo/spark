"""
Pydantic validation schemas for ReliefChain AI.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# --- User & Auth ---
class UserBase(BaseModel):
    user_id: str
    name: str
    email: Optional[str] = None
    role: str
    organization: Optional[str] = None
    wallet_address: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: str

# --- Disaster Reports ---
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

class ReportResponse(BaseModel):
    id: int
    report_id: str
    source: str
    location: str
    sub_zone: Optional[str] = None
    latitude: float
    longitude: float
    description: str
    people_affected: int
    severity: str
    required_resources: Any
    evidence_available: str
    timestamp: str
    trust_score: int
    source_reliability_score: int
    cross_confirmation_score: int
    evidence_score: int
    recency_score: int
    consistency_penalty: int
    verification_status: str
    duplicate_cluster_id: Optional[str] = None
    is_contradictory: int
    safety_gate_note: Optional[str] = None
    content_hash: Optional[str] = None
    created_at: str

# --- Recommendations ---
class RecommendationOverride(BaseModel):
    modified_quantity: int
    override_reason: str
    supervisor_name: str
    supervisor_role: str = "RELIEF_COORDINATOR"

class RecommendationAction(BaseModel):
    actor_name: str
    actor_role: str = "RELIEF_COORDINATOR"
    wallet_address: Optional[str] = None

# --- Citizen Assets ---
class AssetCreate(BaseModel):
    category: str
    description: str
    documented_value: float
    purchase_date: Optional[str] = None
    location_address: str
    latitude: Optional[float] = 12.9806
    longitude: Optional[float] = 79.1417
    household_ref: Optional[str] = "HH-1001"

class EvidenceCreate(BaseModel):
    evidence_type: str
    original_filename: str
    file_content_base64: Optional[str] = None
    file_size: int = 1024
    mime_type: str = "image/jpeg"
    uploader: str = "Demo Citizen"
    captured_timestamp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# --- Disaster Claims ---
class ClaimCreate(BaseModel):
    asset_id: str
    disaster_id: str = "DIS-2026-0007"
    damage_description: str
    household_ref: Optional[str] = "HH-1001"
    post_disaster_photos: Optional[List[str]] = None

class OfficerReviewAction(BaseModel):
    action: str # APPROVE, MODIFY, REQUEST_MORE_EVIDENCE, REJECT, FORWARD_FOR_FIELD_INSPECTION
    officer_name: str = "Officer Rajesh V"
    officer_role: str = "GOVERNMENT_OFFICER"
    comment: Optional[str] = None
    modified_damage_percent: Optional[int] = None
    modified_compensation_amount: Optional[float] = None
    inspection_notes: Optional[str] = None
