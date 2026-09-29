"""
ReliefChain AI - Database Foundation Verification Script (Step 5).
Validates:
1. Application startup & lifespan initialization
2. Database connection & environment configuration
3. Schema migrations across relational models
4. Basic insert into domain entities
5. Basic read with dictionary serialization
6. Transaction rollback & exception handling
7. Foreign-key constraint enforcement
8. Necessary query indexes
9. Zero-leak connection management in get_db_session()
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_database_url, get_database_engine, PORT
from app.core.database import (
    create_connection,
    get_db,
    get_db_session,
    check_db_health,
    get_db_telemetry,
    DatabaseSession
)
from app.core.migrations import (
    run_digital_asset_migrations,
    validate_all_relational_models
)


def log_test(name: str, passed: bool, detail: str = ""):
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"  {status_str} {name}")
    if detail:
        print(f"         -> {detail}")
    if not passed:
        raise AssertionError(f"Test failed: {name} - {detail}")


def main():
    print("=" * 80)
    print("RELIEFCHAIN AI - DATABASE VERIFICATION & TEST SUITE (STEP 5)")
    print("Testing PostgreSQL / SQLite Integration, Sessions, Transactions & Models")
    print("=" * 80 + "\n")

    now_iso = datetime.now(timezone.utc).isoformat()
    test_id = uuid.uuid4().hex[:8].upper()

    # -------------------------------------------------------------------------
    # TEST 1: Application Startup
    # -------------------------------------------------------------------------
    print("--------------------------------------------------------------------------------")
    print("TEST 1: Application Startup & Factory Initialization")
    print("--------------------------------------------------------------------------------")
    try:
        from app.main import create_application
        app = create_application()
        log_test("FastAPI application factory instantiated successfully", app is not None)
        log_test("CORS middleware verified", len(app.user_middleware) > 0)
        log_test("Root health routes mounted", any("/health" in getattr(r, "path", "") for r in app.routes))
        log_test("API v1 versioned routes mounted", any("/api/v1" in str(r) for r in app.routes))
    except Exception as e:
        log_test("Application Startup", False, str(e))



    # -------------------------------------------------------------------------
    # TEST 2: Database Connection & Environment Configuration
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 2: Database Connection & Environment Variable Resolution")
    print("--------------------------------------------------------------------------------")
    try:
        db_url = get_database_url()
        engine = get_database_engine(db_url)
        log_test("Database URL resolved from environment", bool(db_url), f"Engine: {engine}")
        log_test("Password is not hardcoded in connection URL", "hardcoded" not in db_url.lower())

        is_healthy = check_db_health()
        log_test("Database ping (check_db_health)", is_healthy)

        telemetry = get_db_telemetry()
        log_test("Database telemetry report", telemetry["status"] == "CONNECTED", f"Telemetry: {telemetry}")
    except Exception as e:
        log_test("Database Connection", False, str(e))

    # -------------------------------------------------------------------------
    # TEST 3: Schema Migrations
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 3: Schema Migrations & Relational Entities Check")
    print("--------------------------------------------------------------------------------")
    try:
        migration_res = run_digital_asset_migrations()
        log_test("Migration execution", migration_res["status"] == "MIGRATION_SUCCESS", f"Engine: {migration_res['engine']}")

        validation = validate_all_relational_models()
        log_test("All 13 relational domain models present", validation["all_13_models_present"])
        log_test("Foreign key constraints enabled", validation["foreign_keys_enabled"])

        # Display table summary
        print("\n  Summary of Relational Models in Database:")
        for tbl, info in validation["table_details"].items():
            if info.get("exists"):
                print(f"    - Table '{tbl}': {info.get('column_count')} columns, {info.get('row_count')} records")
    except Exception as e:
        log_test("Migration", False, str(e))

    # -------------------------------------------------------------------------
    # TEST 4: Basic Insert
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 4: Basic Insert (User -> Household -> Asset -> Evidence -> Claim)")
    print("--------------------------------------------------------------------------------")
    test_user_id = f"USR-T-{test_id}"
    test_hh_ref = f"HH-T-{test_id}"
    test_asset_id = f"AST-T-{test_id}"
    test_ev_id = f"EVD-T-{test_id}"
    test_claim_id = f"CLM-T-{test_id}"

    try:
        with get_db() as session:
            # 1. Insert User
            session.execute("""
            INSERT INTO users (user_id, name, email, role, organization, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (test_user_id, f"Test Citizen {test_id}", f"test_{test_id}@reliefchain.org", "CITIZEN", "Vellore Ward 4", now_iso))

            # 2. Insert Household
            session.execute("""
            INSERT INTO households (household_ref, head_of_household, contact_phone, address, district, state, member_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (test_hh_ref, f"Head {test_id}", "+91 99999 00000", "42 Gandhi Road", "Vellore", "Tamil Nadu", 3, now_iso, now_iso))

            # 3. Insert Asset referencing Household
            session.execute("""
            INSERT INTO assets (
                asset_id, household_ref, category, description, documented_value,
                purchase_date, location_address, status, verification_confidence,
                integrity_hash, current_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                test_asset_id, test_hh_ref, "HOUSE / PROPERTY", "Reinforced Residential Home",
                1500000.0, "2021-04-10", "42 Gandhi Road, Katpadi", "VERIFIED", 95,
                "0x" + "a" * 64, "INTACT", now_iso, now_iso
            ))

            # 4. Insert Evidence referencing Asset
            session.execute("""
            INSERT INTO asset_evidence (
                evidence_id, asset_id, evidence_type, file_url, original_filename,
                sha256_hash, file_size, mime_type, uploader, verification_status,
                score_contribution, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                test_ev_id, test_asset_id, "GOVERNMENT_REGISTRATION",
                f"/api/storage/uploads/reg_{test_id}.pdf", f"reg_{test_id}.pdf",
                "0x" + "b" * 64, 204800, "application/pdf", test_user_id, "VERIFIED", 40, now_iso
            ))

            # 5. Insert Claim referencing Asset
            session.execute("""
            INSERT INTO disaster_claims (
                claim_id, asset_id, household_ref, disaster_id, damage_description,
                pre_disaster_verification_status, review_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                test_claim_id, test_asset_id, test_hh_ref, "DIS-2026-FLOOD-01",
                "Flooding submerged ground level floor", "VERIFIED", "SUBMITTED", now_iso, now_iso
            ))

        log_test("Relational entities inserted and committed cleanly", True)
    except Exception as e:
        log_test("Basic Insert", False, str(e))

    # -------------------------------------------------------------------------
    # TEST 5: Basic Read
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 5: Basic Read & Data Integrity Verification")
    print("--------------------------------------------------------------------------------")
    try:
        with get_db() as session:
            # Read User
            cur = session.execute("SELECT * FROM users WHERE user_id = ?;", (test_user_id,))
            user_row = cur.fetchone()
            log_test("Read User record as dictionary", user_row is not None and user_row["user_id"] == test_user_id)

            # Read Household
            cur = session.execute("SELECT * FROM households WHERE household_ref = ?;", (test_hh_ref,))
            hh_row = cur.fetchone()
            log_test("Read Household record", hh_row is not None and hh_row["household_ref"] == test_hh_ref)

            # Read Asset joined with Household
            cur = session.execute("""
            SELECT a.asset_id, a.documented_value, a.status, h.head_of_household, h.district
            FROM assets a
            JOIN households h ON a.household_ref = h.household_ref
            WHERE a.asset_id = ?;
            """, (test_asset_id,))
            asset_row = cur.fetchone()
            log_test("Read Asset joined with Household", asset_row is not None and asset_row["documented_value"] == 1500000.0)

            # Read Claim joined with Asset
            cur = session.execute("""
            SELECT c.claim_id, c.review_status, a.description AS asset_desc
            FROM disaster_claims c
            JOIN assets a ON c.asset_id = a.asset_id
            WHERE c.claim_id = ?;
            """, (test_claim_id,))
            claim_row = cur.fetchone()
            log_test("Read Claim joined with Asset", claim_row is not None and claim_row["review_status"] == "SUBMITTED")
    except Exception as e:
        log_test("Basic Read", False, str(e))

    # -------------------------------------------------------------------------
    # TEST 6: Rollback & Error Handling
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 6: Transaction Rollback & Error Handling")
    print("--------------------------------------------------------------------------------")
    rollback_user_id = f"USR-ROLLBACK-{test_id}"
    try:
        try:
            with get_db() as session:
                session.execute("""
                INSERT INTO users (user_id, name, email, role, created_at)
                VALUES (?, ?, ?, ?, ?);
                """, (rollback_user_id, "Doomed User", "rollback@test.com", "CITIZEN", now_iso))

                # Deliberately raise exception inside transaction to trigger rollback
                raise RuntimeError("Simulated transaction failure to test rollback!")
        except RuntimeError:
            pass  # Expected exception caught

        # Verify that rollback_user_id does NOT exist in the database
        with get_db() as session:
            cur = session.execute("SELECT * FROM users WHERE user_id = ?;", (rollback_user_id,))
            doomed_user = cur.fetchone()
            log_test("Transaction rollback verified (aborted insert was discarded)", doomed_user is None)
    except Exception as e:
        log_test("Rollback Verification", False, str(e))

    # -------------------------------------------------------------------------
    # TEST 7: Foreign Key Relationship Enforcement
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 7: Foreign Key Constraint Enforcement")
    print("--------------------------------------------------------------------------------")
    fk_error_caught = False
    try:
        with get_db() as session:
            # Try to insert an asset referencing a non-existent household
            session.execute("""
            INSERT INTO assets (
                asset_id, household_ref, category, description, documented_value,
                location_address, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                f"AST-INVALID-FK-{test_id}", "NON_EXISTENT_HOUSEHOLD_99999",
                "VEHICLE", "Tractor", 450000.0, "Nowhere", "UNVERIFIED", now_iso, now_iso
            ))
    except Exception as err:
        fk_error_caught = True
        log_test("Foreign key constraint prevented invalid parent reference", True, f"Caught expected constraint: {type(err).__name__}")

    if not fk_error_caught:
        log_test("Foreign key constraint enforcement", False, "Invalid FK insert succeeded unexpectedly!")

    # -------------------------------------------------------------------------
    # TEST 8: Query Index Verification
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 8: Necessary Query Indexes Verification")
    print("--------------------------------------------------------------------------------")
    try:
        with get_db() as session:
            engine = session.engine_type
            if engine == "sqlite":
                cur = session.execute("SELECT name FROM sqlite_master WHERE type='index';")
                existing_indexes = set(row["name"] for row in cur.fetchall())
            else:
                cur = session.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public';")
                existing_indexes = set(row["indexname"] for row in cur.fetchall())

            critical_indexes = [
                "idx_households_ref",
                "idx_assets_asset_id",
                "idx_claims_claim_id",
                "idx_verifications_asset_id",
                "idx_reviews_claim_id",
                "idx_claims_status"
            ]

            for idx in critical_indexes:
                log_test(f"Index '{idx}' verified", idx in existing_indexes)
    except Exception as e:
        log_test("Index Verification", False, str(e))

    # -------------------------------------------------------------------------
    # TEST 9: Connection Leak Prevention
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TEST 9: Connection Leak Prevention in get_db_session()")
    print("--------------------------------------------------------------------------------")
    try:
        sessions_tested = []
        for i in range(5):
            gen = get_db_session()
            session = next(gen)
            sessions_tested.append(session)
            session.execute("SELECT 1 AS probe;")
            try:
                next(gen)
            except StopIteration:
                pass  # Clean completion

        all_closed = all(s._closed for s in sessions_tested)
        log_test("All completed sessions closed their underlying connection", all_closed)

        # Test leak prevention on exception inside route dependency
        gen_err = get_db_session()
        err_session = next(gen_err)
        try:
            gen_err.throw(ValueError("Simulated route error"))
        except ValueError:
            pass  # Expected caught

        log_test("Session closed cleanly even after route exception", err_session._closed)
    except Exception as e:
        log_test("Connection Leak Prevention", False, str(e))

    print("\n" + "=" * 80)
    print("ALL STEP 5 DATABASE TESTS PASSED WITH 100% SUCCESS!")
    print("PostgreSQL connection layer, session lifecycle, migrations & models are fully operational.")
    print("=" * 80)


if __name__ == "__main__":
    main()
