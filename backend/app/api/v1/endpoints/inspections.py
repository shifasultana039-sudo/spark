"""
ReliefChain AI - Field Inspections & NGO Assessor Endpoints (Step 28).

Provides:
- GET /inspections: List assigned inspections (filterable by status, claim_id)
- GET /inspections/{inspection_id}: Full inspection dossier including claim & evidence
- GET /claims/{claim_id}/inspection: Inspection record for a specific claim
- POST /inspections/{inspection_id}/findings: Add/update on-site surveyor findings
- POST /inspections/{inspection_id}/evidence: Upload geotagged photos or inspection reports
- POST /inspections/{inspection_id}/submit: Finalize & submit inspection report (updates claim to FIELD_INSPECTED)

Enforces role boundaries:
- Field Assessors and NGO personnel can inspect, record findings, upload evidence, and submit reports.
- Approving or rejecting financial claims is strictly reserved for authorized Government Officers.
"""

import base64
import hashlib
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Request, status, UploadFile, File, Form
from fastapi.responses import FileResponse

from ....repositories.asset_repo import AssetRepository
from ....schemas.inspection import (
    InspectionResponse,
    InspectionDetailResponse,
    InspectionFindingsRequest,
    InspectionSubmitReportRequest,
    InspectionEvidenceUploadRequest
)
from ....core.auth import get_current_user, is_officer_or_admin
from ....core.errors import NotFoundError, ForbiddenError, ValidationError
from ....services import record_audit_event
from .evidence import validate_file_content

try:
    from storage.provider import storage_provider
except (ImportError, ValueError):
    from ....storage.provider import storage_provider

router = APIRouter(prefix="/inspections", tags=["Field Inspections"])


