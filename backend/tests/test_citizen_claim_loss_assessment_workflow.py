"""
Integration Test Suite for Step 25: Value / Loss Assessment Workflow.

Validates:
1. Citizen files claim linked to registered asset with baseline value.
2. AI damage assessment provides damage percentage.
3. Loss assessment calculation via POST /api/claims/{claim_id}/loss-estimate:
   - Original Value
   - Current/Reference Value
   - Damage Percentage
   - Indicative Loss Estimate
4. Prominent display requirement:
   - label: "AI-ASSISTED ESTIMATE"
   - disclaimer: "This is not a guaranteed compensation amount. Final compensation is subject to government verification and applicable rules."
5. Compensation approval constraint:
   - NO automatic compensation approval is created; claim review status is NOT APPROVED.
6. Persistence in SQLite `value_assessments` table.
7. Retrieval via GET /api/claims/{claim_id}/loss-estimate.
8. Sequential hash chain audit log with event LOSS_ESTIMATE_RUN.
9. Access control: Unauthorized citizen B cannot view Citizen A's loss assessment.
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

client = TestClient(app)

CITIZEN_A_ID = "USR-006"        # Senthil Nathan (HH-1001)
CITIZEN_B_ID = "USR-CLAIM-CIT-B" # Kavitha Ramachandran (HH-3003)
DISASTER_ID = "DIS-2026-0007"   # Tamil Nadu Monsoon Flash Flood


def test_complete_value_loss_assessment_workflow():
    """
    Step 25 Full Flow:
    Asset Baseline -> Claim -> Damage Assessment -> Loss Assessment -> Database -> Audit Event -> GET Retrieval
    """
    # 1. Citizen A creates a registered baseline asset
    documented_val = 850000.0
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 25 Reinforced Concrete Residence in Katpadi",
            "documented_value": documented_val,
            "location_address": "42 Lake View Road, Katpadi, Vellore",
            "household_ref": "HH-1001",
            "purchase_date": "2023-01-15T00:00:00Z"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_asset.status_code == 201, f"Failed to create asset: {res_asset.text}"
    asset_id = res_asset.json()["asset_id"]

    # 2. Citizen A files a disaster claim
    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Flood water submerged ground floor; severe structural wall cracking and electrical short.",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_claim.status_code == 201
    claim_id = res_claim.json()["claim_id"]

    # 3. Upload evidence and run AI Damage Assessment (Step 24 prerequisite)
    photo_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00STEP25_DAMAGED_HOUSE"
    res_ev = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("damaged_house.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_ev.status_code == 201

    res_assess = client.post(
        f"/api/claims/{claim_id}/assess",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_assess.status_code == 201
    assessment_data = res_assess.json()
    assessed_damage_pct = assessment_data["estimated_damage_percentage"]

    # 4. Trigger Value / Loss Assessment API (POST /api/claims/{claim_id}/loss-estimate)
    res_loss = client.post(
        f"/api/claims/{claim_id}/loss-estimate",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_loss.status_code == 200, f"Failed to calculate loss estimate: {res_loss.text}"
    loss_data = res_loss.json()

    # 5. Verify all required fields from Step 25 specification
    # - Original Value
    assert loss_data["original_documented_value"] == documented_val
    # - Current/Reference Value
    assert "reference_current_value" in loss_data
    assert isinstance(loss_data["reference_current_value"], (int, float))
    assert loss_data["reference_current_value"] > 0
    # - Damage Percentage
    assert loss_data["damage_percentage"] == assessed_damage_pct
    # - Indicative Loss Estimate
    assert "indicative_loss_estimate" in loss_data
    assert isinstance(loss_data["indicative_loss_estimate"], (int, float))
    expected_approx_loss = round(loss_data["reference_current_value"] * (assessed_damage_pct / 100.0), 2)
    assert abs(loss_data["indicative_loss_estimate"] - expected_approx_loss) < 1.0

    # 6. Clearly display "AI-ASSISTED ESTIMATE" label
    assert loss_data["label"] == "AI-ASSISTED ESTIMATE"

    # 7. Also display statutory non-guarantee disclaimer
    expected_disclaimer = (
        "This is not a guaranteed compensation amount. Final compensation is subject to government verification and applicable rules."
    )
    assert loss_data["disclaimer"] == expected_disclaimer

    # 8. Constraint: DO NOT create automatic compensation approval!
    res_claim_after = client.get(
        f"/api/claims/{claim_id}",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_claim_after.status_code == 200
    claim_status = res_claim_after.json()
    assert claim_status.get("review_status") != "APPROVED", "Loss estimate must NOT automatically approve the claim!"
    assert claim_status.get("claim_status") != "APPROVED", "Compensation must NOT be automatically approved!"

    # 9. Verify database persistence in `value_assessments` table
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT original_documented_value, reference_current_value, estimated_damage_percentage, indicative_loss_amount, approved_compensation_amount, is_ai_assisted "
            "FROM value_assessments WHERE claim_id = ?;",
            (claim_id,)
        )
        row = cursor.fetchone()
        assert row is not None, "Value assessment was not persisted in database!"
        assert row["original_documented_value"] == documented_val
        assert row["estimated_damage_percentage"] == assessed_damage_pct
        assert row["indicative_loss_amount"] == loss_data["indicative_loss_estimate"]
        assert row["approved_compensation_amount"] is None, "Compensation amount must NOT be approved automatically!"
        assert row["is_ai_assisted"] == 1

    # 10. Verify GET retrieval via GET /api/claims/{claim_id}/loss-estimate
    res_get_loss = client.get(
        f"/api/claims/{claim_id}/loss-estimate",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_get_loss.status_code == 200
    retrieved_loss = res_get_loss.json()
    assert retrieved_loss["original_documented_value"] == loss_data["original_documented_value"]
    assert retrieved_loss["reference_current_value"] == loss_data["reference_current_value"]
    assert retrieved_loss["damage_percentage"] == loss_data["damage_percentage"]
    assert retrieved_loss["indicative_loss_estimate"] == loss_data["indicative_loss_estimate"]
    assert retrieved_loss["label"] == "AI-ASSISTED ESTIMATE"
    assert retrieved_loss["disclaimer"] == expected_disclaimer

    # 11. Verify audit event
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_type, entity_type, entity_id, description "
            "FROM audit_events WHERE entity_type = 'CLAIM' AND entity_id = ? AND event_type = 'LOSS_ESTIMATE_RUN';",
            (claim_id,)
        )
        audit_row = cursor.fetchone()
        assert audit_row is not None, "LOSS_ESTIMATE_RUN audit event was not recorded!"
        assert "AI-ASSISTED ESTIMATE" in audit_row["description"]

    # 12. Privacy & Access Control: Citizen B cannot view or calculate Citizen A's loss estimate
    res_unauth_get = client.get(
        f"/api/claims/{claim_id}/loss-estimate",
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_unauth_get.status_code == 403

    res_unauth_post = client.post(
        f"/api/claims/{claim_id}/loss-estimate",
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_unauth_post.status_code == 403

    print(f"[PASS] Complete Step 25 Value/Loss Assessment flow verified successfully for claim '{claim_id}'.")
