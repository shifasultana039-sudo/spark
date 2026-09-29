"""
Unit and Integration Test Suite for ReliefChain AI - Evidence Management (Step 8).
Tests:
1. File upload via multipart/form-data and application/json (base64).
2. All 10 required evidence types:
   - PURCHASE_INVOICE
   - GOVERNMENT_REGISTRATION
   - WARRANTY
   - TIMESTAMPED_PHOTO
   - GEOLOCATION
   - PREVIOUS_INSPECTION
   - ASSESSOR_VERIFICATION
   - POST_DISASTER_PHOTO
   - POST_DISASTER_VIDEO
   - FIELD_INSPECTION_REPORT
3. Cryptographic SHA-256 calculation and verification.
4. Input validation (invalid file extensions, 0 bytes file, invalid evidence type).
5. Association with valid asset and 404 for non-existent asset.
6. User authentication (401 on missing credentials).
7. Privacy & Authorization (Citizen B cannot upload, view, or download Citizen A's evidence -> 403).
8. Government Officer / Admin authorized access.
9. Audit trail verification (sequential hash chain integrity).
10. Pre-verification state (status is PENDING, score_contribution is 0 - no AI verification yet).
11. Secure file retrieval (authenticated download endpoint, no unauthenticated public exposure).
"""

import sys
import io
import json
import base64
import hashlib
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

CITIZEN_A_ID = "USR-006"     # Senthil Nathan (Citizen, HH-1001)
OFFICER_ID = "USR-007"       # Officer Rajesh V (Government Officer)
ADMIN_ID = "USR-001"         # Dr. Ananya Sharma (Admin)


def get_or_create_test_asset() -> str:
    """Ensures an asset exists for Citizen A to attach evidence to."""
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}
    res = client.post("/assets", headers=headers, json={
        "category": "HOUSE_PROPERTY",
        "description": "Step 8 Test House in Katpadi",
        "documented_value": 1500000.0,
        "location": "Sector 4A, Katpadi, Vellore",
        "purchase_date": "2023-01-15",
        "household": "HH-1001"
    })
    assert res.status_code == 201
    return res.json()["asset_id"]


def setup_second_citizen() -> str:
    """Creates a second citizen for privacy isolation testing."""
    citizen_b_uid = f"USR-CIT-EVD-{uuid.uuid4().hex[:6].upper()}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?;", (citizen_b_uid,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO users (user_id, name, email, role, organization, created_at)
            VALUES (?, 'Anand Kumar (Citizen B)', ?, 'CITIZEN', 'Katpadi Resident (HH-3003)', '2026-09-01T00:00:00Z');
            """, (citizen_b_uid, f"{citizen_b_uid.lower()}@reliefchain.org"))
            
            cursor.execute("SELECT id FROM households WHERE household_ref = 'HH-3003';")
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO households (household_ref, head_of_household, address, district, state, created_at, updated_at)
                VALUES ('HH-3003', 'Anand Kumar', '55 Anna Salai, Katpadi', 'Vellore', 'Tamil Nadu', '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z');
                """)
    return citizen_b_uid


def test_authentication_required():
    """Unauthenticated calls must return 401."""
    asset_id = get_or_create_test_asset()

    # POST evidence without auth
    res_post = client.post(f"/assets/{asset_id}/evidence", files={
        "file": ("invoice.pdf", b"%PDF-1.4 test content", "application/pdf")
    }, data={"evidence_type": "PURCHASE_INVOICE"})
    assert res_post.status_code == 401

    # GET evidence without auth
    res_get = client.get(f"/assets/{asset_id}/evidence")
    assert res_get.status_code == 401

    # GET single evidence without auth
    res_single = client.get("/evidence/EV-001")
    assert res_single.status_code == 401

    print("[PASS] test_authentication_required passed (401 returned on unauthenticated access)")


