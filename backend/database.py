"""
Database connection and schema initialization for ReliefChain AI.
Supports SQLite out of the box with standard SQL patterns ready for PostgreSQL.
"""

from pathlib import Path
from typing import Generator
from contextlib import contextmanager

try:
    from app.core.database import get_db, get_db_connection, dict_factory, check_db_health, DatabaseSession
    from app.core.config import get_database_engine, DATABASE_PATH
except (ImportError, ValueError):
    from .app.core.database import get_db, get_db_connection, dict_factory, check_db_health, DatabaseSession
    from .app.core.config import get_database_engine, DATABASE_PATH

def init_db():
    """Initializes tables for core disaster ops and asset verification & claims."""
    engine = get_database_engine()
    if engine == "postgresql":
        schema_file = Path(__file__).resolve().parent / "migrations" / "schema_postgres.sql"
        if schema_file.exists():
            with get_db() as session:
                cur = session.cursor()
                sql_content = schema_file.read_text(encoding="utf-8")
                statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
                for stmt in statements:
                    cur.execute(stmt + ";")
            return

    with get_db() as conn:
        cursor = conn.cursor()


        # 1. Users & Roles
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL,
            organization TEXT,
            wallet_address TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # 2. Locations (Tamil Nadu Simulation)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            district TEXT NOT NULL,
            state TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            population_affected INTEGER NOT NULL DEFAULT 0,
            severity TEXT NOT NULL,
            accessibility TEXT NOT NULL,
            medical_shortage TEXT DEFAULT 'LOW',
            water_shortage TEXT DEFAULT 'LOW',
            food_shortage TEXT DEFAULT 'LOW',
            shelter_shortage TEXT DEFAULT 'LOW',
            nearest_warehouse TEXT,
            distance_km REAL DEFAULT 0.0,
            estimated_delivery_minutes INTEGER DEFAULT 0,
            priority_score INTEGER DEFAULT 0,
            trust_score INTEGER DEFAULT 0,
            active_status TEXT DEFAULT 'ACTIVE'
        );
        """)

        # 3. Resources Inventory
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            unit TEXT NOT NULL,
            available_quantity INTEGER NOT NULL DEFAULT 0,
            reserved_quantity INTEGER NOT NULL DEFAULT 0,
            dispatched_quantity INTEGER NOT NULL DEFAULT 0,
            warehouse TEXT NOT NULL,
            critical_threshold INTEGER NOT NULL DEFAULT 100
        );
        """)

        # 4. Disaster Reports
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS disaster_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            location TEXT NOT NULL,
            sub_zone TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            description TEXT NOT NULL,
            people_affected INTEGER NOT NULL DEFAULT 0,
            severity TEXT NOT NULL,
            required_resources TEXT NOT NULL,
            evidence_available TEXT DEFAULT 'None',
            timestamp TEXT NOT NULL,
            trust_score INTEGER NOT NULL DEFAULT 50,
            source_reliability_score INTEGER DEFAULT 20,
            cross_confirmation_score INTEGER DEFAULT 0,
            evidence_score INTEGER DEFAULT 0,
            recency_score INTEGER DEFAULT 10,
            consistency_penalty INTEGER DEFAULT 0,
            verification_status TEXT NOT NULL DEFAULT 'PENDING_VERIFICATION',
            duplicate_cluster_id TEXT,
            is_contradictory INTEGER DEFAULT 0,
            safety_gate_note TEXT,
            content_hash TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # 5. AI Recommendations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id TEXT UNIQUE NOT NULL,
            location_id INTEGER,
            location_name TEXT NOT NULL,
            primary_report_id TEXT,
            priority_score INTEGER NOT NULL,
            confidence_score INTEGER NOT NULL,
            resource_type TEXT NOT NULL,
            recommended_quantity INTEGER NOT NULL,
            approved_quantity INTEGER,
            explanation TEXT NOT NULL,
            severity_score INTEGER DEFAULT 0,
            population_score INTEGER DEFAULT 0,
            shortage_score INTEGER DEFAULT 0,
            trust_score INTEGER DEFAULT 0,
            logistics_score INTEGER DEFAULT 0,
            alternative_considered TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            two_level_approval_required INTEGER DEFAULT 0,
            approved_by_supervisor_1 TEXT,
            approved_by_supervisor_2 TEXT,
            human_override INTEGER DEFAULT 0,
            override_reason TEXT,
            blockchain_tx_hash TEXT,
            block_number INTEGER,
            approver_wallet TEXT,
            report_hash TEXT,
            created_at TEXT NOT NULL,
            approved_at TEXT,
            dispatched_at TEXT
        );
        """)

        # 6. Disasters Registry
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS disasters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disaster_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            disaster_type TEXT NOT NULL,
            state TEXT NOT NULL,
            district TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            declared_at TEXT NOT NULL,
            description TEXT
        );
        """)

        # 7. Households
        cursor.execute("""
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

        # 8. Pre-Disaster Citizen Assets
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
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

        # 8. Asset Evidence Files
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id TEXT UNIQUE NOT NULL,
            asset_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            file_url TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            sha256_hash TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            uploader TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'VERIFIED',
            score_contribution INTEGER NOT NULL DEFAULT 10,
            captured_timestamp TEXT,
            metadata_json TEXT DEFAULT '{}',
            latitude REAL,
            longitude REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
        );
        """)

        # 10. Asset Verifications
        cursor.execute("""
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

        # 9. Asset Digital Certificates
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id TEXT UNIQUE NOT NULL,
            asset_id TEXT NOT NULL,
            certificate_token TEXT UNIQUE NOT NULL,
            verification_status TEXT NOT NULL,
            evidence_confidence INTEGER NOT NULL,
            evidence_hash TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            qr_payload TEXT NOT NULL,
            FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
        );
        """)

        # 10. Post-Disaster Claims
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS disaster_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT UNIQUE NOT NULL,
            asset_id TEXT NOT NULL,
            household_ref TEXT NOT NULL,
            disaster_id TEXT NOT NULL,
            damage_description TEXT NOT NULL,
            pre_disaster_verification_status TEXT NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'SUBMITTED',
            officer_decision TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
        );
        """)

        # 11. Claim Post-Disaster Evidence
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id TEXT UNIQUE NOT NULL,
            claim_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            file_url TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            sha256_hash TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            captured_timestamp TEXT,
            latitude REAL,
            longitude REAL,
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
        );
        """)

        # 12. AI Damage Assessments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS damage_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT UNIQUE NOT NULL,
            damage_detected INTEGER NOT NULL DEFAULT 1,
            damage_category TEXT NOT NULL,
            estimated_damage_percentage INTEGER NOT NULL,
            asset_match_confidence INTEGER NOT NULL,
            evidence_quality INTEGER NOT NULL,
            overall_confidence INTEGER NOT NULL,
            explanation TEXT NOT NULL,
            provider_name TEXT NOT NULL DEFAULT 'DEMO_CV_MODEL',
            assessment_mode TEXT DEFAULT 'DEMO_SIMULATION',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
        );
        """)

        # 13. Indicative Value Assessments & Compensation Estimates
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS value_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT UNIQUE NOT NULL,
            original_documented_value REAL NOT NULL,
            depreciation_percent REAL NOT NULL DEFAULT 0.0,
            reference_current_value REAL NOT NULL,
            estimated_damage_percentage INTEGER NOT NULL,
            indicative_loss_amount REAL NOT NULL,
            approved_compensation_amount REAL,
            officer_notes TEXT,
            is_ai_assisted INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
        );
        """)

        # 14. Field Inspections Queue
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS field_inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id TEXT UNIQUE NOT NULL,
            claim_id TEXT NOT NULL,
            assigned_officer TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            findings TEXT,
            damage_rating TEXT,
            report_file_url TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id)
        );
        """)

        # 16. Government Officer Reviews
        cursor.execute("""
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

        # 15. Anomaly & Duplicate Flags (Non-accusatory)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            flag_type TEXT NOT NULL,
            similarity_score INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        # 16. Tamper-Evident SHA-256 Chained Audit Trail
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id TEXT UNIQUE,
            timestamp TEXT NOT NULL,
            actor TEXT NOT NULL,
            role TEXT NOT NULL,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            description TEXT NOT NULL,
            evidence_hash TEXT,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            blockchain_tx_hash TEXT
        );
        """)

        # Schema evolution for audit_events (Step 10)
        cursor.execute("PRAGMA table_info(audit_events);")
        audit_cols = [c["name"] for c in cursor.fetchall()]
        if "audit_id" not in audit_cols:
            cursor.execute("ALTER TABLE audit_events ADD COLUMN audit_id TEXT;")
        if "evidence_hash" not in audit_cols:
            cursor.execute("ALTER TABLE audit_events ADD COLUMN evidence_hash TEXT;")

        # Backfill any null audit_ids
        cursor.execute("SELECT id FROM audit_events WHERE audit_id IS NULL;")
        missing_audit_ids = cursor.fetchall()
        for m in missing_audit_ids:
            row_id = m["id"]
            cursor.execute("UPDATE audit_events SET audit_id = ? WHERE id = ?;", (f"AUD-2026-{row_id:06d}", row_id))

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dr_report_id ON disaster_reports(report_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rec_recommendation_id ON recommendations(recommendation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_asset_id ON assets(asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_claim_id ON disaster_claims(claim_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_hash ON audit_events(event_hash);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_id ON audit_events(audit_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity_id ON audit_events(entity_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_households_ref ON households(household_ref);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_asset_id ON asset_verifications(asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_claim_id ON government_reviews(claim_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_entity_id ON anomaly_flags(entity_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_flag_type ON anomaly_flags(flag_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_status ON anomaly_flags(status);")
