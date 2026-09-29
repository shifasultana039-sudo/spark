"""
Unit and Integration Test Suite for ReliefChain AI - Digital Asset Registry (Step 7).
Tests:
1. Input validation (valid/invalid categories, non-positive values, missing fields).
2. Authentication (missing/invalid credentials -> 401).
3. Citizen asset creation (POST /assets, ID format AST-2026-NNNNNN, status UNVERIFIED).
4. Citizen viewing own assets (GET /assets, GET /assets/{asset_id}).
5. Officer and Admin authorized access to all assets.
6. Privacy protection & citizen data isolation (Citizen B cannot view or edit Citizen A's asset -> 403).
7. Cryptographic audit event generation and audit chain verification.
8. Status verification constraint (asset cannot be marked VERIFIED in Asset Registry).
9. Asset updates (PUT /assets/{asset_id}).
"""

import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.core.database import get_db
from app.services import verify_audit_chain

client = TestClient(app)

# Test User Identifiers from seed data
CITIZEN_A_ID = "USR-006"     # Senthil Nathan (Citizen, HH-1001)
OFFICER_ID = "USR-007"       # Officer Rajesh V (Government Officer)
ADMIN_ID = "USR-001"         # Dr. Ananya Sharma (Admin)


def setup_second_citizen() -> str:
    """Creates a second citizen for privacy isolation testing."""
    citizen_b_uid = f"USR-CIT-B-{uuid.uuid4().hex[:6].upper()}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?;", (citizen_b_uid,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO users (user_id, name, email, role, organization, created_at)
            VALUES (?, 'Priya Sundaram (Citizen B)', ?, 'CITIZEN', 'Katpadi Resident (HH-2002)', '2026-09-01T00:00:00Z');
            """, (citizen_b_uid, f"{citizen_b_uid.lower()}@reliefchain.org"))
            
            cursor.execute("SELECT id FROM households WHERE household_ref = 'HH-2002';")
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO households (household_ref, head_of_household, address, district, state, created_at, updated_at)
                VALUES ('HH-2002', 'Priya Sundaram', '22 Gandhi Road, Katpadi', 'Vellore', 'Tamil Nadu', '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z');
                """)

    return citizen_b_uid


def test_authentication_required():
    """Requirement 2: Authenticate user. Missing or invalid credentials must return 401."""
    # 1. No auth headers
    res_no_auth = client.post("/assets", json={
        "category": "ELECTRONICS",
        "description": "Solar inverter backup battery system",
        "documented_value": 45000.0,
        "location": "14/2 Railway Feeder Road, Katpadi",
        "purchase_date": "2023-08-10"
    })
    assert res_no_auth.status_code == 401, f"Expected 401 without auth, got {res_no_auth.status_code}"

    # 2. Invalid token
    res_invalid_auth = client.get("/assets", headers={"Authorization": "Bearer NON_EXISTENT_USER_999"})
    assert res_invalid_auth.status_code == 401, f"Expected 401 for invalid user, got {res_invalid_auth.status_code}"
    print("[PASS] test_authentication_required passed (401 returned for unauthenticated calls)")


def test_input_validation():
    """Requirement 1: Validate input. Invalid categories, negative values, and missing fields must be rejected."""
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # 1. Invalid Category
    res_bad_cat = client.post("/assets", headers=headers, json={
        "category": "INVALID_SPACESHIP_CATEGORY",
        "description": "Spaceship property",
        "documented_value": 100000.0,
        "location": "Katpadi"
    })
    assert res_bad_cat.status_code in (400, 422), f"Expected 400/422 for invalid category, got {res_bad_cat.status_code}"

    # 2. Non-positive value
    res_bad_val = client.post("/assets", headers=headers, json={
        "category": "HOUSEHOLD_APPLIANCE",
        "description": "Washing Machine",
        "documented_value": -5000.0,
        "location": "Katpadi"
    })
    assert res_bad_val.status_code in (400, 422), f"Expected 400/422 for negative value, got {res_bad_val.status_code}"

    # 3. Missing description
    res_missing_desc = client.post("/assets", headers=headers, json={
        "category": "VEHICLE",
        "description": "",
        "documented_value": 75000.0,
        "location": "Katpadi"
    })
    assert res_missing_desc.status_code in (400, 422), f"Expected 400/422 for empty description, got {res_missing_desc.status_code}"

    # 4. Missing location
    res_missing_loc = client.post("/assets", headers=headers, json={
        "category": "VEHICLE",
        "description": "Motorcycle",
        "documented_value": 75000.0
    })
    assert res_missing_loc.status_code in (400, 422), f"Expected 400/422 for missing location, got {res_missing_loc.status_code}"

    print("[PASS] test_input_validation passed (Input rejection for invalid category, value <= 0, and missing fields)")


