"""
Integration Test Suite for Step 28: NGO / Field Assessor Inspection Workflow.

Test Scenario:
1. Government forwards claim for field inspection.
2. NGO / Field Assessor sees assigned inspection.
3. Assessor can:
   - 1. Open inspection
   - 2. Add findings
   - 3. Upload inspection evidence
   - 4. Submit inspection report
4. Do not allow NGO users to approve or reject claims (403 Forbidden).
5. Government officer can see the completed inspection report and findings.
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OFFICER_ID = "USR-007"            # Officer Rajesh V (GOVERNMENT_OFFICER)
CITIZEN_ID = "USR-006"            # Senthil Nathan (CITIZEN)
FIELD_ASSESSOR_ID = "USR-003"     # Kavitha Sundaram (FIELD_ASSESSOR)
DISASTER_ID = "DIS-2026-0007"     # Tamil Nadu Monsoon Flash Flood


def setup_fresh_claim_for_inspection():
    """Sets up an asset and a submitted claim ready for field forwarding."""
    # 1. Register asset
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 28 Katpadi Flood-Prone Residence",
            "documented_value": 1500000.0,
            "location_address": "88 Gandhi Road, Katpadi, Vellore, Tamil Nadu",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_asset.status_code == 201
    asset_id = res_asset.json()["asset_id"]

    # 2. File claim
    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Flood water inundated ground floor up to 4.5 feet; walls cracked.",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_claim.status_code == 201
    claim_id = res_claim.json()["claim_id"]

    return asset_id, claim_id


def test_complete_forward_inspect_report_workflow():
    """
    End-to-End Test:
    Government forwards claim -> NGO sees inspection -> NGO submits report -> Government can see report.
    """
    asset_id, claim_id = setup_fresh_claim_for_inspection()

    # Step 1: Government forwards claim for field inspection
    fwd_payload = {
        "inspection_sector": "Katpadi Sector 4 - Riverbank Zone",
        "assigned_inspector_id": "Kavitha Sundaram (Field Assessor)",
        "special_instructions": "Verify ground floor foundation cracks and water level gauge marks."
    }
    res_fwd = client.post(
        f"/api/claims/{claim_id}/forward-inspection",
        json=fwd_payload,
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_fwd.status_code == 200
    claim_data = res_fwd.json()
    assert claim_data["review_status"] == "FIELD_INSPECTION_PENDING"
    assert "Katpadi Sector 4" in claim_data["officer_decision"]

    # Step 2: NGO / Field Assessor sees assigned inspection
    res_inspections = client.get(
        f"/api/inspections?claim_id={claim_id}",
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_inspections.status_code == 200
    inspections_list = res_inspections.json()
    assert len(inspections_list) >= 1
    target_insp = inspections_list[0]
    inspection_id = target_insp["inspection_id"]
    assert target_insp["claim_id"] == claim_id
    assert target_insp["status"] == "PENDING"
    assert target_insp["asset_id"] == asset_id
    assert "Katpadi" in target_insp["location_address"]

    # Step 3: Assessor opens inspection
    res_detail = client.get(
        f"/api/inspections/{inspection_id}",
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["inspection_id"] == inspection_id
    assert detail["claim_id"] == claim_id

    # Step 4: Assessor adds findings
    findings_payload = {
        "findings": "On-site survey completed. Flood water reached 4.3 ft. Exterior compound wall collapsed, exterior stucco washed away, foundation intact.",
        "damage_rating": "MODERATE_DAMAGE",
        "status": "IN_PROGRESS"
    }
    res_findings = client.post(
        f"/api/inspections/{inspection_id}/findings",
        json=findings_payload,
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_findings.status_code == 200
    updated_detail = res_findings.json()
    assert "4.3 ft" in updated_detail["findings"]
    assert updated_detail["damage_rating"] == "MODERATE_DAMAGE"
    assert updated_detail["status"] == "IN_PROGRESS"

    # Step 5: Assessor uploads inspection evidence
    survey_photo_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00FIELD_SURVEY_WATERMARK"
    res_upload = client.post(
        f"/api/inspections/{inspection_id}/evidence",
        data={"evidence_type": "FIELD_INSPECTION_REPORT"},
        files={"file": ("assessor_watermark_survey.jpg", io.BytesIO(survey_photo_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_upload.status_code == 200
    upload_detail = res_upload.json()
    assert len(upload_detail["evidence_files"]) >= 1
    assert any("assessor_watermark_survey.jpg" in ev["original_filename"] for ev in upload_detail["evidence_files"])

    # Step 6: Assessor submits finalized inspection report
    report_payload = {
        "findings": "Final Physical Assessment: Verified structural settlement within acceptable thresholds. Perimeter wall total loss, interior fittings 40% damaged. Estimated restoration required.",
        "damage_rating": "MODERATE_DAMAGE",
        "inspector_notes": "Recommend clearance for repair compensation under SDRF Category B."
    }
    res_submit = client.post(
        f"/api/inspections/{inspection_id}/submit",
        json=report_payload,
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_submit.status_code == 200
    submitted_detail = res_submit.json()
    assert submitted_detail["status"] == "COMPLETED"
    assert submitted_detail["completed_at"] is not None
    assert submitted_detail["damage_rating"] == "MODERATE_DAMAGE"

    # Step 7: Government Officer can see the report
    res_gov_claim = client.get(
        f"/api/claims/{claim_id}",
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_gov_claim.status_code == 200
    gov_claim = res_gov_claim.json()
    assert gov_claim["review_status"] == "FIELD_INSPECTED"
    assert "FIELD_INSPECTION_COMPLETED" in gov_claim["officer_decision"]

    res_gov_insp = client.get(
        f"/api/claims/{claim_id}/inspection",
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_gov_insp.status_code == 200
    gov_insp = res_gov_insp.json()
    assert gov_insp is not None
    assert gov_insp["inspection_id"] == inspection_id
    assert gov_insp["status"] == "COMPLETED"
    assert "Final Physical Assessment" in gov_insp["findings"]
    assert gov_insp["damage_rating"] == "MODERATE_DAMAGE"
    assert len(gov_insp["evidence_files"]) >= 1


def test_ngo_users_forbidden_from_approving_or_rejecting_claims():
    """
    Validates:
    Do not allow NGO users to approve or reject claims.
    """
    _, claim_id = setup_fresh_claim_for_inspection()

    # 1. Field Assessor attempts to approve claim -> 403 Forbidden
    res_approve = client.post(
        f"/api/claims/{claim_id}/approve",
        json={"approved_amount": 100000.0, "notes": "NGO attempting to approve"},
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_approve.status_code == 403
    assert "Only authorized Government Officers" in res_approve.text

    # 2. Field Assessor attempts to reject claim -> 403 Forbidden
    res_reject = client.post(
        f"/api/claims/{claim_id}/reject",
        json={"reason": "Fraudulent claim", "notes": "NGO attempting to reject"},
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_reject.status_code == 403
    assert "Only authorized Government Officers" in res_reject.text
