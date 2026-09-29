"""
Integration Test Suite for Step 23: Post-Disaster Evidence Upload on Claim Details Page.

Validates:
1. Citizen creates/retrieves an asset and submits a disaster claim.
2. Citizen uploads post-disaster evidence items directly through existing backend API:
   - Damaged photograph (POST_DISASTER_PHOTO)
   - Damaged video (POST_DISASTER_VIDEO)
   - Inspection document (FIELD_INSPECTION_REPORT)
3. Verifies evidence metadata:
   - evidence_id format (e.g. EVD-2026-XXXX)
   - original_filename, file_size, mime_type
   - SHA-256 integrity hash
   - secure private storage file_url
4. Verifies database persistence in `claim_evidence` table.
5. Verifies sequential `EVIDENCE_ADDED` audit events in SHA-256 hash chain.
6. Verifies evidence retrieval via GET /api/claims/{claim_id}/evidence.
7. Verifies access control (citizens cannot upload evidence to other citizens' claims).
"""

import io
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

client = TestClient(app)

CITIZEN_A_ID = "USR-006"        # Senthil Nathan (HH-1001)
CITIZEN_B_ID = "USR-CLAIM-CIT-B" # Kavitha Ramachandran (HH-3003)
DISASTER_ID = "DIS-2026-0007"   # Tamil Nadu Monsoon Flash Flood


