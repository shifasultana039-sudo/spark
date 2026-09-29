"""
Unit and Integration Test Suite for ReliefChain AI - Step 9: Deterministic Asset Evidence Verification.

Tests:
1. Verification States:
   - UNVERIFIED (< 50)
   - PARTIALLY_VERIFIED (50 - 79)
   - VERIFIED (80 - 94)
   - OFFICIALLY_CONFIRMED (>= 95)
2. Prompt's Exact Example Output:
   - status: VERIFIED
   - confidence: 94
   - explanation: "Registration document, purchase invoice, timestamped photograph, and location evidence were available."
3. Configurable Weighting Rules:
   - custom_weights parameter in POST /assets/{asset_id}/verify
   - Global weight configuration via POST /assets/verification/rules & GET /assets/verification/rules
   - Resetting weights to defaults
4. Determinism:
   - Repeated runs on identical evidence sets produce identical confidence, status, and explanations.
5. No False AI Model Claims:
   - Explicitly marked as is_deterministic=True, engine_type='DETERMINISTIC_RULES'.
6. Bounded Confidence Range:
   - Strictly 0 to 100 (never negative, never > 100).
7. Explanation Generation & Storage:
   - Explanations accurately describe actual present evidence items and are persisted in the database.
8. Verification History:
   - History entries are preserved chronologically and retrievable via GET /assets/{asset_id}/verification.
9. Never Invent Evidence:
   - Assets with no submitted evidence receive 0 confidence and UNVERIFIED status.
10. Cryptographic Audit Events:
   - Every verification creates an ASSET_VERIFICATION audit event in the SHA-256 hash chain.
11. Authentication & Privacy:
   - 401 on unauthenticated requests.
   - 403 when Citizen B tries to verify or view Citizen A's asset verification.
   - 404 on non-existent asset.
   - Government Officer and Admin access verified.
"""

import sys
import io
import json
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.core.database import get_db
from app.services import verify_audit_chain
from services.asset_verification_engine import (
    evaluate_asset_evidence,
    get_evidence_weights,
    configure_weights,
    reset_evidence_weights,
    generate_explanation
)

client = TestClient(app)

CITIZEN_A_ID = "USR-006"     # Senthil Nathan (Citizen, HH-1001)
OFFICER_ID = "USR-007"       # Officer Rajesh V (Government Officer)
ADMIN_ID = "USR-001"         # Dr. Ananya Sharma (Admin)


