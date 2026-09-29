"""
ReliefChain AI - Disaster Compensation Claim Schemas (Step 12).
Validates claim creation, listing, retrieval, and workflow states.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
from ..models.entities import ClaimReviewStatus


class ClaimCreateRequest(BaseModel):
    """Payload for submitting a disaster claim against a registered asset."""
    asset_id: str = Field(..., min_length=3, description="Referenced registered asset ID (e.g. AST-2026-000001)")
    damage_description: str = Field(..., min_length=3, description="Detailed description of the disaster damage")
    disaster_id: Optional[str] = Field(None, description="Disaster event identifier")
    disaster_event: Optional[str] = Field(None, description="Alternative field for disaster event identifier")
    household: Optional[str] = Field(None, description="Household reference code")
    household_ref: Optional[str] = Field(None, description="Alternative field for household reference code")

    @model_validator(mode="after")
    def validate_payload(self) -> "ClaimCreateRequest":
        # 1. Clean asset_id
        self.asset_id = self.asset_id.strip()

        # 2. Resolve disaster event identifier
        disaster = self.disaster_id or self.disaster_event
        if disaster and disaster.strip():
            self.disaster_id = disaster.strip()
            self.disaster_event = disaster.strip()
        else:
            self.disaster_id = "DIS-2026-0007"
            self.disaster_event = "DIS-2026-0007"

        # 3. Clean damage description
        self.damage_description = self.damage_description.strip()

        # 4. Resolve household
        hh = self.household or self.household_ref
        if hh and hh.strip():
            self.household = hh.strip()
            self.household_ref = hh.strip()

        return self


class ClaimResponse(BaseModel):
    """
    Standard Disaster Claim Representation (Step 12).
    Contains:
    - claim ID
    - asset ID
    - household
    - disaster event
    - pre-disaster verification state
    - claim status
    - created timestamp
    """
    claim_id: str
    asset_id: str
    household: str
    household_ref: str
    disaster_event: str
    disaster_id: str
    pre_disaster_verification_state: str
    pre_disaster_verification_status: str
    claim_status: str
    status: str
    review_status: str
    created_timestamp: str
    created_at: str
    damage_description: str
    officer_decision: Optional[str] = None
    updated_at: Optional[str] = None
    citizen_id: Optional[int] = None
    asset_category: Optional[str] = None
    asset_description: Optional[str] = None
    location: Optional[str] = None
    location_address: Optional[str] = None
    evidence_confidence: Optional[int] = None
    damage_category: Optional[str] = None
    estimated_damage_percentage: Optional[int] = None
    damage_percentage: Optional[float] = None
    indicative_loss_amount: Optional[float] = None
    approved_compensation_amount: Optional[float] = None

    class Config:
        from_attributes = True


class ClaimEvidenceCreateRequest(BaseModel):
    """Payload for uploading or registering post-disaster claim evidence via JSON."""
    evidence_type: str = Field(..., description="Post-disaster evidence type (e.g. POST_DISASTER_PHOTO, DAMAGED_PHOTO, POST_DISASTER_VIDEO, FIELD_INSPECTION_REPORT)")
    original_filename: str = Field(..., min_length=1, description="Original filename with extension (e.g. damaged_wall.jpg)")
    file_content_base64: str = Field(..., description="Base64 encoded file content")
    captured_timestamp: Optional[str] = Field(None, description="Timestamp when evidence was captured")
    uploader: Optional[str] = Field(None, description="Name or role of person uploading evidence")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional technical metadata")


class ClaimEvidenceResponse(BaseModel):
    """
    Standard Post-Disaster Claim Evidence Representation (Step 13).
    Associates evidence with the claim and preserves original file hash.
    """
    evidence_id: str
    claim_id: str
    asset_id: Optional[str] = None
    evidence_type: str
    file_url: str
    original_filename: str
    sha256_hash: str
    file_size: int
    mime_type: str
    captured_timestamp: Optional[str] = None
    created_at: str
    uploader: Optional[str] = "Citizen"

    class Config:
        from_attributes = True


class ClaimApproveRequest(BaseModel):
    approved_amount: Optional[float] = None
    approved_compensation_amount: Optional[float] = None
    notes: Optional[str] = "Claim approved by revenue officer following evidentiary validation."
    officer_notes: Optional[str] = None


class ClaimRequestEvidenceRequest(BaseModel):
    notes: Optional[str] = None
    officer_notes: Optional[str] = None
    requested_types: Optional[List[str]] = None
    requested_evidence_types: Optional[List[str]] = None


class ClaimModifyAssessmentRequest(BaseModel):
    damage_percentage: Optional[int] = None
    modified_damage_percentage: Optional[float] = None
    damage_category: Optional[str] = None
    modified_damage_category: Optional[str] = None
    notes: Optional[str] = None
    modification_rationale: Optional[str] = None
    officer_notes: Optional[str] = None


class ClaimRejectRequest(BaseModel):
    reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    officer_notes: Optional[str] = None



class ClaimForwardInspectionRequest(BaseModel):
    inspector_notes: Optional[str] = "Physical on-site inspection requested by revenue officer."
    assigned_sector: Optional[str] = None
    assigned_officer: Optional[str] = None
    inspection_sector: Optional[str] = None
    assigned_inspector_id: Optional[str] = None
    special_instructions: Optional[str] = None

    class Config:
        from_attributes = True

