"""
ReliefChain AI - Field Inspection Schemas (Step 28).
Data validation models for field inspections, on-site findings, and reports.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class InspectionResponse(BaseModel):
    """Inspection record representation for listing and basic views."""
    id: Optional[int] = None
    inspection_id: str
    claim_id: str
    assigned_officer: str
    status: str
    findings: Optional[str] = None
    damage_rating: Optional[str] = None
    report_file_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

    # Enriched claim / asset information
    asset_id: Optional[str] = None
    household_ref: Optional[str] = None
    damage_description: Optional[str] = None
    claim_status: Optional[str] = None
    asset_category: Optional[str] = None
    asset_description: Optional[str] = None
    documented_value: Optional[float] = None
    location_address: Optional[str] = None
    evidence_count: Optional[int] = 0

    class Config:
        from_attributes = True


class InspectionDetailResponse(InspectionResponse):
    """Full detailed inspection dossier including claim evidence files."""
    evidence_files: Optional[List[Dict[str, Any]]] = []


class InspectionFindingsRequest(BaseModel):
    """Payload for field assessor updating findings and damage rating."""
    findings: Optional[str] = Field(None, description="On-site physical inspection findings and observations")
    field_findings: Optional[str] = Field(None, description="Alias for findings")
    damage_rating: Optional[str] = Field(None, description="Assessor damage rating")
    damage_severity_rating: Optional[str] = Field(None, description="Alias for damage_rating")
    status: Optional[str] = Field("IN_PROGRESS", description="Inspection status update")

    def get_findings(self) -> str:
        return (self.findings or self.field_findings or "").strip()

    def get_damage_rating(self) -> Optional[str]:
        return self.damage_rating or self.damage_severity_rating


class InspectionSubmitReportRequest(BaseModel):
    """Payload for submitting the finalized inspection report."""
    findings: Optional[str] = Field(None, description="Detailed physical inspection report findings")
    field_findings: Optional[str] = Field(None, description="Alias for findings")
    damage_rating: Optional[str] = Field(None, description="Physical damage rating (e.g. MINOR_DAMAGE, MODERATE_DAMAGE, MAJOR_STRUCTURAL_DAMAGE, TOTAL_LOSS)")
    damage_severity_rating: Optional[str] = Field(None, description="Alias for damage_rating")
    report_file_url: Optional[str] = Field(None, description="URL or path to uploaded inspection report document")
    inspector_notes: Optional[str] = Field(None, description="Additional notes or recommendations for government officer")

    def get_findings(self) -> str:
        return (self.findings or self.field_findings or "").strip()

    def get_damage_rating(self) -> str:
        return (self.damage_rating or self.damage_severity_rating or "MODERATE_DAMAGE").strip()


class InspectionEvidenceUploadRequest(BaseModel):
    """Payload for uploading inspection photos or reports via base64."""
    evidence_type: str = Field("FIELD_INSPECTION_REPORT", description="Evidence type (e.g. FIELD_INSPECTION_REPORT, POST_DISASTER_PHOTO)")
    original_filename: str = Field(..., min_length=1, description="Original filename with extension (e.g. flood_mark.jpg)")
    file_content_base64: str = Field(..., description="Base64-encoded file content")
    captured_timestamp: Optional[str] = Field(None, description="Timestamp when evidence was captured")
    uploader: Optional[str] = Field(None, description="Name or role of person uploading evidence")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Technical metadata (GPS, camera info, etc.)")
