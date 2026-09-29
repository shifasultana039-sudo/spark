"""
Unit and Integration Test Suite for ReliefChain AI - Post-Disaster Claim Evidence (Step 13).

Validates:
1. Endpoints:
   - POST /claims/{claim_id}/evidence
   - GET /claims/{claim_id}/evidence
   - GET /claims/{claim_id}/evidence/{evidence_id}/file
2. Support for all 3 post-disaster evidence categories:
   - Damaged photographs (POST_DISASTER_PHOTO, DAMAGED_PHOTO, etc.)
   - Damaged videos (POST_DISASTER_VIDEO, DAMAGED_VIDEO, etc.)
   - Inspection reports (FIELD_INSPECTION_REPORT, INSPECTION_REPORT, etc.)
3. Reuse existing Evidence and Storage systems:
   - Preserves original file SHA-256 hashes.
   - Records upload and captured timestamps.
   - Protects private evidence from public URLs.
   - Validates file types, extensions, and reasonable sizes.
4. Privacy & Authorization:
   - Citizens can only upload and view evidence for their own claims (403 for other citizens).
   - Government Officers and Admins can view and download all claim evidence.
   - Unauthenticated access returns 401 Unauthorized.
5. Sequential Audit Logging:
   - EVIDENCE_ADDED event recorded with exact evidence_hash in SHA-256 hash chain.
   - Full chain integrity verification passes.
6. Damage Assessment Deferral:
   - Does NOT generate damage assessment yet (Step 14).
   - Review status remains in workflow state without auto-approval/assessment.
7. Route prefix compatibility:
   - /claims/{claim_id}/evidence, /api/claims/{claim_id}/evidence, /api/v1/claims/{claim_id}/evidence.
"""

import sys
import io
import json
import base64
import hashlib
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.database import get_db
from app.services import verify_audit_chain
from storage.provider import storage_provider

client = TestClient(app)

CITIZEN_A_ID = "USR-006"     # Senthil Nathan (Citizen, HH-1001)
CITIZEN_B_ID = "USR-CLAIM-CIT-B" # Kavitha Ramachandran (Citizen B, HH-3003)
OFFICER_ID = "USR-007"       # Officer Rajesh V (Government Officer)
ADMIN_ID = "USR-001"         # Dr. Ananya Sharma (Admin)


def get_error_message(res) -> str:
    """Extracts error message from standardized AppException or HTTPException format."""
    try:
        body = res.json()
        if isinstance(body, dict):
            if "error" in body and isinstance(body["error"], dict):
                return body["error"].get("message", "")
            if "detail" in body:
                return str(body["detail"])
    except Exception:
        pass
    return res.text


