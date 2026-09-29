"""
Step 20 Test Suite: Connect Asset Verification API to Frontend.

Workflow Test:
Asset → Evidence → Verify → Database → Frontend.

Verifies:
1. Asset Creation: Registered via POST /api/assets with baseline UNVERIFIED status.
2. Evidence Upload: Multiple evidence proofs uploaded via POST /api/assets/{asset_id}/evidence.
3. Deterministic Verification: Real backend evaluation via POST /api/assets/{asset_id}/verify.
   - Status (PARTIALLY_VERIFIED -> VERIFIED)
   - Evidence Confidence (0% -> 59% -> 94%)
   - Verification Explanation (Natural language deterministic breakdown)
   - Evidence Contributions (weights: 34%, 25%, 20%, 15%)
4. Database Integrity: SQLite tables ('assets', 'asset_verifications', 'asset_evidence')
   directly verified for persistent state updates.
5. Frontend Contract: Endpoints consumed by frontend UI:
   - GET /api/assets/{asset_id}/verification
   - GET /api/assets/{asset_id}
   - GET /api/assets
"""

import sys
import sqlite3
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.config import DATABASE_PATH

client = TestClient(app)
CITIZEN_ID = "USR-006"  # Senthil Nathan (Citizen)
AUTH_HEADERS = {"Authorization": f"Bearer {CITIZEN_ID}"}


def test_full_asset_evidence_verify_database_frontend_workflow():
    """
    Test Step 20 End-to-End:
    Asset → Evidence → Verify → Database → Frontend
    """
    # ---------------------------------------------------------
    # STEP 1: ASSET REGISTRATION
    # ---------------------------------------------------------
    unique_desc = f"Commercial Cold Storage Unit #{uuid.uuid4().hex[:6]}"
    asset_payload = {
        "category": "BUSINESS_EQUIPMENT",
        "description": unique_desc,
        "documented_value": 750000.0,
        "location_address": "SIDCO Industrial Estate, Phase II, Ranipet",
        "purchase_date": "2023-11-15"
    }

    create_resp = client.post("/api/assets", json=asset_payload, headers=AUTH_HEADERS)
    assert create_resp.status_code == 201, f"Failed to create asset: {create_resp.text}"
    created_asset = create_resp.json()
    asset_id = created_asset["asset_id"]

    assert asset_id.startswith("AST-")
    assert created_asset["status"] == "UNVERIFIED"
    assert created_asset.get("verification_confidence", 0) in (0, None)

    # Verify initial verification endpoint before any evaluation
    init_vrf_resp = client.get(f"/api/assets/{asset_id}/verification", headers=AUTH_HEADERS)
    assert init_vrf_resp.status_code == 200
    init_vrf_data = init_vrf_resp.json()
    assert init_vrf_data["status"] == "UNVERIFIED"
    assert init_vrf_data["confidence"] == 0
    assert "No verifiable evidence" in init_vrf_data["explanation"] or "No evidence" in init_vrf_data["explanation"]

    # ---------------------------------------------------------
    # STEP 2: EVIDENCE UPLOAD
    # ---------------------------------------------------------
    # Evidence 1: Government Registration (Weight: 34%)
    gov_file = b"%PDF-1.4 Tamil Nadu Commercial Business Registration Patta TRD-8821"
    ev1_resp = client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("registration_deed.pdf", gov_file, "application/pdf")},
        data={"evidence_type": "GOVERNMENT_REGISTRATION"},
        headers=AUTH_HEADERS
    )
    assert ev1_resp.status_code == 201, f"Failed to upload evidence 1: {ev1_resp.text}"
    ev1_data = ev1_resp.json()
    assert ev1_data["evidence_type"] == "GOVERNMENT_REGISTRATION"

    # Evidence 2: Purchase Invoice (Weight: 25%)
    invoice_file = b"%PDF-1.4 Industrial Equipment Purchase Invoice INV-2023-4412"
    ev2_resp = client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("purchase_invoice.pdf", invoice_file, "application/pdf")},
        data={"evidence_type": "PURCHASE_INVOICE"},
        headers=AUTH_HEADERS
    )
    assert ev2_resp.status_code == 201, f"Failed to upload evidence 2: {ev2_resp.text}"
    ev2_data = ev2_resp.json()
    assert ev2_data["evidence_type"] == "PURCHASE_INVOICE"

    # ---------------------------------------------------------
    # STEP 3: VERIFY ASSET (Deterministic Rules Evaluation)
    # ---------------------------------------------------------
    verify_resp = client.post(f"/api/assets/{asset_id}/verify", json={}, headers=AUTH_HEADERS)
    assert verify_resp.status_code == 200, f"Verification failed: {verify_resp.text}"
    vrf_result = verify_resp.json()

    # Rule check:
    # GOVERNMENT_REGISTRATION (34) + PURCHASE_INVOICE (25) = 59%
    # 50 <= confidence < 80 => PARTIALLY_VERIFIED
    assert vrf_result["asset_id"] == asset_id
    assert vrf_result["status"] == "PARTIALLY_VERIFIED"
    assert vrf_result["confidence"] == 59
    assert "Registration document and purchase invoice were available." in vrf_result["explanation"]
    assert len(vrf_result["contributions"]) == 2
    assert vrf_result["is_deterministic"] is True
    assert vrf_result["engine_type"] == "DETERMINISTIC_RULES"

    # ---------------------------------------------------------
    # STEP 4: DATABASE INTEGRITY CHECK (SQLite Direct Query)
    # ---------------------------------------------------------
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 4a. Check 'assets' table
    cursor.execute("SELECT status, verification_confidence FROM assets WHERE asset_id = ?;", (asset_id,))
    asset_row = cursor.fetchone()
    assert asset_row is not None, f"Asset {asset_id} not found in database!"
    assert asset_row["status"] == "PARTIALLY_VERIFIED"
    assert asset_row["verification_confidence"] == 59

    # 4b. Check 'asset_verifications' table
    cursor.execute(
        "SELECT * FROM asset_verifications WHERE asset_id = ? ORDER BY verified_at DESC LIMIT 1;",
        (asset_id,)
    )
    vrf_row = cursor.fetchone()
    assert vrf_row is not None, f"No verification record in asset_verifications table for {asset_id}!"
    assert vrf_row["verification_status"] == "PARTIALLY_VERIFIED"
    assert vrf_row["confidence_score"] == 59
    assert vrf_row["scoring_details_json"] is not None

    # 4c. Check 'asset_evidence' table
    cursor.execute("SELECT COUNT(*) AS cnt FROM asset_evidence WHERE asset_id = ?;", (asset_id,))
    ev_count = cursor.fetchone()["cnt"]
    assert ev_count == 2

    conn.close()

    # ---------------------------------------------------------
    # STEP 5: FRONTEND API CONTRACT (What UI fetches and displays)
    # ---------------------------------------------------------
    # 5a. Verification Details (used on Asset Details Modal)
    fe_vrf_resp = client.get(f"/api/assets/{asset_id}/verification", headers=AUTH_HEADERS)
    assert fe_vrf_resp.status_code == 200
    fe_vrf = fe_vrf_resp.json()
    assert fe_vrf["status"] == "PARTIALLY_VERIFIED"
    assert fe_vrf["confidence"] == 59
    assert "Registration document and purchase invoice were available." in fe_vrf["explanation"]
    assert len(fe_vrf["contributions"]) == 2
    contrib_types = {c["type"] for c in fe_vrf["contributions"]}
    assert "GOVERNMENT_REGISTRATION" in contrib_types
    assert "PURCHASE_INVOICE" in contrib_types

    # 5b. Asset Detail endpoint (used when opening modal)
    fe_asset_resp = client.get(f"/api/assets/{asset_id}", headers=AUTH_HEADERS)
    assert fe_asset_resp.status_code == 200
    fe_asset = fe_asset_resp.json()
    assert fe_asset["status"] == "PARTIALLY_VERIFIED"
    assert fe_asset["verification_confidence"] == 59

    # 5c. Asset Registry List (main table)
    fe_list_resp = client.get("/api/assets", headers=AUTH_HEADERS)
    assert fe_list_resp.status_code == 200
    all_assets = fe_list_resp.json()
    matching_assets = [a for a in all_assets if a["asset_id"] == asset_id]
    assert len(matching_assets) == 1
    assert matching_assets[0]["status"] == "PARTIALLY_VERIFIED"
    assert matching_assets[0]["verification_confidence"] == 59


