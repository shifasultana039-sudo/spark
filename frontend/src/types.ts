export interface SystemHealth {
  status: string
  database: string
  storage: string
  timestamp: string
}

export interface KpiData {
  total_reports: number
  verified_reports: number
  pending_recommendations: number
  approved_recommendations: number
  blockchain_anchored_decisions: number
  available_resources: number
  affected_population: number
  critical_zones: number
  timestamp: string
}

export interface OperationalLocation {
  id: number
  name: string
  district: string
  state: string
  latitude: number
  longitude: number
  population_affected: number
  severity: string
  accessibility: string
  medical_shortage: string
  water_shortage: string
  food_shortage: string
  shelter_shortage: string
  priority_score: number
  trust_score: number
}

export interface DisasterReport {
  id: number
  report_id: string
  source: string
  location: string
  sub_zone?: string
  description: string
  people_affected: number
  severity: string
  required_resources: string[]
  evidence_available: string
  trust_score: number
  verification_status: string
  duplicate_cluster_id?: string
  timestamp: string
}

export interface Recommendation {
  id: number
  recommendation_id: string
  location_name: string
  resource_type: string
  recommended_quantity: number
  approved_quantity?: number
  priority_score: number
  confidence_score: number
  explanation: string
  status: string
  blockchain_tx_hash?: string
  created_at: string
}

export interface AuditVerification {
  chain_valid: boolean
  total_events: number
  status: string
  latest_head_hash?: string
}

export interface UserRole {
  id: number
  user_id: string
  name: string
  email?: string
  role: string
  organization?: string
  household_ref?: string
  wallet_address?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserRole
}

export interface Asset {
  id?: number
  asset_id: string
  category: string
  description: string
  documented_value: number
  approximate_value?: number
  purchase_date?: string
  location?: string
  location_address: string
  household?: string
  household_ref?: string
  status: string
  citizen_name?: string
  verification_status?: string
  is_verified?: boolean
  has_certificate?: boolean
  certificate_id?: string
  verification_confidence?: number
  integrity_hash?: string
  certificate_token?: string
  qr_code_url?: string
  current_status?: string
  created_at: string
  updated_at?: string
}

export interface CreateAssetPayload {
  category: string
  description: string
  documented_value: number
  location_address: string
  purchase_date?: string
  household_ref?: string
}

export interface DisasterEvent {
  id?: number
  disaster_code: string
  name: string
  disaster_type: string
  state: string
  district: string
  severity: string
  status: string
  declared_at?: string
  description?: string
}

export interface CreateClaimPayload {
  asset_id: string
  damage_description: string
  disaster_id?: string
  disaster_event?: string
  household_ref?: string
}

export interface Claim {
  id?: number
  claim_id: string
  asset_id: string
  household?: string
  household_ref?: string
  disaster_id: string
  disaster_event?: string
  disaster_type?: string
  damage_description: string
  review_status: string
  claim_status?: string
  status?: string
  pre_disaster_verification_state?: string
  pre_disaster_verification_status?: string
  officer_decision?: string
  created_timestamp?: string
  created_at: string
  updated_at?: string
  citizen_id?: number
  asset_category?: string
  asset_description?: string
  location?: string
  location_address?: string
  evidence_confidence?: number
  damage_category?: string
  damage_percentage?: number
  estimated_damage_percentage?: number
}

export interface EvidenceItem {
  evidence_id: string
  asset_id: string
  evidence_type: string
  file_url: string
  original_filename: string
  sha256_hash: string
  file_size: number
  mime_type: string
  uploader: string
  verification_status: string
  score_contribution?: number
  captured_timestamp?: string
  created_at: string
  updated_at?: string
}

export interface ClaimEvidenceItem {
  evidence_id: string
  claim_id: string
  asset_id?: string
  evidence_type: string
  file_url: string
  original_filename: string
  sha256_hash: string
  file_size: number
  mime_type: string
  captured_timestamp?: string
  created_at: string
  uploader?: string
}

