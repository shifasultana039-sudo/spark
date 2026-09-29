"""
Test Suite for Step 17: Connect Frontend to Backend API Service.
Tests the 4 required features:
1. Login (POST /api/auth/login, POST /auth/login)
2. Get current user (GET /api/auth/me, GET /auth/me, GET /api/users/me)
3. Get assets (GET /api/assets, GET /assets)
4. Get claims (GET /api/claims, GET /claims)
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

CITIZEN_ID = "USR-006"     # Senthil Nathan (Citizen)
OFFICER_ID = "USR-007"     # Officer Rajesh V (Government Officer)
ADMIN_ID = "USR-001"       # Dr. Ananya Sharma (Admin)


# ==========================================
# 1. LOGIN TESTS
# ==========================================

def test_login_successful_by_user_id():
    """Verify citizen login returns access token and user profile."""
    response = client.post("/api/auth/login", json={"user_id": CITIZEN_ID})
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == CITIZEN_ID
    assert data["token_type"] == "bearer"
    assert data["user"]["user_id"] == CITIZEN_ID
    assert data["user"]["role"] == "CITIZEN"
    assert "Senthil" in data["user"]["name"]


def test_login_successful_by_username():
    """Verify login works with username field."""
    response = client.post("/api/auth/login", json={"username": OFFICER_ID})
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == OFFICER_ID
    assert data["user"]["role"] == "GOVERNMENT_OFFICER"


def test_login_successful_by_email():
    """Verify login works with email."""
    response = client.post("/api/auth/login", json={"email": "senthil.n@citizen.tn.gov.in"})
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == CITIZEN_ID
    assert data["user"]["user_id"] == CITIZEN_ID


def test_login_invalid_user():
    """Verify login fails with unknown identifier."""
    response = client.post("/api/auth/login", json={"user_id": "NON_EXISTENT_USER"})
    assert response.status_code == 401


def test_login_missing_identifier():
    """Verify login fails when no identifier is supplied."""
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 422 or response.status_code == 400


# ==========================================
# 2. GET CURRENT USER TESTS
# ==========================================

def test_get_current_user_authenticated():
    """Verify GET /api/auth/me returns current user profile when bearer token is provided."""
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    user = response.json()
    assert user["user_id"] == CITIZEN_ID
    assert user["role"] == "CITIZEN"
    assert user["household_ref"] == "HH-1001"


def test_get_current_user_via_users_me_alias():
    """Verify GET /api/users/me alias works seamlessly."""
    headers = {"Authorization": f"Bearer {OFFICER_ID}"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    user = response.json()
    assert user["user_id"] == OFFICER_ID
    assert user["role"] == "GOVERNMENT_OFFICER"


def test_get_current_user_unauthorized():
    """Verify GET /api/auth/me rejects requests without authentication."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token():
    """Verify GET /api/auth/me rejects invalid token."""
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer INVALID_TOKEN"})
    assert response.status_code == 401


# ==========================================
# 3. GET ASSETS TESTS
# ==========================================

def test_get_assets_citizen():
    """Verify GET /api/assets retrieves citizen's registered assets."""
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}
    response = client.get("/api/assets", headers=headers)
    assert response.status_code == 200
    assets = response.json()
    assert isinstance(assets, list)
    assert len(assets) > 0
    # Every asset returned must belong to this citizen/household
    for asset in assets:
        assert asset["household_ref"] == "HH-1001"
        assert "asset_id" in asset
        assert "category" in asset
        assert "documented_value" in asset


def test_get_assets_officer():
    """Verify GET /api/assets retrieves assets for government officer."""
    headers = {"Authorization": f"Bearer {OFFICER_ID}"}
    response = client.get("/api/assets", headers=headers)
    assert response.status_code == 200
    assets = response.json()
    assert isinstance(assets, list)
    assert len(assets) > 0


def test_get_assets_unauthorized():
    """Verify GET /api/assets rejects unauthenticated requests."""
    response = client.get("/api/assets")
    assert response.status_code == 401


# ==========================================
# 4. GET CLAIMS TESTS
# ==========================================

def test_get_claims_citizen():
    """Verify GET /api/claims retrieves citizen's disaster claims."""
    headers = {"Authorization": f"Bearer {CITIZEN_ID}"}
    response = client.get("/api/claims", headers=headers)
    assert response.status_code == 200
    claims = response.json()
    assert isinstance(claims, list)
    assert len(claims) > 0
    for claim in claims:
        assert claim["household_ref"] == "HH-1001"
        assert "claim_id" in claim
        assert "asset_id" in claim
        assert "damage_description" in claim
        assert "review_status" in claim


def test_get_claims_officer():
    """Verify GET /api/claims retrieves disaster claims for government officer."""
    headers = {"Authorization": f"Bearer {OFFICER_ID}"}
    response = client.get("/api/claims", headers=headers)
    assert response.status_code == 200
    claims = response.json()
    assert isinstance(claims, list)
    assert len(claims) > 0


def test_get_claims_unauthorized():
    """Verify GET /api/claims rejects unauthenticated requests."""
    response = client.get("/api/claims")
    assert response.status_code == 401
