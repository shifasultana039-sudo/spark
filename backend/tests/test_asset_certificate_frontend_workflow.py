"""
Step 21 Test Suite: Digital Asset Certificate Frontend & Backend Integration.

Workflow:
1. Citizen registers an asset.
2. Unverified asset rejected for certificate generation (HTTP 400).
3. Citizen uploads evidence (Registration + Invoice + Photo + GPS = 94% confidence).
4. Citizen verifies asset (status becomes VERIFIED).
5. Citizen generates digital certificate via POST /api/assets/{asset_id}/certificate.
   Validates required fields:
   - Certificate ID (CERT-2026-XXXXXX)
   - Asset ID (AST-YYYY-NNNNNN)
   - Verification Status (VERIFIED)
   - Evidence Confidence (94%)
   - Registration Date / Timestamp
   - QR Code (Base64 data URI)
6. Citizen retrieves certificate via GET /api/assets/{asset_id}/certificate.
7. Verification by Certificate ID via GET /api/certificates/{certificate_id}.
8. Public QR safe verification via GET /api/certificates/verify/{token}.
9. SQLite database persistence and SHA-256 audit event.
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


def test_unverified_asset_certificate_rejected():
    """Verify that an unverified asset cannot generate a certificate (HTTP 400)."""
    # 1. Register asset without evidence
    resp = client.post("/api/assets", json={
        "category": "PERSONAL_PROPERTY",
        "description": f"Unverified Solar Battery Bank #{uuid.uuid4().hex[:6]}",
        "documented_value": 180000.0,
        "location_address": "45 Main Bazaar, Katpadi, Vellore",
        "purchase_date": "2024-01-10"
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 201
    asset_id = resp.json()["asset_id"]

    # 2. Attempt to generate certificate
    cert_resp = client.post(f"/api/assets/{asset_id}/certificate", headers=AUTH_HEADERS)
    assert cert_resp.status_code == 400
    body = cert_resp.json()
    error_detail = body.get("error", {}).get("message", "") if isinstance(body.get("error"), dict) else body.get("detail", str(body))
    assert "Cannot generate certificate for an unverified asset" in error_detail

    # 3. Attempt GET certificate before generation -> 404
    get_resp = client.get(f"/api/assets/{asset_id}/certificate", headers=AUTH_HEADERS)
    assert get_resp.status_code == 404


def test_verified_asset_certificate_generation_and_retrieval():
    """
    Test Step 21 complete certificate generation workflow:
    Verified Asset -> Certificate Generated -> Database Persisted -> Frontend Endpoints Confirmed.
    """
    # 1. Register asset
    create_resp = client.post("/api/assets", json={
        "category": "BUSINESS_EQUIPMENT",
        "description": f"Verified Food Processing Unit #{uuid.uuid4().hex[:6]}",
        "documented_value": 920000.0,
        "location_address": "Plot 18, SIDCO Industrial Complex, Ranipet",
        "purchase_date": "2023-04-15"
    }, headers=AUTH_HEADERS)
    assert create_resp.status_code == 201
    asset_id = create_resp.json()["asset_id"]

    # 2. Upload sufficient evidence proofs to reach >= 80% confidence
    # Government Registration (34)
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("msme_reg.pdf", b"%PDF-1.4 MSME Registration", "application/pdf")},
        data={"evidence_type": "GOVERNMENT_REGISTRATION"},
        headers=AUTH_HEADERS
    )
    # Purchase Invoice (25)
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("machinery_invoice.pdf", b"%PDF-1.4 Machinery Invoice", "application/pdf")},
        data={"evidence_type": "PURCHASE_INVOICE"},
        headers=AUTH_HEADERS
    )
    # Timestamped Photograph (20)
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("factory_photo.jpg", b"\xff\xd8\xff\xe0 photo", "image/jpeg")},
        data={"evidence_type": "TIMESTAMPED_PHOTO"},
        headers=AUTH_HEADERS
    )
    # Geolocation (15)
    client.post(
        f"/api/assets/{asset_id}/evidence",
        files={"file": ("gps_survey.json", b'{"lat": 12.92, "lng": 79.33}', "application/json")},
        data={"evidence_type": "GEOLOCATION"},
        headers=AUTH_HEADERS
    )

    # 3. Verify asset (Deterministic rules engine)
    verify_resp = client.post(f"/api/assets/{asset_id}/verify", headers=AUTH_HEADERS)
    assert verify_resp.status_code == 200
    vrf = verify_resp.json()
    assert vrf["status"] == "VERIFIED"
    assert vrf["confidence"] == 94
    assert vrf["can_issue_certificate"] is True

    # 4. Generate Certificate (POST /api/assets/{asset_id}/certificate)
    cert_gen_resp = client.post(f"/api/assets/{asset_id}/certificate", headers=AUTH_HEADERS)
    assert cert_gen_resp.status_code == 201, f"Failed to generate certificate: {cert_gen_resp.text}"
    cert = cert_gen_resp.json()

    # Verify all 6 required fields from user prompt:
    # 1. Certificate ID
    assert "certificate_id" in cert
    assert cert["certificate_id"].startswith("CERT-2026-")
    cert_id = cert["certificate_id"]

    # 2. Asset ID
    assert cert["asset_id"] == asset_id

    # 3. Verification Status
    assert cert["verification_status"] == "VERIFIED"

    # 4. Evidence Confidence
    assert cert["evidence_confidence"] == 94

    # 5. Registration Date
    assert cert.get("registration_timestamp") is not None
    assert len(cert["registration_timestamp"]) >= 10

    # 6. QR Code
    assert "qr_code" in cert
    assert cert["qr_code"].startswith("data:image/svg+xml;base64,")

    # Auxiliary verification tokens
    cert_token = cert["certificate_token"]
    assert bool(cert_token)
    assert cert["verification_url"] == f"/certificates/verify/{cert_token}"

    # 5. Retrieve Certificate via GET /api/assets/{asset_id}/certificate
    get_cert_resp = client.get(f"/api/assets/{asset_id}/certificate", headers=AUTH_HEADERS)
    assert get_cert_resp.status_code == 200
    retrieved_cert = get_cert_resp.json()
    assert retrieved_cert["certificate_id"] == cert_id
    assert retrieved_cert["asset_id"] == asset_id
    assert retrieved_cert["verification_status"] == "VERIFIED"
    assert retrieved_cert["evidence_confidence"] == 94
    assert retrieved_cert["qr_code"] == cert["qr_code"]

    # 6. Retrieve Certificate by Certificate ID via GET /api/certificates/{certificate_id}
    by_id_resp = client.get(f"/api/certificates/{cert_id}", headers=AUTH_HEADERS)
    assert by_id_resp.status_code == 200
    by_id_cert = by_id_resp.json()
    assert by_id_cert["certificate_id"] == cert_id
    assert by_id_cert["asset_id"] == asset_id

    # 7. Safe Public QR Verification Endpoint (scanned via QR code)
    public_resp = client.get(f"/api/certificates/verify/{cert_token}")
    assert public_resp.status_code == 200
    pub_data = public_resp.json()
    assert pub_data["is_valid"] is True
    assert pub_data["certificate_id"] == cert_id
    assert pub_data["asset_id"] == asset_id
    assert pub_data["verification_status"] == "VERIFIED"
    assert pub_data["evidence_confidence"] == 94
    # Zero PII check: no citizen name or private financials
    assert "citizen_name" not in pub_data
    assert "documented_value" not in pub_data

    # 8. Check Database Persistence
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM asset_certificates WHERE certificate_id = ?;", (cert_id,))
    cert_row = cursor.fetchone()
    assert cert_row is not None, f"Certificate {cert_id} not found in asset_certificates table!"
    assert cert_row["asset_id"] == asset_id
    assert cert_row["certificate_token"] == cert_token
    assert cert_row["evidence_confidence"] == 94
    assert cert_row["verification_status"] == "VERIFIED"

    # Check asset table certificate token
    cursor.execute("SELECT certificate_token FROM assets WHERE asset_id = ?;", (asset_id,))
    asset_row = cursor.fetchone()
    assert asset_row["certificate_token"] == cert_token

    # Check audit event
    cursor.execute(
        "SELECT * FROM audit_events WHERE entity_type = 'CERTIFICATE' AND entity_id = ?;",
        (cert_id,)
    )
    audit_row = cursor.fetchone()
    assert audit_row is not None
    assert audit_row["event_type"] == "CERTIFICATE_GENERATED"

    conn.close()

    # 9. Verify Hash Chain Integrity
    chain_status = verify_audit_chain()
    assert chain_status.get("chain_valid", chain_status.get("is_valid")) is True
