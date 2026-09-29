"""
Integration Test Suite for Step 27: Complete Government Claim Review Page Actions.

Validates:
1. Government Officer can view all 7 review sections for a claim:
   - 1. Asset Information
   - 2. Pre-disaster evidence
   - 3. Post-disaster evidence
   - 4. AI assessment
   - 5. Indicative loss estimate
   - 6. Anomaly warnings
   - 7. Audit history
2. All 5 action buttons call real backend APIs and update DB state without automatic decisions:
   - Button 1: Request More Evidence (POST /api/claims/{claim_id}/request-evidence)
   - Button 2: Modify Assessment (POST /api/claims/{claim_id}/modify-assessment)
   - Button 3: Forward for Field Inspection (POST /api/claims/{claim_id}/forward-inspection)
   - Button 4: Reject (POST /api/claims/{claim_id}/reject)
   - Button 5: Approve (POST /api/claims/{claim_id}/approve)
3. Audit history logs every decision made by the officer.
4. Role-based authorization: Citizens cannot trigger officer decision endpoints (403 Forbidden).
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OFFICER_ID = "USR-007"            # Officer Rajesh V (GOVERNMENT_OFFICER)
CITIZEN_ID = "USR-006"            # Senthil Nathan (CITIZEN)
DISASTER_ID = "DIS-2026-0007"     # Tamil Nadu Monsoon Flash Flood


def setup_claim_with_complete_dossier():
    """Helper to set up an asset, pre-disaster evidence, claim, post-disaster evidence, and AI assessment."""
    # 1. Register asset
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 27 Concrete Two-Storey Residence",
            "documented_value": 1200000.0,
            "location_address": "45 Anna Nagar Main Road, Vellore, Tamil Nadu",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_asset.status_code == 201
    asset_id = res_asset.json()["asset_id"]

    # 2. Upload pre-disaster evidence to asset
    pre_ev_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00PRE_DISASTER_BASELINE"
    res_pre_ev = client.post(
        f"/api/assets/{asset_id}/evidence",
        data={"evidence_type": "PROPERTY_DEED"},
        files={"file": ("property_deed_pre.jpg", io.BytesIO(pre_ev_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_pre_ev.status_code == 201

    # 3. Create disaster claim
    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Flood water inundated ground floor up to 4 feet; walls stained and furniture damaged.",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_claim.status_code == 201
    claim_id = res_claim.json()["claim_id"]

    # 4. Upload post-disaster evidence to claim
    post_ev_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00POST_DISASTER_DAMAGE"
    res_post_ev = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("inundated_living_room.jpg", io.BytesIO(post_ev_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_post_ev.status_code == 201

    # 5. Run AI Damage Assessment
    res_assess = client.post(
        f"/api/claims/{claim_id}/assess",
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_assess.status_code == 201

    # 6. Run Indicative Loss Assessment
    res_loss = client.post(
        f"/api/claims/{claim_id}/value-assessment",
        headers={"Authorization": f"Bearer {CITIZEN_ID}"}
    )
    assert res_loss.status_code == 201

    return asset_id, claim_id


def test_government_claim_review_page_data_loading():
    """
    Step 27: Verify Officer loads all 7 required components for Claim Review:
    1. Asset information
    2. Pre-disaster evidence
    3. Post-disaster evidence
    4. AI assessment
    5. Indicative loss estimate
    6. Anomaly warnings
    7. Audit history
    """
    asset_id, claim_id = setup_claim_with_complete_dossier()

    # 1. Asset Information
    res_asset = client.get(f"/api/assets/{asset_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_asset.status_code == 200
    asset_data = res_asset.json()
    assert asset_data["asset_id"] == asset_id
    assert asset_data["category"] == "HOUSE_PROPERTY"
    assert asset_data["documented_value"] == 1200000.0
    assert "Anna Nagar" in asset_data["location_address"]

    # 2. Pre-disaster Evidence
    res_pre = client.get(f"/api/assets/{asset_id}/evidence", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_pre.status_code == 200
    pre_evidence = res_pre.json()
    assert len(pre_evidence) >= 1
    assert pre_evidence[0]["evidence_type"] == "PROPERTY_DEED"

    # 3. Post-disaster Evidence
    res_post = client.get(f"/api/claims/{claim_id}/evidence", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_post.status_code == 200
    post_evidence = res_post.json()
    assert len(post_evidence) >= 1
    assert post_evidence[0]["original_filename"] == "inundated_living_room.jpg"

    # 4. AI Assessment
    res_ai = client.get(f"/api/claims/{claim_id}/assess", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_ai.status_code == 200
    ai_data = res_ai.json()
    assert "damage_category" in ai_data
    assert "damage_percentage" in ai_data
    assert "assessment_mode" in ai_data

    # 5. Indicative Loss Estimate
    res_loss = client.get(f"/api/claims/{claim_id}/value-assessment", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_loss.status_code == 200
    loss_data = res_loss.json()
    assert "indicative_loss_amount" in loss_data
    assert loss_data["original_value"] == 1200000.0

    # 6. Anomaly Warnings
    res_anomalies = client.get(f"/api/claims/{claim_id}/anomalies", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_anomalies.status_code == 200
    anomalies_data = res_anomalies.json()
    assert "anomalies" in anomalies_data
    assert "total_count" in anomalies_data

    # 7. Audit History
    res_audit = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert isinstance(audit_data, list)
    assert len(audit_data) >= 1


def test_button_request_more_evidence():
    """
    Test Button 1: Request More Evidence
    Calls POST /api/claims/{claim_id}/request-evidence
    """
    _, claim_id = setup_claim_with_complete_dossier()

    payload = {
        "requested_items": ["Clear structural engineer report", "Roof condition photos"],
        "officer_notes": "Please provide clearer images of the roof structure and wall cracks."
    }

    res = client.post(
        f"/api/claims/{claim_id}/request-evidence",
        json=payload,
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == claim_id
    assert data["review_status"] == "EVIDENCE_REQUESTED"
    assert data["officer_decision"] == "EVIDENCE_REQUESTED"

    # Verify claim record in DB
    res_claim = client.get(f"/api/claims/{claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim.status_code == 200
    claim_record = res_claim.json()
    assert claim_record["review_status"] == "EVIDENCE_REQUESTED"
    assert "EVIDENCE_REQUESTED" in claim_record["officer_decision"]

    # Verify Audit History has CLAIM_EVIDENCE_REQUESTED
    res_audit = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_audit.status_code == 200
    events = res_audit.json()
    req_event = next((e for e in events if e["event_type"] == "CLAIM_EVIDENCE_REQUESTED"), None)
    assert req_event is not None
    assert req_event["actor_id"] == OFFICER_ID


def test_button_modify_assessment():
    """
    Test Button 2: Modify Assessment
    Calls POST /api/claims/{claim_id}/modify-assessment
    Modifies damage percentage and category, and recalculates indicative loss.
    """
    _, claim_id = setup_claim_with_complete_dossier()

    payload = {
        "modified_damage_percentage": 65.0,
        "modified_damage_category": "SEVERE_STRUCTURAL_DAMAGE",
        "modification_rationale": "Field inspection review shows structural beam damage not visible in initial AI photo.",
        "officer_notes": "Elevated damage percentage from initial assessment to 65% based on secondary floor examination."
    }

    res = client.post(
        f"/api/claims/{claim_id}/modify-assessment",
        json=payload,
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == claim_id
    assert data["review_status"] == "ASSESSMENT_MODIFIED"
    assert data["damage_percentage"] == 65.0
    assert data["damage_category"] == "SEVERE_STRUCTURAL_DAMAGE"
    # Recalculated indicative loss: 65% of 1,200,000 = 780,000
    assert data["indicative_loss_amount"] == 780000.0

    # Verify in AI assessment endpoint
    res_ai = client.get(f"/api/claims/{claim_id}/assess", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_ai.status_code == 200
    ai_record = res_ai.json()
    assert ai_record["damage_percentage"] == 65.0
    assert ai_record["damage_category"] == "SEVERE_STRUCTURAL_DAMAGE"

    # Verify Audit History has CLAIM_ASSESSMENT_MODIFIED
    res_audit = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_audit.status_code == 200
    events = res_audit.json()
    mod_event = next((e for e in events if e["event_type"] == "CLAIM_ASSESSMENT_MODIFIED"), None)
    assert mod_event is not None
    assert mod_event["actor_id"] == OFFICER_ID


def test_button_forward_for_field_inspection():
    """
    Test Button 3: Forward for Field Inspection
    Calls POST /api/claims/{claim_id}/forward-inspection
    """
    _, claim_id = setup_claim_with_complete_dossier()

    payload = {
        "inspection_sector": "Katpadi Ward 12 Zone B",
        "assigned_inspector_id": "INS-VELLORE-04",
        "special_instructions": "Verify foundation integrity and electrical wiring flood contact."
    }

    res = client.post(
        f"/api/claims/{claim_id}/forward-inspection",
        json=payload,
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == claim_id
    assert data["review_status"] == "FIELD_INSPECTION_PENDING"
    assert "INS-VELLORE-04" in data["officer_decision"]
    assert "Katpadi Ward 12 Zone B" in data["officer_decision"]

    # Verify claim status in DB
    res_claim = client.get(f"/api/claims/{claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim.status_code == 200
    claim_record = res_claim.json()
    assert claim_record["review_status"] == "FIELD_INSPECTION_PENDING"

    # Verify Audit History has CLAIM_FORWARDED_FOR_INSPECTION
    res_audit = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_audit.status_code == 200
    events = res_audit.json()
    insp_event = next((e for e in events if e["event_type"] == "CLAIM_FORWARDED_FOR_INSPECTION"), None)
    assert insp_event is not None
    assert insp_event["actor_id"] == OFFICER_ID


def test_button_reject():
    """
    Test Button 4: Reject
    Calls POST /api/claims/{claim_id}/reject
    """
    _, claim_id = setup_claim_with_complete_dossier()

    payload = {
        "rejection_reason": "Asset damage occurred prior to disaster declaration date according to telemetry records.",
        "officer_notes": "Photographs show weathering indicative of pre-existing decay, not flash flood impact."
    }

    res = client.post(
        f"/api/claims/{claim_id}/reject",
        json=payload,
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == claim_id
    assert data["review_status"] == "REJECTED"
    assert "REJECTED" in data["officer_decision"]

    # Verify claim status in DB
    res_claim = client.get(f"/api/claims/{claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim.status_code == 200
    claim_record = res_claim.json()
    assert claim_record["review_status"] == "REJECTED"

    # Verify Audit History has CLAIM_REJECTED
    res_audit = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_audit.status_code == 200
    events = res_audit.json()
    rej_event = next((e for e in events if e["event_type"] == "CLAIM_REJECTED"), None)
    assert rej_event is not None
    assert rej_event["actor_id"] == OFFICER_ID


def test_button_approve():
    """
    Test Button 5: Approve
    Calls POST /api/claims/{claim_id}/approve
    Records approved compensation amount and final notes.
    """
    _, claim_id = setup_claim_with_complete_dossier()

    payload = {
        "approved_compensation_amount": 540000.0,
        "officer_notes": "Approved in accordance with State SDRF Grade 2 Flood Relief Schedule."
    }

    res = client.post(
        f"/api/claims/{claim_id}/approve",
        json=payload,
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == claim_id
    assert data["review_status"] == "APPROVED"
    assert data["approved_compensation_amount"] == 540000.0

    # Verify claim status in DB
    res_claim = client.get(f"/api/claims/{claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_claim.status_code == 200
    claim_record = res_claim.json()
    assert claim_record["review_status"] == "APPROVED"
    assert claim_record["status"] == "APPROVED"

    # Verify Audit History has CLAIM_APPROVED
    res_audit = client.get(f"/api/audit?entity_id={claim_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_audit.status_code == 200
    events = res_audit.json()
    appr_event = next((e for e in events if e["event_type"] == "CLAIM_APPROVED"), None)
    assert appr_event is not None
    assert appr_event["actor_id"] == OFFICER_ID


def test_officer_action_authorization_protection():
    """
    Ensures that citizens cannot trigger any of the 5 review decision actions.
    Must return 403 Forbidden.
    """
    _, claim_id = setup_claim_with_complete_dossier()

    citizen_headers = {"Authorization": f"Bearer {CITIZEN_ID}"}

    # Attempt Approve
    res_appr = client.post(
        f"/api/claims/{claim_id}/approve",
        json={"approved_compensation_amount": 10000.0, "officer_notes": "Malicious attempt"},
        headers=citizen_headers
    )
    assert res_appr.status_code == 403

    # Attempt Request Evidence
    res_req = client.post(
        f"/api/claims/{claim_id}/request-evidence",
        json={"requested_items": ["Doc 1"], "officer_notes": "Malicious attempt"},
        headers=citizen_headers
    )
    assert res_req.status_code == 403

    # Attempt Modify Assessment
    res_mod = client.post(
        f"/api/claims/{claim_id}/modify-assessment",
        json={"modified_damage_percentage": 90.0, "modified_damage_category": "TOTAL_COLLAPSE", "modification_rationale": "Fraud"},
        headers=citizen_headers
    )
    assert res_mod.status_code == 403

    # Attempt Reject
    res_rej = client.post(
        f"/api/claims/{claim_id}/reject",
        json={"rejection_reason": "Fraudulent action"},
        headers=citizen_headers
    )
    assert res_rej.status_code == 403

    # Attempt Forward Inspection
    res_insp = client.post(
        f"/api/claims/{claim_id}/forward-inspection",
        json={"inspection_sector": "Sector X"},
        headers=citizen_headers
    )
    assert res_insp.status_code == 403
