"""
Test Suite for Step 19: Evidence Upload to Asset Details.
Tests:
1. Select a file
2. Upload evidence (POST /api/assets/{asset_id}/evidence)
3. See uploaded evidence (GET /api/assets/{asset_id}/evidence)
4. See evidence type (GOVERNMENT_REGISTRATION, PURCHASE_INVOICE, etc.)
5. See upload status (PENDING / VERIFIED)
6. Verify database persistence and file storage
"""

import sys
import sqlite3
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.config import DATABASE_PATH

client = TestClient(app)
CITIZEN_ID = "USR-006"


def test_step_19_complete_evidence_upload_workflow():
    """
    Test Step 19:
    Citizen selects a file -> uploads evidence -> stored in backend & DB -> appears in UI.
    """
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}

    # 1. Fetch citizen's registered assets
    assets_resp = client.get("/api/assets", headers=headers)
    assert assets_resp.status_code == 200
    assets = assets_resp.json()
    assert len(assets) > 0
    asset_id = assets[0]["asset_id"]

    # 2. Select file and upload evidence
    file_bytes = b"%PDF-1.4 Official Tamil Nadu Revenue Department Property Patta.\nDocument Ref: TRD-2026-9901"
    files = {"file": ("patta_deed.pdf", file_bytes, "application/pdf")}
    data = {"evidence_type": "GOVERNMENT_REGISTRATION"}

    upload_resp = client.post(
        f"/api/assets/{asset_id}/evidence",
        files=files,
        data=data,
        headers=headers
    )
    assert upload_resp.status_code == 201
    ev_data = upload_resp.json()

    evidence_id = ev_data["evidence_id"]
    assert evidence_id.startswith("EV-")
    assert ev_data["asset_id"] == asset_id
    assert ev_data["evidence_type"] == "GOVERNMENT_REGISTRATION"
    assert ev_data["original_filename"] == "patta_deed.pdf"
    assert ev_data["verification_status"] == "PENDING"
    assert ev_data["sha256_hash"].startswith("0x")
    assert len(ev_data["sha256_hash"]) == 66

    # 3. Verify in SQLite Database
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM asset_evidence WHERE evidence_id = ?;", (evidence_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, f"Evidence {evidence_id} not found in database!"
    assert row["evidence_id"] == evidence_id
    assert row["asset_id"] == asset_id
    assert row["evidence_type"] == "GOVERNMENT_REGISTRATION"
    assert row["verification_status"] == "PENDING"
    assert row["original_filename"] == "patta_deed.pdf"

    # 4. Verify in Asset Evidence list (GET /api/assets/{asset_id}/evidence)
    list_resp = client.get(f"/api/assets/{asset_id}/evidence", headers=headers)
    assert list_resp.status_code == 200
    evidence_items = list_resp.json()
    assert isinstance(evidence_items, list)

    matching = [e for e in evidence_items if e["evidence_id"] == evidence_id]
    assert len(matching) == 1, f"Uploaded evidence {evidence_id} not returned in asset evidence list!"
    item = matching[0]
    assert item["evidence_type"] == "GOVERNMENT_REGISTRATION"
    assert item["original_filename"] == "patta_deed.pdf"
    assert item["verification_status"] == "PENDING"
    assert item["file_size"] > 0


def test_upload_evidence_unsupported_format_error():
    """Verify validation error status when uploading an unsupported file format."""
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}
    assets = client.get("/api/assets", headers=headers).json()
    asset_id = assets[0]["asset_id"]

    files = {"file": ("malicious.exe", b"MZ...", "application/x-msdownload")}
    data = {"evidence_type": "GOVERNMENT_REGISTRATION"}

    resp = client.post(f"/api/assets/{asset_id}/evidence", files=files, data=data, headers=headers)
    assert resp.status_code == 422 or resp.status_code == 400


def test_upload_evidence_invalid_type_error():
    """Verify error status when submitting an invalid evidence type."""
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}
    assets = client.get("/api/assets", headers=headers).json()
    asset_id = assets[0]["asset_id"]

    files = {"file": ("receipt.pdf", b"%PDF-1.4 test", "application/pdf")}
    data = {"evidence_type": "INVALID_TYPE_XYZ"}

    resp = client.post(f"/api/assets/{asset_id}/evidence", files=files, data=data, headers=headers)
    assert resp.status_code == 422 or resp.status_code == 400
