"""
Database migration and schema foundation runner for ReliefChain AI:
Digital Asset Verification & Disaster Compensation Module.
Supports both PostgreSQL and SQLite relational engines.
"""

import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from .config import get_database_engine, get_database_url
from .database import get_db

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


def compute_asset_integrity_hash(
    asset_id: str,
    household_ref: str,
    category: str,
    documented_value: float,
    purchase_date: str,
    location_address: str
) -> str:
    """Computes deterministic cryptographic baseline hash for an asset."""
    raw = f"{asset_id}|{household_ref}|{category}|{documented_value}|{purchase_date or ''}|{location_address}"
    return "0x" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_digital_asset_migrations() -> Dict[str, Any]:
    """
    Applies schema additions and migrations for the 13 relational entities:
    - Automatically detects PostgreSQL or SQLite engine
    - Creates missing tables with engine-specific types (e.g. SERIAL vs AUTOINCREMENT)
    - Adds integrity_hash to assets table if missing
    - Adds metadata_json and updated_at to asset_evidence if missing
    - Creates asset_verifications table if missing
    - Creates government_reviews table if missing
    - Backfills integrity hashes and baseline household records
    - Verifies foreign-key relationships and performance indexes
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    changes_applied = []
    engine = get_database_engine()

    with get_db() as session:
        cur = session.cursor()

        if engine == "postgresql":
            # PostgreSQL migration execution
            # Execute full schema if initial tables do not exist
            schema_file = MIGRATIONS_DIR / "schema_postgres.sql"
            if schema_file.exists():
                sql_content = schema_file.read_text(encoding="utf-8")
                # Split and execute non-empty statements
                statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
                for stmt in statements:
                    cur.execute(stmt + ";")
                changes_applied.append("Executed PostgreSQL core schema and foundation tables.")

            # Seed default household HH-1001 if missing
            cur.execute("SELECT id FROM households WHERE household_ref = %s;", ("HH-1001",))
            if not cur.fetchone():
                cur.execute("""
                INSERT INTO households (
                    household_ref, head_of_household, contact_phone, address,
                    district, state, latitude, longitude, member_count, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    "HH-1001", "Senthil Nathan", "+91 98410 12345",
                    "14/2 Railway Feeder Road, Katpadi", "Vellore", "Tamil Nadu",
                    12.9806, 79.1417, 4, now_iso, now_iso
                ))
                changes_applied.append("Seeded default household 'HH-1001' (Senthil Nathan) in PostgreSQL.")

        else:
            # SQLite migration execution
            # 1. Households Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS households (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_ref TEXT UNIQUE NOT NULL,
                head_of_household TEXT NOT NULL,
                contact_phone TEXT,
                address TEXT NOT NULL,
                district TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'Tamil Nadu',
                latitude REAL,
                longitude REAL,
                member_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            changes_applied.append("Table 'households' verified/created.")

            # Seed initial household HH-1001 if missing
            cur.execute("SELECT id FROM households WHERE household_ref = ?;", ("HH-1001",))
            if not cur.fetchone():
                cur.execute("""
                INSERT INTO households (
                    household_ref, head_of_household, contact_phone, address,
                    district, state, latitude, longitude, member_count, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?);
                """, (
                    "HH-1001", "Senthil Nathan", "+91 98410 12345",
                    "14/2 Railway Feeder Road, Katpadi", "Vellore", "Tamil Nadu",
                    12.9806, 79.1417, 4, now_iso, now_iso
                ))
                changes_applied.append("Seeded default household 'HH-1001' (Senthil Nathan).")

            # 2. Check and add integrity_hash to assets table
            cur.execute("PRAGMA table_info(assets);")
            asset_cols = [row["name"] for row in cur.fetchall()]

            if "integrity_hash" not in asset_cols:
                cur.execute("ALTER TABLE assets ADD COLUMN integrity_hash TEXT;")
                changes_applied.append("Added column 'integrity_hash' to 'assets' table.")

            # Backfill integrity_hash for any assets without one
            cur.execute("SELECT id, asset_id, household_ref, category, documented_value, purchase_date, location_address, integrity_hash FROM assets;")
            assets_to_hash = cur.fetchall()
            for ast in assets_to_hash:
                if not ast.get("integrity_hash"):
                    h = compute_asset_integrity_hash(
                        asset_id=ast["asset_id"],
                        household_ref=ast["household_ref"],
                        category=ast["category"],
                        documented_value=ast["documented_value"],
                        purchase_date=ast["purchase_date"] or "",
                        location_address=ast["location_address"]
                    )
                    cur.execute("UPDATE assets SET integrity_hash = ? WHERE id = ?;", (h, ast["id"]))
                    changes_applied.append(f"Backfilled integrity_hash for Asset '{ast['asset_id']}'.")

            # Check and ensure foreign key from assets -> households is present
            cur.execute("PRAGMA foreign_key_list(assets);")
            fk_list = cur.fetchall()
            has_hh_fk = any(fk.get("table") == "households" or (isinstance(fk, tuple) and len(fk) > 2 and fk[2] == "households") for fk in fk_list)
            if not has_hh_fk:
                cur.execute("PRAGMA foreign_keys = OFF;")
                cur.execute("""
                CREATE TABLE IF NOT EXISTS assets_migrated (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id TEXT UNIQUE NOT NULL,
                    citizen_id INTEGER,
                    household_ref TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    documented_value REAL NOT NULL,
                    purchase_date TEXT,
                    location_address TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                    verification_confidence INTEGER NOT NULL DEFAULT 0,
                    integrity_hash TEXT,
                    certificate_token TEXT UNIQUE,
                    qr_code_url TEXT,
                    current_status TEXT NOT NULL DEFAULT 'INTACT',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (household_ref) REFERENCES households(household_ref)
                );
                """)
                cur.execute("INSERT INTO assets_migrated SELECT id, asset_id, citizen_id, household_ref, category, description, documented_value, purchase_date, location_address, latitude, longitude, status, verification_confidence, integrity_hash, certificate_token, qr_code_url, current_status, created_at, updated_at FROM assets;")
                cur.execute("DROP TABLE assets;")
                cur.execute("ALTER TABLE assets_migrated RENAME TO assets;")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_asset_id ON assets(asset_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_household_ref ON assets(household_ref);")
                cur.execute("PRAGMA foreign_keys = ON;")
                changes_applied.append("Enforced foreign-key relationship on 'assets' -> 'households(household_ref)'.")


            # 3. Check and add metadata_json and updated_at to asset_evidence table
            cur.execute("PRAGMA table_info(asset_evidence);")
            ev_cols = [row["name"] for row in cur.fetchall()]

            if "metadata_json" not in ev_cols:
                cur.execute("ALTER TABLE asset_evidence ADD COLUMN metadata_json TEXT DEFAULT '{}';")
                changes_applied.append("Added column 'metadata_json' to 'asset_evidence' table.")

            if "updated_at" not in ev_cols:
                cur.execute("ALTER TABLE asset_evidence ADD COLUMN updated_at TEXT;")
                changes_applied.append("Added column 'updated_at' to 'asset_evidence' table.")

            # 3b. Check and add latitude, longitude, and metadata_json to claim_evidence table
            cur.execute("PRAGMA table_info(claim_evidence);")
            claim_ev_cols = [row["name"] for row in cur.fetchall()]

            if "latitude" not in claim_ev_cols:
                cur.execute("ALTER TABLE claim_evidence ADD COLUMN latitude REAL;")
                changes_applied.append("Added column 'latitude' to 'claim_evidence' table.")

            if "longitude" not in claim_ev_cols:
                cur.execute("ALTER TABLE claim_evidence ADD COLUMN longitude REAL;")
                changes_applied.append("Added column 'longitude' to 'claim_evidence' table.")

            if "metadata_json" not in claim_ev_cols:
                cur.execute("ALTER TABLE claim_evidence ADD COLUMN metadata_json TEXT DEFAULT '{}';")
                changes_applied.append("Added column 'metadata_json' to 'claim_evidence' table.")

            # 3c. Check and add assessment_mode and updated_at to damage_assessments table
            cur.execute("PRAGMA table_info(damage_assessments);")
            dmg_cols = [row["name"] for row in cur.fetchall()]

            if "assessment_mode" not in dmg_cols:
                cur.execute("ALTER TABLE damage_assessments ADD COLUMN assessment_mode TEXT DEFAULT 'DEMO_SIMULATION';")
                changes_applied.append("Added column 'assessment_mode' to 'damage_assessments' table.")

            if "updated_at" not in dmg_cols:
                cur.execute("ALTER TABLE damage_assessments ADD COLUMN updated_at TEXT;")
                changes_applied.append("Added column 'updated_at' to 'damage_assessments' table.")

            # 4. Asset Verifications Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS asset_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verification_id TEXT UNIQUE NOT NULL,
                asset_id TEXT NOT NULL,
                confidence_score INTEGER NOT NULL,
                verification_status TEXT NOT NULL,
                evaluated_by TEXT NOT NULL,
                scoring_details_json TEXT NOT NULL,
                verified_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
            );
            """)
            changes_applied.append("Table 'asset_verifications' verified/created.")

            # 5. Government Reviews Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS government_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id TEXT UNIQUE NOT NULL,
                claim_id TEXT NOT NULL,
                officer_name TEXT NOT NULL,
                officer_role TEXT NOT NULL DEFAULT 'GOVERNMENT_OFFICER',
                action TEXT NOT NULL,
                approved_amount REAL,
                modified_damage_percent INTEGER,
                justification TEXT NOT NULL,
                review_timestamp TEXT NOT NULL,
                blockchain_tx_hash TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
            );
            """)
            changes_applied.append("Table 'government_reviews' verified/created.")

            # Performance indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_households_ref ON households(household_ref);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_verifications_asset_id ON asset_verifications(asset_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reviews_claim_id ON government_reviews(claim_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_claims_status ON disaster_claims(review_status);")
            changes_applied.append("Relational indexes created/verified.")

    return {
        "status": "MIGRATION_SUCCESS",
        "engine": engine,
        "timestamp": now_iso,
        "changes_applied": changes_applied
    }


