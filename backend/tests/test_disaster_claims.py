"""
Unit and Integration Test Suite for ReliefChain AI - Disaster Claims (Step 12).
Tests:
1. Asset Reference:
   - A claim must reference an existing registered asset.
   - Non-existent asset -> rejected (404 Not Found).
2. Readable ID Generation:
   - Formats IDs matching CLM-2026-010291 (CLM-YYYY-NNNNNN).
3. Required Claim Fields:
   - claim ID
   - asset ID
   - household
   - disaster event
   - pre-disaster verification state
   - claim status
   - created timestamp
4. Endpoints:
   - POST /claims
   - GET /claims
   - GET /claims/{claim_id}
5. Workflow states:
   - SUBMITTED, UNDER_ASSESSMENT, UNDER_REVIEW, MORE_EVIDENCE_REQUIRED,
     FIELD_INSPECTION_REQUIRED, APPROVED, MODIFIED, REJECTED.
   - Claims are not auto-approved or auto-rejected; initial state is SUBMITTED.
6. Audit Logging:
   - CLAIM_CREATED event recorded in SHA-256 hash chain.
   - Integrity verification passes.
7. Citizen and Officer Permissions:
   - Citizen can file claim for their own asset.
   - Citizen cannot file claim for another citizen's asset (403 Forbidden).
   - Citizen can view their own claim.
   - Citizen cannot view another citizen's claim (403 Forbidden).
   - Citizen listing is scoped to own household.
   - Officer can view and list all claims.
   - Unauthenticated requests return 401 Unauthorized.
8. Route prefix compatibility:
   - /claims, /api/claims, /api/v1/claims.
"""

import sys
import json
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.core.database import get_db
from app.services import verify_audit_chain
from app.models.entities import ClaimReviewStatus

client = TestClient(app)

CITIZEN_A_ID = "USR-006"     # Senthil Nathan (Citizen, HH-1001)
OFFICER_ID = "USR-007"       # Officer Rajesh V (Government Officer)
ADMIN_ID = "USR-001"         # Dr. Ananya Sharma (Admin)


def setup_second_citizen() -> str:
    """Ensures a distinct Citizen B exists for authorization and privacy testing."""
    citizen_b_uid = "USR-CLAIM-CIT-B"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?;", (citizen_b_uid,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO users (user_id, name, email, role, organization, created_at)
            VALUES (?, 'Kavitha Ramachandran (Citizen B)', 'kavitha.b@reliefchain.org', 'CITIZEN', 'Katpadi Resident (HH-3003)', '2026-09-01T00:00:00Z');
            """, (citizen_b_uid,))
            cursor.execute("SELECT id FROM households WHERE household_ref = 'HH-3003';")
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO households (household_ref, head_of_household, address, district, state, created_at, updated_at)
                VALUES ('HH-3003', 'Kavitha Ramachandran', '78 Palar River Road, Katpadi', 'Vellore', 'Tamil Nadu', '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z');
                """)
    return citizen_b_uid


def create_test_asset(citizen_id: str, description: str = "Test Residential House", status: str = "UNVERIFIED") -> str:
    """Helper to create a fresh test asset for a specific citizen."""
    res = client.post(
        "/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": description,
            "documented_value": 600000.0,
            "location_address": "45 Main Road, Katpadi, Vellore",
            "household_ref": "HH-1001" if citizen_id == CITIZEN_A_ID else "HH-3003"
        },
        headers={"Authorization": f"Bearer {citizen_id}"}
    )
    assert res.status_code == 201
    asset_id = res.json()["asset_id"]

    if status != "UNVERIFIED":
        # Update status directly in database for testing pre-disaster status snapshots
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE assets SET status = ?, verification_confidence = 94 WHERE asset_id = ?;", (status, asset_id))

    return asset_id


