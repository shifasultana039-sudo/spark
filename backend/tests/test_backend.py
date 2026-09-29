"""
Sanity tests for ReliefChain AI backend.
Verifies health checks, database connections, KPI calculations, and cryptographic audit integrity.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    # Test root /health
    res_root = client.get("/health")
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert data_root["status"] == "HEALTHY"
    assert data_root["database"] == "CONNECTED"
    assert data_root["storage"] == "ACCESSIBLE"

    # Test /api/health
    res_api = client.get("/api/health")
    assert res_api.status_code == 200

    # Test /api/v1/health
    res_v1 = client.get("/api/v1/health")
    assert res_v1.status_code == 200
    assert res_v1.json()["status"] == "HEALTHY"

    print("[PASS] test_health_check passed (/health, /api/health, /api/v1/health)")

def test_kpis():
    response = client.get("/api/kpis")
    assert response.status_code == 200
    data = response.json()
    assert data["total_reports"] >= 40
    assert data["available_resources"] > 0
    assert data["affected_population"] > 0
    print(f"[PASS] test_kpis passed (total_reports={data['total_reports']}, available_resources={data['available_resources']})")

def test_locations():
    response = client.get("/api/locations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    names = [loc["name"] for loc in data]
    assert any("Katpadi" in n for n in names)
    assert any("Vellore" in n for n in names)
    print(f"[PASS] test_locations passed ({len(data)} zones)")

def test_resources():
    response = client.get("/api/resources")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    types = [r["type"] for r in data]
    assert "MEDICAL" in types
    assert "WATER" in types
    print("[PASS] test_resources passed")

def test_audit_verification():
    response = client.get("/api/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["chain_valid"] is True
    assert data["status"] == "VERIFIED_TAMPER_EVIDENT"
    print(f"[PASS] test_audit_verification passed ({data['total_events']} chained events verified)")

if __name__ == "__main__":
    test_health_check()
    test_kpis()
    test_locations()
    test_resources()
    test_audit_verification()
    print("\nALL BACKEND SANITY TESTS PASSED SUCCESSFULLY!")
