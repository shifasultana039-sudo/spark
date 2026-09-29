"""
ReliefChain AI - Evidence Management Endpoints (Step 8).
Implements:
- POST /assets/{asset_id}/evidence: Upload evidence item (supports multipart and base64 JSON)
- GET /assets/{asset_id}/evidence: List all evidence associated with an asset
- GET /evidence/{evidence_id}: Retrieve single evidence metadata with privacy protection
- GET /evidence/{evidence_id}/file: Authenticated retrieval of private evidence file
"""

import base64
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import FileResponse, Response

from ....repositories.asset_repo import AssetRepository
from ....schemas.asset import EvidenceResponse, EvidenceCreateRequest
from ....models.entities import EvidenceType
from ....core.auth import get_current_user, is_officer_or_admin, is_citizen
from ....core.errors import NotFoundError, ForbiddenError, ValidationError
from ....services import record_audit_event
try:
    from storage.provider import storage_provider
except (ImportError, ValueError):
    from ....storage.provider import storage_provider

router = APIRouter(tags=["Evidence Management"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".txt", ".docx", ".doc",
    ".jpg", ".jpeg", ".png", ".webp", ".tiff", ".heic",
    ".mp4", ".mov", ".webm", ".avi", ".mkv",
    ".geojson", ".gpx", ".kml", ".json"
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def validate_file_content(filename: str, content: bytes) -> None:
    """Validates file extension and reasonable size."""
    if not filename or not filename.strip():
        raise ValidationError("Original filename is required.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '{ext}'. Allowed extensions: PDF, Images (JPEG, PNG, WEBP), "
            f"Videos (MP4, WEBM), Documents (DOCX, TXT), GeoJSON/GPX."
        )

    size = len(content)
    if size == 0:
        raise ValidationError("File content is empty (0 bytes).")
    if size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(f"File size exceeds maximum reasonable limit of 50 MB (got {size:,} bytes).")


def validate_and_normalize_evidence_type(raw_type: str) -> str:
    """Validates evidence type against the 10 supported types."""
    if not raw_type:
        raise ValidationError("evidence_type is required.")
    
    clean_type = raw_type.strip().upper().replace(" / ", "_").replace(" ", "_").replace("-", "_")
    if clean_type == "WARRANTY_DOCUMENT":
        clean_type = "WARRANTY"
    elif clean_type in ("FIELD_INSPECTION", "INSPECTION_REPORT"):
        clean_type = "FIELD_INSPECTION_REPORT"
    elif clean_type in ("PROPERTY_DEED", "DEED", "PATTA", "PATTA_CHITTA", "TITLE_DEED", "GOVT_REGISTRATION"):
        clean_type = "PROPERTY_DEED"

    valid_types = {e.value for e in EvidenceType}

    if clean_type not in valid_types:
        raise ValidationError(f"Invalid evidence_type '{raw_type}'. Allowed: {sorted(list(valid_types))}")
    return clean_type


@router.post(
    "/assets/{asset_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and register an evidence proof for an asset"
)
async def upload_asset_evidence(
    asset_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EvidenceResponse:
    """
    Uploads an evidence file (invoice, patta, photo, video, inspection report):
    1. Authenticates user.
    2. Validates asset existence and ownership (citizens can only upload to own assets).
    3. Validates file type and size.
    4. Computes SHA-256 hash.
    5. Saves file to private local storage (no public URL exposure).
    6. Stores metadata with status PENDING (no AI verification yet).
    7. Appends event to tamper-evident audit chain.
    """
    # 1. Verify asset existence
    asset = AssetRepository.get_asset_by_id(asset_id)
    if not asset:
        raise NotFoundError(f"Asset '{asset_id}' not found.")

    # 2. Authorization check
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = asset.get("citizen_id")
        asset_hh = asset.get("household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to upload evidence for another citizen's asset.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to upload evidence.")

    # 3. Extract file content & metadata from multipart form or JSON
    content_type = request.headers.get("content-type", "")
    file_bytes: bytes = b""
    original_filename: str = ""
    evidence_type_raw: str = ""
    captured_timestamp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    extra_metadata: Dict[str, Any] = {}

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file or not hasattr(uploaded_file, "read"):
            raise ValidationError("Missing 'file' in multipart form data.")

        file_bytes = await uploaded_file.read()
        original_filename = getattr(uploaded_file, "filename", "evidence.bin")
        evidence_type_raw = str(form.get("evidence_type", ""))
        captured_timestamp = form.get("captured_timestamp")
        
        lat_str = form.get("latitude")
        if lat_str is not None and str(lat_str).strip():
            latitude = float(lat_str)
        lng_str = form.get("longitude")
        if lng_str is not None and str(lng_str).strip():
            longitude = float(lng_str)

        meta_str = form.get("metadata")
        if meta_str:
            try:
                extra_metadata = json.loads(str(meta_str))
            except Exception:
                extra_metadata = {"raw_metadata": str(meta_str)}

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
        latitude = body.get("latitude")
        longitude = body.get("longitude")
        extra_metadata = body.get("metadata") or {}
    else:
        raise ValidationError("Unsupported media type. Request must be 'multipart/form-data' or 'application/json'.")

    # 4. Validate file type and size
    validate_file_content(original_filename, file_bytes)
    evidence_type = validate_and_normalize_evidence_type(evidence_type_raw)

    # 5. Compute SHA-256 hash & save to private storage
    storage_res = storage_provider.save_file(file_bytes, original_filename, is_private=True)
    sha256_hash = storage_res["sha256_hash"]
    file_size = storage_res["file_size"]
    mime_type = storage_res["mime_type"]
    storage_key = storage_res["storage_key"]

    extra_metadata["storage_key"] = storage_key
    extra_metadata["is_private"] = True

    # 6. Save in database (Do NOT mark VERIFIED - status remains PENDING)
    evidence_id = AssetRepository.generate_evidence_id()
    # Secure private file url pointing to authenticated endpoint
    file_url = f"/evidence/{evidence_id}/file"

    inserted = AssetRepository.add_evidence(
        asset_id=asset_id,
        evidence_type=evidence_type,
        file_url=file_url,
        original_filename=original_filename,
        sha256_hash=sha256_hash,
        file_size=file_size,
        mime_type=mime_type,
        uploader=current_user.get("name", "Citizen"),
        captured_timestamp=captured_timestamp,
        metadata_json=json.dumps(extra_metadata),
        latitude=latitude,
        longitude=longitude,
        verification_status="PENDING",
        score_contribution=0
    )

    # 7. Create sequential audit event with evidence hash
    record_audit_event(
        actor=current_user.get("name", "User"),
        role=current_user.get("role", "CITIZEN"),
        event_type="EVIDENCE_UPLOADED",
        entity_type="EVIDENCE",
        entity_id=evidence_id,
        description=(
            f"Evidence {evidence_id} ({evidence_type}) uploaded for asset {asset_id}. "
            f"File: '{original_filename}' ({file_size:,} bytes), SHA-256: {sha256_hash[:18]}..."
        ),
        evidence_hash=sha256_hash
    )

    return EvidenceResponse(**inserted)


@router.get(
    "/assets/{asset_id}/evidence",
    response_model=List[EvidenceResponse],
    summary="List all evidence associated with an asset"
)
def list_asset_evidence(
    asset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[EvidenceResponse]:
    """
    Retrieves all evidence associated with an asset:
    - Citizens can only view evidence for their own asset.
    - Government Officers / Admins can inspect all evidence.
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
            raise ForbiddenError("Access denied. You do not have permission to view evidence for another citizen's asset.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to view evidence records.")

    evidence_items = AssetRepository.list_evidence_for_asset(asset_id)
    return [EvidenceResponse(**e) for e in evidence_items]


@router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Get single evidence metadata"
)
def get_evidence(
    evidence_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EvidenceResponse:
    """
    Retrieves single evidence metadata item:
    - Protects citizen privacy: Citizens cannot view another citizen's evidence.
    - Officers / Admins have authorized access.
    """
    evidence = AssetRepository.get_evidence_by_id(evidence_id)
    if not evidence:
        raise NotFoundError(f"Evidence '{evidence_id}' not found.")

    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = evidence.get("asset_citizen_id")
        asset_hh = evidence.get("asset_household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to access another citizen's evidence.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to view evidence records.")

    return EvidenceResponse(**evidence)


@router.get(
    "/evidence/{evidence_id}/file",
    summary="Download or view private evidence file (Authenticated)"
)
def get_evidence_file(
    evidence_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Streams private evidence file securely:
    - Prevents public URL exposure of private documents.
    - Requires authenticated access and authorization check.
    """
    evidence = AssetRepository.get_evidence_by_id(evidence_id)
    if not evidence:
        raise NotFoundError(f"Evidence '{evidence_id}' not found.")

    # Authorization
    if is_citizen(current_user):
        user_id = current_user.get("id")
        user_hh = current_user.get("household_ref")
        asset_citizen = evidence.get("asset_citizen_id")
        asset_hh = evidence.get("asset_household_ref")

        is_owner = (asset_citizen is not None and asset_citizen == user_id) or (user_hh and asset_hh == user_hh)
        if not is_owner:
            raise ForbiddenError("Access denied. You do not have permission to access another citizen's file.")
    elif not is_officer_or_admin(current_user):
        raise ForbiddenError("You are not authorized to access private evidence files.")

    # Locate storage file
    storage_key = None
    if evidence.get("metadata_json"):
        try:
            meta = json.loads(evidence["metadata_json"])
            storage_key = meta.get("storage_key")
        except Exception:
            pass

    if not storage_key:
        storage_key = Path(evidence.get("file_url", "")).name

    file_path = storage_provider.get_file_path(storage_key, is_private=True)
    if not file_path or not file_path.exists():
        raise NotFoundError(f"Physical file for evidence '{evidence_id}' not found in storage.")

    return FileResponse(
        path=str(file_path),
        filename=evidence.get("original_filename", "evidence.bin"),
        media_type=evidence.get("mime_type", "application/octet-stream")
    )
