"""
Unit and Integration Test Suite for ReliefChain AI - Digital Asset Certificates (Step 11).
Tests:
1. unverified asset -> certificate rejected (HTTP 400 Bad Request)
2. partially verified asset (< 80 confidence) -> certificate rejected (HTTP 400 Bad Request)
3. verified asset -> certificate generated (HTTP 201 Created)
4. Certificate contains all 10 required fields:
   - certificate ID
   - asset ID
   - category
   - description
   - verification status
   - evidence confidence
   - evidence hash
   - registration timestamp
   - verification history
   - QR code
5. QR requirements:
   - Points to secure verification endpoint
   - Does NOT expose private citizen information (zero PII)
   - Verification endpoint returns only safe certificate verification information
   - Certificate generation creates an audit event
6. Simple frontend certificate representation
7. Privacy and access control (Citizen B cannot access Citizen A's certificate)
8. Route prefix compatibility (/assets, /api/assets, /api/v1/assets, /certificates, /api/certificates, /api/v1/certificates)
"""

import sys
import uuid
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

client = TestClient(app)

CITIZEN_A_ID = "USR-006"     # Senthil Nathan (Citizen, HH-1001)
OFFICER_ID = "USR-007"       # Officer Rajesh V (Government Officer)
ADMIN_ID = "USR-001"         # Dr. Ananya Sharma (Admin)


def setup_second_citizen() -> str:
    """Ensures a distinct Citizen B exists for authorization tests."""
    citizen_b_uid = "USR-TEST-CIT-B"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?;", (citizen_b_uid,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO users (user_id, name, email, role, organization, created_at)
            VALUES (?, 'Priya Sundaram (Citizen B)', 'priya.b@reliefchain.org', 'CITIZEN', 'Katpadi Resident (HH-2002)', '2026-09-01T00:00:00Z');
            """, (citizen_b_uid,))
            cursor.execute("SELECT id FROM households WHERE household_ref = 'HH-2002';")
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO households (household_ref, head_of_household, address, district, state, created_at, updated_at)
                VALUES ('HH-2002', 'Priya Sundaram', '22 Gandhi Road, Katpadi', 'Vellore', 'Tamil Nadu', '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z');
                """)
    return citizen_b_uid