def setup_test_users_and_claims():
    """Ensures test citizens, households, assets, and claims exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Ensure Citizen B exists
        cursor.execute("SELECT id FROM users WHERE user_id = ?;", (CITIZEN_B_ID,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO users (user_id, name, email, role, organization, created_at)
            VALUES (?, 'Kavitha Ramachandran (Citizen B)', 'kavitha.b@reliefchain.org', 'CITIZEN', 'Katpadi Resident (HH-3003)', '2026-09-01T00:00:00Z');
            """, (CITIZEN_B_ID,))
        cursor.execute("SELECT id FROM households WHERE household_ref = 'HH-3003';")
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO households (household_ref, head_of_household, address, district, state, created_at, updated_at)
            VALUES ('HH-3003', 'Kavitha Ramachandran', '78 Palar River Road, Katpadi', 'Vellore', 'Tamil Nadu', '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z');
            """)

    # 1. Create asset for Citizen A
    res_a = client.post(
        "/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 13 Residential House for Citizen A",
            "documented_value": 750000.0,
            "location_address": "12 Gandhi Road, Katpadi, Vellore",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_a.status_code == 201
    asset_a_id = res_a.json()["asset_id"]

    # 2. Create claim for Citizen A
    claim_res_a = client.post(
        "/claims",
        json={
            "asset_id": asset_a_id,
            "damage_description": "Extensive flood water damage to walls, flooring, and roof structure.",
            "disaster_id": "DIS-2026-0007"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert claim_res_a.status_code == 201
    claim_a_id = claim_res_a.json()["claim_id"]

    # 3. Create asset for Citizen B
    res_b = client.post(
        "/assets",
        json={
            "category": "VEHICLE",
            "description": "Step 13 Tractor for Citizen B",
            "documented_value": 450000.0,
            "location_address": "78 Palar River Road, Katpadi, Vellore",
            "household_ref": "HH-3003"
        },
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_b.status_code == 201
    asset_b_id = res_b.json()["asset_id"]

    # 4. Create claim for Citizen B
    claim_res_b = client.post(
        "/claims",
        json={
            "asset_id": asset_b_id,
            "damage_description": "Engine submerged in flood silt and electrical system ruined.",
            "disaster_id": "DIS-2026-0007"
        },
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert claim_res_b.status_code == 201
    claim_b_id = claim_res_b.json()["claim_id"]

    return claim_a_id, claim_b_id, asset_a_id, asset_b_id


@pytest.fixture(scope="module")
def claim_setup():
    return setup_test_users_and_claims()


@pytest.fixture
def claim_a_id(claim_setup):
    return claim_setup[0]


@pytest.fixture
def claim_b_id(claim_setup):
    return claim_setup[1]


@pytest.fixture
def evidence_a_id(claim_a_id):
    photo_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00fixture_photo_content_data"
    res = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("fixture_photo.jpg", photo_content, "image/jpeg")},
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 201
    return res.json()["evidence_id"]


def test_claim_evidence_nonexistent_claim():
    """Attempts to upload or list evidence for non-existent claim must return 404."""
    non_existent = "CLM-2026-999999"
    # POST
    dummy_bytes = b"fake photo content"
    res = client.post(
        f"/claims/{non_existent}/evidence",
        files={"file": ("damaged_wall.jpg", dummy_bytes, "image/jpeg")},
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 404
    err = get_error_message(res)
    assert f"Disaster claim '{non_existent}' not found" in err

    # GET
    res_get = client.get(
        f"/claims/{non_existent}/evidence",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_get.status_code == 404
    print("[PASS] test_claim_evidence_nonexistent_claim: 404 returned correctly for non-existent claim")


def test_file_type_and_size_validation(claim_a_id: str):
    """Verifies that invalid extensions, empty files, and mismatched types are rejected."""
    # 1. Empty file (0 bytes)
    res_empty = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_empty.status_code == 400
    assert "0 bytes" in get_error_message(res_empty)

    # 2. Unsupported extension (.exe)
    res_exe = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("malicious.exe", b"binarycontent", "application/octet-stream")},
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_exe.status_code == 400
    assert "Unsupported file format" in get_error_message(res_exe)

    # 3. Mismatched file type (uploading .mp4 video as damaged photograph)
    res_mismatch = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("clip.mp4", b"video-dummy-data", "video/mp4")},
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_mismatch.status_code == 400
    assert "Invalid file extension '.mp4' for damaged photograph" in get_error_message(res_mismatch)

    # 4. Invalid evidence type
    res_bad_type = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("photo.jpg", b"image-content", "image/jpeg")},
        data={"evidence_type": "INVALID_RANDOM_TYPE"},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_bad_type.status_code == 400
    assert "Unsupported post-disaster evidence type" in get_error_message(res_bad_type)
    print("[PASS] test_file_type_and_size_validation: Validation errors properly enforced (400 Bad Request)")


def test_damaged_photograph_upload_multipart_and_json(claim_a_id: str):
    """
    Tests uploading damaged photographs via multipart form data and base64 JSON:
    - Preserves exact SHA-256 hash.
    - Formats readable evidence ID (CLM-EV-YYYY-NNNNNN).
    - Records upload timestamp.
    - Associates evidence with claim.
    """
    # --- 1. Multipart Form Upload (DAMAGED_PHOTO alias -> POST_DISASTER_PHOTO) ---
    photo_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"damaged_wall_photo_data_12345"
    expected_hash = f"0x{hashlib.sha256(photo_content).hexdigest()}"

    res = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("damaged_exterior_wall.jpg", photo_content, "image/jpeg")},
        data={
            "evidence_type": "DAMAGED_PHOTO",
            "captured_timestamp": "2026-09-28T09:30:00Z"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 201, f"Failed: {res.text}"
    data = res.json()

    assert data["claim_id"] == claim_a_id
    assert data["evidence_type"] == "POST_DISASTER_PHOTO"
    assert data["original_filename"] == "damaged_exterior_wall.jpg"
    assert data["sha256_hash"] == expected_hash, "Original file hash must be preserved"
    assert data["file_size"] == len(photo_content)
    assert data["mime_type"] == "image/jpeg"
    assert data["captured_timestamp"] == "2026-09-28T09:30:00Z"
    assert "created_at" in data
    assert data["evidence_id"].startswith("CLM-EV-2026-")

    # --- 2. JSON Base64 Upload (POST_DISASTER_PHOTO) ---
    photo_b64_content = b"roof_caved_in_photo_content_98765"
    expected_hash_2 = f"0x{hashlib.sha256(photo_b64_content).hexdigest()}"

    res_json = client.post(
        f"/claims/{claim_a_id}/evidence",
        json={
            "evidence_type": "POST_DISASTER_PHOTO",
            "original_filename": "caved_roof.png",
            "file_content_base64": base64.b64encode(photo_b64_content).decode("utf-8"),
            "captured_timestamp": "2026-09-28T10:15:00Z"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_json.status_code == 201
    data_json = res_json.json()
    assert data_json["sha256_hash"] == expected_hash_2
    assert data_json["original_filename"] == "caved_roof.png"
    print("[PASS] test_damaged_photograph_upload_multipart_and_json: Hash preserved and metadata recorded")
    return data["evidence_id"]


def test_damaged_video_upload(claim_a_id: str):
    """Tests uploading damaged video (.mp4) with DAMAGED_VIDEO / POST_DISASTER_VIDEO."""
    video_content = b"\x00\x00\x00\x18ftypmp42" + b"simulated_damaged_room_inundation_video_stream_content"
    expected_hash = f"0x{hashlib.sha256(video_content).hexdigest()}"

    res = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("flood_water_flow_interior.mp4", video_content, "video/mp4")},
        data={
            "evidence_type": "DAMAGED_VIDEO",
            "captured_timestamp": "2026-09-28T11:00:00Z"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["claim_id"] == claim_a_id
    assert data["evidence_type"] == "POST_DISASTER_VIDEO"
    assert data["original_filename"] == "flood_water_flow_interior.mp4"
    assert data["sha256_hash"] == expected_hash
    assert data["mime_type"] == "video/mp4"
    print("[PASS] test_damaged_video_upload: Damaged video successfully uploaded and hash preserved")
    return data["evidence_id"]


def test_field_inspection_report_upload(claim_a_id: str):
    """Tests uploading an inspection report (.pdf) with INSPECTION_REPORT / FIELD_INSPECTION_REPORT."""
    pdf_content = b"%PDF-1.4\n%Field inspection report: Inundation level 1.8 meters, foundation structural crack detected."
    expected_hash = f"0x{hashlib.sha256(pdf_content).hexdigest()}"

    res = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("field_engineer_survey_report.pdf", pdf_content, "application/pdf")},
        data={
            "evidence_type": "INSPECTION_REPORT",
            "captured_timestamp": "2026-09-28T14:00:00Z"
        },
        headers={"Authorization": f"Bearer {OFFICER_ID}"}  # Uploaded by field officer
    )
    assert res.status_code == 201
    data = res.json()
    assert data["claim_id"] == claim_a_id
    assert data["evidence_type"] == "FIELD_INSPECTION_REPORT"
    assert data["original_filename"] == "field_engineer_survey_report.pdf"
    assert data["sha256_hash"] == expected_hash
    assert data["mime_type"] == "application/pdf"
    print("[PASS] test_field_inspection_report_upload: Inspection report successfully uploaded")
    return data["evidence_id"]


def test_list_claim_evidence(claim_a_id: str):
    """Verifies that GET /claims/{claim_id}/evidence lists all uploaded evidence."""
    res = client.get(
        f"/claims/{claim_a_id}/evidence",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 4  # 2 photos, 1 video, 1 report
    types = [i["evidence_type"] for i in items]
    assert "POST_DISASTER_PHOTO" in types
    assert "POST_DISASTER_VIDEO" in types
    assert "FIELD_INSPECTION_REPORT" in types

    # Check that each evidence item contains all expected fields
    for item in items:
        assert item["claim_id"] == claim_a_id
        assert item["evidence_id"].startswith("CLM-EV-")
        assert item["sha256_hash"].startswith("0x")
        assert item["file_size"] > 0
        assert item["created_at"] is not None
        assert item["file_url"] == f"/claims/{claim_a_id}/evidence/{item['evidence_id']}/file"

    print(f"[PASS] test_list_claim_evidence: Found {len(items)} evidence items covering all 3 categories")


def test_privacy_and_permissions(claim_a_id: str, claim_b_id: str, evidence_a_id: str):
    """
    Requirement 6: Protect private evidence:
    - Citizen A cannot access Citizen B's claim evidence (403 Forbidden).
    - Citizen B cannot upload evidence to Citizen A's claim (403 Forbidden).
    - Citizen B cannot list evidence for Citizen A's claim (403 Forbidden).
    - Citizen B cannot download Citizen A's private evidence file (403 Forbidden).
    - Officer can view and download any claim evidence (200 OK).
    - Unauthenticated requests return 401 Unauthorized.
    """
    # 1. Unauthenticated upload -> 401
    res_unauth = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("photo.jpg", b"dummy", "image/jpeg")},
        data={"evidence_type": "POST_DISASTER_PHOTO"}
    )
    assert res_unauth.status_code == 401

    # 2. Citizen B uploading to Citizen A's claim -> 403 Forbidden
    res_cross_upload = client.post(
        f"/claims/{claim_a_id}/evidence",
        files={"file": ("photo.jpg", b"dummy", "image/jpeg")},
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_cross_upload.status_code == 403
    assert "Access denied" in get_error_message(res_cross_upload)

    # 3. Citizen B listing Citizen A's evidence -> 403 Forbidden
    res_cross_list = client.get(
        f"/claims/{claim_a_id}/evidence",
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_cross_list.status_code == 403

    # 4. Citizen B downloading Citizen A's evidence file -> 403 Forbidden
    res_cross_dl = client.get(
        f"/claims/{claim_a_id}/evidence/{evidence_a_id}/file",
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_cross_dl.status_code == 403

    # 5. Citizen A downloading Citizen A's evidence file -> 200 OK
    res_a_dl = client.get(
        f"/claims/{claim_a_id}/evidence/{evidence_a_id}/file",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_a_dl.status_code == 200
    assert len(res_a_dl.content) > 0

    # 6. Officer accessing Citizen A's evidence file -> 200 OK
    res_officer_dl = client.get(
        f"/claims/{claim_a_id}/evidence/{evidence_a_id}/file",
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_officer_dl.status_code == 200

    print("[PASS] test_privacy_and_permissions: Strict citizen isolation and officer access verified")


def test_audit_event_creation(evidence_a_id: str):
    """
    Requirement 5: Create audit events.
    Verifies that EVIDENCE_ADDED events were recorded in audit_events
    and that the sequential SHA-256 hash chain remains unbroken.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM audit_events
        WHERE entity_type = 'CLAIM_EVIDENCE' AND entity_id = ?;
        """, (evidence_a_id,))
        row = cursor.fetchone()
        assert row is not None, f"Audit event for claim evidence {evidence_a_id} not found"
        event = dict(row)
        assert event["event_type"] == "EVIDENCE_ADDED"
        assert event["evidence_hash"] is not None
        assert event["evidence_hash"].startswith("0x")
        assert event["event_hash"] is not None

    # Verify overall audit chain integrity
    integrity = verify_audit_chain()
    assert integrity.get("chain_valid", integrity.get("is_valid")) is True, f"Audit chain broken: {integrity}"
    print(f"[PASS] test_audit_event_creation: Verified {integrity['total_events']} audit events with unbroken SHA-256 chain")


def test_no_damage_assessment_generated_yet(claim_a_id: str):
    """
    Requirement 8: Do not generate damage assessment yet.
    - Verify that damage_assessments table contains NO rows for this claim.
    - Verify that claim review status remains SUBMITTED (not AI_ASSESSED or APPROVED).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM damage_assessments WHERE claim_id = ?;", (claim_a_id,))
        assessments = cursor.fetchall()
        assert len(assessments) == 0, f"Expected 0 damage assessments, found {len(assessments)}!"

    # Verify claim status
    res = client.get(f"/claims/{claim_a_id}", headers={"Authorization": f"Bearer {CITIZEN_A_ID}"})
    assert res.status_code == 200
    claim_data = res.json()
    assert claim_data["review_status"] == "SUBMITTED"
    assert claim_data["claim_status"] == "SUBMITTED"
    print("[PASS] test_no_damage_assessment_generated_yet: No damage assessment generated, status preserved at SUBMITTED")