def test_asset_reference_requirement():
    """
    Requirement: A claim must reference an existing registered asset.
    Attempting to file a claim with non-existent asset ID must be rejected.
    """
    res = client.post(
        "/claims",
        json={
            "asset_id": "AST-2026-999999-NONEXISTENT",
            "damage_description": "Flood water entered the premises.",
            "disaster_id": "DIS-2026-0007"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 404, f"Expected 404 Not Found for non-existent asset, got {res.status_code}"
    error_msg = res.json().get("error", {}).get("message", "")
    assert "must reference an existing registered asset" in error_msg
    print(f"[PASS] test_asset_reference_requirement: Non-existent asset rejected -> {error_msg}")


def test_claim_creation_and_field_contents():
    """
    Requirement:
    Claim should contain:
    - claim ID
    - asset ID
    - household
    - disaster event
    - pre-disaster verification state
    - claim status
    - created timestamp
    IDs such as: CLM-2026-010291
    """
    asset_id = create_test_asset(CITIZEN_A_ID, "Verified Brick Residence", status="VERIFIED")

    res = client.post(
        "/claims",
        json={
            "asset_id": asset_id,
            "damage_description": "Severe flash flood submerged ground floor up to 4 feet; walls cracked.",
            "disaster_id": "DIS-2026-0007",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.text}"
    claim = res.json()

    # 1. Validate ID format (CLM-YYYY-NNNNNN e.g. CLM-2026-010291)
    claim_id = claim.get("claim_id") or ""
    assert claim_id.startswith("CLM-2026-"), f"Unexpected ID format: {claim_id}"
    parts = claim_id.split("-")
    assert len(parts) == 3 and parts[2].isdigit() and len(parts[2]) == 6, f"ID must have 6-digit sequence: {claim_id}"

    # 2. Validate all 7 core required fields
    assert claim["asset_id"] == asset_id
    assert claim["household"] == "HH-1001" or claim["household_ref"] == "HH-1001"
    assert claim["disaster_event"] == "DIS-2026-0007" or claim["disaster_id"] == "DIS-2026-0007"
    assert claim["pre_disaster_verification_state"] == "VERIFIED"
    assert claim["pre_disaster_verification_status"] == "VERIFIED"
    assert claim["claim_status"] == "SUBMITTED"
    assert claim["status"] == "SUBMITTED"
    assert claim["review_status"] == "SUBMITTED"
    assert bool(claim["created_timestamp"])
    assert bool(claim["created_at"])

    # 3. Validate damage description and asset metadata
    assert "flood" in claim["damage_description"].lower()
    assert claim["asset_category"] == "HOUSE_PROPERTY"

    print(f"[PASS] test_claim_creation_and_field_contents: Claim {claim_id} contains all required fields")
    return claim


def test_workflow_states_and_no_auto_decision():
    """
    Requirement:
    Claim statuses should include clear workflow states such as:
    SUBMITTED, UNDER_ASSESSMENT, UNDER_REVIEW, MORE_EVIDENCE_REQUIRED,
    FIELD_INSPECTION_REQUIRED, APPROVED, MODIFIED, REJECTED.
    Do not automatically approve or reject claims.
    """
    # 1. Verify Enum contains all 8 required workflow states
    expected_states = {
        "SUBMITTED",
        "UNDER_ASSESSMENT",
        "UNDER_REVIEW",
        "MORE_EVIDENCE_REQUIRED",
        "FIELD_INSPECTION_REQUIRED",
        "APPROVED",
        "MODIFIED",
        "REJECTED"
    }
    enum_values = {e.value for e in ClaimReviewStatus}
    for state in expected_states:
        assert state in enum_values, f"Missing expected workflow state: {state}"

    # 2. Verify that creating a claim sets initial state strictly to SUBMITTED
    asset_id = create_test_asset(CITIZEN_A_ID, "Tractor for Crop Work", status="VERIFIED")
    res = client.post(
        "/claims",
        json={
            "asset_id": asset_id,
            "damage_description": "Engine flooded during cloudburst."
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 201
    claim = res.json()
    assert claim["claim_status"] == "SUBMITTED"
    assert claim["review_status"] == "SUBMITTED"
    assert claim["officer_decision"] is None
    print("[PASS] test_workflow_states_and_no_auto_decision: Initial state is SUBMITTED, 8 states confirmed")


def test_audit_event_creation():
    """
    Requirement: Create audit events.
    Verifies that CLAIM_CREATED audit event is appended to SHA-256 tamper-evident log.
    """
    asset_id = create_test_asset(CITIZEN_A_ID, "Electronic Solar Inverter")
    res = client.post(
        "/claims",
        json={
            "asset_id": asset_id,
            "damage_description": "Power surge and water damage during cyclone."
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 201
    claim = res.json()
    claim_id = claim["claim_id"]

    # Verify audit event in database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM audit_events
        WHERE event_type = 'CLAIM_CREATED' AND entity_id = ?
        ORDER BY id DESC LIMIT 1;
        """, (claim_id,))
        event = cursor.fetchone()

    assert event is not None, f"Audit event for claim {claim_id} not found"
    assert event["event_type"] == "CLAIM_CREATED"
    assert event["entity_type"] == "CLAIM"
    assert event["entity_id"] == claim_id
    assert event["event_hash"].startswith("0x")
    assert event["previous_hash"].startswith("0x")
    assert bool(event["audit_id"])

    # Verify overall audit hash chain integrity
    report = verify_audit_chain()
    assert report["chain_valid"] is True, f"Audit chain broken: {report}"
    assert report["tampered"] is False
    print(f"[PASS] test_audit_event_creation: Audit ID {event['audit_id']} chained with SHA-256")


def test_citizen_and_officer_permissions():
    """
    Requirement: Test citizen and officer permissions.
    - Citizen can file for their own asset.
    - Citizen cannot file for another citizen's asset (403 Forbidden).
    - Citizen can view their own claim.
    - Citizen cannot view another citizen's claim (403 Forbidden).
    - Citizen listing is scoped to own household.
    - Officer can view and list all claims across all households.
    - Unauthenticated requests rejected with 401.
    """
    citizen_b = setup_second_citizen()

    # Asset A belongs to Citizen A
    asset_a = create_test_asset(CITIZEN_A_ID, "Citizen A House")
    # Asset B belongs to Citizen B
    asset_b = create_test_asset(citizen_b, "Citizen B Shop")

    # 1. Citizen B attempts to file claim for Citizen A's asset -> 403 Forbidden
    res_forbidden_create = client.post(
        "/claims",
        json={
            "asset_id": asset_a,
            "damage_description": "Unauthorized claim attempt."
        },
        headers={"Authorization": f"Bearer {citizen_b}"}
    )
    assert res_forbidden_create.status_code == 403, f"Expected 403 Forbidden, got {res_forbidden_create.status_code}"

    # 2. Citizen A files claim for Asset A -> 201 Created
    res_claim_a = client.post(
        "/claims",
        json={
            "asset_id": asset_a,
            "damage_description": "Flood damage to residential structure."
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_claim_a.status_code == 201
    claim_a_id = res_claim_a.json()["claim_id"]

    # 3. Citizen B files claim for Asset B -> 201 Created
    res_claim_b = client.post(
        "/claims",
        json={
            "asset_id": asset_b,
            "damage_description": "Commercial inventory destroyed."
        },
        headers={"Authorization": f"Bearer {citizen_b}"}
    )
    assert res_claim_b.status_code == 201
    claim_b_id = res_claim_b.json()["claim_id"]

    # 4. Citizen A retrieves own claim -> 200 OK
    res_a_own = client.get(f"/claims/{claim_a_id}", headers={"Authorization": f"Bearer {CITIZEN_A_ID}"})
    assert res_a_own.status_code == 200
    assert res_a_own.json()["claim_id"] == claim_a_id

    # 5. Citizen B attempts to retrieve Citizen A's claim -> 403 Forbidden
    res_b_view_a = client.get(f"/claims/{claim_a_id}", headers={"Authorization": f"Bearer {citizen_b}"})
    assert res_b_view_a.status_code == 403, f"Expected 403 for non-owner viewing claim, got {res_b_view_a.status_code}"

    # 6. Officer retrieves Citizen A's claim -> 200 OK
    res_officer_view_a = client.get(f"/claims/{claim_a_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_officer_view_a.status_code == 200
    assert res_officer_view_a.json()["claim_id"] == claim_a_id

    # 7. Officer retrieves Citizen B's claim -> 200 OK
    res_officer_view_b = client.get(f"/claims/{claim_b_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_officer_view_b.status_code == 200
    assert res_officer_view_b.json()["claim_id"] == claim_b_id

    # 8. Citizen A lists claims -> strictly sees only their own claims (claim_b_id must not be present)
    res_a_list = client.get("/claims", headers={"Authorization": f"Bearer {CITIZEN_A_ID}"})
    assert res_a_list.status_code == 200
    claims_seen_by_a = [c["claim_id"] for c in res_a_list.json()]
    assert claim_a_id in claims_seen_by_a
    assert claim_b_id not in claims_seen_by_a, "Citizen A saw Citizen B's private claim!"

    # 9. Officer lists claims -> sees both claim_a and claim_b
    res_officer_list = client.get("/claims", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_officer_list.status_code == 200
    claims_seen_by_officer = [c["claim_id"] for c in res_officer_list.json()]
    assert claim_a_id in claims_seen_by_officer
    assert claim_b_id in claims_seen_by_officer

    # 10. Unauthenticated access -> 401 Unauthorized
    res_unauth = client.get("/claims")
    assert res_unauth.status_code == 401
    res_unauth_get = client.get(f"/claims/{claim_a_id}")
    assert res_unauth_get.status_code == 401

    print("[PASS] test_citizen_and_officer_permissions: Complete authorization & privacy isolation verified")


def test_api_route_prefixes_compatibility():
    """Validates endpoints across root (/claims), /api/claims, and /api/v1/claims."""
    asset_id = create_test_asset(CITIZEN_A_ID, "Prefix Test Asset")

    for prefix in ["", "/api", "/api/v1"]:
        res_create = client.post(
            f"{prefix}/claims",
            json={
                "asset_id": asset_id,
                "damage_description": f"Test damage under prefix {prefix}."
            },
            headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
        )
        assert res_create.status_code == 201, f"POST failed at {prefix}/claims"
        cid = res_create.json()["claim_id"]

        res_get = client.get(f"{prefix}/claims/{cid}", headers={"Authorization": f"Bearer {CITIZEN_A_ID}"})
        assert res_get.status_code == 200, f"GET failed at {prefix}/claims/{cid}"

        res_list = client.get(f"{prefix}/claims", headers={"Authorization": f"Bearer {CITIZEN_A_ID}"})
        assert res_list.status_code == 200, f"GET list failed at {prefix}/claims"

    print("[PASS] test_api_route_prefixes_compatibility: All prefix variations operational")


if __name__ == "__main__":
    print("\n--- RUNNING DISASTER CLAIMS (STEP 12) TEST SUITE ---")
    test_asset_reference_requirement()
    test_claim_creation_and_field_contents()
    test_workflow_states_and_no_auto_decision()
    test_audit_event_creation()
    test_citizen_and_officer_permissions()
    test_api_route_prefixes_compatibility()
    print("\n[SUCCESS] ALL STEP 12 DISASTER CLAIMS TESTS PASSED WITH 100% COMPLIANCE!\n")
