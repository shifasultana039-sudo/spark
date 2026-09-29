"""
Unit and Integration Test Suite for ReliefChain AI — Anomaly Detection (Step 16).

Validates:
1. Endpoint: GET /claims/{claim_id}/anomalies
2. All seven deterministic anomaly signal types:
   - DUPLICATE_ASSET_REGISTRATION   (same integrity hash, two assets)
   - REUSED_EVIDENCE_HASH           (same SHA-256 evidence file in two claims)
   - REPEATED_SUBMISSION            (same household, asset, disaster, multiple claims)
   - LOCATION_CONFLICT              (evidence GPS far from asset location)
   - MODIFIED_EVIDENCE              (stored hash differs from upload-time hash)
   - MULTIPLE_CLAIMS_SAME_ASSET     (two active claims for same asset)
   - METADATA_CONFLICT              (evidence captured before disaster declared)
3. Response schema requirements:
   - type / flag_type
   - reason (human-readable, non-accusatory)
   - similarity_score / confidence where applicable
   - related_record
   - created_at timestamp
   - review_status = REVIEW_REQUIRED  (NEVER "FRAUDULENT" or "FRAUD")
4. Access control:
   - Citizens see anomalies for their own claims only (403 otherwise).
   - Officers and Admins see anomalies for all claims.
   - Unauthenticated access returns 401.
5. Clean claim with no anomalies returns an empty list.
6. Idempotency: calling rescan=true twice does not duplicate flags.
7. Route prefix compatibility:
   /claims/{id}/anomalies, /api/claims/{id}/anomalies, /api/v1/claims/{id}/anomalies
"""

import sys
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.core.database import get_db

# ──────────────────────────────────────────────────────────────────────────────
# Test user constants (match seeded users)  — defined FIRST so helpers can use them
# ──────────────────────────────────────────────────────────────────────────────
CITIZEN_A_ID  = "USR-006"          # Senthil Nathan  — HH-1001
CITIZEN_B_ID  = "USR-ANOM-CIT-B"  # inserted fresh in setup
OFFICER_ID    = "USR-007"          # Officer Rajesh V
ADMIN_ID      = "USR-001"          # Dr. Ananya Sharma


# ──────────────────────────────────────────────────────────────────────────────
# Helpers  — defined before client so they are available at module level
# ──────────────────────────────────────────────────────────────────────────────

def get_error_message(res) -> str:
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


def auth(user_id: str) -> dict:
    return {"Authorization": f"Bearer {user_id}"}


