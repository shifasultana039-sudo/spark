"""
Digital Asset Registry Endpoints for ReliefChain AI (Step 7).
Provides:
- POST /assets: Citizen registers new tangible asset with automatic ID generation (AST-YYYY-NNNNNN) and audit event
- GET /assets: Lists assets (scoped to citizen's own assets or authorized officer/admin view)
- GET /assets/{asset_id}: Retrieves single asset (enforcing citizen privacy and access control)
- PUT /assets/{asset_id}: Updates asset attributes (maintains unverified state, prevents unauthorized edits)
"""

import json
import secrets
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Body, status

from ....repositories.asset_repo import AssetRepository
from ....schemas.asset import (
    AssetCreateRequest,
    AssetUpdateRequest,
    AssetResponse,
    AssetVerifyRequest,
    AssetVerificationDetailResponse,
    AssetCertificateResponse,
    FrontendCertificateCard
)
from ....core.auth import get_current_user, is_officer_or_admin, is_citizen
from ....core.errors import NotFoundError, ForbiddenError, ValidationError
from ....services import record_audit_event
try:
    from services.asset_verification_engine import (
        evaluate_asset_evidence,
        get_evidence_weights,
        configure_weights,
        reset_evidence_weights
    )
except (ImportError, ValueError):
    from ....services.asset_verification_engine import (
        evaluate_asset_evidence,
        get_evidence_weights,
        configure_weights,
        reset_evidence_weights
    )

try:
    from services.qr_service import generate_qr_bundle
except (ImportError, ValueError):
    from ....services.qr_service import generate_qr_bundle

