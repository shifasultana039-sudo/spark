-- ==============================================================================
-- ReliefChain AI - Database Migration 001: Digital Asset & Compensation Foundation
-- PostgreSQL Dialect (Supports PostgreSQL 14+)
-- ==============================================================================

-- 1. Households Table (Civic registry linking citizen households to assets and claims)
CREATE TABLE IF NOT EXISTS households (
    id SERIAL PRIMARY KEY,
    household_ref VARCHAR(100) UNIQUE NOT NULL,
    head_of_household VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    address TEXT NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL DEFAULT 'Tamil Nadu',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    member_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Asset Verifications Table (Audit evaluations recording transparent scoring)
CREATE TABLE IF NOT EXISTS asset_verifications (
    id SERIAL PRIMARY KEY,
    verification_id VARCHAR(100) UNIQUE NOT NULL,
    asset_id VARCHAR(100) NOT NULL,
    confidence_score INTEGER NOT NULL,
    verification_status VARCHAR(50) NOT NULL,
    evaluated_by VARCHAR(255) NOT NULL,
    scoring_details_json TEXT NOT NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

-- 3. Government Officer Reviews Table (Human-in-the-loop claim decision records)
CREATE TABLE IF NOT EXISTS government_reviews (
    id SERIAL PRIMARY KEY,
    review_id VARCHAR(100) UNIQUE NOT NULL,
    claim_id VARCHAR(100) NOT NULL,
    officer_name VARCHAR(255) NOT NULL,
    officer_role VARCHAR(100) NOT NULL DEFAULT 'GOVERNMENT_OFFICER',
    action VARCHAR(50) NOT NULL,
    approved_amount DOUBLE PRECISION,
    modified_damage_percent INTEGER,
    justification TEXT NOT NULL,
    review_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    blockchain_tx_hash VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
);

-- Targeted Indexes
CREATE INDEX IF NOT EXISTS idx_households_ref ON households(household_ref);
CREATE INDEX IF NOT EXISTS idx_verifications_asset_id ON asset_verifications(asset_id);
CREATE INDEX IF NOT EXISTS idx_reviews_claim_id ON government_reviews(claim_id);