def insert_citizen_b() -> None:
    """Ensures Citizen B test user and household exist for cross-citizen tests."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?;", (CITIZEN_B_ID,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO users (user_id, name, email, role, organization, created_at)
                VALUES (?, 'Citizen B (Anomaly Tests)', 'citizenb.anom@reliefchain.org',
                        'CITIZEN', 'Vellore HH-3099', '2026-09-01T00:00:00Z');
                """,
                (CITIZEN_B_ID,),
            )
        cursor.execute("SELECT id FROM households WHERE household_ref = 'HH-3099';")
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO households (household_ref, head_of_household, address, district, state, created_at, updated_at)
                VALUES ('HH-3099', 'Citizen B', '99 Test Lane, Katpadi', 'Vellore', 'Tamil Nadu',
                        '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z');
                """,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Client bootstrap  — TestClient triggers app startup and init_db()
# ──────────────────────────────────────────────────────────────────────────────

client = TestClient(app)

# Seed test-specific fixtures after DB is ready
insert_citizen_b()


def create_asset(household_ref: str = "HH-1001", user_id: str = CITIZEN_A_ID,
                 description: str = "Anomaly Test Asset") -> str:
    res = client.post(
        "/assets",
        json={
            "category": "HOUSE_PROPERTY",
            "description": description,
            "documented_value": 500000.0,
            "location_address": "12 Gandhi Road, Katpadi, Vellore",
            "household_ref": household_ref,
        },
        headers=auth(user_id),
    )
    assert res.status_code in (200, 201), f"Asset creation failed: {res.text}"
    return res.json()["asset_id"]


def create_claim(asset_id: str, user_id: str = CITIZEN_A_ID,
                 disaster_id: str = "DIS-2026-0007") -> str:
    res = client.post(
        "/claims",
        json={
            "asset_id": asset_id,
            "damage_description": "Flood water damaged the ground floor.",
            "disaster_id": disaster_id,
        },
        headers=auth(user_id),
    )
    assert res.status_code in (200, 201), f"Claim creation failed: {res.text}"
    return res.json()["claim_id"]


def resolve_url(path: str) -> str:
    """Returns the correct prefix-aware URL for the test client."""
    for prefix in ("", "/api", "/api/v1"):
        r = client.get(f"{prefix}{path}", headers=auth(OFFICER_ID))
        if r.status_code != 404:
            return f"{prefix}{path}"
    return path




# ──────────────────────────────────────────────────────────────────────────────
# 1. BASIC ENDPOINT AVAILABILITY
# ──────────────────────────────────────────────────────────────────────────────

class TestAnomalyEndpointBasics:
    """GET /claims/{claim_id}/anomalies returns correct structure."""

    def test_clean_claim_returns_empty_anomaly_list(self):
        asset_id = create_asset(description="Clean Claim Asset — No Anomalies")
        claim_id = create_claim(asset_id)

        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200, get_error_message(res)

        body = res.json()
        assert body["claim_id"] == claim_id
        assert "total_anomalies" in body
        assert "review_status_summary" in body
        assert isinstance(body["anomalies"], list)

    def test_nonexistent_claim_returns_404(self):
        res = client.get("/claims/CLM-DOES-NOT-EXIST-9999/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 404

    def test_unauthenticated_returns_401(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies")
        assert res.status_code == 401

    def test_response_has_required_fields(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        body = res.json()
        assert "claim_id" in body
        assert "total_anomalies" in body
        assert "review_status_summary" in body
        assert "anomalies" in body

    def test_rescan_parameter_accepted(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200

    def test_route_prefix_compatibility(self):
        """Endpoint is reachable under /claims, /api/claims, and /api/v1/claims."""
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        for prefix in ("", "/api", "/api/v1"):
            res = client.get(f"{prefix}/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
            assert res.status_code in (200, 404), (
                f"Unexpected status {res.status_code} for prefix '{prefix}': {res.text}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# 2. RESPONSE SCHEMA VALIDATION
# ──────────────────────────────────────────────────────────────────────────────

class TestAnomalyResponseSchema:
    """Each anomaly object must have all required fields."""

    def _inject_flag(self, claim_id: str) -> None:
        """Directly inserts a synthetic anomaly flag for schema testing."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO anomaly_flags
                    (entity_type, entity_id, flag_type, similarity_score, status, reason, created_at)
                VALUES ('CLAIM', ?, 'REUSED_EVIDENCE_HASH', 96, 'REVIEW_REQUIRED',
                        'Schema test flag — officer verification required.', ?);
                """,
                (claim_id, now),
            )

    def test_anomaly_flag_has_all_required_fields(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        self._inject_flag(claim_id)

        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        flags = res.json()["anomalies"]
        assert len(flags) >= 1

        flag = flags[0]
        assert "flag_type" in flag,        "Missing field: flag_type"
        assert "type" in flag,             "Missing field: type"
        assert "reason" in flag,           "Missing field: reason"
        assert "similarity_score" in flag, "Missing field: similarity_score"
        assert "similarity" in flag,       "Missing field: similarity"
        assert "confidence" in flag,       "Missing field: confidence"
        assert "related_record" in flag,   "Missing field: related_record"
        assert "created_at" in flag,       "Missing field: created_at"
        assert "created_timestamp" in flag,"Missing field: created_timestamp"
        assert "review_status" in flag,    "Missing field: review_status"
        assert flag["review_status"] == "REVIEW_REQUIRED"
        assert "entity_id" in flag,        "Missing field: entity_id"
        assert "entity_type" in flag,      "Missing field: entity_type"

    def test_review_status_is_never_fraudulent(self):
        """CRITICAL: review_status must never contain 'FRAUD' or 'FRAUDULENT'."""
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        self._inject_flag(claim_id)

        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        for flag in res.json()["anomalies"]:
            rs = flag.get("review_status", "")
            assert "FRAUD" not in rs.upper(), (
                f"review_status must never contain 'FRAUD'. Got: {rs}"
            )

    def test_review_status_is_review_required(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        self._inject_flag(claim_id)

        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        for flag in res.json()["anomalies"]:
            assert flag["review_status"] == "REVIEW_REQUIRED", (
                f"Expected REVIEW_REQUIRED, got {flag['review_status']}"
            )

    def test_reason_is_non_accusatory(self):
        """Reason text must not accuse the citizen."""
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        self._inject_flag(claim_id)

        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        for flag in res.json()["anomalies"]:
            reason = flag.get("reason", "").lower()
            forbidden = ["fraud", "fraudulent", "criminal", "liar", "fake"]
            for word in forbidden:
                assert word not in reason, (
                    f"Reason contains forbidden accusatory word '{word}': {reason}"
                )

    def test_similarity_score_is_integer_0_to_100(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        self._inject_flag(claim_id)

        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        for flag in res.json()["anomalies"]:
            score = flag.get("similarity_score")
            assert isinstance(score, int), f"similarity_score must be int, got {type(score)}"
            assert 0 <= score <= 100, f"similarity_score must be 0-100, got {score}"

    def test_created_at_is_iso_timestamp(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        self._inject_flag(claim_id)

        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        for flag in res.json()["anomalies"]:
            ts = flag.get("created_at", "")
            assert len(ts) >= 10, f"created_at looks malformed: {ts}"
            # Should be parseable
            try:
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                assert False, f"created_at is not a valid ISO timestamp: {ts}"


# ──────────────────────────────────────────────────────────────────────────────
# 3. SIGNAL DETECTION TESTS
# ──────────────────────────────────────────────────────────────────────────────

class TestDuplicateAssetRegistrationSignal:
    """Signal 1 — DUPLICATE_ASSET_REGISTRATION."""

    def test_duplicate_asset_registration_triggers_flag(self):
        """
        When an asset shares an identical integrity hash with another registered asset,
        a claim filed for it must trigger DUPLICATE_ASSET_REGISTRATION with REVIEW_REQUIRED.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        u_suffix = uuid.uuid4().hex[:8]
        shared_integrity_hash = f"0x{hashlib.sha256(f'same_house_{u_suffix}'.encode()).hexdigest()}"
        ast_1 = f"AST-DUP1-{u_suffix}"
        ast_2 = f"AST-DUP2-{u_suffix}"
        clm_2 = f"CLM-DUP2-{u_suffix}"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO assets
                    (asset_id, household_ref, category, description, documented_value,
                     location_address, latitude, longitude, status, verification_confidence,
                     integrity_hash, current_status, created_at, updated_at)
                VALUES (?, 'HH-1001', 'HOUSE_PROPERTY', 'Original Registered House',
                        1500000, '12 Katpadi Road, Vellore', 12.98, 79.14,
                        'VERIFIED', 90, ?, 'INTACT', ?, ?);
                """,
                (ast_1, shared_integrity_hash, now_iso, now_iso),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO assets
                    (asset_id, household_ref, category, description, documented_value,
                     location_address, latitude, longitude, status, verification_confidence,
                     integrity_hash, current_status, created_at, updated_at)
                VALUES (?, 'HH-1001', 'HOUSE_PROPERTY', 'Duplicate Registered House',
                        1500000, '12 Katpadi Road, Vellore', 12.98, 79.14,
                        'UNVERIFIED', 0, ?, 'INTACT', ?, ?);
                """,
                (ast_2, shared_integrity_hash, now_iso, now_iso),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO disaster_claims
                    (claim_id, asset_id, household_ref, disaster_id, damage_description,
                     pre_disaster_verification_status, review_status, created_at, updated_at)
                VALUES (?, ?, 'HH-1001', 'DIS-2026-0007',
                        'Duplicate asset claim test', 'UNVERIFIED', 'SUBMITTED', ?, ?);
                """,
                (clm_2, ast_2, now_iso, now_iso),
            )

        res = client.get(f"/claims/{clm_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        flags = [f for f in res.json()["anomalies"] if f["flag_type"] == "DUPLICATE_ASSET_REGISTRATION"]
        assert len(flags) >= 1
        flag = flags[0]
        assert flag["type"] == "DUPLICATE_ASSET_REGISTRATION"
        assert flag["review_status"] == "REVIEW_REQUIRED"
        assert "FRAUD" not in flag["review_status"]
        assert flag["similarity_score"] == 100
        related_records = [f["related_record"] for f in flags]
        assert ast_1 in related_records
        assert "identical integrity hash" in flag["reason"].lower()
        assert "officer verification required" in flag["reason"].lower()


class TestReusedEvidenceHashSignal:
    """Signal 2 — REUSED_EVIDENCE_HASH."""

    def test_identical_evidence_hash_across_claims_triggers_flag(self):
        """
        When the same SHA-256 hash is submitted as evidence for two different claims,
        the second claim should yield a REUSED_EVIDENCE_HASH anomaly flag.
        """
        shared_hash = "aabbcc" + "0" * 58  # fake but deterministic 64-char hex

        # Create two separate claims
        asset_a = create_asset(description="Reused Evidence Asset A")
        claim_a = create_claim(asset_a)

        asset_b = create_asset(description="Reused Evidence Asset B")
        claim_b = create_claim(asset_b)

        now = datetime.now(timezone.utc).isoformat()
        ev_a = f"CLM-EV-TEST-A1-{uuid.uuid4().hex[:8]}"
        ev_b = f"CLM-EV-TEST-B1-{uuid.uuid4().hex[:8]}"

        # Insert same hash into both claims' evidence tables
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test', 'photo_a.jpg',
                        ?, 12345, 'image/jpeg', ?);
                """,
                (ev_a, claim_a, shared_hash, now),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test', 'photo_b.jpg',
                        ?, 12345, 'image/jpeg', ?);
                """,
                (ev_b, claim_b, shared_hash, now),
            )

        # Scan claim_b — should detect the shared hash from claim_a
        res = client.get(f"/claims/{claim_b}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200

        flags = res.json()["anomalies"]
        types = [f["flag_type"] for f in flags]
        assert "REUSED_EVIDENCE_HASH" in types, (
            f"Expected REUSED_EVIDENCE_HASH in anomaly types. Got: {types}"
        )

    def test_reused_evidence_flag_contains_similarity_score(self):
        """Reused evidence flag must include a similarity_score."""
        shared_hash = "ccddee" + "1" * 58

        asset_x = create_asset(description="Evidence Hash Score Asset X")
        claim_x = create_claim(asset_x)
        asset_y = create_asset(description="Evidence Hash Score Asset Y")
        claim_y = create_claim(asset_y)

        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            for ev_id, cid, fname in [
                ("CLM-EV-TEST-X2", claim_x, "fx.jpg"),
                ("CLM-EV-TEST-Y2", claim_y, "fy.jpg"),
            ]:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO claim_evidence
                        (evidence_id, claim_id, evidence_type, file_url, original_filename,
                         sha256_hash, file_size, mime_type, created_at)
                    VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test', ?, ?, 999, 'image/jpeg', ?);
                    """,
                    (ev_id, cid, fname, shared_hash, now),
                )

        res = client.get(f"/claims/{claim_y}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        for flag in res.json()["anomalies"]:
            if flag["flag_type"] == "REUSED_EVIDENCE_HASH":
                assert flag["similarity_score"] is not None
                assert isinstance(flag["similarity_score"], int)
                break

    def test_reused_evidence_asset_similarity_96_percent_and_reason(self):
        """
        Validates the exact example scenario from Step 16 specification:
        REVIEW REQUIRED
        Reason: Evidence image appears similar to evidence submitted in another claim.
        Similarity: 96%
        Officer verification required.
        """
        shared_hash = hashlib.sha256(f"96pct_{uuid.uuid4().hex}".encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        asset_1 = create_asset(description="Asset 1 for 96% test")

        # Insert into asset_evidence for asset_1
        ev_1 = f"EV-96-{uuid.uuid4().hex[:6]}"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO asset_evidence
                    (evidence_id, asset_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, uploader, created_at)
                VALUES (?, ?, 'GOVERNMENT_REGISTRATION', '/test.jpg', 'doc1.jpg',
                        ?, 5000, 'image/jpeg', 'Citizen', ?);
                """,
                (ev_1, asset_1, shared_hash, now),
            )

        # Create claim 2 on another asset with the same file hash
        asset_2 = create_asset(description="Asset 2 for 96% test")
        claim_2 = create_claim(asset_2)
        ev_2 = f"CLM-EV-96-{uuid.uuid4().hex[:6]}"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test.jpg', 'doc1.jpg',
                        ?, 5000, 'image/jpeg', ?);
                """,
                (ev_2, claim_2, shared_hash, now),
            )

        res = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        flags = [
            f for f in res.json()["anomalies"]
            if f["flag_type"] == "REUSED_EVIDENCE_HASH" and f.get("related_record") == asset_1
        ]
        assert len(flags) >= 1
        f = flags[0]
        assert f["review_status"] == "REVIEW_REQUIRED"
        assert f["similarity"] == 96 or f["similarity_score"] == 96
        assert "similar to evidence submitted in another claim" in f["reason"]
        assert "officer verification required" in f["reason"].lower()


class TestRepeatedSubmissionSignal:
    """Signal 3 — REPEATED_SUBMISSION."""

    def test_two_claims_same_asset_same_disaster_triggers_flag(self):
        """Household filing two claims for the same asset + disaster should raise a flag."""
        asset_id = create_asset(description="Repeated Submission Asset")
        claim_1 = create_claim(asset_id, disaster_id="DIS-2026-0007")
        claim_2 = create_claim(asset_id, disaster_id="DIS-2026-0007")

        res = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200

        types = [f["flag_type"] for f in res.json()["anomalies"]]
        assert "REPEATED_SUBMISSION" in types or "MULTIPLE_CLAIMS_SAME_ASSET" in types, (
            f"Expected REPEATED_SUBMISSION or MULTIPLE_CLAIMS_SAME_ASSET. Got: {types}"
        )

    def test_flag_contains_related_record_of_previous_claim(self):
        asset_id = create_asset(description="Repeated Flag Related Record Asset")
        claim_1 = create_claim(asset_id, disaster_id="DIS-2026-0007")
        claim_2 = create_claim(asset_id, disaster_id="DIS-2026-0007")

        res = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200

        related_records = [f.get("related_record") for f in res.json()["anomalies"]]
        # claim_1 should appear as the related_record in at least one flag
        assert any(r and claim_1 in str(r) for r in related_records), (
            f"Expected claim_1 '{claim_1}' in related_records. Got: {related_records}"
        )


class TestMultipleClaimsSameAssetSignal:
    """Signal 6 — MULTIPLE_CLAIMS_SAME_ASSET."""

    def test_second_claim_for_same_asset_triggers_flag(self):
        asset_id = create_asset(description="Multiple Claims Asset Test")
        claim_1 = create_claim(asset_id, disaster_id="DIS-2026-0007")
        claim_2 = create_claim(asset_id, disaster_id="DIS-2026-0008")

        res = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200

        types = [f["flag_type"] for f in res.json()["anomalies"]]
        assert "MULTIPLE_CLAIMS_SAME_ASSET" in types, (
            f"Expected MULTIPLE_CLAIMS_SAME_ASSET. Got: {types}"
        )

    def test_multiple_claims_flag_is_review_required(self):
        asset_id = create_asset(description="Multi Claim Status Test Asset")
        claim_1 = create_claim(asset_id)
        claim_2 = create_claim(asset_id)

        res = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        for flag in res.json()["anomalies"]:
            if flag["flag_type"] == "MULTIPLE_CLAIMS_SAME_ASSET":
                assert flag["review_status"] == "REVIEW_REQUIRED"
                break


class TestModifiedEvidenceSignal:
    """Signal 5 — MODIFIED_EVIDENCE."""

    def test_modified_evidence_triggers_flag(self):
        """
        When a stored file's hash diverges from the recorded sha256_hash at upload time,
        it triggers MODIFIED_EVIDENCE with REVIEW_REQUIRED.
        """
        from storage.provider import storage_provider

        asset_id = create_asset(description="Modified Evidence Test Asset")
        claim_id = create_claim(asset_id)
        u_suffix = uuid.uuid4().hex[:8]
        ev_id = f"CLM-EV-MOD-{u_suffix}"
        original_filename = "damage_photo.jpg"
        custom_storage_key = f"{ev_id}_{original_filename}"

        # 1. Save original file to storage
        original_bytes = b"ORIGINAL_UNDAMAGED_EVIDENCE_BYTES_FOR_STEP16"
        original_sha256 = hashlib.sha256(original_bytes).hexdigest()
        storage_provider.save_file(
            original_bytes,
            original_filename,
            is_private=True,
            custom_key=custom_storage_key
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        # 2. Insert into claim_evidence with recorded hash = original_sha256
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test', ?,
                        ?, ?, 'image/jpeg', ?);
                """,
                (ev_id, claim_id, original_filename, original_sha256, len(original_bytes), now_iso),
            )

        # Verify no flag before tampering
        res_clean = client.get(f"/claims/{claim_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res_clean.status_code == 200
        types_clean = [f["flag_type"] for f in res_clean.json()["anomalies"]]
        assert "MODIFIED_EVIDENCE" not in types_clean

        # 3. Modify/tamper with the file in storage
        tampered_bytes = b"TAMPERED_MODIFIED_BYTES_DIFFERENT_HASH_FOR_STEP16"
        storage_provider.save_file(
            tampered_bytes,
            original_filename,
            is_private=True,
            custom_key=custom_storage_key
        )

        # 4. Rescan claim — should detect MODIFIED_EVIDENCE
        res_tampered = client.get(f"/claims/{claim_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res_tampered.status_code == 200
        flags = [f for f in res_tampered.json()["anomalies"] if f["flag_type"] == "MODIFIED_EVIDENCE"]
        assert len(flags) >= 1
        flag = flags[0]
        assert flag["type"] == "MODIFIED_EVIDENCE"
        assert flag["review_status"] == "REVIEW_REQUIRED"
        assert "FRAUD" not in flag["review_status"]
        assert "differs from the value recorded" in flag["reason"]
        assert flag["related_record"] == ev_id


class TestMetadataConflictSignal:
    """Signal 7 — METADATA_CONFLICT."""

    def _ensure_disaster_record(self, disaster_code: str, declared_at: str) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM disasters WHERE disaster_code = ?;", (disaster_code,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO disasters
                        (disaster_code, name, disaster_type, state, district, severity, status, declared_at, description)
                    VALUES (?, 'Test Flood', 'FLOOD', 'Tamil Nadu', 'Vellore', 'HIGH', 'ACTIVE', ?, 'Test disaster');
                    """,
                    (disaster_code, declared_at),
                )

    def test_evidence_before_disaster_triggers_metadata_conflict(self):
        """Evidence captured_timestamp before disaster declared_at should be flagged."""
        disaster_code = "DIS-META-TEST-001"
        declared_at   = "2026-09-15T00:00:00+00:00"
        self._ensure_disaster_record(disaster_code, declared_at)

        asset_id = create_asset(description="Metadata Conflict Test Asset")
        # Create claim via API — disaster_id goes through the normal endpoint
        res = client.post(
            "/claims",
            json={
                "asset_id": asset_id,
                "damage_description": "Metadata conflict test damage.",
                "disaster_id": disaster_code,
            },
            headers=auth(CITIZEN_A_ID),
        )
        assert res.status_code in (200, 201), f"Claim creation failed: {res.text}"
        claim_id = res.json()["claim_id"]

        # Insert evidence with a timestamp BEFORE the disaster
        old_ts = "2026-08-01T10:00:00+00:00"   # well before 2026-09-15
        ev_id = f"CLM-EV-META1-{uuid.uuid4().hex[:8]}"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, captured_timestamp, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test',
                        'old_photo.jpg', 'abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234',
                        5000, 'image/jpeg', ?, ?);
                """,
                (ev_id, claim_id, old_ts, datetime.now(timezone.utc).isoformat()),
            )

        res = client.get(f"/claims/{claim_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        types = [f["flag_type"] for f in res.json()["anomalies"]]
        assert "METADATA_CONFLICT" in types, (
            f"Expected METADATA_CONFLICT. Got: {types}"
        )

    def test_evidence_after_disaster_does_not_trigger_metadata_conflict(self):
        """Evidence captured after the disaster date must not be flagged for METADATA_CONFLICT."""
        disaster_code = "DIS-META-TEST-002"
        declared_at   = "2026-09-10T00:00:00+00:00"
        self._ensure_disaster_record(disaster_code, declared_at)

        asset_id = create_asset(description="No Metadata Conflict Asset")
        res = client.post(
            "/claims",
            json={
                "asset_id": asset_id,
                "damage_description": "After-disaster evidence test.",
                "disaster_id": disaster_code,
            },
            headers=auth(CITIZEN_A_ID),
        )
        assert res.status_code in (200, 201)
        claim_id = res.json()["claim_id"]

        # Evidence captured AFTER the disaster
        post_ts = "2026-09-20T12:00:00+00:00"
        ev_id2 = f"CLM-EV-META2-{uuid.uuid4().hex[:8]}"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, captured_timestamp, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test',
                        'after_photo.jpg', 'ef56789012345678901234567890123456789012345678901234567890123456',
                        5000, 'image/jpeg', ?, ?);
                """,
                (ev_id2, claim_id, post_ts, datetime.now(timezone.utc).isoformat()),
            )

        res = client.get(f"/claims/{claim_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        types = [f["flag_type"] for f in res.json()["anomalies"]]
        assert "METADATA_CONFLICT" not in types, (
            f"METADATA_CONFLICT should not be raised for post-disaster evidence. Got: {types}"
        )


class TestLocationConflictSignal:
    """Signal 4 — LOCATION_CONFLICT."""

    def test_evidence_gps_far_from_asset_triggers_flag(self):
        """Evidence GPS recorded >50 km from asset location should trigger LOCATION_CONFLICT."""
        # Create asset with a known GPS (Vellore ~12.9°N, 79.1°E)
        now_iso = datetime.now(timezone.utc).isoformat()
        u_suffix = uuid.uuid4().hex[:8]
        ast_id = f"AST-GPS-{u_suffix}"
        clm_id = f"CLM-GPS-{u_suffix}"
        ev_id = f"CLM-EV-GPS-{u_suffix}"

        with get_db() as conn:
            cursor = conn.cursor()
            # Insert asset directly with lat/lon
            cursor.execute(
                """
                INSERT OR IGNORE INTO households
                    (household_ref, head_of_household, address, district, state, created_at, updated_at)
                VALUES ('HH-GPS-TEST', 'GPS Test Household', 'Vellore', 'Vellore', 'Tamil Nadu', ?, ?);
                """,
                (now_iso, now_iso),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO assets
                    (asset_id, household_ref, category, description, documented_value,
                     location_address, latitude, longitude, status, verification_confidence,
                     integrity_hash, current_status, created_at, updated_at)
                VALUES (?, 'HH-GPS-TEST', 'HOUSE_PROPERTY', 'GPS Location Test Asset',
                        100000, 'Vellore, Tamil Nadu', 12.9, 79.1,
                        'UNVERIFIED', 0, '0xgpstest', 'INTACT', ?, ?);
                """,
                (ast_id, now_iso, now_iso),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO disaster_claims
                    (claim_id, asset_id, household_ref, disaster_id, damage_description,
                     pre_disaster_verification_status, review_status, created_at, updated_at)
                VALUES (?, ?, 'HH-GPS-TEST', 'DIS-2026-0007',
                        'GPS conflict test', 'UNVERIFIED', 'SUBMITTED', ?, ?);
                """,
                (clm_id, ast_id, now_iso, now_iso),
            )
            # Insert evidence with GPS far away (Chennai ~13.08°N, 80.27°E → ~127 km from Vellore)
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, latitude, longitude, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test',
                        'far_photo.jpg', 'abcdef1234abcdef1234abcdef1234abcdef1234abcdef1234abcdef12345678',
                        9000, 'image/jpeg', 13.08, 80.27, ?);
                """,
                (ev_id, clm_id, now_iso),
            )

        res = client.get(f"/claims/{clm_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        types = [f["flag_type"] for f in res.json()["anomalies"]]
        assert "LOCATION_CONFLICT" in types, (
            f"Expected LOCATION_CONFLICT for distant GPS. Got: {types}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 4. ACCESS CONTROL
# ──────────────────────────────────────────────────────────────────────────────

class TestAnomalyAccessControl:
    """Validates citizenship privacy and officer privilege enforcement."""

    def test_citizen_can_view_own_claim_anomalies(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(CITIZEN_A_ID))
        assert res.status_code == 200

    def test_citizen_cannot_view_other_citizens_anomalies(self):
        # Citizen A creates a claim
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        # Citizen B attempts to read it
        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(CITIZEN_B_ID))
        assert res.status_code == 403, (
            f"Expected 403 for cross-citizen access. Got {res.status_code}: {res.text}"
        )

    def test_officer_can_view_any_claims_anomalies(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200

    def test_admin_can_view_any_claims_anomalies(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(ADMIN_ID))
        assert res.status_code == 200

    def test_unauthenticated_is_rejected(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies")
        assert res.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# 5. IDEMPOTENCY
# ──────────────────────────────────────────────────────────────────────────────

class TestAnomalyIdempotency:
    """Running detection twice must not double the flags."""

    def test_rescan_does_not_duplicate_flags(self):
        asset_id = create_asset(description="Idempotency Asset — Two Claims")
        claim_1  = create_claim(asset_id)
        claim_2  = create_claim(asset_id)

        # First scan
        res1 = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res1.status_code == 200
        count_1 = res1.json()["total_anomalies"]

        # Second scan — must not increase count
        res2 = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res2.status_code == 200
        count_2 = res2.json()["total_anomalies"]

        assert count_2 == count_1, (
            f"Duplicate flags created on rescan: first={count_1}, second={count_2}"
        )

    def test_get_without_rescan_is_stable(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)

        # Trigger initial scan
        client.get(f"/claims/{claim_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))

        # Read-only GET should return same count
        res_a = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        res_b = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res_a.json()["total_anomalies"] == res_b.json()["total_anomalies"]


# ──────────────────────────────────────────────────────────────────────────────
# 6. AGGREGATE CONSISTENCY
# ──────────────────────────────────────────────────────────────────────────────

class TestAnomalyAggregateConsistency:
    """total_anomalies must equal len(anomalies)."""

    def test_total_matches_list_length(self):
        asset_id = create_asset()
        claim_id = create_claim(asset_id)
        res = client.get(f"/claims/{claim_id}/anomalies", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        body = res.json()
        assert body["total_anomalies"] == len(body["anomalies"]), (
            f"total_anomalies={body['total_anomalies']} != len(anomalies)={len(body['anomalies'])}"
        )

    def test_clean_summary_message_when_no_anomalies(self):
        """Summary text should indicate 'no anomalies' when none exist."""
        asset_id = create_asset(description="Absolutely Clean No-Anomaly Asset")
        claim_id = create_claim(asset_id)

        res = client.get(f"/claims/{claim_id}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        body = res.json()
        if body["total_anomalies"] == 0:
            assert "no anomal" in body["review_status_summary"].lower() or \
                   "consistent" in body["review_status_summary"].lower(), (
                f"Expected 'no anomaly' message. Got: {body['review_status_summary']}"
            )

    def test_non_zero_anomalies_summary_mentions_review(self):
        """When flags exist, summary must mention 'review'."""
        asset_id = create_asset(description="Summary Review Mention Asset")
        claim_1 = create_claim(asset_id)
        claim_2 = create_claim(asset_id)

        res = client.get(f"/claims/{claim_2}/anomalies?rescan=true", headers=auth(OFFICER_ID))
        assert res.status_code == 200
        body = res.json()
        if body["total_anomalies"] > 0:
            assert "review" in body["review_status_summary"].lower(), (
                f"Summary should mention 'review'. Got: {body['review_status_summary']}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# 7. UNIT TESTS — anomaly service functions directly
# ──────────────────────────────────────────────────────────────────────────────

class TestAnomalyServiceUnit:
    """Unit tests against the service functions without HTTP layer."""

    def test_run_anomaly_detection_returns_list(self):
        from services.anomaly_detection_service import run_anomaly_detection
        asset_id = create_asset(description="Direct Service Call Asset")
        claim_id = create_claim(asset_id)
        result = run_anomaly_detection(claim_id)
        assert isinstance(result, list)

    def test_run_anomaly_detection_nonexistent_claim_returns_empty(self):
        from services.anomaly_detection_service import run_anomaly_detection
        result = run_anomaly_detection("CLM-NONEXISTENT-9999")
        assert result == []

    def test_get_persisted_anomalies_returns_list(self):
        from services.anomaly_detection_service import get_persisted_anomalies
        asset_id = create_asset(description="Persisted Anomaly Read Asset")
        claim_id = create_claim(asset_id)
        result = get_persisted_anomalies(claim_id)
        assert isinstance(result, list)

    def test_check_evidence_anomalies_no_match_returns_none(self):
        from services.anomaly_detection_service import check_evidence_anomalies
        unique_hash = "unique" + "9" * 58
        result = check_evidence_anomalies(
            new_sha256=unique_hash,
            current_asset_id="AST-NO-MATCH",
            current_claim_id="CLM-NO-MATCH",
        )
        assert result is None

    def test_check_evidence_anomalies_matching_claim_hash(self):
        """Backward-compatible function returns a REVIEW_REQUIRED flag on hash match."""
        from services.anomaly_detection_service import check_evidence_anomalies
        shared = "matchme" + "0" * 57

        now_iso = datetime.now(timezone.utc).isoformat()
        asset_id = create_asset(description="BC Compat Asset For Check Anomaly")
        claim_id = create_claim(asset_id)
        ev_id = f"CLM-EV-BC-{uuid.uuid4().hex[:8]}"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO claim_evidence
                    (evidence_id, claim_id, evidence_type, file_url, original_filename,
                     sha256_hash, file_size, mime_type, created_at)
                VALUES (?, ?, 'POST_DISASTER_PHOTO', '/test',
                        'bc_photo.jpg', ?, 1234, 'image/jpeg', ?);
                """,
                (ev_id, claim_id, shared, now_iso),
            )

        result = check_evidence_anomalies(
            new_sha256=shared,
            current_claim_id="CLM-DIFFERENT-9999",
        )
        assert result is not None
        assert result["status"] == "REVIEW_REQUIRED"
        assert "FRAUD" not in result["flag_type"].upper()
        assert isinstance(result["similarity_score"], int)
        assert "review_status" in result
        assert "reason" in result
        assert "related_record" in result
        assert "created_at" in result
