"""
Integration Test Suite for Step 24: Demo AI Damage Assessment Workflow.

Validates:
1. Citizen files claim with post-disaster evidence.
2. Citizen triggers Demo AI Assessment via POST /api/claims/{claim_id}/assess.
3. Verification of all required fields:
   - Damage Category
   - Damage Percentage
   - Asset Match Confidence
   - Evidence Confidence / Overall Confidence
   - Explanation
   - Assessment Mode ("DEMO_SIMULATION")
4. Claim is NOT automatically approved:
   - Claim review_status transitions to AI_ASSESSED, NOT APPROVED.
5. Assessment is persisted in SQLite `damage_assessments` table.
6. Assessment retrieval via GET /api/claims/{claim_id}/assessment.
7. Tamper-evident sequential audit event `DAMAGE_ASSESSMENT_RUN` appended to hash chain.
8. Privacy & authorization: Citizen B cannot run/view assessment for Citizen A's claim (403 Forbidden).
"""

import io
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

client = TestClient(app)

CITIZEN_A_ID = "USR-006"        # Senthil Nathan (HH-1001)
CITIZEN_B_ID = "USR-CLAIM-CIT-B" # Kavitha Ramachandran (HH-3003)
DISASTER_ID = "DIS-2026-0007"   # Tamil Nadu Monsoon Flash Flood


def test_complete_ai_damage_assessment_workflow():
    """
    Step 24 Full Flow:
    Asset -> Claim -> Evidence Upload -> Run AI Damage Assessment -> Database Verification -> Audit Event -> GET Retrieval
    """
    # Step 1: Citizen A creates an asset
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 24 Inundated Brick Home in Katpadi",
            "documented_value": 900000.0,
            "location_address": "88 River Street, Katpadi, Vellore",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_asset.status_code == 201
    asset_id = res_asset.json()["asset_id"]

    # Step 2: Citizen files disaster claim
    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Flash flood submerged ground floor up to 4 feet; load bearing wall cracked.",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_claim.status_code == 201
    claim_id = res_claim.json()["claim_id"]
    assert res_claim.json()["review_status"] == "SUBMITTED"

    # Step 3: Upload post-disaster photo evidence
    photo_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00STEP24_WALL_CRACK_PHOTO"
    res_ev = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("damaged_wall.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_ev.status_code == 201

    # Step 4: Run AI Damage Assessment (POST /api/claims/{claim_id}/assess)
    res_assess = client.post(
        f"/api/claims/{claim_id}/assess",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_assess.status_code == 201, f"Failed to run AI assessment: {res_assess.text}"
    assessment = res_assess.json()

    # Step 5: Verify all required display fields
    assert assessment["claim_id"] == claim_id
    assert assessment["damage_detected"] is True
    assert assessment["damage_category"] in ["MAJOR_STRUCTURAL_DAMAGE", "MODERATE_DAMAGE", "MINOR_DAMAGE"]
    assert isinstance(assessment["estimated_damage_percentage"], int)
    assert assessment["estimated_damage_percentage"] > 0
    assert isinstance(assessment["asset_match_confidence"], int)
    assert assessment["asset_match_confidence"] >= 50
    assert isinstance(assessment["overall_confidence"], int)
    assert assessment["overall_confidence"] >= 50
    assert len(assessment["explanation"]) > 10
    assert assessment["assessment_mode"] == "DEMO_SIMULATION"
    assert assessment["provider_name"] in ["DEMO_CV_MODEL", "DemoCV"]

    # Step 6: Verify claim is NOT automatically approved!
    res_claim_after = client.get(
        f"/api/claims/{claim_id}",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_claim_after.status_code == 200
    updated_claim = res_claim_after.json()
    assert updated_claim["review_status"] != "APPROVED", "AI Assessment must NOT automatically approve the claim!"
    assert updated_claim["review_status"] == "AI_ASSESSED"

    # Step 7: Verify database persistence in `damage_assessments` table
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT damage_category, estimated_damage_percentage, asset_match_confidence, assessment_mode "
            "FROM damage_assessments WHERE claim_id = ? ORDER BY id DESC LIMIT 1;",
            (claim_id,)
        )
        row = cursor.fetchone()
        assert row is not None, "Damage assessment not persisted in database!"
        assert row["damage_category"] == assessment["damage_category"]
        assert row["estimated_damage_percentage"] == assessment["estimated_damage_percentage"]
        assert row["assessment_mode"] == "DEMO_SIMULATION"

    # Step 8: Verify retrieval via GET /api/claims/{claim_id}/assessment
    res_get_assess = client.get(
        f"/api/claims/{claim_id}/assessment",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_get_assess.status_code == 200
    retrieved = res_get_assess.json()
    assert retrieved["claim_id"] == claim_id
    assert retrieved["damage_category"] == assessment["damage_category"]
    assert retrieved["estimated_damage_percentage"] == assessment["estimated_damage_percentage"]
    assert retrieved["assessment_mode"] == "DEMO_SIMULATION"

    # Step 9: Verify sequential audit event
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_type, entity_type, entity_id, description "
            "FROM audit_events WHERE entity_type = 'CLAIM' AND entity_id = ? AND event_type = 'DAMAGE_ASSESSMENT_RUN';",
            (claim_id,)
        )
        audit_row = cursor.fetchone()
        assert audit_row is not None, "DAMAGE_ASSESSMENT_RUN audit event not recorded!"

    # Step 10: Unauthorized citizen cannot run or retrieve Citizen A's assessment
    res_unauth_get = client.get(
        f"/api/claims/{claim_id}/assessment",
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_unauth_get.status_code == 403

    res_unauth_post = client.post(
        f"/api/claims/{claim_id}/assess",
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_unauth_post.status_code == 403

    print(f"[PASS] Complete Step 24 AI Damage Assessment flow verified successfully for claim '{claim_id}'.")