def test_transition_to_fully_verified_with_photograph_and_geolocation():
    """
    Test uploading additional photographic and geolocation proofs to reach VERIFIED status (>= 80% confidence).
    """
    # 1. Create asset
    asset_resp = client.post("/api/assets", json={
        "category": "HOUSE_PROPERTY",
        "description": "Multi-story Residential Building with Solar Array",
        "documented_value": 2400000.0,
        "location_address": "88 Gandhi Road, Vellore Central",
        "purchase_date": "2022-06-10"
    }, headers=AUTH_HEADERS)
    assert asset_resp.status_code == 201
    asset_id = asset_resp.json()["asset_id"]

    # 2. Upload 4 proofs:
    # Registration (34) + Invoice (25) + Photo (20) + Geolocation (15) = 94%
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("title.pdf", b"Title Deed", "application/pdf")},
        data={"evidence_type": "GOVERNMENT_REGISTRATION"},
        headers=AUTH_HEADERS
    )
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("bill.pdf", b"Purchase Bill", "application/pdf")},
        data={"evidence_type": "PURCHASE_INVOICE"},
        headers=AUTH_HEADERS
    )
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("photo.jpg", b"EXIF Timestamped Photo", "image/jpeg")},
        data={"evidence_type": "TIMESTAMPED_PHOTO"},
        headers=AUTH_HEADERS
    )
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("gps.json", b'{"lat": 12.9165, "lng": 79.1325}', "application/json")},
        data={"evidence_type": "GEOLOCATION"},
        headers=AUTH_HEADERS
    )

    # 3. Verify
    verify_resp = client.post(f"/api/assets/{asset_id}/verify", headers=AUTH_HEADERS)
    assert verify_resp.status_code == 200
    vrf = verify_resp.json()

    # Confidence must be 94, status must be VERIFIED
    assert vrf["status"] == "VERIFIED"
    assert vrf["confidence"] == 94
    assert "Registration document, purchase invoice, timestamped photograph, and location evidence were available." in vrf["explanation"]
    assert len(vrf["contributions"]) == 4

    # 4. Database verification
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT status, verification_confidence FROM assets WHERE asset_id = ?;", (asset_id,))
    row = cursor.fetchone()
    conn.close()

    assert row["status"] == "VERIFIED"
    assert row["verification_confidence"] == 94

    # 5. Frontend UI Verification retrieval
    fe_resp = client.get(f"/api/assets/{asset_id}/verification", headers=AUTH_HEADERS)
    assert fe_resp.status_code == 200
    fe_data = fe_resp.json()
    assert fe_data["status"] == "VERIFIED"
    assert fe_data["confidence"] == 94
    assert len(fe_data["contributions"]) == 4
