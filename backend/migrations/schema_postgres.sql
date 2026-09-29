-- ==============================================================================
-- ReliefChain AI - Complete PostgreSQL Schema Definition
-- Digital Asset Verification, Disaster Compensation, and Emergency Operations
-- PostgreSQL 14+ Compatible
-- ==============================================================================

-- 1. Users & Roles
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) NOT NULL,
    organization VARCHAR(255),
    wallet_address VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);

-- 2. Locations (Civic & Emergency Geographies)
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    population_affected INTEGER NOT NULL DEFAULT 0,
    severity VARCHAR(50) NOT NULL,
    accessibility VARCHAR(50) NOT NULL,
    medical_shortage VARCHAR(50) DEFAULT 'LOW',
    water_shortage VARCHAR(50) DEFAULT 'LOW',
    food_shortage VARCHAR(50) DEFAULT 'LOW',
    shelter_shortage VARCHAR(50) DEFAULT 'LOW',
    nearest_warehouse VARCHAR(255),
    distance_km DOUBLE PRECISION DEFAULT 0.0,
    estimated_delivery_minutes INTEGER DEFAULT 0,
    priority_score INTEGER DEFAULT 0,
    trust_score INTEGER DEFAULT 0,
    active_status VARCHAR(50) DEFAULT 'ACTIVE'
);
CREATE INDEX IF NOT EXISTS idx_locations_district ON locations(district);

-- 3. Emergency Relief Inventory Resources
CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    type VARCHAR(100) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    available_quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    dispatched_quantity INTEGER NOT NULL DEFAULT 0,
    warehouse VARCHAR(255) NOT NULL,
    critical_threshold INTEGER NOT NULL DEFAULT 100
);

-- 4. Multi-Source Disaster Incident Reports
CREATE TABLE IF NOT EXISTS disaster_reports (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) UNIQUE NOT NULL,
    source VARCHAR(100) NOT NULL,
    location VARCHAR(255) NOT NULL,
    sub_zone VARCHAR(100),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    description TEXT NOT NULL,
    people_affected INTEGER NOT NULL DEFAULT 0,
    severity VARCHAR(50) NOT NULL,
    required_resources TEXT NOT NULL,
    evidence_available VARCHAR(100) DEFAULT 'None',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trust_score INTEGER NOT NULL DEFAULT 50,
    source_reliability_score INTEGER DEFAULT 20,
    cross_confirmation_score INTEGER DEFAULT 0,
    evidence_score INTEGER DEFAULT 0,
    recency_score INTEGER DEFAULT 10,
    consistency_penalty INTEGER DEFAULT 0,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'PENDING_VERIFICATION',
    duplicate_cluster_id VARCHAR(100),
    is_contradictory INTEGER DEFAULT 0,
    safety_gate_note TEXT,
    content_hash VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dr_report_id ON disaster_reports(report_id);

-- 5. Explainable AI Resource Allocation Recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(100) UNIQUE NOT NULL,
    location_id INTEGER,
    location_name VARCHAR(255) NOT NULL,
    primary_report_id VARCHAR(100),
    priority_score INTEGER NOT NULL,
    confidence_score INTEGER NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    recommended_quantity INTEGER NOT NULL,
    approved_quantity INTEGER,
    explanation TEXT NOT NULL,
    severity_score INTEGER DEFAULT 0,
    population_score INTEGER DEFAULT 0,
    shortage_score INTEGER DEFAULT 0,
    trust_score INTEGER DEFAULT 0,
    logistics_score INTEGER DEFAULT 0,
    alternative_considered TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    two_level_approval_required INTEGER DEFAULT 0,
    approved_by_supervisor_1 VARCHAR(255),
    approved_by_supervisor_2 VARCHAR(255),
    human_override INTEGER DEFAULT 0,
    override_reason TEXT,
    blockchain_tx_hash VARCHAR(100),
    block_number INTEGER,
    approver_wallet VARCHAR(100),
    report_hash VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    dispatched_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_rec_recommendation_id ON recommendations(recommendation_id);

-- 6. Disasters Registry
CREATE TABLE IF NOT EXISTS disasters (
    id SERIAL PRIMARY KEY,
    disaster_code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    disaster_type VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    declared_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT
);
CREATE INDEX IF NOT EXISTS idx_disasters_code ON disasters(disaster_code);

-- 7. Households (Model 2)
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
CREATE INDEX IF NOT EXISTS idx_households_ref ON households(household_ref);

-- 8. Pre-Disaster Citizen Registered Assets (Model 3)
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    asset_id VARCHAR(100) UNIQUE NOT NULL,
    citizen_id INTEGER,
    household_ref VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    documented_value DOUBLE PRECISION NOT NULL,
    purchase_date VARCHAR(50),
    location_address TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    status VARCHAR(50) NOT NULL DEFAULT 'UNVERIFIED',
    verification_confidence INTEGER NOT NULL DEFAULT 0,
    integrity_hash VARCHAR(128),
    certificate_token VARCHAR(100) UNIQUE,
    qr_code_url TEXT,
    current_status VARCHAR(50) NOT NULL DEFAULT 'INTACT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (household_ref) REFERENCES households(household_ref) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_assets_asset_id ON assets(asset_id);
CREATE INDEX IF NOT EXISTS idx_assets_household_ref ON assets(household_ref);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);