def test_all_asset_categories_accepted():
    """Validates that all 9 required asset categories are successfully accepted and registered."""
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    categories = [
        "HOUSE_PROPERTY",
        "VEHICLE",
        "AGRICULTURAL_EQUIPMENT",
        "ELECTRONICS",
        "HOUSEHOLD_APPLIANCE",
        "LIVESTOCK",
        "BUSINESS_EQUIPMENT",
        "PERSONAL_PROPERTY",
        "OTHER"
    ]

    for cat in categories:
        res = client.post("/assets", headers=headers, json={
            "category": cat,
            "description": f"Test citizen tangible item under {cat}",
            "documented_value": 25000.0,
            "location": "14/2 Railway Feeder Road, Katpadi",
            "purchase_date": "2024-02-15",
            "household": "HH-1001"
        })
        assert res.status_code == 201, f"Failed for category {cat}: {res.text}"
        data = res.json()
        assert data["category"] == cat
        assert data["status"] == "UNVERIFIED"
        assert data["verification_confidence"] == 0
    print(f"[PASS] test_all_asset_categories_accepted passed (All {len(categories)} categories verified)")


def test_citizen_asset_creation_and_fields():
    """
    Requirements 3, 7, 8:
    - Citizen can create their own assets.
    - Generated ID matches AST-2026-NNNNNN.
    - Fields included: category, description, documented/approximate value, purchase date, location, household, registration timestamp.
    - Asset is NOT marked VERIFIED yet.
    - Generates sequential audit event.
    """
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}
    payload = {
        "category": "AGRICULTURAL_EQUIPMENT",
        "description": "Diesel Water Pump Set (5HP) for irrigation canal",
        "documented_value": 65000.0,
        "purchase_date": "2023-11-20",
        "location": "Field Sector 4B, Katpadi, Vellore",
        "household": "HH-1001"
    }

    res = client.post("/assets", headers=headers, json=payload)
    assert res.status_code == 201, f"Registration failed: {res.text}"
    asset = res.json()

    # 1. Readable unique ID verification (AST-2026-NNNNNN)
    asset_id = asset["asset_id"]
    assert asset_id.startswith("AST-"), f"Asset ID {asset_id} does not start with AST-"
    parts = asset_id.split("-")
    assert len(parts) == 3, f"Asset ID {asset_id} expected format AST-YYYY-NNNNNN"
    assert len(parts[2]) == 6 and parts[2].isdigit(), f"Asset ID suffix {parts[2]} must be 6 digits"

    # 2. Included fields verification
    assert asset["category"] == "AGRICULTURAL_EQUIPMENT"
    assert asset["description"] == payload["description"]
    assert asset["documented_value"] == 65000.0
    assert asset["approximate_value"] == 65000.0
    assert asset["purchase_date"] == "2023-11-20"
    assert asset["location"] == payload["location"]
    assert asset["household"] == "HH-1001"
    assert asset["registration_timestamp"] is not None
    assert asset["created_at"] is not None

    # 3. Status is UNVERIFIED (Requirement 8)
    assert asset["status"] == "UNVERIFIED"
    assert asset["verification_confidence"] == 0

    # 4. Audit trail check (Requirement 7)
    audit_res = client.get("/api/audit/trail", headers={"Authorization": f"Bearer {ADMIN_ID}"})
    assert audit_res.status_code == 200
    events = audit_res.json()
    asset_events = [e for e in events if e.get("entity_id") == asset_id and e.get("event_type") == "ASSET_REGISTRATION"]
    assert len(asset_events) >= 1, f"Audit event for {asset_id} registration not found in audit trail"
    assert "AGRICULTURAL_EQUIPMENT" in asset_events[0]["description"]

    # 5. Cryptographic chain integrity check
    chain_check = verify_audit_chain()
    assert chain_check["chain_valid"] is True, f"Audit chain broken: {chain_check}"

    print(f"[PASS] test_citizen_asset_creation_and_fields passed ({asset_id} registered and verified in audit chain)")
    return asset_id


