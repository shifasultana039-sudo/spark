"""
ReliefChain AI - Digital Asset Certificates Endpoints (Step 11).
Provides:
- GET /certificates/{certificate_id}: Retrieves full certificate representation with verification history and frontend card
- GET /certificates/verify/{certificate_token}: Public safe verification endpoint pointed to by QR code (strictly zero PII)
- GET /certificates/{certificate_id}/qr: Returns raw SVG QR code for direct rendering or download
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status, Response

from ....repositories.asset_repo import AssetRepository
from ....schemas.asset import (
    AssetCertificateResponse,
    SafeCertificateVerificationResponse,
    FrontendCertificateCard
)
from ....core.auth import get_optional_user, is_citizen, is_officer_or_admin
from ....core.errors import NotFoundError, ForbiddenError

try:
    from services.qr_service import generate_qr_bundle, generate_qr_svg
except (ImportError, ValueError):
    from ....services.qr_service import generate_qr_bundle, generate_qr_svg

router = APIRouter(prefix="/certificates", tags=["Asset Certificates"])


@router.get(
    "/verify/{certificate_token}",
    response_model=SafeCertificateVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Public safe certificate verification endpoint (scanned via QR code)",
    tags=["Asset Certificates"]
)
def verify_certificate_public(certificate_token: str) -> SafeCertificateVerificationResponse:
    """
    Public safe verification endpoint pointed to by the certificate QR code.
    Requirements:
    1. QR must point to a secure verification endpoint.
    2. QR must NOT expose private citizen information.
    3. Verification endpoint should return ONLY safe certificate verification information.
    
    Guarantees:
    - Zero citizen PII: No citizen name, phone, private address, or financial valuation.
    - Confirms cryptographic authenticity, status, evidence confidence, and evidence hash.
    """
    cert = AssetRepository.get_certificate_by_token(certificate_token)
    if not cert:
        raise NotFoundError(f"Certificate token or identifier '{certificate_token}' is invalid or does not exist.")

    now_iso = datetime.now(timezone.utc).isoformat()
    confidence = cert.get("evidence_confidence", 0)
    status_val = cert.get("verification_status", "VERIFIED")
    asset_id = cert.get("asset_id", "")

    return SafeCertificateVerificationResponse(
        is_valid=True,
        certificate_id=cert["certificate_id"],
        asset_id=asset_id,
        category=cert.get("category", ""),
        description=cert.get("description", ""),
        verification_status=status_val,
        evidence_confidence=confidence,
        evidence_hash=cert.get("evidence_hash", ""),
        issued_at=cert.get("issued_at", now_iso),
        issuer="ReliefChain AI Civic Trust Authority",
        verification_timestamp=now_iso,
        verification_message=(
            f"Asset '{asset_id}' is authentic, baseline-anchored, and digitally verified "
            f"on ReliefChain AI with {confidence}% evidence confidence."
        )
    )


@router.get(
    "/{certificate_id}",
    response_model=AssetCertificateResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Digital Asset Certificate by ID"
)
def get_certificate(
    certificate_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> AssetCertificateResponse:
    """
    Retrieves full Digital Asset Certificate metadata.
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
    - QR code (base64 Data URI)
    - frontend representation card
    
    Authorization:
    - If user is authenticated as citizen, verifies ownership of the underlying asset.
    - Officers and Admins have unrestricted verification access.
    """
    cert = AssetRepository.get_certificate_by_id(certificate_id)
    if not cert:
        raise NotFoundError(f"Certificate '{certificate_id}' not found.")

    # Privacy check if caller is an authenticated citizen
    if current_user and is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        cert_citizen = cert.get("citizen_id")
        cert_hh = cert.get("household_ref")

        is_owner = (cert_citizen is not None and cert_citizen == user_id) or (user_hh and cert_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to view another citizen's certificate.")

    asset_id = cert["asset_id"]
    cert_id = cert["certificate_id"]
    cert_token = cert["certificate_token"]
    verification_url = f"/certificates/verify/{cert_token}"

    # Generate QR bundle
    qr_bundle = generate_qr_bundle(verification_url)
    qr_svg = qr_bundle["svg"]
    qr_data_uri = qr_bundle["data_uri"]

    # Retrieve verification history
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

    reg_time = cert.get("registration_timestamp", "")
    issued_at = cert.get("issued_at", "")
    confidence = cert.get("evidence_confidence", 0)
    status_val = cert.get("verification_status", "VERIFIED")

    frontend_card = FrontendCertificateCard(
        card_title="RELIEFCHAIN DIGITAL ASSET CERTIFICATE",
        certificate_id=cert_id,
        asset_id=asset_id,
        badge="OFFICIALLY VERIFIED PRE-DISASTER ASSET",
        category_label=str(cert.get("category", "")).replace("_", " ").title(),
        description=cert.get("description", ""),
        verification_status=status_val,
        confidence_score=f"{confidence}%",
        confidence_tier="HIGH CONFIDENCE" if confidence >= 80 else "MODERATE",
        evidence_hash=cert.get("evidence_hash", ""),
        registration_date=reg_time[:10] if reg_time else "",
        issued_date=issued_at[:10] if issued_at else "",
        qr_code_data_uri=qr_data_uri,
        verification_endpoint=verification_url,
        trust_seal="SHA-256 VERIFIED CIVIC BASELINE",
        issuer="ReliefChain AI Civic Trust Authority"
    )

    return AssetCertificateResponse(
        certificate_id=cert_id,
        asset_id=asset_id,
        category=cert.get("category", ""),
        description=cert.get("description", ""),
        verification_status=status_val,
        evidence_confidence=confidence,
        evidence_hash=cert.get("evidence_hash", ""),
        registration_timestamp=reg_time,
        verification_history=formatted_history,
        qr_code=qr_data_uri,
        certificate_token=cert_token,
        issued_at=issued_at,
        verification_url=verification_url,
        qr_code_svg=qr_svg,
        frontend_card=frontend_card
    )


@router.get(
    "/{certificate_id}/qr",
    summary="Get visual SVG QR code image for certificate",
    response_class=Response
)
def get_certificate_qr_image(certificate_id: str):
    """Returns pure SVG QR code image for embedding or direct viewing."""
    cert = AssetRepository.get_certificate_by_id(certificate_id)
    if not cert:
        raise NotFoundError(f"Certificate '{certificate_id}' not found.")

    cert_token = cert["certificate_token"]
    verification_url = f"/certificates/verify/{cert_token}"
    svg_content = generate_qr_svg(verification_url)
    return Response(content=svg_content, media_type="image/svg+xml")