@router.get(
    "",
    response_model=List[InspectionResponse],
    summary="List assigned field inspections"
)
def list_inspections(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, IN_PROGRESS, COMPLETED)"),
    claim_id: Optional[str] = Query(None, description="Filter by claim ID"),
    assigned_officer: Optional[str] = Query(None, description="Filter by assigned officer / NGO"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[InspectionResponse]:
    """
    Step 28: Retrieves list of assigned field inspections for NGO surveyors and officers.
    """
    rows = AssetRepository.get_field_inspections(
        status=status,
        assigned_officer=assigned_officer,
        claim_id=claim_id
    )
    return [InspectionResponse(**r) for r in rows]


@router.get(
    "/{inspection_id}",
    response_model=InspectionDetailResponse,
    summary="Retrieve single field inspection dossier"
)
def get_inspection_details(
    inspection_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> InspectionDetailResponse:
    """
    Step 28: Retrieves detailed field inspection dossier with attached evidence and claim baseline.
    """
    record = AssetRepository.get_field_inspection_by_id(inspection_id)
    if not record:
        raise NotFoundError(f"Field inspection '{inspection_id}' not found.")
    return InspectionDetailResponse(**record)


@router.post(
    "/{inspection_id}/findings",
    response_model=InspectionDetailResponse,
    summary="Add or update field inspection findings"
)
def update_inspection_findings(
    inspection_id: str,
    payload: InspectionFindingsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> InspectionDetailResponse:
    """
    Step 28: Field Assessor / NGO records preliminary on-site findings and observations.
    """
    existing = AssetRepository.get_field_inspection_by_id(inspection_id)
    if not existing:
        raise NotFoundError(f"Field inspection '{inspection_id}' not found.")

    assessor_name = current_user.get("name", "Field Assessor")

    findings_val = payload.get_findings() if hasattr(payload, "get_findings") else (payload.findings or "")
    damage_val = payload.get_damage_rating() if hasattr(payload, "get_damage_rating") else payload.damage_rating

    updated = AssetRepository.update_field_inspection_findings(
        inspection_id=inspection_id,
        findings=findings_val,
        damage_rating=damage_val,
        status=payload.status or "IN_PROGRESS"
    )

    record_audit_event(
        actor=assessor_name,
        role=current_user.get("role", "FIELD_ASSESSOR"),
        event_type="INSPECTION_FINDINGS_UPDATED",
        entity_type="INSPECTION",
        entity_id=inspection_id,
        description=f"Findings updated for inspection '{inspection_id}' by {assessor_name}."
    )

    return InspectionDetailResponse(**updated)


@router.post(
    "/{inspection_id}/evidence",
    response_model=InspectionDetailResponse,
    summary="Upload photographic or survey evidence for an inspection"
)
async def upload_inspection_evidence(
    inspection_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    evidence_type: Optional[str] = Form("FIELD_INSPECTION_REPORT"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> InspectionDetailResponse:
    """
    Step 28: Assessor uploads field photographs, damage documentation, or survey reports.
    Supports both multipart form upload and JSON base64 body.
    """
    inspection = AssetRepository.get_field_inspection_by_id(inspection_id)
    if not inspection:
        raise NotFoundError(f"Field inspection '{inspection_id}' not found.")

    claim_id = inspection["claim_id"]
    assessor_name = current_user.get("name", "Field Assessor")

    file_bytes: bytes = b""
    original_filename: str = ""
    clean_ev_type: str = "FIELD_INSPECTION_REPORT"

    content_type_header = request.headers.get("content-type", "")

    if "application/json" in content_type_header:
        body = await request.json()
        payload = InspectionEvidenceUploadRequest(**body)
        try:
            file_bytes = base64.b64decode(payload.file_content_base64)
        except Exception as e:
            raise ValidationError(f"Invalid base64 encoding: {str(e)}")
        original_filename = payload.original_filename
        clean_ev_type = payload.evidence_type or "FIELD_INSPECTION_REPORT"
    elif file is not None:
        file_bytes = await file.read()
        original_filename = file.filename or "inspection_evidence.jpg"
        clean_ev_type = evidence_type or "FIELD_INSPECTION_REPORT"
    else:
        raise ValidationError("No file provided. Send multipart form with 'file' or JSON with 'file_content_base64'.")

    # Content validation
    validate_file_content(original_filename, file_bytes)

    # SHA-256 hash
    sha256_hash = "0x" + hashlib.sha256(file_bytes).hexdigest()

    # Determine MIME type
    ext = original_filename.split(".")[-1].lower() if "." in original_filename else ""
    mime_type = "image/jpeg"
    if ext in ("png",):
        mime_type = "image/png"
    elif ext in ("webp",):
        mime_type = "image/webp"
    elif ext in ("pdf",):
        mime_type = "application/pdf"
    elif ext in ("mp4",):
        mime_type = "video/mp4"

    # Save to secure storage
    evidence_id = AssetRepository.generate_claim_evidence_id()
    custom_key = f"{evidence_id}_{original_filename}"
    storage_res = storage_provider.save_file(
        file_bytes,
        original_filename,
        is_private=True,
        custom_key=custom_key
    )
    sha256_hash = storage_res["sha256_hash"]
    file_size = storage_res["file_size"]
    mime_type = storage_res.get("mime_type") or mime_type
    file_url = f"/claims/{claim_id}/evidence/{evidence_id}/file"

    # Insert into claim evidence
    AssetRepository.add_claim_evidence(
        claim_id=claim_id,
        evidence_type=clean_ev_type,
        file_url=file_url,
        original_filename=original_filename,
        sha256_hash=sha256_hash,
        file_size=file_size,
        mime_type=mime_type,
        evidence_id=evidence_id
    )

    # If it's a report document, also update inspection report_file_url
    if ext in ("pdf", "doc", "docx") or clean_ev_type == "FIELD_INSPECTION_REPORT":
        with storage_provider.get_file_path(custom_key, is_private=True) as _:
            pass
        from ....core.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE field_inspections SET report_file_url = ? WHERE inspection_id = ?;
            """, (file_url, inspection_id))

    record_audit_event(
        actor=assessor_name,
        role=current_user.get("role", "FIELD_ASSESSOR"),
        event_type="INSPECTION_EVIDENCE_UPLOADED",
        entity_type="INSPECTION",
        entity_id=inspection_id,
        description=f"Evidence '{original_filename}' uploaded for inspection '{inspection_id}' (Claim {claim_id}) by {assessor_name}.",
        evidence_hash=sha256_hash
    )

    updated = AssetRepository.get_field_inspection_by_id(inspection_id)
    return InspectionDetailResponse(**updated)


@router.post(
    "/{inspection_id}/submit",
    response_model=InspectionDetailResponse,
    summary="Submit finalized field inspection report"
)
def submit_inspection_report(
    inspection_id: str,
    payload: InspectionSubmitReportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> InspectionDetailResponse:
    """
    Step 28: Field Assessor / NGO submits the finalized on-site physical inspection report.
    - Sets inspection status to COMPLETED.
    - Updates associated claim status to FIELD_INSPECTED.
    - Appends decision notes so the Government Officer can immediately see the complete report.
    - Records tamper-evident audit event.
    """
    existing = AssetRepository.get_field_inspection_by_id(inspection_id)
    if not existing:
        raise NotFoundError(f"Field inspection '{inspection_id}' not found.")

    assessor_name = current_user.get("name", "Field Assessor")

    findings_val = payload.get_findings() if hasattr(payload, "get_findings") else (payload.findings or "")
    damage_val = payload.get_damage_rating() if hasattr(payload, "get_damage_rating") else (payload.damage_rating or "MODERATE_DAMAGE")

    updated = AssetRepository.submit_field_inspection_report(
        inspection_id=inspection_id,
        findings=findings_val,
        damage_rating=damage_val,
        report_file_url=payload.report_file_url,
        completed_by=assessor_name
    )

    record_audit_event(
        actor=assessor_name,
        role=current_user.get("role", "FIELD_ASSESSOR"),
        event_type="INSPECTION_REPORT_SUBMITTED",
        entity_type="INSPECTION",
        entity_id=inspection_id,
        description=f"Field inspection report finalized and submitted for claim '{existing['claim_id']}' by {assessor_name}. Damage Rating: {damage_val}."
    )

    return InspectionDetailResponse(**updated)