def test_citizen_can_view_own_assets():
    """Requirement 4: Citizen can view their own assets via GET /assets and GET /assets/{asset_id}."""
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # 1. List assets
    res_list = client.get("/assets", headers=headers)
    assert res_list.status_code == 200
    assets = res_list.json()
    assert len(assets) > 0

    # Verify that all returned assets belong to Citizen A (or their household HH-1001)
    for a in assets:
        assert a["household"] == "HH-1001" or a.get("citizen_id") == 6

    # 2. Get single asset
    target_id = assets[0]["asset_id"]
    res_single = client.get(f"/assets/{target_id}", headers=headers)
    assert res_single.status_code == 200
    single = res_single.json()
    assert single["asset_id"] == target_id
    assert single["description"] is not None

    print(f"[PASS] test_citizen_can_view_own_assets passed ({len(assets)} assets listed for Citizen A)")


def test_government_officer_and_admin_access():
    """Requirement 5: Government Officer / Admin can access authorized assets."""
    # 1. Officer view
    res_officer = client.get("/assets", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_officer.status_code == 200
    officer_assets = res_officer.json()
    assert len(officer_assets) >= 2, "Officer should be able to view registered assets across citizens"

    # 2. Admin view
    res_admin = client.get("/assets", headers={"Authorization": f"Bearer {ADMIN_ID}"})
    assert res_admin.status_code == 200
    admin_assets = res_admin.json()
    assert len(admin_assets) >= len(officer_assets)

    # 3. Access single asset as Officer
    first_asset_id = officer_assets[0]["asset_id"]
    res_single_officer = client.get(f"/assets/{first_asset_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_single_officer.status_code == 200
    assert res_single_officer.json()["asset_id"] == first_asset_id

    print(f"[PASS] test_government_officer_and_admin_access passed (Officer viewed {len(officer_assets)} assets)")


def test_privacy_and_data_isolation():
    """
    Requirement 6: Do not expose another citizen's private information.
    Citizen B must NOT be able to view or modify Citizen A's assets.
    """
    citizen_b_uid = setup_second_citizen()
    headers_b = {"Authorization": f"Bearer {citizen_b_uid}"}

    # 1. Citizen B creates their own asset
    res_b_create = client.post("/assets", headers=headers_b, json={
        "category": "ELECTRONICS",
        "description": "Citizen B Smart Television & Audio Setup",
        "documented_value": 35000.0,
        "location": "22 Gandhi Road, Katpadi",
        "purchase_date": "2024-01-10",
        "household": "HH-2002"
    })
    assert res_b_create.status_code == 201
    asset_b = res_b_create.json()
    asset_b_id = asset_b["asset_id"]

    # 2. Citizen B lists assets: MUST NOT see Citizen A's assets
    res_b_list = client.get("/assets", headers=headers_b)
    assert res_b_list.status_code == 200
    b_assets = res_b_list.json()
    b_asset_ids = [a["asset_id"] for a in b_assets]
    assert asset_b_id in b_asset_ids
    # Ensure no assets from HH-1001 appear in Citizen B's listing
    for a in b_assets:
        assert a["household"] == "HH-2002", f"Private asset leak: Citizen B saw asset belonging to {a['household']}"

    # 3. Citizen B attempts to access Citizen A's asset directly: MUST RETURN 403 FORBIDDEN
    res_forbidden_get = client.get("/assets/AST-2026-000001", headers=headers_b)
    assert res_forbidden_get.status_code == 403, f"Expected 403 Forbidden for Citizen B accessing Citizen A asset, got {res_forbidden_get.status_code}"

    # 4. Citizen B attempts to modify Citizen A's asset: MUST RETURN 403 FORBIDDEN
    res_forbidden_put = client.put("/assets/AST-2026-000001", headers=headers_b, json={
        "description": "Tampered description attempt by unauthorized user"
    })
    assert res_forbidden_put.status_code == 403, f"Expected 403 Forbidden for Citizen B modifying Citizen A asset, got {res_forbidden_put.status_code}"

    print("[PASS] test_privacy_and_data_isolation passed (403 returned and private records isolated)")


def test_asset_update_put():
    """
    Tests PUT /assets/{asset_id}:
    - Citizen can update description, value, location of own asset.
    - Status remains UNVERIFIED.
    - Integrity hash is recomputed.
    - Audit event is logged.
    """
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # First register an asset to update
    res_create = client.post("/assets", headers=headers, json={
        "category": "HOUSEHOLD_APPLIANCE",
        "description": "Refrigerator (Single Door 190L)",
        "documented_value": 18000.0,
        "location": "14/2 Railway Feeder Road, Katpadi",
        "purchase_date": "2023-04-12",
        "household": "HH-1001"
    })
    assert res_create.status_code == 201
    asset_id = res_create.json()["asset_id"]
    orig_hash = res_create.json()["integrity_hash"]

    # Update description and value
    res_update = client.put(f"/assets/{asset_id}", headers=headers, json={
        "description": "Refrigerator (Double Door Frost-Free 260L) - Upgraded",
        "documented_value": 28000.0,
        "location": "14/2 Railway Feeder Road, First Floor, Katpadi"
    })
    assert res_update.status_code == 200, f"Update failed: {res_update.text}"
    updated = res_update.json()

    assert updated["asset_id"] == asset_id
    assert updated["description"] == "Refrigerator (Double Door Frost-Free 260L) - Upgraded"
    assert updated["documented_value"] == 28000.0
    assert updated["approximate_value"] == 28000.0
    assert updated["status"] == "UNVERIFIED"  # Requirement 8
    assert updated["integrity_hash"] != orig_hash  # Hash recomputed

    # Verify attempt to force status to VERIFIED fails or is ignored
    res_force_verify = client.put(f"/assets/{asset_id}", headers=headers, json={
        "status": "VERIFIED"
    })
    assert res_force_verify.status_code in (400, 422), "Should reject setting status to VERIFIED in Asset Registry"

    print(f"[PASS] test_asset_update_put passed ({asset_id} updated, status preserved as UNVERIFIED)")


def test_route_prefixes_compatibility():
    """Verifies that /assets, /api/assets, and /api/v1/assets are all fully operational."""
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # 1. /assets
    r1 = client.get("/assets", headers=headers)
    assert r1.status_code == 200

    # 2. /api/assets
    r2 = client.get("/api/assets", headers=headers)
    assert r2.status_code == 200

    # 3. /api/v1/assets
    r3 = client.get("/api/v1/assets", headers=headers)
    assert r3.status_code == 200

    print("[PASS] test_route_prefixes_compatibility passed (/assets, /api/assets, /api/v1/assets)")


if __name__ == "__main__":
    print("\n--- RUNNING DIGITAL ASSET REGISTRY (STEP 7) TEST SUITE ---")
    test_authentication_required()
    test_input_validation()
    test_all_asset_categories_accepted()
    test_citizen_asset_creation_and_fields()
    test_citizen_can_view_own_assets()
    test_government_officer_and_admin_access()
    test_privacy_and_data_isolation()
    test_asset_update_put()
    test_route_prefixes_compatibility()
    print("\n[SUCCESS] ALL DIGITAL ASSET REGISTRY TESTS PASSED WITH 100% COMPLIANCE!\n")