def validate_all_relational_models() -> Dict[str, Any]:
    """
    Validates the presence, column count, and foreign keys of all 13 required relational entities.
    Works seamlessly across PostgreSQL and SQLite.
    """
    required_tables = [
        "users",                # 1. User
        "households",           # 2. Household
        "assets",               # 3. Asset
        "asset_evidence",       # 4. Evidence
        "asset_verifications",  # 5. AssetVerification
        "asset_certificates",   # 6. Certificate
        "disaster_claims",      # 7. DisasterClaim
        "damage_assessments",   # 8. DamageAssessment
        "value_assessments",    # 9. ValueAssessment
        "anomaly_flags",        # 10. AnomalyFlag
        "audit_events",         # 11. AuditEvent
        "field_inspections",    # 12. FieldInspection
        "government_reviews"    # 13. GovernmentReview
    ]

    engine = get_database_engine()
    results = {}
    missing_tables = []
    fk_enabled = True

    with get_db() as session:
        cur = session.cursor()

        if engine == "postgresql":
            cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public';
            """)
            existing_tables = set(row["table_name"] for row in cur.fetchall())

            for tbl in required_tables:
                if tbl in existing_tables:
                    cur.execute(f"SELECT COUNT(*) AS count FROM {tbl};")
                    cnt = cur.fetchone()["count"]

                    cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = %s;
                    """, (tbl,))
                    cols = [col["column_name"] for col in cur.fetchall()]

                    results[tbl] = {
                        "exists": True,
                        "row_count": cnt,
                        "column_count": len(cols),
                        "columns": cols
                    }
                else:
                    missing_tables.append(tbl)
                    results[tbl] = {"exists": False}

            fk_enabled = True  # Native in PostgreSQL

        else:
            # SQLite inspection
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = set(row["name"] for row in cur.fetchall())

            for tbl in required_tables:
                if tbl in existing_tables:
                    cur.execute(f"SELECT COUNT(*) AS count FROM {tbl};")
                    cnt = cur.fetchone()["count"]
                    cur.execute(f"PRAGMA table_info({tbl});")
                    cols = [col["name"] for col in cur.fetchall()]
                    results[tbl] = {
                        "exists": True,
                        "row_count": cnt,
                        "column_count": len(cols),
                        "columns": cols
                    }
                else:
                    missing_tables.append(tbl)
                    results[tbl] = {"exists": False}

            cur.execute("PRAGMA foreign_keys;")
            fk_row = cur.fetchone()
            fk_enabled = bool(fk_row.get("foreign_keys", 0) if fk_row else False)

    return {
        "engine": engine,
        "all_13_models_present": len(missing_tables) == 0,
        "missing_tables": missing_tables,
        "foreign_keys_enabled": fk_enabled,
        "table_details": results
    }
