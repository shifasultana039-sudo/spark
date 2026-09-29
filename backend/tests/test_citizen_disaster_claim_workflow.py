"""
Step 22 Test Suite: Citizen Disaster Claim Page Workflow.

Workflow Test:
Asset → Create Claim → Database → Claim appears.

Verifies:
1. Citizen has/creates a registered asset.
2. Citizen selects asset and disaster event (e.g. DIS-2026-0007).
3. Citizen creates claim via POST /api/claims.
   - Snapshots pre-disaster verification baseline.
   - Sets initial workflow review_status to SUBMITTED.
   - Does NOT calculate compensation on frontend/client.
4. SQLite Database persistence in 'disaster_claims' table.
5. Tamper-evident sequential audit event recorded in 'audit_events'.
6. Claim appears in UI queries:
   - GET /api/claims (lists the citizen's filed claims)
   - GET /api/claims/{claim_id} (retrieves full claim details)
   - GET /api/disasters (lists active declared disasters for selector)
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
from app.services import verify_audit_chain

client = TestClient(app)
CITIZEN_ID = "USR-006"  # Senthil Nathan (Citizen)
AUTH_HEADERS = {"Authorization": f"Bearer {CITIZEN_ID}"}


def test_asset_to_create_claim_to_database_to_claims_list():
    """
    Test Step 22 End-to-End Workflow:
    Asset → Create Claim → Database → Claim appears.
    """
    # -------------------------------------------------------------
    # 1. ASSET: Citizen registers an asset
    # -------------------------------------------------------------
    unique_desc = f"Single-family Dwelling with Tile Roof #{uuid.uuid4().hex[:6]}"
    asset_resp = client.post("/api/assets", json={
        "category": "HOUSE_PROPERTY",
        "description": unique_desc,
        "documented_value": 650000.0,
        "location_address": "22 Riverbank Feeder Road, Katpadi, Vellore",
        "purchase_date": "2023-08-20"
    }, headers=AUTH_HEADERS)
    assert asset_resp.status_code == 201, f"Failed to register asset: {asset_resp.text}"
    asset = asset_resp.json()
    asset_id = asset["asset_id"]
    initial_status = asset["status"]

    # -------------------------------------------------------------
    # 2. DISASTER SELECTION: Verify declared disasters endpoint
    # -------------------------------------------------------------
    disasters_resp = client.get("/api/disasters", headers=AUTH_HEADERS)
    assert disasters_resp.status_code == 200
    disasters = disasters_resp.json()
    assert len(disasters) > 0
    disaster_event_id = disasters[0]["disaster_code"]
    assert "DIS-" in disaster_event_id

    # -------------------------------------------------------------
    # 3. CREATE CLAIM: Citizen selects asset + disaster event
    # -------------------------------------------------------------
    damage_desc = "Flood water inundated living areas up to 1.2m depth, cracked exterior boundary wall, electrical wiring compromised."
    claim_payload = {
        "asset_id": asset_id,
        "disaster_id": disaster_event_id,
        "damage_description": damage_desc,
        "household_ref": "HH-1001"
    }

    create_claim_resp = client.post("/api/claims", json=claim_payload, headers=AUTH_HEADERS)
    assert create_claim_resp.status_code == 201, f"Failed to create claim: {create_claim_resp.text}"
    claim = create_claim_resp.json()

    # Validate claim properties
    claim_id = claim["claim_id"]
    assert claim_id.startswith("CLM-2026-")
    assert claim["asset_id"] == asset_id
    assert claim["disaster_id"] == disaster_event_id
    assert claim["damage_description"] == damage_desc
    assert claim["review_status"] == "SUBMITTED"
    assert claim["pre_disaster_verification_status"] == initial_status

    # Validate that no frontend compensation was calculated or automatically approved
    assert claim.get("calculated_compensation") is None or "calculated_compensation" not in claim
    assert claim.get("approved_compensation") is None or "approved_compensation" not in claim
    assert claim["review_status"] != "APPROVED"
    assert claim["review_status"] != "REJECTED"

    # -------------------------------------------------------------
    # 4. DATABASE: Verify direct SQLite persistence
    # -------------------------------------------------------------
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 4a. Check disaster_claims table
    cursor.execute("SELECT * FROM disaster_claims WHERE claim_id = ?;", (claim_id,))
    claim_row = cursor.fetchone()
    assert claim_row is not None, f"Claim {claim_id} not found in disaster_claims table!"
    assert claim_row["asset_id"] == asset_id
    assert claim_row["disaster_id"] == disaster_event_id
    assert claim_row["review_status"] == "SUBMITTED"
    assert claim_row["pre_disaster_verification_status"] == initial_status
    assert claim_row["damage_description"] == damage_desc

    # 4b. Check audit_events table
    cursor.execute(
        "SELECT * FROM audit_events WHERE entity_type = 'CLAIM' AND entity_id = ?;",
        (claim_id,)
    )
    audit_row = cursor.fetchone()
    assert audit_row is not None, f"Audit event for claim {claim_id} not recorded!"
    assert audit_row["event_type"] == "CLAIM_CREATED"
    assert audit_row["actor"] is not None

    conn.close()

    # -------------------------------------------------------------
    # 5. CLAIM APPEARS: Verify frontend endpoints
    # -------------------------------------------------------------
    # 5a. Claim appears in citizen's claims list (GET /api/claims)
    list_resp = client.get("/api/claims", headers=AUTH_HEADERS)
    assert list_resp.status_code == 200
    all_claims = list_resp.json()
    matching_claims = [c for c in all_claims if c["claim_id"] == claim_id]
    assert len(matching_claims) == 1, f"Claim {claim_id} does not appear in GET /api/claims!"
    retrieved_claim = matching_claims[0]
    assert retrieved_claim["asset_id"] == asset_id
    assert retrieved_claim["review_status"] == "SUBMITTED"

    # 5b. Open claim details (GET /api/claims/{claim_id})
    detail_resp = client.get(f"/api/claims/{claim_id}", headers=AUTH_HEADERS)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["claim_id"] == claim_id
    assert detail["asset_id"] == asset_id
    assert detail["disaster_id"] == disaster_event_id
    assert detail["damage_description"] == damage_desc
    assert detail["review_status"] == "SUBMITTED"
    assert detail["created_at"] is not None


def test_claim_with_verified_pre_disaster_baseline():
    """
    Test that filing a claim against a verified asset captures the VERIFIED pre-disaster status.
    """
    # 1. Create and verify asset
    asset_resp = client.post("/api/assets", json={
        "category": "VEHICLE",
        "description": "Commercial Delivery Van with Cold Storage Unit",
        "documented_value": 480000.0,
        "location_address": "SIDCO Estate, Ranipet",
        "purchase_date": "2023-01-15"
    }, headers=AUTH_HEADERS)
    asset_id = asset_resp.json()["asset_id"]

    # Upload proofs
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("reg.pdf", b"Reg", "application/pdf")},
        data={"evidence_type": "GOVERNMENT_REGISTRATION"},
        headers=AUTH_HEADERS
    )
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("inv.pdf", b"Inv", "application/pdf")},
        data={"evidence_type": "PURCHASE_INVOICE"},
        headers=AUTH_HEADERS
    )
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("photo.jpg", b"Photo", "image/jpeg")},
        data={"evidence_type": "TIMESTAMPED_PHOTO"},
        headers=AUTH_HEADERS
    )
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("gps.json", b"GPS", "application/json")},
        data={"evidence_type": "GEOLOCATION"},
        headers=AUTH_HEADERS
    )

    # Verify asset
    vrf = client.post(f"/api/assets/{asset_id}/verify", headers=AUTH_HEADERS).json()
    assert vrf["status"] == "VERIFIED"

    # 2. File disaster claim
    claim_resp = client.post("/api/claims", json={
        "asset_id": asset_id,
        "disaster_id": "DIS-2026-0007",
        "damage_description": "Engine and cooling compressor flooded and seized during storm surge."
    }, headers=AUTH_HEADERS)
    assert claim_resp.status_code == 201
    claim_data = claim_resp.json()

    # Pre-disaster baseline status MUST be VERIFIED
    assert claim_data["pre_disaster_verification_status"] == "VERIFIED"
    assert claim_data["review_status"] == "SUBMITTED"