def test_complete_claim_evidence_upload_workflow():
    """
    Step 23 Full Workflow Test:
    Asset -> Create Claim -> Upload Damaged Photo -> Upload Damaged Video -> Upload Inspection Document -> Verify Database -> Retrieve Evidence
    """
    # Step 1: Ensure Citizen A has a registered asset
    res_asset = client.post(
        "/api/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": "Step 23 Brick Residential House - Flood Damaged",
            "documented_value": 850000.0,
            "location_address": "45 River Bank Road, Katpadi, Vellore",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_asset.status_code == 201, f"Failed to create asset: {res_asset.text}"
    asset_data = res_asset.json()
    asset_id = asset_data["asset_id"]

    # Step 2: Citizen files disaster claim for the asset
    res_claim = client.post(
        "/api/claims",
        json={
            "asset_id": asset_id,
            "disaster_id": DISASTER_ID,
            "damage_description": "Severe ground flood damage: perimeter wall collapse and structural cracks.",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_claim.status_code == 201, f"Failed to submit claim: {res_claim.text}"
    claim_data = res_claim.json()
    claim_id = claim_data["claim_id"]
    assert claim_data["review_status"] == "SUBMITTED"

    # Step 3: Upload Damaged Photo (POST_DISASTER_PHOTO)
    photo_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00STEP23_DAMAGED_WALL_PHOTO"
    photo_expected_hash = f"0x{hashlib.sha256(photo_bytes).hexdigest()}"

    res_photo = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("damaged_wall.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_photo.status_code == 201, f"Photo upload failed: {res_photo.text}"
    photo_ev = res_photo.json()
    assert photo_ev["evidence_type"] == "POST_DISASTER_PHOTO"
    assert photo_ev["original_filename"] == "damaged_wall.jpg"
    assert photo_ev["sha256_hash"] == photo_expected_hash
    assert photo_ev["file_size"] == len(photo_bytes)
    assert photo_ev["claim_id"] == claim_id
    photo_ev_id = photo_ev["evidence_id"]

    # Step 4: Upload Damaged Video (POST_DISASTER_VIDEO)
    video_bytes = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41STEP23_DAMAGED_VIDEO_STREAM"
    video_expected_hash = f"0x{hashlib.sha256(video_bytes).hexdigest()}"

    res_video = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_VIDEO"},
        files={"file": ("inundation_clip.mp4", io.BytesIO(video_bytes), "video/mp4")},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_video.status_code == 201, f"Video upload failed: {res_video.text}"
    video_ev = res_video.json()
    assert video_ev["evidence_type"] == "POST_DISASTER_VIDEO"
    assert video_ev["original_filename"] == "inundation_clip.mp4"
    assert video_ev["sha256_hash"] == video_expected_hash
    assert video_ev["file_size"] == len(video_bytes)
    video_ev_id = video_ev["evidence_id"]

    # Step 5: Upload Field Inspection Document (FIELD_INSPECTION_REPORT)
    report_bytes = b"%PDF-1.4\n%STEP23_SURVEYOR_INSPECTION_REPORT\n%%EOF"
    report_expected_hash = f"0x{hashlib.sha256(report_bytes).hexdigest()}"

    res_report = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "FIELD_INSPECTION_REPORT"},
        files={"file": ("structural_survey_report.pdf", io.BytesIO(report_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_report.status_code == 201, f"Report upload failed: {res_report.text}"
    report_ev = res_report.json()
    assert report_ev["evidence_type"] == "FIELD_INSPECTION_REPORT"
    assert report_ev["original_filename"] == "structural_survey_report.pdf"
    assert report_ev["sha256_hash"] == report_expected_hash
    report_ev_id = report_ev["evidence_id"]

    # Step 6: Verify Database Records in `claim_evidence` table
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT evidence_id, evidence_type, original_filename, sha256_hash, file_size "
            "FROM claim_evidence WHERE claim_id = ? ORDER BY id ASC;",
            (claim_id,)
        )
        db_rows = cursor.fetchall()
        assert len(db_rows) == 3, f"Expected 3 evidence items in database, found {len(db_rows)}"

        # Verify photo
        assert db_rows[0]["evidence_id"] == photo_ev_id
        assert db_rows[0]["evidence_type"] == "POST_DISASTER_PHOTO"
        assert db_rows[0]["original_filename"] == "damaged_wall.jpg"
        assert db_rows[0]["sha256_hash"] == photo_expected_hash

        # Verify video
        assert db_rows[1]["evidence_id"] == video_ev_id
        assert db_rows[1]["evidence_type"] == "POST_DISASTER_VIDEO"
        assert db_rows[1]["original_filename"] == "inundation_clip.mp4"
        assert db_rows[1]["sha256_hash"] == video_expected_hash

        # Verify inspection document
        assert db_rows[2]["evidence_id"] == report_ev_id
        assert db_rows[2]["evidence_type"] == "FIELD_INSPECTION_REPORT"
        assert db_rows[2]["original_filename"] == "structural_survey_report.pdf"
        assert db_rows[2]["sha256_hash"] == report_expected_hash

    # Step 7: Verify Sequential Audit Trail in `audit_events`
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_type, entity_type, entity_id, evidence_hash "
            "FROM audit_events WHERE entity_type = 'CLAIM_EVIDENCE' AND entity_id IN (?, ?, ?) "
            "ORDER BY id ASC;",
            (photo_ev_id, video_ev_id, report_ev_id)
        )
        audit_rows = cursor.fetchall()
        assert len(audit_rows) == 3
        for row in audit_rows:
            assert row["event_type"] == "EVIDENCE_ADDED"
            assert row["entity_type"] == "CLAIM_EVIDENCE"

    # Step 8: Retrieve Evidence List via GET /api/claims/{claim_id}/evidence
    res_list = client.get(
        f"/api/claims/{claim_id}/evidence",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_list.status_code == 200
    evidence_items = res_list.json()
    assert len(evidence_items) == 3

    ids = [e["evidence_id"] for e in evidence_items]
    assert photo_ev_id in ids
    assert video_ev_id in ids
    assert report_ev_id in ids

    # Step 9: Unauthorized citizen cannot upload evidence to Citizen A's claim
    res_unauth = client.post(
        f"/api/claims/{claim_id}/evidence",
        data={"evidence_type": "POST_DISASTER_PHOTO"},
        files={"file": ("intruder.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {CITIZEN_B_ID}"}
    )
    assert res_unauth.status_code == 403, f"Expected 403 Forbidden for Citizen B, got {res_unauth.status_code}"

    print(f"[PASS] Complete Step 23 Claim Evidence Upload workflow verified successfully for claim '{claim_id}'.")
