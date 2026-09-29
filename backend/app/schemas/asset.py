"""
ReliefChain AI - Digital Asset Registry Schemas.
Validates asset registration, queries, and updates.
"""

import re
from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
from ..models.entities import AssetCategory


class AssetCreateRequest(BaseModel):
    """Payload for registering a citizen asset in ReliefChain AI."""
    category: AssetCategory = Field(..., description="Asset category")
    description: str = Field(..., min_length=3, description="Detailed description of the asset")
    documented_value: Optional[float] = Field(None, description="Documented or approximate value in INR")
    approximate_value: Optional[float] = Field(None, description="Alternative field for documented value")
    value: Optional[float] = Field(None, description="Alternative field for documented value")
    purchase_date: Optional[str] = Field(None, description="Purchase date (YYYY-MM-DD or ISO)")
    location: Optional[str] = Field(None, description="Asset location or address")
    location_address: Optional[str] = Field(None, description="Alternative field for location")
    household: Optional[str] = Field(None, description="Associated household reference code")
    household_ref: Optional[str] = Field(None, description="Alternative field for household")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

    @model_validator(mode="after")
    def validate_asset_payload(self) -> "AssetCreateRequest":
        # 1. Resolve and validate value
        val = (
            self.documented_value
            if self.documented_value is not None
            else (self.approximate_value if self.approximate_value is not None else self.value)
        )
        if val is None or val <= 0:
            raise ValueError("approximate/documented value is required and must be greater than 0.")
        self.documented_value = float(val)
        self.approximate_value = float(val)

        # 2. Resolve and validate location
        loc = self.location or self.location_address
        if not loc or not loc.strip():
            raise ValueError("location (or location_address) is required and cannot be empty.")
        self.location = loc.strip()
        self.location_address = loc.strip()

        # 3. Resolve household
        hh = self.household or self.household_ref
        if hh and hh.strip():
            self.household = hh.strip()
            self.household_ref = hh.strip()

        # 4. Validate purchase_date format if provided
        if self.purchase_date:
            pd = self.purchase_date.strip()
            # Accept YYYY-MM-DD or ISO
            date_pattern = r"^\d{4}-\d{2}-\d{2}"
            if not re.match(date_pattern, pd):
                raise ValueError(f"Invalid purchase_date format '{pd}'. Expected YYYY-MM-DD.")
            self.purchase_date = pd
        else:
            # Default to today's date if omitted
            self.purchase_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 5. Sanitize description
        self.description = self.description.strip()
        return self


class AssetUpdateRequest(BaseModel):
    """Payload for updating an existing asset."""
    category: Optional[AssetCategory] = None
    description: Optional[str] = Field(None, min_length=3)
    documented_value: Optional[float] = None
    approximate_value: Optional[float] = None
    value: Optional[float] = None
    purchase_date: Optional[str] = None
    location: Optional[str] = None
    location_address: Optional[str] = None
    household: Optional[str] = None
    household_ref: Optional[str] = None
    current_status: Optional[str] = None
    status: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

    @model_validator(mode="after")
    def validate_update_payload(self) -> "AssetUpdateRequest":
        # Ensure status cannot be marked VERIFIED in Asset Registry
        if self.status and self.status.strip().upper() == "VERIFIED":
            raise ValueError("Assets cannot be marked as VERIFIED directly in Asset Registry. Official verification occurs in the verification pipeline.")

        val = (
            self.documented_value
            if self.documented_value is not None
            else (self.approximate_value if self.approximate_value is not None else self.value)
        )
        if val is not None:
            if val <= 0:
                raise ValueError("approximate/documented value must be greater than 0.")
            self.documented_value = float(val)
            self.approximate_value = float(val)

        loc = self.location or self.location_address
        if loc is not None:
            if not loc.strip():
                raise ValueError("location cannot be empty.")
            self.location = loc.strip()
            self.location_address = loc.strip()

        hh = self.household or self.household_ref
        if hh is not None:
            if not hh.strip():
                raise ValueError("household cannot be empty.")
            self.household = hh.strip()
            self.household_ref = hh.strip()

        if self.purchase_date:
            pd = self.purchase_date.strip()
            date_pattern = r"^\d{4}-\d{2}-\d{2}"
            if not re.match(date_pattern, pd):
                raise ValueError(f"Invalid purchase_date format '{pd}'. Expected YYYY-MM-DD.")
            self.purchase_date = pd

        return self