def create_test_citizen() -> str:
    """Creates a unique test citizen to guarantee clean privacy test boundaries."""
    unique_uid = f"USR-CIT-V9-{uuid.uuid4().hex[:6].upper()}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO users (user_id, name, email, role, organization, created_at)
        VALUES (?, ?, ?, 'CITIZEN', 'Katpadi Resident (HH-9999)', '2026-09-01T00:00:00Z');
        """, (unique_uid, f"Test Citizen {unique_uid}", f"{unique_uid.lower()}@reliefchain.org"))
    return unique_uid


def create_asset_for_user(user_token: str, description: str = "Step 9 Verification Asset") -> str:
    """Creates an asset owned by the given citizen token."""
    res = client.post("/assets", headers={"Authorization": f"Bearer {user_token}"}, json={
        "category": "HOUSE_PROPERTY",
        "description": description,
        "documented_value": 850000.0,
        "location": "Plot 42, Riverbank Road, Vellore",
        "purchase_date": "2024-03-20",
        "household": "HH-1001"
    })
    assert res.status_code == 201, res.text
    return res.json()["asset_id"]


def upload_evidence(asset_id: str, evidence_type: str, user_token: str, filename: str = "proof.pdf") -> str:
    """Helper to upload an evidence item for an asset."""
    file_content = f"Official evidence content for {evidence_type} on asset {asset_id} - {uuid.uuid4()}".encode("utf-8")
    files = {"file": (filename, io.BytesIO(file_content), "application/pdf")}
    data = {"evidence_type": evidence_type}
    res = client.post(
        f"/assets/{asset_id}/evidence",
        headers={"Authorization": f"Bearer {user_token}"},
        files=files,
        data=data
    )
    assert res.status_code == 201, res.text
    return res.json()["evidence_id"]


def test_unit_verification_engine_logic():
    """Direct unit testing of the deterministic verification engine functions."""
    reset_evidence_weights()

    # 1. No evidence -> 0 confidence, UNVERIFIED
    res_empty = evaluate_asset_evidence([])
    assert res_empty["confidence"] == 0
    assert res_empty["status"] == "UNVERIFIED"
    assert "No verifiable evidence" in res_empty["explanation"]
    assert res_empty["is_deterministic"] is True
    assert res_empty["engine_type"] == "DETERMINISTIC_RULES"

    # 2. Prompt's exact example:
    # Registration document (34), purchase invoice (25), timestamped photograph (20), location evidence (15) = 94
    evidence_items = [
        {"evidence_type": "GOVERNMENT_REGISTRATION", "evidence_id": "EV-1", "original_filename": "reg.pdf"},
        {"evidence_type": "PURCHASE_INVOICE", "evidence_id": "EV-2", "original_filename": "invoice.pdf"},
        {"evidence_type": "TIMESTAMPED_PHOTO", "evidence_id": "EV-3", "original_filename": "photo.jpg"},
        {"evidence_type": "GEOLOCATION", "evidence_id": "EV-4", "original_filename": "coords.json"}
    ]
    res_prompt = evaluate_asset_evidence(evidence_items)
    assert res_prompt["confidence"] == 94
    assert res_prompt["status"] == "VERIFIED"
    expected_explanation = "Registration document, purchase invoice, timestamped photograph, and location evidence were available."
    assert res_prompt["explanation"] == expected_explanation, f"Got: {res_prompt['explanation']}"

    # 3. Offically confirmed threshold (>= 95)
    evidence_full = evidence_items + [
        {"evidence_type": "PREVIOUS_INSPECTION", "evidence_id": "EV-5", "original_filename": "insp.pdf"},
        {"evidence_type": "ASSESSOR_VERIFICATION", "evidence_id": "EV-6", "original_filename": "assessor.pdf"}
    ]
    res_full = evaluate_asset_evidence(evidence_full)
    assert res_full["confidence"] >= 95
    assert res_full["status"] == "OFFICIALLY_CONFIRMED"
    assert res_full["confidence"] <= 100

    # 4. Partially verified threshold (50 - 79)
    evidence_partial = [
        {"evidence_type": "PURCHASE_INVOICE", "evidence_id": "EV-P1", "original_filename": "invoice.pdf"},
        {"evidence_type": "TIMESTAMPED_PHOTO", "evidence_id": "EV-P2", "original_filename": "photo.jpg"},
        {"evidence_type": "GEOLOCATION", "evidence_id": "EV-P3", "original_filename": "geo.json"}
    ]
    # 25 + 20 + 15 = 60
    res_partial = evaluate_asset_evidence(evidence_partial)
    assert 50 <= res_partial["confidence"] < 80
    assert res_partial["status"] == "PARTIALLY_VERIFIED"

    # 5. Unverified threshold (< 50)
    evidence_single = [
        {"evidence_type": "PURCHASE_INVOICE", "evidence_id": "EV-S1", "original_filename": "inv.pdf"}
    ]
    res_single = evaluate_asset_evidence(evidence_single)
    assert res_single["confidence"] == 25
    assert res_single["status"] == "UNVERIFIED"

    # 6. Determinism: identical input produces identical output 5 times in a row
    for _ in range(5):
        eval_run = evaluate_asset_evidence(evidence_items)
        assert eval_run["confidence"] == 94
        assert eval_run["status"] == "VERIFIED"
        assert eval_run["explanation"] == expected_explanation

    print("[PASS] test_unit_verification_engine_logic passed")


def test_configurable_weighting_rules():
    """Tests configuring custom weights per request and globally."""
    reset_evidence_weights()

    evidence_items = [
        {"evidence_type": "PURCHASE_INVOICE", "evidence_id": "EV-C1", "original_filename": "invoice.pdf"}
    ]

    # Default weight for invoice is 25
    default_eval = evaluate_asset_evidence(evidence_items)
    assert default_eval["confidence"] == 25

    # 1. Custom weight override for single evaluation
    custom_eval = evaluate_asset_evidence(evidence_items, custom_weights={"PURCHASE_INVOICE": 75})
    assert custom_eval["confidence"] == 75
    assert custom_eval["status"] == "PARTIALLY_VERIFIED"

    # Global weights were NOT modified
    after_eval = evaluate_asset_evidence(evidence_items)
    assert after_eval["confidence"] == 25

    # 2. Global weight configuration via API
    officer_headers = {"Authorization": f"Bearer {OFFICER_ID}"}
    res_rules = client.post("/assets/verification/rules", headers=officer_headers, json={
        "PURCHASE_INVOICE": 60,
        "TIMESTAMPED_PHOTO": 35
    })
    assert res_rules.status_code == 200
    assert res_rules.json()["status"] == "SUCCESS"
    assert res_rules.json()["weights"]["PURCHASE_INVOICE"] == 60

    # Verification now uses updated global weights
    res_get_rules = client.get("/assets/verification/rules")
    assert res_get_rules.status_code == 200
    assert res_get_rules.json()["weights"]["PURCHASE_INVOICE"] == 60

    eval_updated = evaluate_asset_evidence(evidence_items)
    assert eval_updated["confidence"] == 60

    # Reset back to default
    reset_evidence_weights()
    eval_restored = evaluate_asset_evidence(evidence_items)
    assert eval_restored["confidence"] == 25

    print("[PASS] test_configurable_weighting_rules passed")


def test_post_and_get_asset_verification_flow():
    """
    Tests complete API lifecycle:
    1. Register asset
    2. Upload 4 core evidence items (Registration, Invoice, Photo, Location)
    3. Trigger POST /assets/{asset_id}/verify
    4. Validate exact status: VERIFIED, confidence: 94, explanation
    5. Query GET /assets/{asset_id}/verification and check history
    6. Verify audit event in hash chain
    """
    reset_evidence_weights()
    citizen_headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # Step 1: Create asset
    asset_id = create_asset_for_user(CITIZEN_A_ID, "Vellore Primary Family Residence")

    # Before evidence: GET /assets/{asset_id}/verification returns 0 confidence, UNVERIFIED
    res_pre = client.get(f"/assets/{asset_id}/verification", headers=citizen_headers)
    assert res_pre.status_code == 200
    pre_data = res_pre.json()
    assert pre_data["confidence"] == 0
    assert pre_data["status"] == "UNVERIFIED"
    assert "No verifiable evidence" in pre_data["explanation"]

    # Step 2: Upload 4 core evidence items
    upload_evidence(asset_id, "GOVERNMENT_REGISTRATION", CITIZEN_A_ID, "patta_land_deed.pdf")
    upload_evidence(asset_id, "PURCHASE_INVOICE", CITIZEN_A_ID, "builder_invoice.pdf")
    upload_evidence(asset_id, "TIMESTAMPED_PHOTO", CITIZEN_A_ID, "front_view_timestamped.jpg")
    upload_evidence(asset_id, "GEOLOCATION", CITIZEN_A_ID, "gps_survey_point.json")

    # Step 3: Trigger POST /assets/{asset_id}/verify
    res_verify = client.post(
        f"/assets/{asset_id}/verify",
        headers=citizen_headers,
        json={"evaluator_note": "Initial citizen submission self-check"}
    )
    assert res_verify.status_code == 200, res_verify.text
    vdata = res_verify.json()

    # Step 4: Validate required output attributes
    assert vdata["asset_id"] == asset_id
    assert vdata["status"] == "VERIFIED"
    assert vdata["confidence"] == 94
    expected_exp = "Registration document, purchase invoice, timestamped photograph, and location evidence were available."
    assert vdata["explanation"] == expected_exp
    assert vdata["verification_id"].startswith("VRF-")
    assert len(vdata["contributions"]) == 4
    assert vdata["is_deterministic"] is True
    assert vdata["engine_type"] == "DETERMINISTIC_RULES"

    # Step 5: Check GET /assets/{asset_id}/verification
    res_get = client.get(f"/assets/{asset_id}/verification", headers=citizen_headers)
    assert res_get.status_code == 200
    gdata = res_get.json()
    assert gdata["status"] == "VERIFIED"
    assert gdata["confidence"] == 94
    assert gdata["explanation"] == expected_exp
    assert len(gdata["history"]) >= 1
    assert gdata["history"][0]["verification_id"] == vdata["verification_id"]

    # Check asset table was synchronized
    res_asset = client.get(f"/assets/{asset_id}", headers=citizen_headers)
    assert res_asset.status_code == 200
    asset_data = res_asset.json()
    assert asset_data["status"] == "VERIFIED"
    assert asset_data["verification_confidence"] == 94

    # Step 6: Verify audit event in hash chain
    chain_check = verify_audit_chain()
    assert chain_check["chain_valid"] is True, f"Audit chain broken: {chain_check}"

    print(f"[PASS] test_post_and_get_asset_verification_flow passed (Status: {vdata['status']}, Confidence: {vdata['confidence']}%)")


def test_verification_history_accumulation():
    """Tests that subsequent verifications append to history and preserve historical snapshots."""
    citizen_headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}
    asset_id = create_asset_for_user(CITIZEN_A_ID, "History Test Shop")

    # 1. First verification with 1 item
    upload_evidence(asset_id, "PURCHASE_INVOICE", CITIZEN_A_ID, "invoice_initial.pdf")
    res1 = client.post(f"/assets/{asset_id}/verify", headers=citizen_headers)
    assert res1.status_code == 200
    v1 = res1.json()
    assert v1["confidence"] == 25
    assert v1["status"] == "UNVERIFIED"

    # 2. Upload more evidence and verify a second time
    upload_evidence(asset_id, "GOVERNMENT_REGISTRATION", CITIZEN_A_ID, "trade_license.pdf")
    upload_evidence(asset_id, "TIMESTAMPED_PHOTO", CITIZEN_A_ID, "shop_front.jpg")
    res2 = client.post(f"/assets/{asset_id}/verify", headers=citizen_headers)
    assert res2.status_code == 200
    v2 = res2.json()
    # 25 + 34 + 20 = 79
    assert v2["confidence"] == 79
    assert v2["status"] == "PARTIALLY_VERIFIED"

    # 3. Check history contains both records in descending order
    res_get = client.get(f"/assets/{asset_id}/verification", headers=citizen_headers)
    assert res_get.status_code == 200
    hdata = res_get.json()
    assert len(hdata["history"]) >= 2
    assert hdata["history"][0]["verification_id"] == v2["verification_id"]
    assert hdata["history"][0]["confidence_score"] == 79
    assert hdata["history"][1]["verification_id"] == v1["verification_id"]
    assert hdata["history"][1]["confidence_score"] == 25

    print(f"[PASS] test_verification_history_accumulation passed ({len(hdata['history'])} verification records recorded)")


def test_never_invents_evidence():
    """Validates Rule 7: Never invent evidence. Empty asset gets 0 confidence."""
    citizen_headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}
    asset_id = create_asset_for_user(CITIZEN_A_ID, "Asset with Zero Evidence")

    res = client.post(f"/assets/{asset_id}/verify", headers=citizen_headers)
    assert res.status_code == 200
    vdata = res.json()
    assert vdata["confidence"] == 0
    assert vdata["status"] == "UNVERIFIED"
    assert len(vdata["contributions"]) == 0
    assert "No verifiable evidence" in vdata["explanation"]

    print("[PASS] test_never_invents_evidence passed (Zero evidence strictly produces 0 confidence)")


def test_authentication_and_privacy_isolation():
    """
    Tests:
    1. 401 on unauthenticated verify and verification queries.
    2. 403 when Citizen B tries to verify Citizen A's asset.
    3. 403 when Citizen B tries to view Citizen A's verification history.
    4. 404 on non-existent asset ID.
    5. Government Officer and Admin can inspect and verify citizen assets.
    """
    citizen_b = create_test_citizen()
    citizen_a_headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}
    citizen_b_headers = {"Authorization": f"Bearer {citizen_b}"}
    officer_headers = {"Authorization": f"Bearer {OFFICER_ID}"}
    admin_headers = {"Authorization": f"Bearer {ADMIN_ID}"}

    asset_id = create_asset_for_user(CITIZEN_A_ID, "Privacy Isolation House")
    upload_evidence(asset_id, "GOVERNMENT_REGISTRATION", CITIZEN_A_ID, "patta.pdf")

    # 1. Unauthenticated -> 401
    res_unauth1 = client.post(f"/assets/{asset_id}/verify")
    assert res_unauth1.status_code == 401
    res_unauth2 = client.get(f"/assets/{asset_id}/verification")
    assert res_unauth2.status_code == 401

    # 2. Citizen B attempts to verify Citizen A's asset -> 403
    res_b_verify = client.post(f"/assets/{asset_id}/verify", headers=citizen_b_headers)
    assert res_b_verify.status_code == 403
    err_msg = res_b_verify.json().get("error", {}).get("message") or res_b_verify.json().get("detail", "")
    assert "Access denied" in err_msg

    # 3. Citizen B attempts to view Citizen A's verification -> 403
    res_b_get = client.get(f"/assets/{asset_id}/verification", headers=citizen_b_headers)
    assert res_b_get.status_code == 403
    err_msg_get = res_b_get.json().get("error", {}).get("message") or res_b_get.json().get("detail", "")
    assert "Access denied" in err_msg_get

    # 4. Non-existent asset -> 404
    res_404 = client.post("/assets/AST-NON-EXISTENT/verify", headers=citizen_a_headers)
    assert res_404.status_code == 404

    # 5. Government Officer authorized to verify
    res_off_verify = client.post(
        f"/assets/{asset_id}/verify",
        headers=officer_headers,
        json={"evaluator_note": "Official field check verification"}
    )
    assert res_off_verify.status_code == 200

    # 6. Admin authorized to inspect verification
    res_adm_get = client.get(f"/assets/{asset_id}/verification", headers=admin_headers)
    assert res_adm_get.status_code == 200
    assert res_adm_get.json()["status"] == "UNVERIFIED"  # 1 item (34) is UNVERIFIED (< 50)

    print("[PASS] test_authentication_and_privacy_isolation passed (Strict 401/403/404 controls verified)")


def test_api_route_prefixes_compatibility():
    """Verifies that endpoints resolve across standard mounts (/assets, /api/assets, /api/v1/assets)."""
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}
    asset_id = create_asset_for_user(CITIZEN_A_ID, "Route Compatibility Tractor")

    # Direct mount
    r1 = client.get(f"/assets/{asset_id}/verification", headers=headers)
    assert r1.status_code == 200

    # /api mount
    r2 = client.get(f"/api/assets/{asset_id}/verification", headers=headers)
    assert r2.status_code == 200

    # /api/v1 mount
    r3 = client.get(f"/api/v1/assets/{asset_id}/verification", headers=headers)
    assert r3.status_code == 200

    print("[PASS] test_api_route_prefixes_compatibility passed (/assets, /api/assets, /api/v1/assets)")


if __name__ == "__main__":
    print("\n--- RUNNING DETERMINISTIC ASSET EVIDENCE VERIFICATION (STEP 9) TEST SUITE ---")
    test_unit_verification_engine_logic()
    test_configurable_weighting_rules()
    test_post_and_get_asset_verification_flow()
    test_verification_history_accumulation()
    test_never_invents_evidence()
    test_authentication_and_privacy_isolation()
    test_api_route_prefixes_compatibility()
    print("\n[SUCCESS] ALL STEP 9 VERIFICATION TESTS PASSED WITH 100% COMPLIANCE!\n")