def test_file_validation_error_cases():
    """Validates file type and size constraints."""
    asset_id = get_or_create_test_asset()
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # 1. Dangerous / executable file rejected
    res_bad_ext = client.post(f"/assets/{asset_id}/evidence", headers=headers, files={
        "file": ("malicious_payload.exe", b"MZ\x90\x00executable", "application/x-msdownload")
    }, data={"evidence_type": "PURCHASE_INVOICE"})
    assert res_bad_ext.status_code in (400, 422), f"Expected 400/422 for .exe, got {res_bad_ext.status_code}"

    # 2. Empty file (0 bytes) rejected
    res_empty = client.post(f"/assets/{asset_id}/evidence", headers=headers, files={
        "file": ("empty_file.pdf", b"", "application/pdf")
    }, data={"evidence_type": "PURCHASE_INVOICE"})
    assert res_empty.status_code in (400, 422), f"Expected 400/422 for 0 bytes file, got {res_empty.status_code}"

    # 3. Invalid evidence type rejected
    res_bad_type = client.post(f"/assets/{asset_id}/evidence", headers=headers, files={
        "file": ("doc.pdf", b"%PDF-1.4 valid content", "application/pdf")
    }, data={"evidence_type": "INVALID_UNKNOWN_EVIDENCE"})
    assert res_bad_type.status_code in (400, 422), f"Expected 400/422 for bad evidence type, got {res_bad_type.status_code}"

    # 4. Upload to non-existent asset rejected with 404
    res_bad_asset = client.post("/assets/AST-NON-EXISTENT-999999/evidence", headers=headers, files={
        "file": ("doc.pdf", b"%PDF-1.4 valid content", "application/pdf")
    }, data={"evidence_type": "PURCHASE_INVOICE"})
    assert res_bad_asset.status_code == 404, f"Expected 404 for non-existent asset, got {res_bad_asset.status_code}"

    print("[PASS] test_file_validation_error_cases passed (Invalid extension, empty file, invalid type, and 404 handled)")


def test_all_10_evidence_types_accepted():
    """Verifies that all 10 required evidence types can be uploaded and stored."""
    asset_id = get_or_create_test_asset()
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    evidence_types = [
        ("PURCHASE_INVOICE", "invoice.pdf", b"%PDF-1.4 Purchase Bill Content", "application/pdf"),
        ("GOVERNMENT_REGISTRATION", "patta_deed.pdf", b"%PDF-1.4 Government Patta Registration", "application/pdf"),
        ("WARRANTY", "warranty_card.pdf", b"%PDF-1.4 5-Year Structural Warranty", "application/pdf"),
        ("TIMESTAMPED_PHOTO", "front_elevation.jpg", b"\xFF\xD8\xFF\xE0JPEG_PHOTO_DATA", "image/jpeg"),
        ("GEOLOCATION", "boundary_survey.geojson", b'{"type": "Point", "coordinates": [79.1417, 12.9806]}', "application/geo+json"),
        ("PREVIOUS_INSPECTION", "inspection_2024.pdf", b"%PDF-1.4 Annual Municipal Tax Receipt", "application/pdf"),
        ("ASSESSOR_VERIFICATION", "engineer_stamp.pdf", b"%PDF-1.4 Structural Engineer Signed Report", "application/pdf"),
        ("POST_DISASTER_PHOTO", "flood_damage_room.jpg", b"\xFF\xD8\xFF\xE0POST_DISASTER_PHOTO", "image/jpeg"),
        ("POST_DISASTER_VIDEO", "water_ingress_clip.mp4", b"\x00\x00\x00\x18ftypmp42POST_DISASTER_VIDEO", "video/mp4"),
        ("FIELD_INSPECTION_REPORT", "officer_field_notes.pdf", b"%PDF-1.4 Revenue Inspector Survey Notes", "application/pdf")
    ]

    for etype, fname, raw_bytes, mime in evidence_types:
        expected_hash = "0x" + hashlib.sha256(raw_bytes).hexdigest()
        
        res = client.post(
            f"/assets/{asset_id}/evidence",
            headers=headers,
            files={"file": (fname, raw_bytes, mime)},
            data={
                "evidence_type": etype,
                "captured_timestamp": "2026-09-28T10:00:00Z",
                "latitude": "12.9806",
                "longitude": "79.1417"
            }
        )
        assert res.status_code == 201, f"Failed uploading {etype}: {res.text}"
        data = res.json()

        # Verify attributes
        assert data["evidence_type"] == etype
        assert data["original_filename"] == fname
        assert data["sha256_hash"] == expected_hash
        assert data["file_size"] == len(raw_bytes)
        assert data["verification_status"] == "PENDING"  # Requirement: Do not implement AI verification yet
        assert data["score_contribution"] == 0
        assert data["asset_id"] == asset_id
        assert data["evidence_id"].startswith("EV-")
        assert not data["file_url"].startswith("/api/storage/uploads/"), "Private file must not expose public upload URL"

    print(f"[PASS] test_all_10_evidence_types_accepted passed (All {len(evidence_types)} evidence types uploaded & hashed)")


