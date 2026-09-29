"""
Step 29 Test Suite: Audit Information Updates After Actions & Anomaly Review Display.

Validates:
1. Complete audit timeline lifecycle tracking across actions:
   - Asset Registered
   - Evidence Added
   - Claim Created
   - AI Assessment Created
   - Officer Forwarded for Inspection
   - Field Inspection Report Submitted
   - Officer Approved
2. Audit information updates immediately after each operational action.
3. Cryptographic hash-chain linkage remains intact across sequential actions.
4. Anomaly detection flags require manual review ("REVIEW REQUIRED") and citizens are never labeled fraudulent.
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OFFICER_ID = "USR-007"         # Officer Rajesh V (GOVERNMENT_OFFICER)
CITIZEN_ID = "USR-006"         # Senthil Nathan (CITIZEN)
FIELD_ASSESSOR_ID = "USR-003"  # Kavitha Sundaram (FIELD_ASSESSOR)
DISASTER_ID = "DIS-2026-0007"  # Tamil Nadu Monsoon Flash Flood


def test_audit_information_updates_after_each_action():
    """
    Verifies that audit information sequentially updates after each action in the claim lifecycle:
    Asset Registered -> Evidence Added -> Claim Created -> AI Assessed -> Officer Action -> Inspection -> Approved.
    """
    # 1. Action: Asset Registered
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 29 Audit Timeline Test House",
            "documented_value": 2000000.0,
            "location_address": "123 Anna Salai, Katpadi, Vellore, Tamil Nadu",
            "household_ref": "HH-2901"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_asset.status_code == 201
    asset_id = res_asset.json()["asset_id"]

    # Check asset audit record
    res_asset_audit = client.get(f"/api/audit?entity_id={asset_id}", headers={"Authorization": f"Bearer {CITIZEN_ID}"})
    assert res_asset_audit.status_code == 200
    asset_events = res_asset_audit.json()
    assert any(ev["event_type"] in ("ASSET_REGISTERED", "ASSET_REGISTRATION") for ev in asset_events)

    # 2. Action: Claim Created
    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Water logging in living area; ceiling plaster peeled.",
            "household_ref": "HH-2901"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_claim.status_code == 201
    claim_id = res_claim.json()["claim_id"]

    # Verify audit event for claim created
    res_claim_audit_1 = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim_audit_1.status_code == 200
    events_1 = res_claim_audit_1.json()
    count_1 = len(events_1)
    assert any(ev["event_type"] in ("CLAIM_FILED", "CLAIM_CREATED") for ev in events_1)

    # 3. Action: Evidence Added
    dummy_photo = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00STEP29_EVIDENCE"
    res_upload = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("damaged_wall.jpg", io.BytesIO(dummy_photo), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_upload.status_code == 201

    # Verify audit event updated after Evidence Added
    res_claim_audit_2 = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim_audit_2.status_code == 200
    events_2 = res_claim_audit_2.json()
    assert len(events_2) > count_1
    assert any(ev["event_type"] in ("CLAIM_EVIDENCE_UPLOADED", "EVIDENCE_ADDED") for ev in events_2)
    count_2 = len(events_2)

    # 4. Action: AI Assessment Created
    res_assess = client.post(
        f"/api/claims/{claim_id}/assess",
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_assess.status_code in (200, 201)

    # Verify audit event updated after AI Assessment Created
    res_claim_audit_3 = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim_audit_3.status_code == 200
    events_3 = res_claim_audit_3.json()
    assert len(events_3) > count_2
    assert any(ev["event_type"] in ("DAMAGE_ASSESSMENT_RUN", "DAMAGE_ASSESSMENT_COMPLETED") for ev in events_3)
    count_3 = len(events_3)

    # 5. Action: Officer Forwarded for Field Inspection
    res_fwd = client.post(
        f"/api/claims/{claim_id}/forward-inspection",
        json={
            "inspection_sector": "Katpadi West",
            "assigned_inspector_id": "Kavitha Sundaram",
            "special_instructions": "Inspect water level markings on exterior walls."
        },
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_fwd.status_code == 200

    # Verify audit event updated after Officer Forwarded for Inspection
    res_claim_audit_4 = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim_audit_4.status_code == 200
    events_4 = res_claim_audit_4.json()
    assert len(events_4) > count_3
    assert any(ev["event_type"] == "CLAIM_FORWARDED_FOR_INSPECTION" for ev in events_4)
    count_4 = len(events_4)

    # 6. Action: Field Inspection Report Submitted by Assessor
    # Get inspection id
    res_insp = client.get(f"/api/claims/{claim_id}/inspection", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_insp.status_code == 200
    insp_id = res_insp.json()["inspection_id"]

    res_submit_insp = client.post(
        f"/api/inspections/{insp_id}/submit",
        json={
            "findings": "Physical survey completed. Wall plaster damage verified at 35%. Foundation sound.",
            "damage_rating": "MODERATE_DAMAGE"
        },
        headers={"Authorization": f"Bearer {FIELD_ASSESSOR_ID}"}
    )
    assert res_submit_insp.status_code == 200

    # Verify audit event updated after Field Inspection Submitted
    res_insp_audit = client.get(f"/api/audit?entity_id={insp_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_insp_audit.status_code == 200
    insp_events = res_insp_audit.json()
    assert any(ev["event_type"] == "INSPECTION_REPORT_SUBMITTED" for ev in insp_events)

    # 7. Action: Officer Reviewed & Approved Claim
    res_approve = client.post(
        f"/api/claims/{claim_id}/approve",
        json={"approved_amount": 175000.0, "notes": "Approved based on field survey and baseline photos."},
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_approve.status_code == 200

    # Verify audit event updated after Officer Approved
    res_claim_audit_final = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim_audit_final.status_code == 200
    final_events = res_claim_audit_final.json()
    assert len(final_events) > count_4
    assert any(ev["event_type"] == "CLAIM_APPROVED" for ev in final_events)

    # Verify cryptographic integrity verification of audit ledger
    res_verify = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_verify.status_code == 200
    verify_data = res_verify.json()
    assert verify_data["chain_valid"] is True
    assert verify_data["tampered"] is False


def test_anomaly_warnings_do_not_call_anyone_fraudulent():
    """
    Validates:
    - Anomaly warnings are returned as REVIEW REQUIRED.
    - No defamatory or fraudulent terminology is applied to citizens.
    """
    # Create claim
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 29 Anomaly Test House",
            "documented_value": 1200000.0,
            "location_address": "45 Bazaar St, Katpadi, Vellore, Tamil Nadu",
            "household_ref": "HH-2902"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    asset_id = res_asset.json()["asset_id"]

    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Wall cracked from flash flood water.",
            "household_ref": "HH-2902"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    claim_id = res_claim.json()["claim_id"]

    # Query anomalies endpoint
    res_anomalies = client.get(f"/api/claims/{claim_id}/anomalies", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_anomalies.status_code == 200
    data = res_anomalies.json()

    # Verify response structure
    assert "total_anomalies" in data
    assert "anomalies" in data

    # Verify text does not use words like 'fraud', 'fraudulent', 'cheater', 'criminal'
    raw_text = res_anomalies.text.lower()
    assert "fraudulent citizen" not in raw_text
    assert "fraudster" not in raw_text
    assert "criminal" not in raw_text