-- 9. Asset Evidence Artifacts (Model 4)
CREATE TABLE IF NOT EXISTS asset_evidence (
    id SERIAL PRIMARY KEY,
    evidence_id VARCHAR(100) UNIQUE NOT NULL,
    asset_id VARCHAR(100) NOT NULL,
    evidence_type VARCHAR(100) NOT NULL,
    file_url TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    sha256_hash VARCHAR(128) NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    mime_type VARCHAR(100) NOT NULL DEFAULT 'image/jpeg',
    uploader VARCHAR(255) NOT NULL,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'VERIFIED',
    score_contribution INTEGER NOT NULL DEFAULT 10,
    captured_timestamp VARCHAR(50),
    metadata_json TEXT DEFAULT '{}',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_evidence_asset_id ON asset_evidence(asset_id);
CREATE INDEX IF NOT EXISTS idx_evidence_hash ON asset_evidence(sha256_hash);

-- 10. Asset Verifications (Model 5)
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
CREATE INDEX IF NOT EXISTS idx_verifications_asset_id ON asset_verifications(asset_id);

-- 11. Asset Digital Certificates (Model 6)
CREATE TABLE IF NOT EXISTS asset_certificates (
    id SERIAL PRIMARY KEY,
    certificate_id VARCHAR(100) UNIQUE NOT NULL,
    asset_id VARCHAR(100) NOT NULL,
    certificate_token VARCHAR(100) UNIQUE NOT NULL,
    verification_status VARCHAR(50) NOT NULL,
    evidence_confidence INTEGER NOT NULL,
    evidence_hash VARCHAR(128) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    qr_payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_certs_asset_id ON asset_certificates(asset_id);
CREATE INDEX IF NOT EXISTS idx_certs_token ON asset_certificates(certificate_token);

-- 12. Post-Disaster Claims (Model 7)
CREATE TABLE IF NOT EXISTS disaster_claims (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(100) UNIQUE NOT NULL,
    asset_id VARCHAR(100) NOT NULL,
    household_ref VARCHAR(100) NOT NULL,
    disaster_id VARCHAR(100) NOT NULL,
    damage_description TEXT NOT NULL,
    pre_disaster_verification_status VARCHAR(50) NOT NULL,
    review_status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
    officer_decision TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_claims_claim_id ON disaster_claims(claim_id);
CREATE INDEX IF NOT EXISTS idx_claims_asset_id ON disaster_claims(asset_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON disaster_claims(review_status);

-- 13. Claim Evidence
CREATE TABLE IF NOT EXISTS claim_evidence (
    id SERIAL PRIMARY KEY,
    evidence_id VARCHAR(100) UNIQUE NOT NULL,
    claim_id VARCHAR(100) NOT NULL,
    evidence_type VARCHAR(100) NOT NULL,
    file_url TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    sha256_hash VARCHAR(128) NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    mime_type VARCHAR(100) NOT NULL,
    captured_timestamp VARCHAR(50),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim_id ON claim_evidence(claim_id);

-- 14. Computer Vision Damage Assessments (Model 8)
CREATE TABLE IF NOT EXISTS damage_assessments (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(100) UNIQUE NOT NULL,
    damage_detected INTEGER NOT NULL DEFAULT 1,
    damage_category VARCHAR(50) NOT NULL,
    estimated_damage_percentage INTEGER NOT NULL,
    asset_match_confidence INTEGER NOT NULL,
    evidence_quality INTEGER NOT NULL,
    overall_confidence INTEGER NOT NULL,
    explanation TEXT NOT NULL,
    provider_name VARCHAR(100) NOT NULL DEFAULT 'DEMO_CV_MODEL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_damage_claim_id ON damage_assessments(claim_id);

-- 15. Value Assessments & Indicative Loss Amounts (Model 9)
CREATE TABLE IF NOT EXISTS value_assessments (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(100) UNIQUE NOT NULL,
    original_documented_value DOUBLE PRECISION NOT NULL,
    depreciation_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    reference_current_value DOUBLE PRECISION NOT NULL,
    estimated_damage_percentage INTEGER NOT NULL,
    indicative_loss_amount DOUBLE PRECISION NOT NULL,
    approved_compensation_amount DOUBLE PRECISION,
    officer_notes TEXT,
    is_ai_assisted INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_value_claim_id ON value_assessments(claim_id);

-- 16. Field Inspections Queue (Model 12)
CREATE TABLE IF NOT EXISTS field_inspections (
    id SERIAL PRIMARY KEY,
    inspection_id VARCHAR(100) UNIQUE NOT NULL,
    claim_id VARCHAR(100) NOT NULL,
    assigned_officer VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    findings TEXT,
    damage_rating VARCHAR(50),
    report_file_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (claim_id) REFERENCES disaster_claims(claim_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_inspections_claim_id ON field_inspections(claim_id);

-- 17. Government Officer Reviews (Model 13)
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
CREATE INDEX IF NOT EXISTS idx_reviews_claim_id ON government_reviews(claim_id);

-- 18. Anomaly & Duplicate Flags (Model 10)
CREATE TABLE IF NOT EXISTS anomaly_flags (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    flag_type VARCHAR(100) NOT NULL,
    similarity_score INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'REVIEW_REQUIRED',
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_anomalies_entity ON anomaly_flags(entity_type, entity_id);

-- 19. Tamper-Evident SHA-256 Audit Trail (Model 11)
CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    previous_hash VARCHAR(128) NOT NULL,
    event_hash VARCHAR(128) NOT NULL,
    blockchain_tx_hash VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS idx_audit_event_hash ON audit_events(event_hash);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id);