class AssetResponse(BaseModel):
    """Standard asset response structure."""
    asset_id: str
    category: str
    description: str
    documented_value: float
    approximate_value: float
    purchase_date: Optional[str] = None
    location: str
    location_address: str
    household: str
    household_ref: str
    registration_timestamp: str
    created_at: str
    updated_at: Optional[str] = None
    status: str
    verification_confidence: int = 0
    current_status: str = "INTACT"
    citizen_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    integrity_hash: Optional[str] = None

    class Config:
        from_attributes = True


from ..models.entities import AssetCategory, EvidenceType


class EvidenceResponse(BaseModel):
    """Normalized evidence artifact response."""
    evidence_id: str
    asset_id: str
    evidence_type: str
    file_url: str
    original_filename: str
    sha256_hash: str
    file_size: int
    mime_type: str
    uploader: str
    verification_status: str = "PENDING"
    score_contribution: int = 0
    captured_timestamp: Optional[str] = None
    metadata_json: Optional[str] = "{}"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class EvidenceCreateRequest(BaseModel):
    """Payload for uploading or registering evidence via JSON."""
    evidence_type: EvidenceType
    original_filename: str = Field(..., min_length=1)
    file_content_base64: Optional[str] = None
    captured_timestamp: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    metadata: Optional[Dict[str, Any]] = None


class AssetVerifyRequest(BaseModel):
    """Optional payload when triggering verification evaluation."""
    custom_weights: Optional[Dict[str, int]] = Field(None, description="Optional override weights for this evaluation")
    evaluator_note: Optional[str] = Field(None, description="Evaluator annotation or inspection note")


class AssetVerificationDetailResponse(BaseModel):
    """Deterministic verification output matching requested format."""
    asset_id: str
    status: str
    confidence: int
    explanation: str
    contributions: List[Dict[str, Any]] = []
    weights_used: Optional[Dict[str, int]] = None
    verification_id: Optional[str] = None
    evaluated_by: Optional[str] = None
    verified_at: Optional[str] = None
    is_deterministic: bool = True
    engine_type: str = "DETERMINISTIC_RULES"
    can_issue_certificate: bool = False
    history: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class FrontendCertificateCard(BaseModel):
    """Clean representation of the certificate formatted for frontend card display."""
    card_title: str = "RELIEFCHAIN DIGITAL ASSET CERTIFICATE"
    certificate_id: str
    asset_id: str
    badge: str = "OFFICIALLY VERIFIED PRE-DISASTER ASSET"
    category_label: str
    description: str
    verification_status: str
    confidence_score: str
    confidence_tier: str = "HIGH CONFIDENCE"
    evidence_hash: str
    registration_date: str
    issued_date: str
    qr_code_data_uri: str
    verification_endpoint: str
    trust_seal: str = "SHA-256 VERIFIED CIVIC BASELINE"
    issuer: str = "ReliefChain AI Civic Trust Authority"


class AssetCertificateResponse(BaseModel):
    """
    Standard Digital Asset Certificate representation (Step 11).
    Contains:
    - certificate ID
    - asset ID
    - category
    - description
    - verification status
    - evidence confidence
    - evidence hash
    - registration timestamp
    - verification history
    - QR code
    """
    certificate_id: str
    asset_id: str
    category: str
    description: str
    verification_status: str
    evidence_confidence: int
    evidence_hash: str
    registration_timestamp: str
    verification_history: List[Dict[str, Any]] = []
    qr_code: str
    certificate_token: str
    issued_at: str
    verification_url: str
    qr_code_svg: Optional[str] = None
    frontend_card: Optional[FrontendCertificateCard] = None

    class Config:
        from_attributes = True


class SafeCertificateVerificationResponse(BaseModel):
    """
    Public safe verification response returned by QR verification endpoint.
    Crucial Privacy Guarantee: Strictly excludes citizen PII (name, phone, address, valuation).
    """
    is_valid: bool = True
    certificate_id: str
    asset_id: str
    category: str
    description: str
    verification_status: str
    evidence_confidence: int
    evidence_hash: str
    issued_at: str
    issuer: str = "ReliefChain AI Civic Trust Authority"
    verification_timestamp: str
    verification_message: str

    class Config:
        from_attributes = True


# Preserve legacy base schemas for backwards compatibility
class AssetBase(BaseModel):
    category: str
    description: str
    documented_value: float
    location_address: str
    purchase_date: Optional[str] = None
    household_ref: Optional[str] = "HH-1001"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class AssetEvidenceBase(BaseModel):
    evidence_type: str
    original_filename: str
    file_size: int = 1024
    mime_type: str = "image/jpeg"
    uploader: str = "Citizen"

class DisasterClaimBase(BaseModel):
    asset_id: str
    disaster_id: str
    damage_description: str
    household_ref: Optional[str] = "HH-1001"


