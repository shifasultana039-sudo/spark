"""
Relational domain models and status enumerations for ReliefChain AI:
Digital Asset Verification & Disaster Compensation Module.
Supports both SQLite and PostgreSQL relational conventions.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# --- Status & Type Enumerations ---

class UserRole(str, Enum):
    CITIZEN = "CITIZEN"
    NGO = "NGO"
    GOVERNMENT_OFFICER = "GOVERNMENT_OFFICER"
    FIELD_ASSESSOR = "FIELD_ASSESSOR"
    RELIEF_COORDINATOR = "RELIEF_COORDINATOR"
    ADMIN = "ADMIN"
    PUBLIC_VIEWER = "PUBLIC_VIEWER"



class AssetCategory(str, Enum):
    HOUSE_PROPERTY = "HOUSE_PROPERTY"
    VEHICLE = "VEHICLE"
    AGRICULTURAL_EQUIPMENT = "AGRICULTURAL_EQUIPMENT"
    ELECTRONICS = "ELECTRONICS"
    HOUSEHOLD_APPLIANCE = "HOUSEHOLD_APPLIANCE"
    LIVESTOCK = "LIVESTOCK"
    BUSINESS_EQUIPMENT = "BUSINESS_EQUIPMENT"
    PERSONAL_PROPERTY = "PERSONAL_PROPERTY"
    OTHER = "OTHER"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized = value.strip().upper().replace(" / ", "_").replace(" ", "_").replace("-", "_")
            for member in cls:
                if member.value == normalized or member.name == normalized:
                    return member
        return None



class AssetVerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    VERIFIED = "VERIFIED"
    OFFICIALLY_CONFIRMED = "OFFICIALLY_CONFIRMED"


class AssetPhysicalStatus(str, Enum):
    INTACT = "INTACT"
    DAMAGED = "DAMAGED"
    DESTROYED = "DESTROYED"


class EvidenceType(str, Enum):
    PURCHASE_INVOICE = "PURCHASE_INVOICE"
    GOVERNMENT_REGISTRATION = "GOVERNMENT_REGISTRATION"
    PROPERTY_DEED = "PROPERTY_DEED"
    WARRANTY = "WARRANTY"
    TIMESTAMPED_PHOTO = "TIMESTAMPED_PHOTO"
    GEOLOCATION = "GEOLOCATION"
    PREVIOUS_INSPECTION = "PREVIOUS_INSPECTION"
    ASSESSOR_VERIFICATION = "ASSESSOR_VERIFICATION"
    POST_DISASTER_PHOTO = "POST_DISASTER_PHOTO"
    POST_DISASTER_VIDEO = "POST_DISASTER_VIDEO"
    FIELD_INSPECTION_REPORT = "FIELD_INSPECTION_REPORT"
    OTHER = "OTHER"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized = value.strip().upper().replace(" / ", "_").replace(" ", "_").replace("-", "_")
            if normalized == "WARRANTY_DOCUMENT":
                return cls.WARRANTY
            if normalized in ("FIELD_INSPECTION", "INSPECTION_REPORT"):
                return cls.FIELD_INSPECTION_REPORT
            for member in cls:
                if member.value == normalized or member.name == normalized:
                    return member
        return None



class EvidenceVerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ClaimReviewStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_ASSESSMENT = "UNDER_ASSESSMENT"
    AI_ASSESSED = "AI_ASSESSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    MORE_EVIDENCE_REQUIRED = "MORE_EVIDENCE_REQUIRED"
    FIELD_INSPECTION_REQUIRED = "FIELD_INSPECTION_REQUIRED"
    APPROVED = "APPROVED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
            if normalized in ("UNDER_ASSESSMENT", "ASSESSMENT", "AI_ASSESSMENT"):
                return cls.UNDER_ASSESSMENT
            if normalized in ("AI_ASSESSED", "ASSESSED"):
                return cls.AI_ASSESSED
            for member in cls:
                if member.value == normalized or member.name == normalized:
                    return member
        return None


class DamageCategory(str, Enum):
    NO_DAMAGE = "NO_DAMAGE"
    MINOR_DAMAGE = "MINOR_DAMAGE"
    MODERATE_DAMAGE = "MODERATE_DAMAGE"
    MAJOR_STRUCTURAL_DAMAGE = "MAJOR_STRUCTURAL_DAMAGE"
    TOTAL_LOSS = "TOTAL_LOSS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class InspectionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReviewAction(str, Enum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
    ASSIGN_FIELD_INSPECTION = "ASSIGN_FIELD_INSPECTION"
    REJECT = "REJECT"


class AnomalyFlagStatus(str, Enum):
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VERIFIED_VALID = "VERIFIED_VALID"
    CONFIRMED_ANOMALY = "CONFIRMED_ANOMALY"
    DISMISSED = "DISMISSED"


class AnomalyFlagType(str, Enum):
    REUSED_EVIDENCE = "REUSED_EVIDENCE"
    DUPLICATE_CLAIM_MEDIA = "DUPLICATE_CLAIM_MEDIA"
    LOCATION_CONFLICT = "LOCATION_CONFLICT"
    VALUE_OUTLIER = "VALUE_OUTLIER"


# --- 13 Relational Domain Models ---

# 1. User Model
class UserModel(BaseModel):
    """Actors interacting with the system (Citizen, Officer, Coordinator, Admin)."""
    id: Optional[int] = None
    user_id: str
    name: str
    email: Optional[str] = None
    role: UserRole
    organization: Optional[str] = None
    wallet_address: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


# 2. Household Model
class HouseholdModel(BaseModel):
    """Civic household unit grouping registered property and disaster aid records."""
    id: Optional[int] = None
    household_ref: str
    head_of_household: str
    contact_phone: Optional[str] = None
    address: str
    district: str
    state: str = "Tamil Nadu"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    member_count: int = 1
    created_at: str
    updated_at: Optional[str] = None


# 3. Asset Model
class AssetModel(BaseModel):
    """Citizen pre-disaster registered tangible property with baseline integrity."""
    id: Optional[int] = None
    asset_id: str
    citizen_id: Optional[int] = None
    household_ref: str
    category: AssetCategory
    description: str
    documented_value: float
    purchase_date: Optional[str] = None
    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: AssetVerificationStatus = AssetVerificationStatus.UNVERIFIED
    verification_confidence: int = 0
    integrity_hash: Optional[str] = None
    certificate_token: Optional[str] = None
    qr_code_url: Optional[str] = None
    current_status: AssetPhysicalStatus = AssetPhysicalStatus.INTACT
    created_at: str
    updated_at: Optional[str] = None


# 4. Evidence Model
class EvidenceModel(BaseModel):
    """Cryptographic proof artifact supporting asset registration or damage claim."""
    id: Optional[int] = None
    evidence_id: str
    asset_id: Optional[str] = None
    claim_id: Optional[str] = None
    evidence_type: EvidenceType
    file_url: str
    original_filename: str
    sha256_hash: str
    file_size: int = 0
    mime_type: str = "image/jpeg"
    uploader: str
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.PENDING
    score_contribution: int = 0
    captured_timestamp: Optional[str] = None
    metadata_json: Optional[str] = "{}"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: str
    updated_at: Optional[str] = None


# 5. Asset Verification Evaluation Model
class AssetVerificationModel(BaseModel):
    """Evaluation audit log recording transparent confidence scoring and verification checks."""
    id: Optional[int] = None
    verification_id: str
    asset_id: str
    confidence_score: int
    verification_status: AssetVerificationStatus
    evaluated_by: str
    scoring_details_json: str
    verified_at: str
    created_at: str


# 6. Digital Certificate Model
class CertificateModel(BaseModel):
    """Cryptographic Digital Asset Certificate with secure verification token and safe QR payload."""
    id: Optional[int] = None
    certificate_id: str
    asset_id: str
    certificate_token: str
    verification_status: str
    evidence_confidence: int
    evidence_hash: str
    issued_at: str
    expires_at: Optional[str] = None
    qr_payload: str
    created_at: str


# 7. Disaster Claim Model
class DisasterClaimModel(BaseModel):
    """Post-disaster compensation claim submitted against pre-registered asset baseline."""
    id: Optional[int] = None
    claim_id: str
    asset_id: str
    household_ref: str
    disaster_id: str
    damage_description: str
    pre_disaster_verification_status: str
    review_status: ClaimReviewStatus = ClaimReviewStatus.SUBMITTED
    officer_decision: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


# 8. Damage Assessment Model
class DamageAssessmentModel(BaseModel):
    """Computer Vision pre vs. post imagery structural damage evaluation."""
    id: Optional[int] = None
    claim_id: str
    damage_detected: bool = True
    damage_category: DamageCategory
    estimated_damage_percentage: int
    asset_match_confidence: int
    evidence_quality: int
    overall_confidence: int
    explanation: str
    provider_name: str = "DEMO_CV_MODEL"
    assessment_mode: str = "DEMO_SIMULATION"
    created_at: str
    updated_at: Optional[str] = None


# 9. Value Assessment Model
class ValueAssessmentModel(BaseModel):
    """Indicative depreciated loss estimation with mandatory non-binding legal disclaimers."""
    id: Optional[int] = None
    claim_id: str
    original_documented_value: float
    depreciation_percent: float = 0.0
    reference_current_value: float
    estimated_damage_percentage: int
    indicative_loss_amount: float
    approved_compensation_amount: Optional[float] = None
    officer_notes: Optional[str] = None
    is_ai_assisted: bool = True
    disclaimer_text: str = (
        "AI-assisted estimate — Final compensation is subject to government verification, "
        "applicable disaster relief norms, and authorized officer approval."
    )
    created_at: str
    updated_at: Optional[str] = None


# 10. Anomaly Flag Model
class AnomalyFlagModel(BaseModel):
    """Non-accusatory duplicate media or discrepancy flag requiring human review."""
    id: Optional[int] = None
    entity_type: str
    entity_id: str
    flag_type: AnomalyFlagType
    similarity_score: int = 100
    status: AnomalyFlagStatus = AnomalyFlagStatus.REVIEW_REQUIRED
    reason: str
    flagged_by: str = "SYSTEM_INTEGRITY_SERVICE"
    created_at: str
    resolved_at: Optional[str] = None


# 11. Audit Event Model
class AuditEventModel(BaseModel):
    """Immutable sequential SHA-256 chained audit record."""
    id: Optional[int] = None
    timestamp: str
    actor: str
    role: str
    event_type: str
    entity_type: str
    entity_id: str
    description: str
    previous_hash: str
    event_hash: str
    blockchain_tx_hash: Optional[str] = None


# 12. Field Inspection Model
class FieldInspectionModel(BaseModel):
    """Physical on-site damage assessment assignment and report log."""
    id: Optional[int] = None
    inspection_id: str
    claim_id: str
    assigned_officer: str
    status: InspectionStatus = InspectionStatus.PENDING
    findings: Optional[str] = None
    damage_rating: Optional[str] = None
    report_file_url: Optional[str] = None
    scheduled_date: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


# 13. Government Review Model
class GovernmentReviewModel(BaseModel):
    """Human-in-the-loop government officer decision record on post-disaster claims."""
    id: Optional[int] = None
    review_id: str
    claim_id: str
    officer_name: str
    officer_role: str = "GOVERNMENT_OFFICER"
    action: ReviewAction
    approved_amount: Optional[float] = None
    modified_damage_percent: Optional[int] = None
    justification: str
    review_timestamp: str
    blockchain_tx_hash: Optional[str] = None
    created_at: str
