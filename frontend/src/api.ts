import {
  SystemHealth,
  KpiData,
  OperationalLocation,
  DisasterReport,
  Recommendation,
  AuditVerification,
  UserRole,
  AuthResponse,
  Asset,
  CreateAssetPayload,
  EvidenceItem,
  AssetVerificationResult,
  AssetCertificate,
  Claim,
  CreateClaimPayload,
  ClaimEvidenceItem,
  DamageAssessment,
  ValueLossAssessment,
  DisasterEvent,
  AnomalyFlag,
  AnomalyListResponse,
  AuditRecordItem,
  AuditHistoryResponse,
  InspectionItem,
  InspectionDetail,
  InspectionFindingsRequest,
  InspectionSubmitRequest
} from './types'

const API_BASE = ((import.meta as any).env?.VITE_API_BASE_URL as string) || '/api'

let authToken: string | null = typeof window !== 'undefined' ? localStorage.getItem('reliefchain_auth_token') : null

export function setAuthToken(token: string | null) {
  authToken = token
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('reliefchain_auth_token', token)
    } else {
      localStorage.removeItem('reliefchain_auth_token')
    }
  }
}

export function getAuthToken(): string | null {
  if (!authToken && typeof window !== 'undefined') {
    authToken = localStorage.getItem('reliefchain_auth_token')
  }
  return authToken
}

function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken()
  const headers: Record<string, string> = {
    'Accept': 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/**
 * 1. Login
 * Authenticates against backend POST /auth/login and stores session token.
 */
export async function login(userIdOrPayload: string | { user_id?: string; username?: string; email?: string }): Promise<AuthResponse> {
  const body = typeof userIdOrPayload === 'string'
    ? { user_id: userIdOrPayload }
    : userIdOrPayload

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(body)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Login failed: ${res.statusText}`
    throw new Error(msg)
  }

  const data: AuthResponse = await res.json()
  setAuthToken(data.access_token)
  return data
}

/**
 * Clear authentication session and token.
 */
export function logout(): void {
  setAuthToken(null)
}

export interface RegisterPayload {
  name: string
  email: string
  role?: string
  organization?: string
  household_ref?: string
  password?: string
}

/**
 * Register a new user account (Citizen, Officer, Assessor) and store token.
 */
export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Registration failed: ${res.statusText}`
    throw new Error(msg)
  }

  const data: AuthResponse = await res.json()
  setAuthToken(data.access_token)
  return data
}

/**
 * 2. Get current user
 * Retrieves profile for currently authenticated user from GET /auth/me
 */
export async function getCurrentUser(): Promise<UserRole> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to get current user: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * 3. Get assets
 * Retrieves registered assets from GET /assets (scoped to current user/role)
 */