def test_api_route_prefixes_compatibility(claim_a_id: str):
    """Tests that claim evidence endpoints respond across all router prefixes."""
    prefixes = ["", "/api", "/api/v1"]
    for prefix in prefixes:
        res = client.get(
            f"{prefix}/claims/{claim_a_id}/evidence",
            headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
        )
        assert res.status_code == 200, f"Failed for prefix '{prefix}': {res.status_code}"
    print("[PASS] test_api_route_prefixes_compatibility: Endpoints responsive across /claims, /api/claims, and /api/v1/claims")


def run_all_tests():
    print("\n--- RUNNING POST-DISASTER CLAIM EVIDENCE (STEP 13) TEST SUITE ---")
    claim_a_id, claim_b_id, asset_a_id, asset_b_id = setup_test_users_and_claims()
    print(f"[SETUP] Created Claim A ({claim_a_id}) and Claim B ({claim_b_id})")

    test_claim_evidence_nonexistent_claim()
    test_file_type_and_size_validation(claim_a_id)
    evidence_photo_id = test_damaged_photograph_upload_multipart_and_json(claim_a_id)
    evidence_video_id = test_damaged_video_upload(claim_a_id)
    evidence_report_id = test_field_inspection_report_upload(claim_a_id)
    test_list_claim_evidence(claim_a_id)
    test_privacy_and_permissions(claim_a_id, claim_b_id, evidence_photo_id)
    test_audit_event_creation(evidence_photo_id)
    test_no_damage_assessment_generated_yet(claim_a_id)
    test_api_route_prefixes_compatibility(claim_a_id)

    print("\n[SUCCESS] ALL STEP 13 CLAIM EVIDENCE TESTS PASSED WITH 100% COMPLIANCE!\n")


if __name__ == "__main__":
    run_all_tests()
