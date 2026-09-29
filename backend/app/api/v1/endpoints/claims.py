"""
ReliefChain AI - Disaster Claims Endpoints (Step 12).
Provides:
- POST /claims: Citizen or authorized officer files claim referencing an existing registered asset
- GET /claims: Lists disaster claims (scoped to citizen's own household or officer/admin full view)
- GET /claims/{claim_id}: Retrieves single disaster claim with ownership validation
"""

import base64
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status, Request
from fastapi.responses import FileResponse

from ....repositories.asset_repo import AssetRepository
from ....schemas.claim import (
    ClaimCreateRequest,
    ClaimResponse,
    ClaimEvidenceResponse,
    ClaimEvidenceCreateRequest,
    ClaimApproveRequest,
    ClaimRequestEvidenceRequest,
    ClaimModifyAssessmentRequest,
    ClaimRejectRequest,
    ClaimForwardInspectionRequest
)
from ....schemas.assessment import DamageAssessmentResponse, LossAssessmentRequest, LossAssessmentResponse
from ....schemas.anomaly import AnomalyFlagResponse, AnomalyListResponse
from ....models.entities import EvidenceType
from ....core.auth import get_current_user, is_citizen, is_officer_or_admin
from ....core.errors import NotFoundError, ForbiddenError, ValidationError
from ....services import record_audit_event, cv_provider, loss_engine, run_anomaly_detection, get_persisted_anomalies
from .evidence import validate_file_content

try:
    from storage.provider import storage_provider
except (ImportError, ValueError):
    from ....storage.provider import storage_provider

router = APIRouter(prefix="/claims", tags=["Disaster Claims"])

CLAIM_EVIDENCE_TYPE_MAPPING = {
    # Damaged photographs
    "DAMAGED_PHOTO": "POST_DISASTER_PHOTO",
    "DAMAGED_PHOTOGRAPH": "POST_DISASTER_PHOTO",
    "DAMAGED_PHOTOS": "POST_DISASTER_PHOTO",
    "DAMAGED_PHOTOGRAPHS": "POST_DISASTER_PHOTO",
    "POST_DISASTER_PHOTO": "POST_DISASTER_PHOTO",
    "POST_DISASTER_PHOTOGRAPH": "POST_DISASTER_PHOTO",
    "POST_DISASTER_PHOTOS": "POST_DISASTER_PHOTO",
    "PHOTO": "POST_DISASTER_PHOTO",
    "PHOTOGRAPH": "POST_DISASTER_PHOTO",

    # Damaged videos
    "DAMAGED_VIDEO": "POST_DISASTER_VIDEO",
    "DAMAGED_VIDEOS": "POST_DISASTER_VIDEO",
    "POST_DISASTER_VIDEO": "POST_DISASTER_VIDEO",
    "POST_DISASTER_VIDEOS": "POST_DISASTER_VIDEO",
    "VIDEO": "POST_DISASTER_VIDEO",
    "VIDEOS": "POST_DISASTER_VIDEO",

    # Inspection reports
    "FIELD_INSPECTION_REPORT": "FIELD_INSPECTION_REPORT",
    "INSPECTION_REPORT": "FIELD_INSPECTION_REPORT",
    "INSPECTION_REPORTS": "FIELD_INSPECTION_REPORT",
    "FIELD_INSPECTION": "FIELD_INSPECTION_REPORT",
    "FIELD_REPORT": "FIELD_INSPECTION_REPORT",
    "INSPECTION": "FIELD_INSPECTION_REPORT",
    "REPORT": "FIELD_INSPECTION_REPORT",
}

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
REPORT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png"}


def validate_and_normalize_claim_evidence_type(raw_type: str) -> str:
    """Validates evidence type against supported post-disaster claim evidence types."""
    if not raw_type or not raw_type.strip():
        raise ValidationError("evidence_type is required.")

    clean_type = raw_type.strip().upper().replace(" / ", "_").replace(" ", "_").replace("-", "_")
    if clean_type in CLAIM_EVIDENCE_TYPE_MAPPING:
        return CLAIM_EVIDENCE_TYPE_MAPPING[clean_type]

    valid_types = {e.value for e in EvidenceType}
    if clean_type in valid_types:
        return clean_type

    raise ValidationError(
        f"Unsupported post-disaster evidence type '{raw_type}'. "
        f"Supported types: damaged photographs (POST_DISASTER_PHOTO, DAMAGED_PHOTO), "
        f"damaged videos (POST_DISASTER_VIDEO, DAMAGED_VIDEO), "
        f"inspection reports (FIELD_INSPECTION_REPORT, INSPECTION_REPORT)."
    )


