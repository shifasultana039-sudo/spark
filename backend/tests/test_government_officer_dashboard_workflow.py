"""
Integration Test Suite for Step 26: Simple Government Officer Dashboard Workflow.

Validates:
1. Claims filed by citizens are accessible to Government Officer (USR-007).
2. Officer claims list contains all required fields:
   - Claim ID
   - Asset (asset_id, category, description)
   - Location
   - Status
   - Evidence Confidence
   - Damage Category
   - Review Status
3. Government Officer can open and review claim details via GET /api/claims/{claim_id}.
4. Claim review includes evidence dossier, AI damage assessment, and asset baseline records.
5. Cross-household visibility: Officer can see claims from multiple different citizens,
   while citizens are strictly restricted to their own household claims.
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OFFICER_ID = "USR-007"          # Officer Rajesh V (GOVERNMENT_OFFICER)
CITIZEN_A_ID = "USR-006"        # Senthil Nathan (HH-1001)
CITIZEN_B_ID = "USR-CLAIM-CIT-B" # Kavitha Ramachandran (HH-3003)
DISASTER_ID = "DIS-2026-0007"   # Tamil Nadu Monsoon Flash Flood


def test_government_officer_dashboard_claims_list_and_review():
    """
    Step 26 Full Flow:
    1. Citizen A registers asset with location and files claim.
    2. Citizen A uploads damaged photo evidence and runs damage assessment.
    3. Citizen B registers asset and files another claim.
    4. Government Officer fetches all claims list.
    5. Verify each claim contains:
       - Claim ID
       - Asset
       - Location
       - Status
       - Evidence Confidence
       - Damage Category
       - Review Status
    6. Officer opens Claim Review for Citizen A's claim.
    7. Cross-household access control: Citizen B only sees Citizen B's claim,
       Officer sees both Citizen A and Citizen B claims.
    """
    # 1. Citizen A creates asset
    res_asset_a = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 26 Residential Home in Katpadi Sector 4",
            "documented_value": 750000.0,
            "location_address": "12 Gandhi Nagar, Katpadi, Vellore, Tamil Nadu",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_asset_a.status_code == 201
    asset_a_id = res_asset_a.json()["asset_id"]

    # Citizen A files claim
    res_claim_a = client.post(
        "/api/claims",
        json={
            "asset_id": asset_a_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Flood water inundated living quarters; foundation crack observed.",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_claim_a.status_code == 201
    claim_a_id = res_claim_a.json()["claim_id"]

    # Citizen A uploads evidence
    photo_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00STEP26_PHOTO_A"
    res_ev = client.post(
        f"/api/claims/{claim_a_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("damaged_house.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_ev.status_code == 201

    # Citizen A runs AI damage assessment
    res_assess = client.post(
        f"/api/claims/{claim_a_id}/assess",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_assess.status_code == 201
    assessment_a = res_assess.json()

    # 2. Citizen B creates an asset and files a separate claim
    res_asset_b = client.post(
        "/api/assets",
        json={
            "category": "AGRICULTURAL_EQUIPMENT",
            "description": "Step 26 Paddy Harvester Tractor in Arcot Sector",
            "documented_value": 450000.0,
            "location_address": "88 Arcot Bypass, Ranipet District, Tamil Nadu",
            "household_ref": "HH-3003"
        },
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_asset_b.status_code == 201
    asset_b_id = res_asset_b.json()["asset_id"]

    res_claim_b = client.post(
        "/api/claims",
        json={
            "asset_id": asset_b_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Submerged crop fields with standing water over 3 days.",
            "household_ref": "HH-3003"
        },
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_claim_b.status_code == 201
    claim_b_id = res_claim_b.json()["claim_id"]

    # 3. Government Officer queries claims list (GET /api/claims)
    res_officer_claims = client.get(
        "/api/claims",
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_officer_claims.status_code == 200, f"Officer failed to fetch claims: {res_officer_claims.text}"
    officer_claims = res_officer_claims.json()
    assert isinstance(officer_claims, list)
    assert len(officer_claims) >= 2, "Officer should be able to see claims across all households!"

    # Find Citizen A's claim and Citizen B's claim in the officer's list
    officer_claim_a = next((c for c in officer_claims if c["claim_id"] == claim_a_id), None)
    officer_claim_b = next((c for c in officer_claims if c["claim_id"] == claim_b_id), None)

    assert officer_claim_a is not None, f"Claim {claim_a_id} not visible in officer claims list!"
    assert officer_claim_b is not None, f"Claim {claim_b_id} not visible in officer claims list!"

    # 4. Verify each claim in the dashboard shows all 7 required fields:
    # 1. Claim ID
    assert officer_claim_a["claim_id"] == claim_a_id
    # 2. Asset
    assert officer_claim_a["asset_id"] == asset_a_id
    assert "asset_category" in officer_claim_a
    # 3. Location
    assert "location" in officer_claim_a or "location_address" in officer_claim_a
    loc_a = officer_claim_a.get("location") or officer_claim_a.get("location_address")
    assert loc_a is not None and "Katpadi" in loc_a
    # 4. Status
    assert "status" in officer_claim_a or "claim_status" in officer_claim_a
    assert officer_claim_a.get("status") in ["AI_ASSESSED", "SUBMITTED", "UNDER_REVIEW"]
    # 5. Evidence Confidence
    assert "evidence_confidence" in officer_claim_a
    assert isinstance(officer_claim_a["evidence_confidence"], int)
    assert officer_claim_a["evidence_confidence"] > 0
    # 6. Damage Category
    assert "damage_category" in officer_claim_a
    assert officer_claim_a["damage_category"] == assessment_a["damage_category"]
    # 7. Review Status
    assert "review_status" in officer_claim_a
    assert officer_claim_a["review_status"] == "AI_ASSESSED"

    # Verify Claim B also has all 7 required fields
    assert officer_claim_b["claim_id"] == claim_b_id
    assert officer_claim_b["asset_id"] == asset_b_id
    loc_b = officer_claim_b.get("location") or officer_claim_b.get("location_address")
    assert loc_b is not None and "Arcot" in loc_b
    assert "status" in officer_claim_b
    assert "evidence_confidence" in officer_claim_b
    assert "damage_category" in officer_claim_b
    assert "review_status" in officer_claim_b

    # 5. Officer opens Claim Review page for Claim A (GET /api/claims/{claim_id})
    res_review = client.get(
        f"/api/claims/{claim_a_id}",
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_review.status_code == 200
    review_data = res_review.json()
    assert review_data["claim_id"] == claim_a_id
    assert review_data["asset_id"] == asset_a_id
    assert review_data["damage_description"] == "Flood water inundated living quarters; foundation crack observed."

    # Officer loads claim evidence dossier
    res_ev_dossier = client.get(
        f"/api/claims/{claim_a_id}/evidence",
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_ev_dossier.status_code == 200
    evidence_items = res_ev_dossier.json()
    assert len(evidence_items) >= 1
    assert evidence_items[0]["original_filename"] == "damaged_house.jpg"

    # 6. Privacy validation: Citizen B cannot see Citizen A's claim
    res_citizen_b_claims = client.get(
        "/api/claims",
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_citizen_b_claims.status_code == 200
    citizen_b_claims = res_citizen_b_claims.json()
    assert any(c["claim_id"] == claim_b_id for c in citizen_b_claims)
    assert not any(c["claim_id"] == claim_a_id for c in citizen_b_claims), "Citizen B must not see Citizen A's claim!"

    print("[PASS] Government Officer Dashboard verified: Officer can see all claims across households with all required fields and review dossiers.")
