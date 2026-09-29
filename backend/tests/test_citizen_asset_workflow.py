"""
Test Suite for Step 18: Citizen Asset Page Workflow.
Tests:
1. View assets (GET /api/assets)
2. Add an asset (POST /api/assets) -> Backend -> Database -> Asset appears in UI
3. View asset details (GET /api/assets/{asset_id})
4. See verification status (UNVERIFIED baseline, confidence, integrity hash)
"""

import sys
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.config import DATABASE_PATH

client = TestClient(app)

CITIZEN_ID = "USR-006"  # Senthil Nathan (Citizen, HH-1001)


def test_step_18_citizen_asset_full_workflow():
    """
    Test Step 18 Requirements:
    Add Asset -> Backend -> Database -> Asset appears in UI.
    Verify:
    1. View assets
    2. Add an asset
    3. View asset details
    4. See verification status
    """
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}

    # 1. View assets
    initial_resp = client.get("/api/assets", headers=headers)
    assert initial_resp.status_code == 200
    initial_assets = initial_resp.json()
    assert isinstance(initial_assets, list)

    # 2. Add an asset
    payload = {
        "category": "AGRICULTURAL_EQUIPMENT",
        "description": "Solar powered agricultural water pump and micro-irrigation controller",
        "documented_value": 145000.0,
        "location_address": "Survey No. 42/B, Katpadi Agricultural Belt, Vellore",
        "purchase_date": "2023-11-20"
    }

    create_resp = client.post("/api/assets", json=payload, headers=headers)
    assert create_resp.status_code == 201
    created_asset = create_resp.json()

    new_asset_id = created_asset["asset_id"]
    assert new_asset_id.startswith("AST-")
    assert created_asset["category"] == "AGRICULTURAL_EQUIPMENT"
    assert created_asset["status"] == "UNVERIFIED"
    assert created_asset["documented_value"] == 145000.0

    # 3. Verify directly in the Database
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assets WHERE asset_id = ?;", (new_asset_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, f"Asset {new_asset_id} was not persisted to the database!"
    assert row["asset_id"] == new_asset_id
    assert row["documented_value"] == 145000.0
    assert row["status"] == "UNVERIFIED"
    assert row["category"] == "AGRICULTURAL_EQUIPMENT"

    # 4. Verify asset appears in the UI list (GET /api/assets)
    list_resp = client.get("/api/assets", headers=headers)
    assert list_resp.status_code == 200
    updated_assets = list_resp.json()

    # The newly created asset must appear in the list
    matching = [a for a in updated_assets if a["asset_id"] == new_asset_id]
    assert len(matching) == 1, f"Newly created asset {new_asset_id} did not appear in asset list!"
    asset_in_ui = matching[0]
    assert asset_in_ui["description"] == payload["description"]
    assert asset_in_ui["status"] == "UNVERIFIED"

    # 5. View asset details (GET /api/assets/{asset_id})
    details_resp = client.get(f"/api/assets/{new_asset_id}", headers=headers)
    assert details_resp.status_code == 200
    details = details_resp.json()

    assert details["asset_id"] == new_asset_id
    assert details["category"] == "AGRICULTURAL_EQUIPMENT"
    assert details["status"] == "UNVERIFIED"
    assert details["location_address"] == payload["location_address"]
    assert details["documented_value"] == 145000.0
    assert details.get("integrity_hash") is not None
    assert details.get("current_status") == "INTACT"


def test_asset_input_validation():
    """Verify loading/error handling for invalid asset registration."""
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}

    # Missing description and negative value
    bad_payload = {
        "category": "VEHICLE",
        "description": "",
        "documented_value": -500,
        "location_address": ""
    }
    resp = client.post("/api/assets", json=bad_payload, headers=headers)
    assert resp.status_code == 422 or resp.status_code == 400


def test_view_asset_details_not_found():
    """Verify 404 error message when viewing non-existent asset."""
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}
    resp = client.get("/api/assets/AST-NON-EXISTENT", headers=headers)
    assert resp.status_code == 404