export async function getAssets(): Promise<Asset[]> {
  const res = await fetch(`${API_BASE}/assets`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to load assets: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves a single registered asset with verification status and metadata
 */
export async function getAsset(assetId: string): Promise<Asset> {
  const res = await fetch(`${API_BASE}/assets/${encodeURIComponent(assetId)}`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch asset: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Registers a new citizen asset
 */
export async function createAsset(payload: CreateAssetPayload): Promise<Asset> {
  const res = await fetch(`${API_BASE}/assets`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to create asset: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves all uploaded evidence items for an asset
 */
export async function getAssetEvidence(assetId: string): Promise<EvidenceItem[]> {
  const res = await fetch(`${API_BASE}/assets/${encodeURIComponent(assetId)}/evidence`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch evidence: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Uploads an evidence file with specified evidence type for an asset
 */
export async function uploadAssetEvidence(assetId: string, file: File, evidenceType: string): Promise<EvidenceItem> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('evidence_type', evidenceType)

  const token = getAuthToken()
  const headers: Record<string, string> = {
    'Accept': 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}/assets/${encodeURIComponent(assetId)}/evidence`, {
    method: 'POST',
    headers,
    body: formData
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to upload evidence: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves the current verification result and explanation for an asset
 */
export async function getAssetVerification(assetId: string): Promise<AssetVerificationResult> {
  const res = await fetch(`${API_BASE}/assets/${encodeURIComponent(assetId)}/verification`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch verification: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Triggers deterministic evidence verification evaluation for an asset
 */
export async function verifyAsset(assetId: string): Promise<AssetVerificationResult> {
  const res = await fetch(`${API_BASE}/assets/${encodeURIComponent(assetId)}/verify`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to verify asset: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves digital certificate for an asset (GET /assets/{asset_id}/certificate)
 */
export async function getAssetCertificate(assetId: string): Promise<AssetCertificate> {
  const res = await fetch(`${API_BASE}/assets/${encodeURIComponent(assetId)}/certificate`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch certificate: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Generates digital certificate for a verified asset (POST /assets/{asset_id}/certificate)
 */
export async function generateAssetCertificate(assetId: string): Promise<AssetCertificate> {
  const res = await fetch(`${API_BASE}/assets/${encodeURIComponent(assetId)}/certificate`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to generate certificate: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves digital certificate by Certificate ID (GET /certificates/{certificate_id})
 */
export async function getCertificateById(certificateId: string): Promise<AssetCertificate> {
  const res = await fetch(`${API_BASE}/certificates/${encodeURIComponent(certificateId)}`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to load certificate: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * 4. Get claims
 * Retrieves disaster claims from GET /claims (scoped to current user/role)
 */
export async function getClaims(): Promise<Claim[]> {
  const res = await fetch(`${API_BASE}/claims`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to load claims: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves single disaster claim by ID (GET /claims/{claim_id})
 */
export async function getClaim(claimId: string): Promise<Claim> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to load claim: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Creates a new disaster claim against a registered asset (POST /claims)
 */
export async function createClaim(payload: CreateClaimPayload): Promise<Claim> {
  const res = await fetch(`${API_BASE}/claims`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to submit claim: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves all post-disaster evidence items for a claim (GET /claims/{claim_id}/evidence)
 */
export async function getClaimEvidence(claimId: string): Promise<ClaimEvidenceItem[]> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/evidence`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch claim evidence: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Uploads post-disaster evidence file for a disaster claim (POST /claims/{claim_id}/evidence)
 * Supports: damaged photographs, damaged videos, inspection reports
 */
export async function uploadClaimEvidence(claimId: string, file: File, evidenceType: string): Promise<ClaimEvidenceItem> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('evidence_type', evidenceType)

  const token = getAuthToken()
  const headers: Record<string, string> = {
    'Accept': 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/evidence`, {
    method: 'POST',
    headers,
    body: formData
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to upload claim evidence: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Triggers Demo AI Damage Assessment for a claim (POST /claims/{claim_id}/assess)
 * Uses the existing demo AI assessment API (computer vision simulation)
 */
export async function runClaimDamageAssessment(claimId: string): Promise<DamageAssessment> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/assess`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to run damage assessment: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves latest damage assessment for a claim if available (GET /claims/{claim_id}/assessment)
 */
export async function getClaimDamageAssessment(claimId: string): Promise<DamageAssessment | null> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/assessment`, {
    headers: getAuthHeaders()
  })

  if (res.status === 404 || res.status === 204) {
    return null
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch damage assessment: ${res.statusText}`
    throw new Error(msg)
  }

  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

/**
 * Triggers Value / Loss Assessment for a claim (POST /claims/{claim_id}/loss-estimate)
 * Calculates indicative loss estimate based on documented asset value, depreciation, and damage %.
 */
export async function calculateClaimLossEstimate(
  claimId: string,
  payload?: { reference_value?: number; estimated_damage_percentage?: number }
): Promise<ValueLossAssessment> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/loss-estimate`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload || {})
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to calculate loss estimate: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves existing Value / Loss Assessment for a claim if available (GET /claims/{claim_id}/loss-estimate)
 */
export async function getClaimLossEstimate(claimId: string): Promise<ValueLossAssessment | null> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/loss-estimate`, {
    headers: getAuthHeaders()
  })

  if (res.status === 404 || res.status === 204) {
    return null
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch loss estimate: ${res.statusText}`
    throw new Error(msg)
  }

  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

/**
 * Retrieves list of declared disaster events (GET /disasters)
 */
export async function getDisasters(): Promise<DisasterEvent[]> {
  const res = await fetch(`${API_BASE}/disasters`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to load disasters: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

// Supporting existing platform endpoints
export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`)
  return res.json()
}

export async function fetchKpis(): Promise<KpiData> {
  const res = await fetch(`${API_BASE}/kpis`)
  if (!res.ok) throw new Error(`Failed to load KPIs: ${res.statusText}`)
  return res.json()
}

export async function fetchLocations(): Promise<OperationalLocation[]> {
  const res = await fetch(`${API_BASE}/locations`)
  if (!res.ok) throw new Error(`Failed to load locations: ${res.statusText}`)
  return res.json()
}

export async function fetchReports(): Promise<DisasterReport[]> {
  const res = await fetch(`${API_BASE}/reports?limit=15`)
  if (!res.ok) throw new Error(`Failed to load reports: ${res.statusText}`)
  return res.json()
}

export async function fetchRecommendations(): Promise<Recommendation[]> {
  const res = await fetch(`${API_BASE}/recommendations`)
  if (!res.ok) throw new Error(`Failed to load recommendations: ${res.statusText}`)
  return res.json()
}

export async function fetchAuditVerification(): Promise<AuditVerification> {
  const res = await fetch(`${API_BASE}/audit/verify`)
  if (!res.ok) throw new Error(`Failed to verify audit chain: ${res.statusText}`)
  return res.json()
}

export async function fetchUsers(): Promise<UserRole[]> {
  const res = await fetch(`${API_BASE}/users`)
  if (!res.ok) throw new Error(`Failed to load users: ${res.statusText}`)
  return res.json()
}


/**
 * Retrieves anomaly detection warnings for a claim (GET /claims/{claim_id}/anomalies)
 */
export async function getClaimAnomalies(claimId: string, rescan: boolean = false): Promise<AnomalyListResponse> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/anomalies${rescan ? '?rescan=true' : ''}`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch anomalies: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Retrieves audit history records relating to a claim entity and optional linked asset
 */
export async function getClaimAuditHistory(claimId: string, assetId?: string): Promise<AuditRecordItem[]> {
  const fetchForEntity = async (entId: string): Promise<AuditRecordItem[]> => {
    try {
      const res = await fetch(`${API_BASE}/audit?entity_id=${encodeURIComponent(entId)}&limit=100`, {
        headers: getAuthHeaders()
      })
      if (!res.ok) return []
      const data = await res.json()
      return data.events || (Array.isArray(data) ? data : [])
    } catch {
      return []
    }
  }

  const claimEvents = await fetchForEntity(claimId)
  const allEvents = [...claimEvents]

  if (assetId && assetId !== claimId) {
    const assetEvents = await fetchForEntity(assetId)
    const seen = new Set(allEvents.map((e) => e.record_id || e.id || `${e.event_type}_${e.timestamp}`))
    for (const ae of assetEvents) {
      const key = ae.record_id || ae.id || `${ae.event_type}_${ae.timestamp}`
      if (key && !seen.has(key)) {
        seen.add(key)
        allEvents.push(ae)
      }
    }
  }

  // Sort chronologically ascending
  allEvents.sort((a, b) => {
    const tA = new Date(a.timestamp || a.created_at || 0).getTime()
    const tB = new Date(b.timestamp || b.created_at || 0).getTime()
    return tA - tB
  })

  return allEvents
}

/**
 * Government Officer decision: Approve claim (POST /claims/{claim_id}/approve)
 */
export async function approveClaim(claimId: string, payload?: { approved_amount?: number; notes?: string }): Promise<Claim> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/approve`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload || {})
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to approve claim: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Government Officer decision: Request more evidence (POST /claims/{claim_id}/request-evidence)
 */
export async function requestClaimEvidence(claimId: string, payload: { notes: string; requested_types?: string[] }): Promise<Claim> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/request-evidence`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to request evidence: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Government Officer decision: Modify assessment (POST /claims/{claim_id}/modify-assessment)
 */
export async function modifyClaimAssessment(claimId: string, payload: { damage_percentage: number; damage_category?: string; notes: string }): Promise<Claim> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/modify-assessment`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to modify assessment: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Government Officer decision: Reject claim (POST /claims/{claim_id}/reject)
 */
export async function rejectClaim(claimId: string, payload: { reason: string; notes?: string }): Promise<Claim> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/reject`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to reject claim: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Government Officer decision: Forward for field inspection (POST /claims/{claim_id}/forward-inspection)
 */
export async function forwardClaimInspection(claimId: string, payload?: { inspector_notes?: string; assigned_sector?: string }): Promise<Claim> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/forward-inspection`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload || {})
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to forward for inspection: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * NGO / Field Assessor: Fetch assigned field inspections (GET /inspections)
 */
export async function getInspections(status?: string, claimId?: string): Promise<InspectionItem[]> {
  const params = new URLSearchParams()
  if (status && status !== 'ALL') params.append('status', status)
  if (claimId) params.append('claim_id', claimId)

  const url = `${API_BASE}/inspections${params.toString() ? `?${params.toString()}` : ''}`
  const res = await fetch(url, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch inspections: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * NGO / Field Assessor: Open inspection dossier (GET /inspections/{inspection_id})
 */
export async function getInspectionDetails(inspectionId: string): Promise<InspectionDetail> {
  const res = await fetch(`${API_BASE}/inspections/${encodeURIComponent(inspectionId)}`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch inspection details: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * NGO / Field Assessor: Add/update field findings (POST /inspections/{inspection_id}/findings)
 */
export async function updateInspectionFindings(
  inspectionId: string,
  payload: InspectionFindingsRequest
): Promise<InspectionDetail> {
  const res = await fetch(`${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/findings`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to update findings: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * NGO / Field Assessor: Upload inspection evidence (POST /inspections/{inspection_id}/evidence)
 */
export async function uploadInspectionEvidence(
  inspectionId: string,
  file: File,
  evidenceType: string = 'FIELD_PHOTO'
): Promise<InspectionDetail> {
  const token = getAuthToken()
  const formData = new FormData()
  formData.append('file', file)
  formData.append('evidence_type', evidenceType)

  const headers: Record<string, string> = {
    'Accept': 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/evidence`, {
    method: 'POST',
    headers,
    body: formData
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to upload evidence: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * NGO / Field Assessor: Submit final inspection report (POST /inspections/{inspection_id}/submit)
 */
export async function submitInspectionReport(
  inspectionId: string,
  payload: InspectionSubmitRequest
): Promise<InspectionDetail> {
  const res = await fetch(`${API_BASE}/inspections/${encodeURIComponent(inspectionId)}/submit`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to submit inspection report: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}

/**
 * Get inspection for a specific claim (GET /claims/{claim_id}/inspection)
 */
export async function getClaimInspection(claimId: string): Promise<InspectionDetail | null> {
  const res = await fetch(`${API_BASE}/claims/${encodeURIComponent(claimId)}/inspection`, {
    headers: getAuthHeaders()
  })

  if (res.status === 404) {
    return null
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    const msg = errorData?.detail || errorData?.error?.message || `Failed to fetch claim inspection: ${res.statusText}`
    throw new Error(msg)
  }

  return res.json()
}