def create_test_asset(description: str = "Test Agricultural Tractor") -> str:
    """Helper to create a fresh unverified asset."""
    res = client.post(
        "/assets",
        json={
            "category": "AGRICULTURAL_EQUIPMENT",
            "description": description,
            "documented_value": 450000.0,
            "location_address": "Plot 12, Katpadi Agricultural Sector",
            "household_ref": "HH-1001"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 201
    return res.json()["asset_id"]


def test_unverified_asset_rejected():
    """
    Requirement: A certificate can only be generated for an appropriately verified asset.
    Test: unverified asset -> certificate rejected
    """
    asset_id = create_test_asset("Unverified Harvester Model X")

    # Attempt to generate certificate without any evidence or verification
    res = client.post(
        f"/assets/{asset_id}/certificate",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res.status_code == 400, f"Expected 400 for unverified asset, got {res.status_code}"
    data = res.json()
    error_msg = data.get("error", {}).get("message", "")
    assert "Cannot generate certificate for an unverified asset" in error_msg
    assert "UNVERIFIED" in error_msg
    print(f"[PASS] test_unverified_asset_rejected: {error_msg}")


def test_partially_verified_asset_rejected():
    """
    Requirement: Asset with confidence < 80 (e.g. partially verified) MUST be rejected.
    """
    asset_id = create_test_asset("Partially Verified Irrigation Pump")

    # Add only 1 evidence item with low confidence (TIMESTAMPED_PHOTO = 20 points)
    res_ev = client.post(
        f"/assets/{asset_id}/evidence",
        json={
            "evidence_type": "TIMESTAMPED_PHOTO",
            "original_filename": "pump_photo.jpg",
            "file_content_base64": "/9j/4AAQSkZJRgABAQEASABIAAD/",
            "uploader": "Senthil Nathan"
        },
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_ev.status_code == 201

    # Run verification evaluation
    res_vrf = client.post(
        f"/assets/{asset_id}/verify",
        json={},
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_vrf.status_code == 200
    vrf_data = res_vrf.json()
    assert vrf_data["confidence"] < 80
    assert vrf_data["can_issue_certificate"] is False

    # Attempt to generate certificate
    res_cert = client.post(
        f"/assets/{asset_id}/certificate",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_cert.status_code == 400
    error_msg = res_cert.json().get("error", {}).get("message", "")
    assert "Cannot generate certificate for an unverified asset" in error_msg
    print(f"[PASS] test_partially_verified_asset_rejected: Rejected confidence {vrf_data['confidence']}%")


def test_verified_asset_certificate_generated():
    """
    Requirement:
    Test: verified asset -> certificate generated
    Certificate contains:
    - certificate ID
    - asset ID
    - category
    - description
    - verification status
    - evidence confidence
    - evidence hash
    - registration timestamp
    - verification history
    - QR code
    """
    asset_id = create_test_asset("Full Verified Commercial Delivery Truck")

    # 1. Attach full set of evidence to achieve confidence >= 80 (34 + 25 + 20 + 15 = 94%)
    evidence_items = [
        ("GOVERNMENT_REGISTRATION", "truck_registration_rc.pdf", "JVBERi0xLjQKJcfsj6IKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwo="),
        ("PURCHASE_INVOICE", "dealer_tax_invoice.pdf", "JVBERi0xLjQKJcfsj6IKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwo="),
        ("TIMESTAMPED_PHOTO", "truck_front_view.jpg", "/9j/4AAQSkZJRgABAQEASABIAAD/"),
        ("GEOLOCATION", "gps_depot_lock.json", "eyJwb3MiOiAiMTIuOTgwNiwgNzkuMTQxNyJ9")
    ]

    for ev_type, filename, b64 in evidence_items:
        res_ev = client.post(
            f"/assets/{asset_id}/evidence",
            json={
                "evidence_type": ev_type,
                "original_filename": filename,
                "file_content_base64": b64,
                "uploader": "Senthil Nathan"
            },
            headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
        )
        assert res_ev.status_code == 201

    # 2. Run deterministic verification
    res_vrf = client.post(
        f"/assets/{asset_id}/verify",
        json={},
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_vrf.status_code == 200
    vrf_data = res_vrf.json()
    assert vrf_data["status"] == "VERIFIED"
    assert vrf_data["confidence"] == 94
    assert vrf_data["can_issue_certificate"] is True

    # 3. Generate Certificate (POST /assets/{asset_id}/certificate)
    res_cert = client.post(
        f"/assets/{asset_id}/certificate",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_cert.status_code == 201, f"Expected 201 Created, got {res_cert.status_code}: {res_cert.text}"
    cert = res_cert.json()

    # Validate all 10 required fields
    assert "certificate_id" in cert and cert["certificate_id"].startswith("CERT-2026-")
    assert cert["asset_id"] == asset_id
    assert cert["category"] == "AGRICULTURAL_EQUIPMENT"
    assert cert["description"] == "Full Verified Commercial Delivery Truck"
    assert cert["verification_status"] == "VERIFIED"
    assert cert["evidence_confidence"] == 94
    assert cert["evidence_hash"].startswith("0x") and len(cert["evidence_hash"]) == 66
    assert bool(cert["registration_timestamp"])
    assert isinstance(cert["verification_history"], list) and len(cert["verification_history"]) >= 1
    assert cert["qr_code"].startswith("data:image/svg+xml;base64,")

    # Validate auxiliary fields
    assert bool(cert["certificate_token"])
    assert cert["verification_url"] == f"/certificates/verify/{cert['certificate_token']}"
    assert "<svg" in cert["qr_code_svg"]
    assert cert["frontend_card"] is not None
    assert cert["frontend_card"]["certificate_id"] == cert["certificate_id"]
    assert cert["frontend_card"]["confidence_score"] == "94%"
    assert cert["frontend_card"]["trust_seal"] == "SHA-256 VERIFIED CIVIC BASELINE"

    print(f"[PASS] test_verified_asset_certificate_generated: {cert['certificate_id']} issued successfully")
    return cert


def test_qr_requirements_and_privacy_guarantee():
    """
    QR requirements:
    1. QR must point to a secure verification endpoint.
    2. QR must not expose private citizen information.
    3. Verification endpoint should return only safe certificate verification information.
    """
    cert = test_verified_asset_certificate_generated()
    token = cert["certificate_token"]
    cert_id = cert["certificate_id"]
    asset_id = cert["asset_id"]

    # 1. QR verification endpoint lookup
    res_public = client.get(f"/certificates/verify/{token}")
    assert res_public.status_code == 200, f"Public verification endpoint failed: {res_public.text}"
    data = res_public.json()

    # 2. Check safe verification fields
    assert data["is_valid"] is True
    assert data["certificate_id"] == cert_id
    assert data["asset_id"] == asset_id
    assert data["category"] == "AGRICULTURAL_EQUIPMENT"
    assert data["verification_status"] == "VERIFIED"
    assert data["evidence_confidence"] == 94
    assert data["evidence_hash"] == cert["evidence_hash"]
    assert data["issuer"] == "ReliefChain AI Civic Trust Authority"
    assert "authentic, baseline-anchored" in data["verification_message"]

    # 3. Privacy Guarantee: Strictly NO Citizen PII
    private_keys = [
        "citizen_id", "citizen_name", "head_of_household", "contact_phone",
        "phone", "household_ref", "location_address", "address",
        "documented_value", "approximate_value", "value", "bank_account"
    ]
    for key in private_keys:
        assert key not in data, f"Privacy violation! Safe verification exposed '{key}'"

    # Also check stored qr_payload in database does not leak citizen info
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT qr_payload FROM asset_certificates WHERE certificate_id = ?;", (cert_id,))
        row = cursor.fetchone()
        assert row is not None
        payload_dict = json.loads(row["qr_payload"])
        for key in private_keys:
            assert key not in payload_dict, f"Privacy violation in qr_payload! Found '{key}'"

    print(f"[PASS] test_qr_requirements_and_privacy_guarantee: Zero PII exposed in verification endpoint")


def test_certificate_generation_creates_audit_event():
    """
    Requirement 4: Certificate generation creates an audit event.
    Verifies sequential SHA-256 tamper-evident hash chain.
    """
    cert = test_verified_asset_certificate_generated()
    cert_id = cert["certificate_id"]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM audit_events
        WHERE event_type = 'CERTIFICATE_GENERATED' AND entity_id = ?
        ORDER BY id DESC LIMIT 1;
        """, (cert_id,))
        audit_event = cursor.fetchone()

    assert audit_event is not None, f"Audit event for certificate {cert_id} not found"
    assert audit_event["event_type"] == "CERTIFICATE_GENERATED"
    assert audit_event["entity_type"] == "CERTIFICATE"
    assert audit_event["entity_id"] == cert_id
    assert audit_event["evidence_hash"] == cert["evidence_hash"]
    assert audit_event["event_hash"].startswith("0x")
    assert audit_event["previous_hash"].startswith("0x")

    # Verify overall audit chain integrity
    integrity_report = verify_audit_chain()
    assert integrity_report["chain_valid"] is True, f"Audit chain broken: {integrity_report}"
    assert integrity_report["tampered"] is False
    print(f"[PASS] test_certificate_generation_creates_audit_event: Audit ID {audit_event['audit_id']} chained with SHA-256")


def test_get_certificate_by_id_and_authorization():
    """
    Requirement: Implement GET /certificates/{certificate_id}
    Enforces privacy: Citizen B cannot view Citizen A's certificate.
    """
    cert = test_verified_asset_certificate_generated()
    cert_id = cert["certificate_id"]
    citizen_b = setup_second_citizen()

    # 1. Citizen A (owner) retrieves own certificate -> 200 OK
    res_a = client.get(
        f"/certificates/{cert_id}",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_a.status_code == 200
    assert res_a.json()["certificate_id"] == cert_id

    # 2. Officer retrieves certificate -> 200 OK
    res_officer = client.get(
        f"/certificates/{cert_id}",
        headers={"Authorization": f"Bearer {OFFICER_ID}"}
    )
    assert res_officer.status_code == 200
    assert res_officer.json()["certificate_id"] == cert_id

    # 3. Citizen B (non-owner) retrieves Citizen A's certificate -> 403 Forbidden
    res_b = client.get(
        f"/certificates/{cert_id}",
        headers={"Authorization": f"Bearer {citizen_b}"}
    )
    assert res_b.status_code == 403, f"Expected 403 Forbidden for non-owner, got {res_b.status_code}"

    # 4. Invalid certificate ID -> 404 Not Found
    res_invalid = client.get(
        "/certificates/CERT-2026-INVALID999",
        headers={"Authorization": f"Bearer {CITIZEN_A_ID}"}
    )
    assert res_invalid.status_code == 404

    print(f"[PASS] test_get_certificate_by_id_and_authorization: Ownership isolation strictly verified")


def test_qr_svg_image_endpoint():
    """Tests GET /certificates/{certificate_id}/qr endpoint returning image/svg+xml."""
    cert = test_verified_asset_certificate_generated()
    cert_id = cert["certificate_id"]

    res = client.get(f"/certificates/{cert_id}/qr")
    assert res.status_code == 200
    assert "image/svg+xml" in res.headers.get("content-type", "")
    assert "<svg" in res.text
    print(f"[PASS] test_qr_svg_image_endpoint: Valid SVG QR returned ({len(res.text)} bytes)")


def test_api_route_prefixes_compatibility():
    """Validates route availability across /, /api, and /api/v1 prefixes."""
    cert = test_verified_asset_certificate_generated()
    token = cert["certificate_token"]
    cert_id = cert["certificate_id"]

    for prefix in ["", "/api", "/api/v1"]:
        # Verify endpoint
        res_v = client.get(f"{prefix}/certificates/verify/{token}")
        assert res_v.status_code == 200, f"Failed at {prefix}/certificates/verify"

        # Certificate by ID endpoint
        res_c = client.get(f"{prefix}/certificates/{cert_id}", headers={"Authorization": f"Bearer {CITIZEN_A_ID}"})
        assert res_c.status_code == 200, f"Failed at {prefix}/certificates/{cert_id}"

    print("[PASS] test_api_route_prefixes_compatibility: All prefix variations operational")


if __name__ == "__main__":
    print("\n--- RUNNING DIGITAL ASSET CERTIFICATE (STEP 11) TEST SUITE ---")
    test_unverified_asset_rejected()
    test_partially_verified_asset_rejected()
    test_verified_asset_certificate_generated()
    test_qr_requirements_and_privacy_guarantee()
    test_certificate_generation_creates_audit_event()
    test_get_certificate_by_id_and_authorization()
    test_qr_svg_image_endpoint()
    test_api_route_prefixes_compatibility()
    print("\n[SUCCESS] ALL STEP 11 DIGITAL ASSET CERTIFICATE TESTS PASSED WITH 100% COMPLIANCE!\n")