def test_json_base64_upload_and_sha256_generation():
    """Tests alternative upload method via application/json base64 and verifies exact hash generation."""
    asset_id = get_or_create_test_asset()
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    sample_content = b"Official Tamil Nadu Revenue Department Ownership Verification Document 2026"
    expected_hash = "0x" + hashlib.sha256(sample_content).hexdigest()
    b64_content = base64.b64encode(sample_content).decode("utf-8")

    res = client.post(f"/assets/{asset_id}/evidence", headers=headers, json={
        "evidence_type": "GOVERNMENT_REGISTRATION",
        "original_filename": "official_patta.pdf",
        "file_content_base64": b64_content,
        "captured_timestamp": "2026-08-15T12:00:00Z",
        "latitude": 12.9806,
        "longitude": 79.1417,
        "metadata": {"doc_number": "PATTA-VEL-9921", "registrar_office": "Katpadi"}
    })
    assert res.status_code == 201, f"JSON upload failed: {res.text}"
    ev = res.json()

    assert ev["sha256_hash"] == expected_hash
    assert ev["file_size"] == len(sample_content)
    assert ev["verification_status"] == "PENDING"
    assert ev["evidence_id"].startswith("EV-")

    # Retrieve single evidence via GET /evidence/{evidence_id}
    res_single = client.get(f"/evidence/{ev['evidence_id']}", headers=headers)
    assert res_single.status_code == 200
    single_data = res_single.json()
    assert single_data["evidence_id"] == ev["evidence_id"]
    assert single_data["sha256_hash"] == expected_hash

    print(f"[PASS] test_json_base64_upload_and_sha256_generation passed (Hash generated: {expected_hash[:18]}...)")
    return ev["evidence_id"]


def test_audit_event_generation():
    """Requirement 6: Create audit event on evidence upload and verify hash chain."""
    asset_id = get_or_create_test_asset()
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    content = b"Proof of Purchase Receipt dated 2025"
    res = client.post(f"/assets/{asset_id}/evidence", headers=headers, files={
        "file": ("purchase_receipt.pdf", content, "application/pdf")
    }, data={"evidence_type": "PURCHASE_INVOICE"})
    assert res.status_code == 201
    evidence_id = res.json()["evidence_id"]

    # Verify audit event in audit trail
    res_audit = client.get("/api/audit/trail", headers={"Authorization": f"Bearer {ADMIN_ID}"})
    assert res_audit.status_code == 200
    events = res_audit.json()

    matching = [e for e in events if e.get("entity_id") == evidence_id and e.get("event_type") == "EVIDENCE_UPLOADED"]
    assert len(matching) >= 1, f"Audit event for evidence {evidence_id} not found"
    assert "PURCHASE_INVOICE" in matching[0]["description"]

    # Verify audit chain integrity
    chain_status = verify_audit_chain()
    assert chain_status["chain_valid"] is True, f"Tamper detected in audit chain: {chain_status}"
    print(f"[PASS] test_audit_event_generation passed (Audit event chained and verified for {evidence_id})")


