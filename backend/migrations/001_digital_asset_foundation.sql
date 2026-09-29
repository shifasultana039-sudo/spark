-- ==============================================================================
-- ReliefChain AI - Database Migration 001: Digital Asset & Compensation Foundation
-- Supported on SQLite 3.35+ and PostgreSQL 14+
-- ==============================================================================

-- 1. Households Table (Civic registry linking citizen households to assets and claims)
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

-- 2. Asset Verifications Table (Audit evaluations recording transparent scoring)
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

-- 3. Government Officer Reviews Table (Human-in-the-loop claim decision records)
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_households_ref ON households(household_ref);
CREATE INDEX IF NOT EXISTS idx_verifications_asset_id ON asset_verifications(asset_id);
CREATE INDEX IF NOT EXISTS idx_reviews_claim_id ON government_reviews(claim_id);