def validate_claim_file(evidence_type: str, filename: str, content: bytes) -> None:
    """Validates file extension and reasonable size with evidence-type consistency checks."""
    validate_file_content(filename, content)
    ext = Path(filename).suffix.lower()

    if evidence_type == "POST_DISASTER_PHOTO" and ext not in PHOTO_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension '{ext}' for damaged photograph. Allowed: {sorted(list(PHOTO_EXTENSIONS))}"
        )
    if evidence_type == "POST_DISASTER_VIDEO" and ext not in VIDEO_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension '{ext}' for damaged video. Allowed: {sorted(list(VIDEO_EXTENSIONS))}"
        )
    if evidence_type == "FIELD_INSPECTION_REPORT" and ext not in REPORT_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension '{ext}' for inspection report. Allowed: {sorted(list(REPORT_EXTENSIONS))}"
        )


def check_claim_access(claim: Dict[str, Any], current_user: Dict[str, Any]) -> None:
    """Verifies that current_user has permission to access the claim."""
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        claim_citizen = claim.get("citizen_id")
        claim_hh = claim.get("household_ref")

        is_owner = (claim_citizen is not None and claim_citizen == user_id) or (user_hh and claim_hh == user_hh)
        if not is_owner:
            raise ForbiddenError(
                "Access denied. You do not have permission to access another citizen's disaster claim."
            )
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to access disaster claims.")