def test_privacy_and_authorization_isolation():
    """
    Requirement 8 & Security:
    - Citizen B cannot upload evidence to Citizen A's asset.
    - Citizen B cannot view Citizen A's asset evidence list.
    - Citizen B cannot view Citizen A's single evidence metadata.
    - Citizen B cannot download Citizen A's private evidence file.
    - Government Officer / Admin can access authorized records.
    """
    asset_a_id = get_or_create_test_asset()
    citizen_b_uid = setup_second_citizen()
    headers_b = {"Authorization": f"Bearer {citizen_b_uid}"}
    headers_a = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # Citizen A uploads evidence
    secret_bytes = b"Citizen A Confidential Tax & Financial Invoice"
    res_upload_a = client.post(f"/assets/{asset_a_id}/evidence", headers=headers_a, files={
        "file": ("confidential_tax.pdf", secret_bytes, "application/pdf")
    }, data={"evidence_type": "PURCHASE_INVOICE"})
    assert res_upload_a.status_code == 201
    ev_a_id = res_upload_a.json()["evidence_id"]

    # 1. Citizen B attempts to upload evidence to Citizen A's asset -> 403 Forbidden
    res_b_upload = client.post(f"/assets/{asset_a_id}/evidence", headers=headers_b, files={
        "file": ("b_rogue_file.pdf", b"unauthorized upload", "application/pdf")
    }, data={"evidence_type": "PURCHASE_INVOICE"})
    assert res_b_upload.status_code == 403, f"Expected 403 for cross-citizen upload, got {res_b_upload.status_code}"

    # 2. Citizen B attempts to list Citizen A's evidence -> 403 Forbidden
    res_b_list = client.get(f"/assets/{asset_a_id}/evidence", headers=headers_b)
    assert res_b_list.status_code == 403, f"Expected 403 for cross-citizen list, got {res_b_list.status_code}"

    # 3. Citizen B attempts to view Citizen A's single evidence metadata -> 403 Forbidden
    res_b_single = client.get(f"/evidence/{ev_a_id}", headers=headers_b)
    assert res_b_single.status_code == 403, f"Expected 403 for cross-citizen get, got {res_b_single.status_code}"

    # 4. Citizen B attempts to download Citizen A's private file -> 403 Forbidden
    res_b_file = client.get(f"/evidence/{ev_a_id}/file", headers=headers_b)
    assert res_b_file.status_code == 403, f"Expected 403 for cross-citizen download, got {res_b_file.status_code}"

    # 5. Citizen A CAN download their own file
    res_a_file = client.get(f"/evidence/{ev_a_id}/file", headers=headers_a)
    assert res_a_file.status_code == 200
    assert res_a_file.content == secret_bytes

    # 6. Officer CAN access Citizen A's evidence metadata and download file
    res_officer_single = client.get(f"/evidence/{ev_a_id}", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_officer_single.status_code == 200
    res_officer_file = client.get(f"/evidence/{ev_a_id}/file", headers={"Authorization": f"Bearer {OFFICER_ID}"})
    assert res_officer_file.status_code == 200
    assert res_officer_file.content == secret_bytes

    print("[PASS] test_privacy_and_authorization_isolation passed (Strict 403 enforcement & authorized file streaming)")


def test_list_evidence_for_asset():
    """Tests GET /assets/{asset_id}/evidence returns all items associated with the asset."""
    asset_id = get_or_create_test_asset()
    headers = {"Authorization": f"Bearer {CITIZEN_A_ID}"}

    # Upload two items
    client.post(f"/assets/{asset_id}/evidence", headers=headers, files={
        "file": ("doc1.pdf", b"doc 1 content", "application/pdf")
    }, data={"evidence_type": "WARRANTY"})

    client.post(f"/assets/{asset_id}/evidence", headers=headers, files={
        "file": ("doc2.jpg", b"\xFF\xD8doc 2 photo", "image/jpeg")
    }, data={"evidence_type": "TIMESTAMPED_PHOTO"})

    # List evidence
    res = client.get(f"/assets/{asset_id}/evidence", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2
    for item in items:
        assert item["asset_id"] == asset_id
        assert item["verification_status"] == "PENDING"
        assert item["sha256_hash"].startswith("0x")

    print(f"[PASS] test_list_evidence_for_asset passed ({len(items)} items listed for {asset_id})")


if __name__ == "__main__":
    print("\n--- RUNNING EVIDENCE MANAGEMENT (STEP 8) TEST SUITE ---")
    test_authentication_required()
    test_file_validation_error_cases()
    test_all_10_evidence_types_accepted()
    test_json_base64_upload_and_sha256_generation()
    test_audit_event_generation()
    test_privacy_and_authorization_isolation()
    test_list_evidence_for_asset()
    print("\n[SUCCESS] ALL EVIDENCE MANAGEMENT TESTS PASSED WITH 100% COMPLIANCE!\n")