router = APIRouter(prefix="/assets", tags=["Digital Asset Registry"])


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen asset"
)
def create_asset(
    payload: AssetCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AssetResponse:
    """
    Registers a pre-disaster citizen asset with baseline cryptographic integrity:
    1. Authenticates caller.
    2. Citizen creates their own asset (citizen_id assigned automatically).
    3. Generates readable unique ID: AST-YYYY-NNNNNN.
    4. Computes baseline integrity hash.
    5. Leaves status as UNVERIFIED (verification scheduled for subsequent steps).
    6. Generates sequential audit event.
    """
    # 1. Determine citizen_id
    if is_citizen(current_user):
        citizen_id = current_user["id"]
    else:
        # Officer/Admin registering
        citizen_id = current_user.get("id")

    # 2. Determine household reference
    household_ref = (
        payload.household_ref
        or current_user.get("household_ref")
        or f"HH-{citizen_id + 1000 if citizen_id else 1001}"
    )

    # Ensure household exists in database for relational integrity
    AssetRepository.ensure_household_exists(
        household_ref=household_ref,
        head_of_household=current_user.get("name", "Citizen"),
        address=payload.location_address
    )

    # 3. Create the asset
    category_val = payload.category.value if hasattr(payload.category, "value") else str(payload.category)
    new_asset = AssetRepository.create_asset(
        category=category_val,
        description=payload.description,
        documented_value=payload.documented_value,
        location_address=payload.location_address,
        household_ref=household_ref,
        purchase_date=payload.purchase_date,
        citizen_id=citizen_id,
        latitude=payload.latitude or 12.9806,
        longitude=payload.longitude or 79.1417
    )

    # 4. Generate immutable audit event
    record_audit_event(
        actor=current_user.get("name", "Citizen"),
        role=current_user.get("role", "CITIZEN"),
        event_type="ASSET_REGISTRATION",
        entity_type="ASSET",
        entity_id=new_asset["asset_id"],
        description=(
            f"Asset registered: {new_asset['asset_id']} ({category_val}) "
            f"valued at INR {payload.documented_value:,.2f} at {payload.location_address}."
        )
    )

    return AssetResponse(**new_asset)


@router.get(
    "",
    response_model=List[AssetResponse],
    summary="List registered assets"
)
def list_assets(
    category: Optional[str] = Query(None, description="Filter by asset category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    household_ref: Optional[str] = Query(None, description="Filter by household reference (Officers/Admins only)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[AssetResponse]:
    """
    Lists assets enforcing privacy and authorization:
    - Citizens ONLY see their own assets (other citizen data is never exposed).
    - Government Officers / Admins can view all authorized assets across households.
    """
    if is_citizen(current_user):
        # Strict isolation: citizen only sees their own assets
        assets = AssetRepository.list_assets(
            citizen_id=current_user["id"],
            category=category,
            status=status_filter
        )
    elif is_officer_or_admin(current_user):
        # Government Officer / Admin authorized access
        assets = AssetRepository.list_assets(
            household_ref=household_ref,
            category=category,
            status=status_filter
        )
    else:
        raise ForbiddenError("You are not authorized to view the asset registry.")

    return [AssetResponse(**a) for a in assets]


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get single asset metadata"
)
def get_asset(
    asset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AssetResponse:
    """
    Retrieves single asset record:
    - Protects private citizen data: Citizens cannot access assets belonging to another citizen.
    - Government Officers / Admins can access authorized asset details.
    """
    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    # Privacy & Access Control Check
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to access another citizen's asset.")

    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to view asset records.")

    return AssetResponse(**asset)


@router.put(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Update an existing asset"
)
def update_asset(
    asset_id: str,
    payload: AssetUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AssetResponse:
    """
    Updates an asset record:
    - Citizens can only update their own assets.
    - Protects against marking asset as VERIFIED (verification handled in subsequent verification step).
    - Recalculates baseline cryptographic hash.
    """
    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    # Ownership & Authorization Check
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to modify another citizen's asset.")

    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to modify asset records.")

    update_data = payload.model_dump(exclude_unset=True)
    if "category" in update_data and hasattr(update_data["category"], "value"):
        update_data["category"] = update_data["category"].value

    updated_asset = AssetRepository.update_asset(asset_id, update_data)
    if not updated_asset:
        raise NotFoundError(f"Failed to update asset '{asset_id}'.")

    # Audit log update
    record_audit_event(
        actor=current_user.get("name", "User"),
        role=current_user.get("role", "CITIZEN"),
        event_type="ASSET_UPDATE",
        entity_type="ASSET",
        entity_id=asset_id,
        description=f"Asset {asset_id} updated by {current_user.get('name')} ({current_user.get('role')})."
    )

    return AssetResponse(**updated_asset)


# -------------------------------------------------------------------------
# Step 9: Deterministic Asset Evidence Verification Endpoints
# -------------------------------------------------------------------------

@router.get(
    "/verification/rules",
    summary="Get current evidence weighting rules",
    tags=["Asset Verification"]
)
def get_verification_weight_rules() -> Dict[str, Any]:
    """Returns currently active evidence weighting configuration."""
    return {
        "engine": "DETERMINISTIC_RULES",
        "description": "Rule-based deterministic evidence weighting engine (not a black-box AI model)",
        "weights": get_evidence_weights(),
        "thresholds": {
            "OFFICIALLY_CONFIRMED": ">= 95",
            "VERIFIED": "80 - 94",
            "PARTIALLY_VERIFIED": "50 - 79",
            "UNVERIFIED": "< 50"
        }
    }


@router.post(
    "/verification/rules",
    summary="Configure evidence weighting rules",
    tags=["Asset Verification"]
)
def update_verification_weight_rules(
    new_weights: Dict[str, int],
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Allows authorized disaster officers or admins to configure weighting rules."""
    if not is_officer_or_admin(current_user):
        raise ForbiddenError("Only Disaster Officers or System Admins can configure evidence weighting rules.")
    
    updated = configure_weights(new_weights)
    record_audit_event(
        actor=current_user.get("name", "Officer"),
        role=current_user.get("role", "DISASTER_OFFICER"),
        event_type="CONFIGURATION_UPDATE",
        entity_type="SYSTEM",
        entity_id="EVIDENCE_WEIGHTING_RULES",
        description=f"Evidence weighting rules updated by {current_user.get('name')}."
    )
    return {
        "status": "SUCCESS",
        "message": "Evidence weighting rules updated.",
        "weights": updated
    }


@router.post(
    "/{asset_id}/verify",
    response_model=AssetVerificationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate deterministic evidence verification for an asset",
    tags=["Asset Verification"]
)
def verify_asset(
    asset_id: str,
    payload: Optional[AssetVerifyRequest] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AssetVerificationDetailResponse:
    """
    Step 9: Deterministic Asset Evidence Verification.
    1. Authenticates user and checks asset existence.
    2. Validates ownership / authorization (Citizen owns asset OR Officer/Admin).
    3. Examines ONLY actual submitted evidence (never invents evidence).
    4. Evaluates evidence weights deterministically (configurable via payload.custom_weights).
    5. Computes confidence score strictly between 0 and 100.
    6. Assigns verification status: UNVERIFIED, PARTIALLY_VERIFIED, VERIFIED, OFFICIALLY_CONFIRMED.
    7. Stores explanation and verification history in database.
    8. Updates asset state and evidence contribution scores.
    9. Generates cryptographic audit event.
    """
    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    # Ownership & Authorization Check
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to verify another citizen's asset.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to verify asset records.")

    # Retrieve actual evidence items associated with this asset (Never invent evidence)
    evidence_list = AssetRepository.list_evidence_for_asset(asset_id)

    # Perform deterministic rule evaluation
    custom_weights = payload.custom_weights if payload else None
    eval_result = evaluate_asset_evidence(evidence_list, custom_weights=custom_weights)

    evaluator_label = f"{current_user.get('name', 'User')} ({current_user.get('role', 'CITIZEN')})"
    details_json = json.dumps({
        "explanation": eval_result["explanation"],
        "contributions": eval_result["contributions"],
        "weights_used": eval_result["weights_used"],
        "is_deterministic": True,
        "engine_type": "DETERMINISTIC_RULES",
        "evaluator_note": payload.evaluator_note if payload else None
    })

    # Save to verification history table and update asset status + confidence
    saved_vrf = AssetRepository.save_verification(
        asset_id=asset_id,
        confidence_score=eval_result["confidence"],
        verification_status=eval_result["status"],
        evaluated_by=evaluator_label,
        scoring_details_json=details_json,
        contributions=eval_result["contributions"]
    )

    # Record SHA-256 chained audit event
    record_audit_event(
        actor=current_user.get("name", "User"),
        role=current_user.get("role", "CITIZEN"),
        event_type="ASSET_VERIFICATION",
        entity_type="ASSET",
        entity_id=asset_id,
        description=(
            f"Asset {asset_id} verified: status={eval_result['status']}, "
            f"confidence={eval_result['confidence']}%. {eval_result['explanation']}"
        )
    )

    # Fetch updated verification history
    history_records = AssetRepository.get_verification_history(asset_id)
    formatted_history = []
    for h in history_records:
        h_dict = dict(h)
        if "scoring_details_json" in h_dict and h_dict["scoring_details_json"]:
            try:
                h_dict["details"] = json.loads(h_dict["scoring_details_json"])
            except Exception:
                h_dict["details"] = {}
        formatted_history.append(h_dict)

    return AssetVerificationDetailResponse(
        asset_id=asset_id,
        status=eval_result["status"],
        confidence=eval_result["confidence"],
        explanation=eval_result["explanation"],
        contributions=eval_result["contributions"],
        weights_used=eval_result["weights_used"],
        verification_id=saved_vrf["verification_id"],
        evaluated_by=evaluator_label,
        verified_at=saved_vrf["verified_at"],
        is_deterministic=True,
        engine_type="DETERMINISTIC_RULES",
        can_issue_certificate=eval_result["can_issue_certificate"],
        history=formatted_history
    )


@router.get(
    "/{asset_id}/verification",
    response_model=AssetVerificationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve asset verification status and history",
    tags=["Asset Verification"]
)
def get_asset_verification(
    asset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AssetVerificationDetailResponse:
    """
    Step 9: Retrieve Asset Evidence Verification Status & History.
    - Requires authentication.
    - Citizens can only view verification for their own assets.
    - Officers/Admins can view verification for any asset.
    - Returns current verification status, confidence score (0-100),
      explanation, contributing evidence items, and complete history.
    """
    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    # Ownership & Authorization Check
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to view verification for another citizen's asset.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to view asset verification records.")

    latest_vrf = AssetRepository.get_latest_verification(asset_id)
    history_records = AssetRepository.get_verification_history(asset_id)

    formatted_history = []
    for h in history_records:
        h_dict = dict(h)
        if "scoring_details_json" in h_dict and h_dict["scoring_details_json"]:
            try:
                h_dict["details"] = json.loads(h_dict["scoring_details_json"])
            except Exception:
                h_dict["details"] = {}
        formatted_history.append(h_dict)

    if latest_vrf:
        details = {}
        if latest_vrf.get("scoring_details_json"):
            try:
                details = json.loads(latest_vrf["scoring_details_json"])
            except Exception:
                details = {}

        return AssetVerificationDetailResponse(
            asset_id=asset_id,
            status=latest_vrf["verification_status"],
            confidence=latest_vrf["confidence_score"],
            explanation=details.get("explanation", "Verification record retrieved."),
            contributions=details.get("contributions", []),
            weights_used=details.get("weights_used"),
            verification_id=latest_vrf["verification_id"],
            evaluated_by=latest_vrf.get("evaluated_by"),
            verified_at=latest_vrf.get("verified_at"),
            is_deterministic=True,
            engine_type="DETERMINISTIC_RULES",
            can_issue_certificate=latest_vrf["confidence_score"] >= 80,
            history=formatted_history
        )
    else:
        # No formal verification run yet. Evaluate current evidence dynamically to reflect current state.
        evidence_list = AssetRepository.list_evidence_for_asset(asset_id)
        eval_result = evaluate_asset_evidence(evidence_list)
        return AssetVerificationDetailResponse(
            asset_id=asset_id,
            status=eval_result["status"],
            confidence=eval_result["confidence"],
            explanation=eval_result["explanation"],
            contributions=eval_result["contributions"],
            weights_used=eval_result["weights_used"],
            verification_id=None,
            evaluated_by=None,
            verified_at=None,
            is_deterministic=True,
            engine_type="DETERMINISTIC_RULES",
            can_issue_certificate=eval_result["can_issue_certificate"],
            history=[]
        )


@router.post(
    "/{asset_id}/certificate",
    response_model=AssetCertificateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Digital Asset Certificate for a verified asset",
    tags=["Asset Certificates"]
)
def create_asset_certificate(
    asset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AssetCertificateResponse:
    """
    Step 11: Generate Digital Asset Certificate.
    - A certificate can ONLY be generated for an appropriately verified asset (confidence >= 80).
    - Unverified or partially verified assets are rejected with 400 Bad Request.
    - Generates cryptographic evidence hash binding all verified proofs.
    - Produces secure QR code pointing to safe verification endpoint with zero citizen PII.
    - Records tamper-evident CERTIFICATE_GENERATED audit event.
    - Provides frontend-ready certificate representation.
    """
    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    # 1. Authorization check: Citizen must own the asset; Officers/Admins authorized
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to generate a certificate for another citizen's asset.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to issue asset certificates.")

    # 2. Eligibility requirement: MUST be appropriately verified
    asset_status = (asset.get("status") or "").upper()
    asset_confidence = int(asset.get("verification_confidence") or 0)

    if asset_status not in ("VERIFIED", "OFFICIALLY_CONFIRMED") or asset_confidence < 80:
        raise ValidationError(
            f"Cannot generate certificate for an unverified asset. "
            f"Asset '{asset_id}' has status '{asset_status}' with {asset_confidence}% confidence. "
            f"Assets must be verified with at least 80% evidence confidence."
        )

    # 3. Compute evidence hash binding all evidence items
    evidence_list = AssetRepository.list_evidence_for_asset(asset_id)
    evidence_hashes = [
        e["sha256_hash"]
        for e in sorted(evidence_list, key=lambda x: x.get("evidence_id", ""))
        if e.get("sha256_hash")
    ]
    if evidence_hashes:
        combined_hashes = "|".join(evidence_hashes)
        evidence_hash = "0x" + hashlib.sha256(combined_hashes.encode("utf-8")).hexdigest()
    else:
        evidence_hash = asset.get("integrity_hash") or (
            "0x" + hashlib.sha256(f"{asset_id}|{asset['category']}|VERIFIED".encode("utf-8")).hexdigest()
        )

    # 4. Generate or retrieve existing certificate
    existing_cert = AssetRepository.get_certificate_by_asset_id(asset_id)
    if existing_cert:
        cert_id = existing_cert["certificate_id"]
        cert_token = existing_cert["certificate_token"]
    else:
        cert_id = AssetRepository.generate_certificate_id()
        cert_token = secrets.token_urlsafe(24)

    now_iso = datetime.now(timezone.utc).isoformat()
    verification_url = f"/certificates/verify/{cert_token}"

    # 5. Generate QR code payload & visual SVG / Data URI
    # Crucial Privacy Rule: QR payload MUST NOT expose private citizen information
    qr_payload_dict = {
        "certificate_id": cert_id,
        "asset_id": asset_id,
        "category": asset.get("category", ""),
        "verification_status": asset_status,
        "evidence_confidence": f"{asset_confidence}%",
        "evidence_hash": evidence_hash,
        "issued_at": now_iso,
        "verification_url": verification_url
    }
    qr_payload_str = json.dumps(qr_payload_dict)

    qr_bundle = generate_qr_bundle(verification_url)
    qr_svg = qr_bundle["svg"]
    qr_data_uri = qr_bundle["data_uri"]

    # 6. Save certificate record and update asset
    saved_cert = AssetRepository.save_certificate(
        certificate_id=cert_id,
        asset_id=asset_id,
        certificate_token=cert_token,
        verification_status=asset_status,
        evidence_confidence=asset_confidence,
        evidence_hash=evidence_hash,
        qr_payload=qr_payload_str,
        issued_at=now_iso,
        verify_url=verification_url
    )

    # 7. Record tamper-evident sequential audit event
    record_audit_event(
        actor=current_user.get("name", "Citizen"),
        role=current_user.get("role", "CITIZEN"),
        event_type="CERTIFICATE_GENERATED",
        entity_type="CERTIFICATE",
        entity_id=cert_id,
        evidence_hash=evidence_hash,
        description=(
            f"Digital Asset Certificate '{cert_id}' generated for verified asset '{asset_id}' "
            f"({asset.get('category')}) with {asset_confidence}% evidence confidence."
        )
    )

    # 8. Retrieve complete verification history
    history_records = AssetRepository.get_verification_history(asset_id)
    formatted_history = []
    for h in history_records:
        h_dict = dict(h)
        if "scoring_details_json" in h_dict and h_dict["scoring_details_json"]:
            try:
                h_dict["details"] = json.loads(h_dict["scoring_details_json"])
            except Exception:
                h_dict["details"] = {}
        formatted_history.append(h_dict)

    # 9. Build frontend representation card
    reg_time = asset.get("registration_timestamp") or asset.get("created_at") or now_iso
    frontend_card = FrontendCertificateCard(
        card_title="RELIEFCHAIN DIGITAL ASSET CERTIFICATE",
        certificate_id=cert_id,
        asset_id=asset_id,
        badge="OFFICIALLY VERIFIED PRE-DISASTER ASSET",
        category_label=str(asset.get("category", "")).replace("_", " ").title(),
        description=asset.get("description", ""),
        verification_status=asset_status,
        confidence_score=f"{asset_confidence}%",
        confidence_tier="HIGH CONFIDENCE" if asset_confidence >= 80 else "MODERATE",
        evidence_hash=evidence_hash,
        registration_date=reg_time[:10] if reg_time else "",
        issued_date=now_iso[:10],
        qr_code_data_uri=qr_data_uri,
        verification_endpoint=verification_url,
        trust_seal="SHA-256 VERIFIED CIVIC BASELINE",
        issuer="ReliefChain AI Civic Trust Authority"
    )

    return AssetCertificateResponse(
        certificate_id=cert_id,
        asset_id=asset_id,
        category=asset.get("category", ""),
        description=asset.get("description", ""),
        verification_status=asset_status,
        evidence_confidence=asset_confidence,
        evidence_hash=evidence_hash,
        registration_timestamp=reg_time,
        verification_history=formatted_history,
        qr_code=qr_data_uri,
        certificate_token=cert_token,
        issued_at=now_iso,
        verification_url=verification_url,
        qr_code_svg=qr_svg,
        frontend_card=frontend_card
    )


@router.get(
    "/{asset_id}/certificate",
    response_model=AssetCertificateResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Digital Asset Certificate for an asset",
    tags=["Asset Certificates"]
)
def get_asset_certificate_by_asset_id(
    asset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AssetCertificateResponse:
    """
    Step 21: Retrieve existing Digital Asset Certificate for an asset.
    - Asset existence check (404)
    - Citizen ownership check (403 for other citizens)
    - If certificate not yet issued -> 404
    """
    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to view another citizen's asset certificate.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to view asset certificates.")

    existing_cert = AssetRepository.get_certificate_by_asset_id(asset_id)
    if not existing_cert:
        raise NotFoundError(f"Digital asset certificate has not been generated yet for asset '{asset_id}'.")

    from .certificates import get_certificate
    return get_certificate(certificate_id=existing_cert["certificate_id"], current_user=current_user)