export interface EvidenceContribution {
  type: string
  display_name: string
  weight: number
  evidence_id?: string
  filename?: string
  verified?: boolean
}

export interface AssetVerificationResult {
  asset_id: string
  status: string
  confidence: number
  explanation: string
  contributions?: EvidenceContribution[]
  verification_id?: string
  evaluated_by?: string
  verified_at?: string
  can_issue_certificate?: boolean
}

export interface FrontendCertificateCard {
  card_title: string
  certificate_id: string
  asset_id: string
  badge: string
  category_label: string
  description: string
  verification_status: string
  confidence_score: string
  confidence_tier: string
  evidence_hash: string
  registration_date: string
  issued_date: string
  qr_code_data_uri: string
  verification_endpoint: string
  trust_seal: string
  issuer: string
}

export interface AssetCertificate {
  certificate_id: string
  asset_id: string
  category: string
  description: string
  verification_status: string
  evidence_confidence: number
  evidence_hash: string
  registration_timestamp: string
  verification_history?: any[]
  qr_code: string
  certificate_token: string
  issued_at: string
  verification_url: string
  qr_code_svg?: string
  frontend_card?: FrontendCertificateCard
}

export interface DamageAssessment {
  id?: number
  claim_id: string
  damage_detected: boolean
  damage_category: string
  estimated_damage_percentage: number
  asset_match_confidence: number
  evidence_quality: number
  overall_confidence: number
  explanation: string
  provider_name: string
  assessment_mode: string
  created_at: string
  updated_at?: string
}

export interface ValueLossAssessment {
  label: string
  disclaimer: string
  original_documented_value: number
  reference_current_value: number
  depreciation: number
  damage_percentage: number
  indicative_loss_estimate: number
  calculation_explanation: string
}

export interface AnomalyFlag {
  id?: number
  entity_type: string
  entity_id: string
  flag_type: string
  type?: string
  reason: string
  similarity_score?: number
  similarity?: number
  confidence?: number
  review_status: string
  related_record?: string
  created_at: string
  created_timestamp?: string
}

export interface AnomalyListResponse {
  claim_id: string
  total_anomalies: number
  review_status_summary: string
  anomalies: AnomalyFlag[]
}

export interface AuditRecordItem {
  id?: number
  record_id?: string
  event_type: string
  actor: string
  role?: string
  entity_type: string
  entity_id: string
  description?: string
  current_hash: string
  previous_hash?: string
  evidence_hash?: string
  timestamp: string
  created_at?: string
}

export interface AuditHistoryResponse {
  total: number
  chain_valid?: boolean
  events: AuditRecordItem[]
}

export interface InspectionItem {
  inspection_id: string
  claim_id: string
  asset_id: string
  assigned_officer: string
  assigned_inspector_id?: string
  assigned_inspector_name?: string
  inspection_sector?: string
  inspection_status: string
  special_instructions?: string
  field_findings?: string
  damage_severity_rating?: string
  report_file_url?: string
  report_submitted_at?: string
  submitted_by?: string
  created_at: string
  updated_at?: string
  // Joined Claim fields
  claim_status?: string
  disaster_type?: string
  incident_description?: string
  household_ref?: string
  claim_damage_percentage?: number
  claimed_amount?: number
  // Joined Asset fields
  asset_category?: string
  asset_description?: string
  asset_address?: string
  asset_declared_value?: number
}

export interface InspectionDetail extends InspectionItem {
  claim_evidence?: ClaimEvidenceItem[]
  asset_evidence?: EvidenceItem[]
  inspection_evidence?: ClaimEvidenceItem[]
}

export interface InspectionFindingsRequest {
  field_findings: string
  damage_severity_rating?: string
}

export interface InspectionSubmitRequest {
  field_findings: string
  damage_severity_rating: string
  report_file_url?: string
}