@router.post(
    "",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="File a new disaster claim against a registered asset"
)
def create_claim(
    payload: ClaimCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimResponse:
    """
    Step 12: File Disaster Compensation Claim.
    - Requirement: A claim must reference an existing registered asset.
    - Captures pre-disaster baseline verification state from registered asset.
    - Initial workflow state is SUBMITTED.
    - Do not automatically approve or reject claims.
    - Generates sequential CLAIM_CREATED audit event in the SHA-256 hash chain.
    - Enforces citizen ownership: citizens can only claim for their own assets.
    """
    # 1. Validate referenced asset existence
    asset = AssetRepository.get_asset_by_id(payload.asset_id)
    if not asset:
        raise NotFoundError(
            f"Asset '{payload.asset_id}' not found. A disaster claim must reference an existing registered asset."
        )

    # 2. Check authorization: citizen must own the referenced asset
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError(
                "Access denied. Citizens can only file disaster claims for their own registered assets."
            )
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to file disaster claims.")

    # 3. Snapshot pre-disaster verification state from the registered asset baseline
    pre_disaster_status = (asset.get("status") or "UNVERIFIED").upper()

    # 4. Determine household reference
    household_ref = (
        payload.household_ref
        or payload.household
        or asset.get("household_ref")
        or current_user.get("household_ref")
        or "HH-1001"
    )

    AssetRepository.ensure_household_exists(
        household_ref=household_ref,
        head_of_household=current_user.get("name", "Citizen"),
        address=asset.get("location_address", "Vellore, Tamil Nadu")
    )

    # 5. Determine disaster event identifier
    disaster_id = payload.disaster_id or payload.disaster_event or "DIS-2026-0007"

    # 6. Create claim in SUBMITTED state (no automatic approval or rejection)
    new_claim = AssetRepository.create_claim(
        asset_id=payload.asset_id,
        household_ref=household_ref,
        disaster_id=disaster_id,
        damage_description=payload.damage_description,
        pre_disaster_verification_status=pre_disaster_status,
        review_status="SUBMITTED"
    )

    # 7. Record tamper-evident sequential audit event
    record_audit_event(
        actor=current_user.get("name", "Citizen"),
        role=current_user.get("role", "CITIZEN"),
        event_type="CLAIM_CREATED",
        entity_type="CLAIM",
        entity_id=new_claim["claim_id"],
        description=(
            f"Disaster claim '{new_claim['claim_id']}' created for asset '{payload.asset_id}' "
            f"({asset.get('category')}) under disaster '{disaster_id}'. "
            f"Pre-disaster verification state: {pre_disaster_status}."
        )
    )

    return ClaimResponse(**new_claim)


@router.get(
    "",
    response_model=List[ClaimResponse],
    summary="List disaster claims"
)
def list_claims(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by claim review status"),
    disaster_id: Optional[str] = Query(None, description="Filter by disaster event ID"),
    household_ref: Optional[str] = Query(None, description="Filter by household reference (Officers/Admins only)"),
    asset_id: Optional[str] = Query(None, description="Filter by asset ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[ClaimResponse]:
    """
    Lists disaster claims enforcing citizen privacy and officer permissions:
    - Citizens ONLY see claims belonging to their household / own assets.
    - Government Officers and Admins can view all claims across households.
    """
    if is_citizen(current_user):
        claims = AssetRepository.list_claims(
            citizen_id=current_user.get("id"),
            household_ref=current_user.get("household_ref"),
            status_filter=status_filter,
            disaster_id=disaster_id,
            asset_id=asset_id
        )
    elif is_officer_or_admin(current_user):
        claims = AssetRepository.list_claims(
            household_ref=household_ref,
            status_filter=status_filter,
            disaster_id=disaster_id,
            asset_id=asset_id
        )
    else:
        raise ForbiddenError("You are not authorized to view disaster claims.")

    return [ClaimResponse(**c) for c in claims]


@router.get(
    "/{claim_id}",
    response_model=ClaimResponse,
    summary="Retrieve single disaster claim"
)
def get_claim(
    claim_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimResponse:
    """
    Retrieves single disaster claim by ID.
    Enforces privacy:
    - Citizens can only view their own claims (403 for unauthorized access).
    - Officers and Admins can view any claim.
    """
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        claim_citizen = claim.get("citizen_id")
        claim_hh = claim.get("household_ref")

        is_owner = (claim_citizen is not None and claim_citizen == user_id) or (user_hh and claim_hh == user_hh)
        if not is_owner:
            raise ForbiddenError(
                "Access denied. You do not have permission to view another citizen's disaster claim."
            )
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to view disaster claims.")

    return ClaimResponse(**claim)


@router.post(
    "/{claim_id}/evidence",
    response_model=ClaimEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload post-disaster evidence for a disaster claim"
)
async def upload_claim_evidence(
    claim_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimEvidenceResponse:
    """
    Step 13: Add post-disaster evidence to disaster claims.
    Supported types:
    - damaged photographs (POST_DISASTER_PHOTO, DAMAGED_PHOTO, etc.)
    - damaged videos (POST_DISASTER_VIDEO, DAMAGED_VIDEO, etc.)
    - inspection reports (FIELD_INSPECTION_REPORT, INSPECTION_REPORT, etc.)

    Reuses existing Evidence system:
    1. Authenticates user and checks claim access.
    2. Validates file types and sizes.
    3. Preserves original file SHA-256 hash.
    4. Saves file in private local storage.
    5. Records upload timestamp.
    6. Associates evidence with the claim in claim_evidence.
    7. Creates sequential EVIDENCE_ADDED audit event.
    8. Does NOT generate damage assessment yet (deferred to Step 14).
    """
    # 1. Verify claim existence
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Disaster claim '{claim_id}' not found.")

    # 2. Check authorization & privacy protection
    check_claim_access(claim, current_user)

    # 3. Extract file content & metadata from multipart form or JSON
    content_type = request.headers.get("content-type", "")
    file_bytes: bytes = b""
    original_filename: str = ""
    evidence_type_raw: str = ""
    captured_timestamp: Optional[str] = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file or not hasattr(uploaded_file, "read"):
            raise ValidationError("Missing 'file' in multipart form data.")

        file_bytes = await uploaded_file.read()
        original_filename = getattr(uploaded_file, "filename", "evidence.bin")
        evidence_type_raw = str(form.get("evidence_type", ""))
        captured_timestamp = form.get("captured_timestamp")

    elif "application/json" in content_type:
        body = await request.json()
        evidence_type_raw = body.get("evidence_type", "")
        original_filename = body.get("original_filename", "")
        b64_content = body.get("file_content_base64")
        if not b64_content:
            raise ValidationError("Missing 'file_content_base64' in JSON upload payload.")

        try:
            file_bytes = base64.b64decode(b64_content)
        except Exception as e:
            raise ValidationError(f"Invalid base64 encoding: {str(e)}")

        captured_timestamp = body.get("captured_timestamp")
    else:
        raise ValidationError("Unsupported media type. Request must be 'multipart/form-data' or 'application/json'.")

    # 4. Normalize evidence type and validate file content
    evidence_type = validate_and_normalize_claim_evidence_type(evidence_type_raw)
    validate_claim_file(evidence_type, original_filename, file_bytes)

    # 5. Generate readable evidence ID and compute SHA-256 hash
    evidence_id = AssetRepository.generate_claim_evidence_id()
    custom_storage_key = f"{evidence_id}_{Path(original_filename).name}"

    # 6. Save in private storage preserving original SHA-256 hash
    storage_res = storage_provider.save_file(
        file_bytes,
        original_filename,
        is_private=True,
        custom_key=custom_storage_key
    )
    sha256_hash = storage_res["sha256_hash"]
    file_size = storage_res["file_size"]
    mime_type = storage_res["mime_type"]

    # 7. Formulate authenticated file URL protecting private evidence
    file_url = f"/claims/{claim_id}/evidence/{evidence_id}/file"

    # 8. Insert into claim_evidence table
    inserted = AssetRepository.add_claim_evidence(
        claim_id=claim_id,
        evidence_type=evidence_type,
        file_url=file_url,
        original_filename=original_filename,
        sha256_hash=sha256_hash,
        file_size=file_size,
        mime_type=mime_type,
        captured_timestamp=captured_timestamp,
        evidence_id=evidence_id
    )

    # 9. Create tamper-evident sequential audit event
    record_audit_event(
        actor=current_user.get("name", "Citizen"),
        role=current_user.get("role", "CITIZEN"),
        event_type="EVIDENCE_ADDED",
        entity_type="CLAIM_EVIDENCE",
        entity_id=evidence_id,
        evidence_hash=sha256_hash,
        description=(
            f"Post-disaster evidence '{evidence_id}' ({evidence_type}) added to claim '{claim_id}'. "
            f"File: '{original_filename}' ({file_size:,} bytes), SHA-256: {sha256_hash[:18]}..."
        )
    )

    # Requirement 8: Do not generate damage assessment yet!
    return ClaimEvidenceResponse(**inserted)


@router.get(
    "/{claim_id}/evidence",
    response_model=List[ClaimEvidenceResponse],
    summary="List all post-disaster evidence for a claim"
)
def list_claim_evidence(
    claim_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[ClaimEvidenceResponse]:
    """
    Retrieves all post-disaster evidence associated with a claim:
    - Citizens can only view evidence for their own claim.
    - Officers and Admins can view evidence across claims.
    """
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Disaster claim '{claim_id}' not found.")

    check_claim_access(claim, current_user)

    evidence_items = AssetRepository.list_evidence_for_claim(claim_id)
    return [ClaimEvidenceResponse(**e) for e in evidence_items]


@router.get(
    "/{claim_id}/evidence/{evidence_id}/file",
    summary="Download or stream private claim evidence file"
)
def get_claim_evidence_file(
    claim_id: str,
    evidence_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Authenticated retrieval of private post-disaster claim evidence:
    - Protects private evidence from public URLs.
    - Enforces citizen ownership and officer access.
    """
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Disaster claim '{claim_id}' not found.")

    check_claim_access(claim, current_user)

    evidence = AssetRepository.get_claim_evidence_by_id(evidence_id)
    if not evidence or evidence.get("claim_id") != claim_id:
        raise NotFoundError(f"Evidence '{evidence_id}' for claim '{claim_id}' not found.")

    # Locate physical file
    custom_key = f"{evidence_id}_{evidence.get('original_filename', '')}"
    file_path = storage_provider.get_file_path(custom_key, is_private=True)
    if (not file_path or not file_path.exists()) and evidence.get("sha256_hash"):
        file_path = storage_provider.find_file_by_hash(evidence["sha256_hash"])

    if not file_path or not file_path.exists():
        raise NotFoundError(f"Physical file for evidence '{evidence_id}' not found in storage.")

    return FileResponse(
        path=str(file_path),
        filename=evidence.get("original_filename", "evidence.bin"),
        media_type=evidence.get("mime_type", "application/octet-stream")
    )

@router.get("/{claim_id}/assessment", response_model=Optional[DamageAssessmentResponse], summary="Get latest damage assessment for a claim")
@router.get("/{claim_id}/assess", response_model=Optional[DamageAssessmentResponse], include_in_schema=False)
def get_claim_damage_assessment(
    claim_id: str,
    user_data: Dict[str, Any] = Depends(get_current_user)
) -> Optional[DamageAssessmentResponse]:
    """
    Step 24: Retrieve the latest AI damage assessment for a claim.
    Citizens can retrieve assessments for their own claims; officers/admins for any claim.
    """
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    check_claim_access(claim, user_data)

    assessment = AssetRepository.get_damage_assessment_for_claim(claim_id)
    if not assessment:
        return None
    d = dict(assessment)
    if "damage_percentage" not in d or d["damage_percentage"] is None:
        d["damage_percentage"] = float(d.get("estimated_damage_percentage", 0))
    return DamageAssessmentResponse(**d)


@router.post("/{claim_id}/assess", response_model=DamageAssessmentResponse, status_code=status.HTTP_201_CREATED)
def assess_claim_damage(
    claim_id: str,
    request: Request,
    user_data: Dict[str, Any] = Depends(get_current_user)
):
    """
    Step 24: AI Damage Assessment (Demo/Simulation Mode).
    Uses the existing cv_provider demo engine to assess damage from uploaded post-disaster photos/evidence.
    Does not automatically approve the claim.
    """
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    check_claim_access(claim, user_data)

    evidence_list = AssetRepository.list_evidence_for_claim(claim_id)
    post_disaster_photos = [
        e for e in evidence_list
        if "PHOTO" in str(e.get("evidence_type", "")).upper() or str(e.get("mime_type", "")).startswith("image/")
    ]

    if not post_disaster_photos and not evidence_list:
        post_evidence_items = []
    else:
        post_evidence_items = [{"url": e.get("file_url", ""), "type": e.get("evidence_type", "")} for e in (post_disaster_photos or evidence_list)]

    asset_id = claim.get("asset_id")
    asset = AssetRepository.get_asset_by_id(asset_id) if asset_id else None

    # Run deterministic comparison
    damage_desc = claim.get("damage_description") or claim.get("citizen_description") or ""
    assessment_result = cv_provider.compare(
        asset_category=asset.get("category", "General Asset") if asset else "General Asset",
        pre_evidence=[],
        post_evidence=post_evidence_items,
        citizen_description=damage_desc
    )

    # Save the assessment
    saved_assessment = AssetRepository.save_damage_assessment(
        claim_id=claim_id,
        damage_detected=assessment_result.get("damage_detected", False),
        damage_category=assessment_result.get("damage_category", "INSUFFICIENT_EVIDENCE"),
        estimated_damage_percentage=assessment_result.get("estimated_damage_percentage", 0),
        asset_match_confidence=assessment_result.get("asset_match_confidence", 0),
        evidence_quality=assessment_result.get("evidence_quality", 0),
        overall_confidence=assessment_result.get("overall_confidence", 0),
        explanation=assessment_result.get("explanation", ""),
        provider_name=assessment_result.get("provider_name", "DEMO_CV_MODEL"),
        assessment_mode=assessment_result.get("assessment_mode", "DEMO_SIMULATION")
    )

    record_audit_event(
        actor=user_data.get("name", "Citizen"),
        role=user_data.get("role", "CITIZEN"),
        event_type="DAMAGE_ASSESSMENT_RUN",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=(
            f"Demo AI damage assessment performed for claim '{claim_id}': "
            f"Category={saved_assessment['damage_category']}, "
            f"Estimated Damage={saved_assessment['estimated_damage_percentage']}%, "
            f"Mode={saved_assessment['assessment_mode']}."
        )
    )

    d_saved = dict(saved_assessment)
    if "damage_percentage" not in d_saved or d_saved["damage_percentage"] is None:
        d_saved["damage_percentage"] = float(d_saved.get("estimated_damage_percentage", 0))

    return DamageAssessmentResponse(**d_saved)

@router.get("/{claim_id}/loss-estimate", response_model=Optional[LossAssessmentResponse], summary="Get existing loss estimate for a claim")
@router.get("/{claim_id}/value-assessment", response_model=Optional[LossAssessmentResponse], include_in_schema=False)
def get_claim_loss_estimate(
    claim_id: str,
    user_data: Dict[str, Any] = Depends(get_current_user)
) -> Optional[LossAssessmentResponse]:
    """
    Step 25: Retrieves the latest value/loss assessment for a claim if available.
    """
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    check_claim_access(claim, user_data)

    va = AssetRepository.get_value_assessment_for_claim(claim_id)
    if not va:
        return None

    depreciation_amt = round(va["original_documented_value"] - va["reference_current_value"], 2)
    explanation = (
        f"Calculated based on original documented value ₹{va['original_documented_value']:,.2f}, "
        f"reference current value ₹{va['reference_current_value']:,.2f} "
        f"(depreciation: {va.get('depreciation_percent', 0.0):.1f}%), and "
        f"{va['estimated_damage_percentage']}% estimated damage."
    )

    return LossAssessmentResponse(
        label="AI-ASSISTED ESTIMATE",
        disclaimer="This is not a guaranteed compensation amount. Final compensation is subject to government verification and applicable rules.",
        original_documented_value=va["original_documented_value"],
        reference_current_value=va["reference_current_value"],
        depreciation=max(0.0, depreciation_amt),
        damage_percentage=va["estimated_damage_percentage"],
        indicative_loss_estimate=va["indicative_loss_amount"],
        calculation_explanation=explanation
    )


@router.post("/{claim_id}/loss-estimate", response_model=LossAssessmentResponse, status_code=status.HTTP_200_OK)
@router.post("/{claim_id}/value-assessment", response_model=LossAssessmentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def estimate_claim_loss(
    claim_id: str,
    request: Optional[LossAssessmentRequest] = None,
    user_data: Dict[str, Any] = Depends(get_current_user)
) -> LossAssessmentResponse:
    """
    Step 25: Calculates an indicative loss estimate for a claim based on original asset value,
    depreciation over time, and estimated damage percentage.
    Clearly displays "AI-ASSISTED ESTIMATE" and the statutory non-guarantee disclaimer.
    Does NOT automatically approve compensation.
    """
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    check_claim_access(claim, user_data)

    asset_id = claim.get("asset_id")
    if not asset_id:
        raise ValidationError("Claim must be linked to a registered asset to calculate loss.")

    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    original_value = float(asset.get("documented_value") or asset.get("declared_value") or 100000.0)
    purchase_date = str(asset.get("purchase_date") or asset.get("created_at") or "2024-01-01T00:00:00Z")
    category = str(asset.get("category", "property")).lower()

    # Determine damage percentage
    damage_pct = None
    if request and request.estimated_damage_percentage is not None:
        damage_pct = request.estimated_damage_percentage
    else:
        # Check existing damage assessment
        existing_assessment = AssetRepository.get_damage_assessment_for_claim(claim_id)
        if existing_assessment and existing_assessment.get("estimated_damage_percentage") is not None:
            damage_pct = existing_assessment["estimated_damage_percentage"]
        else:
            damage_pct = 70

    ref_val = request.reference_value if request else None

    result = loss_engine.assess_loss(
        original_value=original_value,
        purchase_date=purchase_date,
        asset_category=category,
        reference_value=ref_val,
        estimated_damage_percentage=damage_pct
    )

    depreciation_pct = round((result["depreciation"] / original_value * 100.0) if original_value > 0 else 0.0, 2)

    # Persist in value_assessments table
    AssetRepository.save_value_assessment(
        claim_id=claim_id,
        original_documented_value=result["original_documented_value"],
        reference_current_value=result["reference_current_value"],
        depreciation_percent=depreciation_pct,
        estimated_damage_percentage=result["damage_percentage"],
        indicative_loss_amount=result["indicative_loss_estimate"],
        is_ai_assisted=1
    )

    record_audit_event(
        actor=user_data.get("name", "Citizen"),
        role=user_data.get("role", "CITIZEN"),
        event_type="LOSS_ESTIMATE_RUN",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=(
            f"Indicative loss estimate calculated for claim '{claim_id}': "
            f"Original=₹{result['original_documented_value']:,.2f}, "
            f"Current=₹{result['reference_current_value']:,.2f}, "
            f"Damage={result['damage_percentage']}%, "
            f"Indicative Loss=₹{result['indicative_loss_estimate']:,.2f}. "
            f"Label: {result['label']}."
        )
    )

    return LossAssessmentResponse(**result)


@router.get(
    "/{claim_id}/anomalies",
    response_model=AnomalyListResponse,
    summary="Get anomaly flags for a disaster claim"
)
def get_claim_anomalies(
    claim_id: str,
    rescan: bool = Query(
        False,
        description="When true, re-runs all detectors and persists new flags before returning results."
    ),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AnomalyListResponse:
    """
    Step 16 — Deterministic Anomaly Detection.

    Returns all anomaly flags for a given disaster claim.
    Each flag has review_status = REVIEW_REQUIRED — citizens are NEVER labelled
    as fraudulent; all flags require officer verification.

    Detected signals
    ----------------
    1. DUPLICATE_ASSET_REGISTRATION  — same integrity hash as another asset
    2. REUSED_EVIDENCE_HASH          — evidence file SHA-256 seen in another claim/asset
    3. REPEATED_SUBMISSION           — multiple claims for same asset + disaster by household
    4. LOCATION_CONFLICT             — evidence GPS far from asset registered location
    5. MODIFIED_EVIDENCE             — stored file hash differs from upload-time hash
    6. MULTIPLE_CLAIMS_SAME_ASSET    — more than one active claim for the same asset
    7. METADATA_CONFLICT             — evidence captured before disaster was declared

    Access control
    --------------
    - Citizens may view anomaly flags for their own claims.
    - Government Officers and Admins can view flags for any claim.

    Query parameters
    ----------------
    rescan : bool (default False)
        Pass ?rescan=true to force re-execution of all detectors.
        New flags are merged/persisted; previously dismissed flags are preserved.
    """
    # 1. Verify claim exists
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    # 2. Enforce access control
    check_claim_access(claim, current_user)

    # 3. Run detectors or return cached flags
    if rescan:
        anomaly_dicts = run_anomaly_detection(claim_id)
    else:
        anomaly_dicts = get_persisted_anomalies(claim_id)
        # If no cached flags exist, run detection once automatically
        if not anomaly_dicts:
            anomaly_dicts = run_anomaly_detection(claim_id)

    # 4. Build response models
    flag_models = []
    for d in anomaly_dicts:
        try:
            f_type = d.get("flag_type") or d.get("type", "UNKNOWN")
            sim_val = int(
                d.get("similarity_score")
                if d.get("similarity_score") is not None
                else (d.get("similarity") if d.get("similarity") is not None else 100)
            )
            c_time = d.get("created_at") or d.get("created_timestamp") or ""
            flag_models.append(
                AnomalyFlagResponse(
                    id=d.get("id"),
                    entity_type=d.get("entity_type", "CLAIM"),
                    entity_id=d.get("entity_id", claim_id),
                    flag_type=f_type,
                    type=f_type,
                    reason=d.get("reason", ""),
                    similarity_score=sim_val,
                    similarity=sim_val,
                    confidence=sim_val,
                    review_status="REVIEW_REQUIRED",
                    related_record=d.get("related_record"),
                    created_at=c_time,
                    created_timestamp=c_time,
                )
            )
        except Exception:
            continue

    total = len(flag_models)
    summary = (
        f"{total} anomaly flag(s) require officer review."
        if total > 0
        else "No anomalies detected. Claim appears consistent with registered records."
    )

    return AnomalyListResponse(
        claim_id=claim_id,
        total_anomalies=total,
        review_status_summary=summary,
        anomalies=flag_models,
    )


@router.post(
    "/{claim_id}/approve",
    response_model=ClaimResponse,
    summary="Government Officer approves disaster compensation claim"
)
def approve_claim(
    claim_id: str,
    payload: Optional[ClaimApproveRequest] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimResponse:
    """
    Step 27: Human government officer approves claim.
    Explicit decision by authorized officer, records approved compensation and audit event.
    """
    if not is_officer_or_admin(current_user):
        raise ForbiddenError("Only authorized Government Officers or Administrators can approve claims.")

    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    p = payload or ClaimApproveRequest()
    officer_name = current_user.get("name", "Government Officer")
    notes = p.officer_notes or p.notes or 'Claim approved by revenue officer.'
    amt = p.approved_compensation_amount if p.approved_compensation_amount is not None else p.approved_amount
    decision_text = f"APPROVED: {notes}"

    # If approved amount provided or available in loss estimate
    if amt is not None:
        AssetRepository.approve_claim_compensation(claim_id, amt, notes)
    else:
        va = AssetRepository.get_value_assessment_for_claim(claim_id)
        if va and va.get("indicative_loss_amount"):
            AssetRepository.approve_claim_compensation(claim_id, va["indicative_loss_amount"], notes)

    # Update claim in database after recording compensation so get_claim_by_id returns updated values
    updated = AssetRepository.update_claim_decision(
        claim_id=claim_id,
        review_status="APPROVED",
        officer_decision=decision_text
    )

    record_audit_event(
        actor=officer_name,
        role=current_user.get("role", "GOVERNMENT_OFFICER"),
        event_type="CLAIM_APPROVED",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=f"Claim '{claim_id}' approved by {officer_name}. Decision: {decision_text}"
    )

    return ClaimResponse(**updated)


@router.post(
    "/{claim_id}/request-evidence",
    response_model=ClaimResponse,
    summary="Government Officer requests additional evidence from citizen"
)
def request_claim_evidence(
    claim_id: str,
    payload: ClaimRequestEvidenceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimResponse:
    """
    Step 27: Human government officer requests additional evidence from citizen.
    """
    if not is_officer_or_admin(current_user):
        raise ForbiddenError("Only authorized Government Officers or Administrators can request claim evidence.")

    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    officer_name = current_user.get("name", "Government Officer")
    notes = payload.officer_notes or payload.notes or "Additional evidence required from citizen."
    decision_text = "EVIDENCE_REQUESTED"

    updated = AssetRepository.update_claim_decision(
        claim_id=claim_id,
        review_status="EVIDENCE_REQUESTED",
        officer_decision=decision_text
    )

    record_audit_event(
        actor=officer_name,
        role=current_user.get("role", "GOVERNMENT_OFFICER"),
        event_type="CLAIM_EVIDENCE_REQUESTED",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=f"Additional evidence requested for claim '{claim_id}' by {officer_name}: {notes}"
    )

    return ClaimResponse(**updated)


@router.post(
    "/{claim_id}/modify-assessment",
    response_model=ClaimResponse,
    summary="Government Officer modifies damage assessment parameters"
)
def modify_claim_assessment(
    claim_id: str,
    payload: ClaimModifyAssessmentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimResponse:
    """
    Step 27: Human government officer modifies assessment parameters with justification.
    """
    if not is_officer_or_admin(current_user):
        raise ForbiddenError("Only authorized Government Officers or Administrators can modify assessments.")

    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    officer_name = current_user.get("name", "Government Officer")
    damage_pct = int(payload.modified_damage_percentage if payload.modified_damage_percentage is not None else (payload.damage_percentage or 50))
    category = payload.modified_damage_category or payload.damage_category
    notes = payload.modification_rationale or payload.officer_notes or payload.notes or "Assessment adjusted by officer."
    decision_text = f"ASSESSMENT_MODIFIED: Damage adjusted to {damage_pct}%. Notes: {notes}"

    AssetRepository.modify_claim_damage_assessment(
        claim_id=claim_id,
        damage_percentage=damage_pct,
        damage_category=category,
        notes=notes
    )

    updated = AssetRepository.update_claim_decision(
        claim_id=claim_id,
        review_status="ASSESSMENT_MODIFIED",
        officer_decision=decision_text
    )

    record_audit_event(
        actor=officer_name,
        role=current_user.get("role", "GOVERNMENT_OFFICER"),
        event_type="CLAIM_ASSESSMENT_MODIFIED",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=f"Assessment modified for claim '{claim_id}' by {officer_name}: {damage_pct}% damage. Justification: {notes}"
    )

    return ClaimResponse(**updated)


@router.post(
    "/{claim_id}/reject",
    response_model=ClaimResponse,
    summary="Government Officer rejects disaster claim"
)
def reject_claim(
    claim_id: str,
    payload: ClaimRejectRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimResponse:
    """
    Step 27: Human government officer rejects claim with formal reason.
    """
    if not is_officer_or_admin(current_user):
        raise ForbiddenError("Only authorized Government Officers or Administrators can reject claims.")

    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    officer_name = current_user.get("name", "Government Officer")
    reason = payload.rejection_reason or payload.reason or "Claim rejected by revenue officer."
    notes = payload.officer_notes or payload.notes or "None"
    decision_text = f"REJECTED: {reason}. Notes: {notes}"

    updated = AssetRepository.update_claim_decision(
        claim_id=claim_id,
        review_status="REJECTED",
        officer_decision=decision_text
    )

    record_audit_event(
        actor=officer_name,
        role=current_user.get("role", "GOVERNMENT_OFFICER"),
        event_type="CLAIM_REJECTED",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=f"Claim '{claim_id}' rejected by {officer_name}. Reason: {reason}"
    )

    return ClaimResponse(**updated)


@router.post(
    "/{claim_id}/forward-inspection",
    response_model=ClaimResponse,
    summary="Government Officer forwards claim for field inspection"
)
def forward_claim_inspection(
    claim_id: str,
    payload: Optional[ClaimForwardInspectionRequest] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ClaimResponse:
    """
    Step 27: Human government officer forwards claim for on-site physical field inspection.
    """
    if not is_officer_or_admin(current_user):
        raise ForbiddenError("Only authorized Government Officers or Administrators can forward claims for inspection.")

    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")

    p = payload or ClaimForwardInspectionRequest()
    officer_name = current_user.get("name", "Government Officer")

    inspector_id = getattr(p, "assigned_inspector_id", None) or getattr(p, "assigned_officer", None)
    sector = getattr(p, "inspection_sector", None) or getattr(p, "assigned_sector", None)
    instructions = getattr(p, "special_instructions", None) or getattr(p, "inspector_notes", None) or "Field inspection scheduled."

    decision_parts = ["FIELD_INSPECTION_PENDING:"]
    if sector:
        decision_parts.append(f"{sector}")
    if inspector_id:
        decision_parts.append(f"{inspector_id}")
    if instructions:
        decision_parts.append(f"{instructions}")
    decision_text = " - ".join(decision_parts)

    updated = AssetRepository.update_claim_decision(
        claim_id=claim_id,
        review_status="FIELD_INSPECTION_PENDING",
        officer_decision=decision_text
    )

    # Create / update field inspection record so NGO/Field Assessor immediately sees it
    assigned_name = inspector_id or (f"Katpadi Youth Emergency Corps (NGO) - {sector}" if sector else "Katpadi Youth Emergency Corps (NGO)")
    AssetRepository.create_or_update_field_inspection(
        claim_id=claim_id,
        assigned_officer=assigned_name,
        notes=instructions,
        status="PENDING"
    )

    record_audit_event(
        actor=officer_name,
        role=current_user.get("role", "GOVERNMENT_OFFICER"),
        event_type="CLAIM_FORWARDED_FOR_INSPECTION",
        entity_type="CLAIM",
        entity_id=claim_id,
        description=f"Claim '{claim_id}' forwarded for physical inspection by {officer_name}. Sector: {sector or 'Unassigned'}. Inspector: {inspector_id or 'Assigned NGO'}. Notes: {instructions}"
    )

    return ClaimResponse(**updated)


@router.get(
    "/{claim_id}/inspection",
    summary="Get field inspection details for a claim"
)
def get_claim_inspection(
    claim_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Optional[Dict[str, Any]]:
    """Retrieves field inspection record for a disaster claim."""
    claim = AssetRepository.get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Claim '{claim_id}' not found.")
    insp = AssetRepository.get_field_inspection_by_claim_id(claim_id)
    return insp


