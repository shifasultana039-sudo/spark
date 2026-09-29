import React, { useEffect, useState } from 'react'
import {
  ShieldCheck,
  FileText,
  Boxes,
  MapPin,
  RefreshCw,
  AlertCircle,
  Eye,
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  Sparkles,
  Calculator,
  Paperclip,
  Camera,
  Video,
  Search,
  Filter,
  Shield,
  Building,
  HelpCircle,
  Sliders,
  XCircle,
  Compass,
  Clock,
  History,
  Lock,
  Calendar,
  X,
  ClipboardCheck
} from 'lucide-react'
import {
  Claim,
  Asset,
  EvidenceItem,
  ClaimEvidenceItem,
  DamageAssessment,
  ValueLossAssessment,
  AnomalyListResponse,
  AuditRecordItem,
  UserRole,
  InspectionDetail
} from './types'
import {
  getClaims,
  getClaim,
  getAsset,
  getAssetEvidence,
  getClaimEvidence,
  getClaimDamageAssessment,
  getClaimLossEstimate,
  getClaimAnomalies,
  getClaimAuditHistory,
  approveClaim,
  requestClaimEvidence,
  modifyClaimAssessment,
  rejectClaim,
  forwardClaimInspection,
  getClaimInspection
} from './api'
import { AuditTimeline } from './AuditTimeline'

interface OfficerDashboardProps {
  currentUser?: UserRole | null
  onBackToDashboard?: () => void
}

type ActionModalType = 'APPROVE' | 'REQUEST_EVIDENCE' | 'MODIFY_ASSESSMENT' | 'REJECT' | 'FORWARD_INSPECTION' | null

export function OfficerDashboard({ currentUser, onBackToDashboard }: OfficerDashboardProps) {
  const [claims, setClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Filters & search
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  // Selected claim for the Claim Review page
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null)
  const [reviewClaim, setReviewClaim] = useState<Claim | null>(null)
  const [reviewAsset, setReviewAsset] = useState<Asset | null>(null)
  const [preDisasterEvidence, setPreDisasterEvidence] = useState<EvidenceItem[]>([])
  const [postDisasterEvidence, setPostDisasterEvidence] = useState<ClaimEvidenceItem[]>([])
  const [reviewAssessment, setReviewAssessment] = useState<DamageAssessment | null>(null)
  const [reviewLoss, setReviewLoss] = useState<ValueLossAssessment | null>(null)
  const [anomaliesData, setAnomaliesData] = useState<AnomalyListResponse | null>(null)
  const [auditHistory, setAuditHistory] = useState<AuditRecordItem[]>([])
  const [reviewInspection, setReviewInspection] = useState<InspectionDetail | null>(null)
  const [reviewLoading, setReviewLoading] = useState<boolean>(false)
  const [reviewError, setReviewError] = useState<string | null>(null)

  // Action decision modals & state
  const [actionModal, setActionModal] = useState<ActionModalType>(null)
  const [actionLoading, setActionLoading] = useState<boolean>(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Decision inputs
  const [approveAmount, setApproveAmount] = useState<string>('')
  const [approveNotes, setApproveNotes] = useState<string>('')
  const [evidenceNotes, setEvidenceNotes] = useState<string>('')
  const [modifyDamagePct, setModifyDamagePct] = useState<number>(50)
  const [modifyCategory, setModifyCategory] = useState<string>('MODERATE_DAMAGE')
  const [modifyNotes, setModifyNotes] = useState<string>('')
  const [rejectReason, setRejectReason] = useState<string>('')
  const [rejectNotes, setRejectNotes] = useState<string>('')
  const [forwardNotes, setForwardNotes] = useState<string>('')
  const [forwardSector, setForwardSector] = useState<string>('Katpadi Sector 4')

  const loadClaims = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getClaims()
      setClaims(data)
    } catch (err: any) {
      console.error('Failed to load officer claims:', err)
      setError(err.message || 'Failed to load claims list.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadClaims()
  }, [])

  // Open Claim Review page and load all 7 components
  const handleOpenClaimReview = async (claimId: string) => {
    setSelectedClaimId(claimId)
    setReviewLoading(true)
    setReviewError(null)
    setActionError(null)
    setActionSuccess(null)
    setReviewClaim(null)
    setReviewAsset(null)
    setPreDisasterEvidence([])
    setPostDisasterEvidence([])
    setReviewAssessment(null)
    setReviewLoss(null)
    setAnomaliesData(null)
    setAuditHistory([])

    try {
      const [claimData, postEvList, damageData, lossData, anomalies, inspectionData] = await Promise.all([
        getClaim(claimId),
        getClaimEvidence(claimId).catch(() => []),
        getClaimDamageAssessment(claimId).catch(() => null),
        getClaimLossEstimate(claimId).catch(() => null),
        getClaimAnomalies(claimId).catch(() => null),
        getClaimInspection(claimId).catch(() => null)
      ])

      const auditEvents = await getClaimAuditHistory(claimId, claimData.asset_id).catch(() => [])

      setReviewClaim(claimData)
      setPostDisasterEvidence(postEvList)
      setReviewAssessment(damageData)
      setReviewLoss(lossData)
      setAnomaliesData(anomalies)
      setAuditHistory(auditEvents)
      setReviewInspection(inspectionData)

      // Initialize form defaults
      if (lossData?.indicative_loss_estimate) {
        setApproveAmount(lossData.indicative_loss_estimate.toString())
      }
      if (damageData?.estimated_damage_percentage) {
        setModifyDamagePct(damageData.estimated_damage_percentage)
      }
      if (damageData?.damage_category) {
        setModifyCategory(damageData.damage_category)
      }

      // Fetch linked asset & pre-disaster evidence
      if (claimData.asset_id) {
        const [assetData, preEvList] = await Promise.all([
          getAsset(claimData.asset_id).catch(() => null),
          getAssetEvidence(claimData.asset_id).catch(() => [])
        ])
        setReviewAsset(assetData)
        setPreDisasterEvidence(preEvList)
      }
    } catch (err: any) {
      console.error('Failed to load claim review details:', err)
      setReviewError(err.message || 'Failed to load claim review dossier.')
      const fallback = claims.find((c) => c.claim_id === claimId) || null
      setReviewClaim(fallback)
    } finally {
      setReviewLoading(false)
    }
  }

  const handleBackToList = () => {
    setSelectedClaimId(null)
    setReviewClaim(null)
    setReviewAsset(null)
    setPreDisasterEvidence([])
    setPostDisasterEvidence([])
    setReviewAssessment(null)
    setReviewLoss(null)
    setAnomaliesData(null)
    setAuditHistory([])
    setReviewInspection(null)
    setActionModal(null)
    // Reload claims list
    loadClaims()
  }

  // -------------------------------------------------------------
  // Decision Action Handlers calling real backend APIs
  // -------------------------------------------------------------
  const handleApproveSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reviewClaim) return
    setActionLoading(true)
    setActionError(null)
    try {
      const amt = approveAmount ? parseFloat(approveAmount) : undefined
      const updated = await approveClaim(reviewClaim.claim_id, {
        approved_amount: amt,
        notes: approveNotes.trim() || 'Claim approved by revenue officer following evidentiary validation.'
      })
      setReviewClaim(updated)
      setActionSuccess(`Claim ${updated.claim_id} successfully APPROVED!`)
      setActionModal(null)
      // Refresh audit history
      getClaimAuditHistory(reviewClaim.claim_id, reviewClaim.asset_id).then(setAuditHistory).catch(() => {})
      loadClaims()
    } catch (err: any) {
      console.error('Failed to approve claim:', err)
      setActionError(err.message || 'Failed to approve claim.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleRequestEvidenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reviewClaim) return
    if (!evidenceNotes.trim()) {
      setActionError('Please specify the required additional evidence.')
      return
    }
    setActionLoading(true)
    setActionError(null)
    try {
      const updated = await requestClaimEvidence(reviewClaim.claim_id, {
        notes: evidenceNotes.trim()
      })
      setReviewClaim(updated)
      setActionSuccess(`Requested additional evidence for claim ${updated.claim_id}. Status updated to EVIDENCE_REQUESTED.`)
      setActionModal(null)
      setEvidenceNotes('')
      getClaimAuditHistory(reviewClaim.claim_id, reviewClaim.asset_id).then(setAuditHistory).catch(() => {})
      loadClaims()
    } catch (err: any) {
      console.error('Failed to request evidence:', err)
      setActionError(err.message || 'Failed to request evidence.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleModifyAssessmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reviewClaim) return
    if (!modifyNotes.trim()) {
      setActionError('Please provide an officer justification for modifying the assessment.')
      return
    }
    setActionLoading(true)
    setActionError(null)
    try {
      const updated = await modifyClaimAssessment(reviewClaim.claim_id, {
        damage_percentage: Number(modifyDamagePct),
        damage_category: modifyCategory,
        notes: modifyNotes.trim()
      })
      setReviewClaim(updated)
      setActionSuccess(`Assessment modified for claim ${updated.claim_id}: Damage set to ${modifyDamagePct}%.`)
      setActionModal(null)
      // Refresh damage assessment & loss estimate
      getClaimDamageAssessment(reviewClaim.claim_id).then(setReviewAssessment).catch(() => {})
      getClaimLossEstimate(reviewClaim.claim_id).then(setReviewLoss).catch(() => {})
      getClaimAuditHistory(reviewClaim.claim_id, reviewClaim.asset_id).then(setAuditHistory).catch(() => {})
      loadClaims()
    } catch (err: any) {
      console.error('Failed to modify assessment:', err)
      setActionError(err.message || 'Failed to modify assessment.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reviewClaim) return
    if (!rejectReason.trim()) {
      setActionError('Please provide a formal rejection reason.')
      return
    }
    setActionLoading(true)
    setActionError(null)
    try {
      const updated = await rejectClaim(reviewClaim.claim_id, {
        reason: rejectReason.trim(),
        notes: rejectNotes.trim() || undefined
      })
      setReviewClaim(updated)
      setActionSuccess(`Claim ${updated.claim_id} has been REJECTED.`)
      setActionModal(null)
      setRejectReason('')
      setRejectNotes('')
      getClaimAuditHistory(reviewClaim.claim_id, reviewClaim.asset_id).then(setAuditHistory).catch(() => {})
      loadClaims()
    } catch (err: any) {
      console.error('Failed to reject claim:', err)
      setActionError(err.message || 'Failed to reject claim.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleForwardInspectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reviewClaim) return
    setActionLoading(true)
    setActionError(null)
    try {
      const updated = await forwardClaimInspection(reviewClaim.claim_id, {
        inspector_notes: forwardNotes.trim() || 'Physical on-site inspection requested by revenue officer.',
        assigned_sector: forwardSector.trim() || 'Katpadi Sector'
      })
      setReviewClaim(updated)
      setActionSuccess(`Claim ${updated.claim_id} forwarded for field inspection. Sector: ${forwardSector}.`)
      setActionModal(null)
      setForwardNotes('')
      getClaimInspection(reviewClaim.claim_id).then(setReviewInspection).catch(() => {})
      getClaimAuditHistory(reviewClaim.claim_id, reviewClaim.asset_id).then(setAuditHistory).catch(() => {})
      loadClaims()
    } catch (err: any) {
      console.error('Failed to forward for inspection:', err)
      setActionError(err.message || 'Failed to forward for field inspection.')
    } finally {
      setActionLoading(false)
    }
  }

  // Filtered claims list
  const filteredClaims = claims.filter((c) => {
    const matchesStatus =
      statusFilter === 'ALL' ||
      (c.review_status && c.review_status.toUpperCase() === statusFilter.toUpperCase()) ||
      (c.status && c.status.toUpperCase() === statusFilter.toUpperCase())

    const query = searchTerm.toLowerCase().trim()
    const matchesSearch =
      !query ||
      c.claim_id.toLowerCase().includes(query) ||
      c.asset_id.toLowerCase().includes(query) ||
      (c.household_ref && c.household_ref.toLowerCase().includes(query)) ||
      (c.location && c.location.toLowerCase().includes(query)) ||
      (c.damage_description && c.damage_description.toLowerCase().includes(query))

    return matchesStatus && matchesSearch
  })

  // Helper for status badge styling
  const renderStatusBadge = (statusStr?: string) => {
    const s = (statusStr || 'SUBMITTED').toUpperCase()
    if (s.includes('APPROVED')) return <span className="badge badge-success">{s}</span>
    if (s.includes('REJECTED')) return <span className="badge badge-danger">{s}</span>
    if (s.includes('AI_ASSESSED') || s.includes('ASSESSED')) return <span className="badge badge-purple">{s}</span>
    if (s.includes('EVIDENCE_REQUESTED') || s.includes('REQUESTED')) return <span className="badge badge-warning">{s}</span>
    if (s.includes('INSPECTION')) return <span className="badge badge-primary">{s}</span>
    if (s.includes('UNDER_REVIEW') || s.includes('REVIEW')) return <span className="badge badge-warning">{s}</span>
    return <span className="badge badge-primary">{s}</span>
  }

  // Helper for evidence confidence badge
  const renderConfidenceBadge = (confidence?: number) => {
    const score = confidence !== undefined ? confidence : 85
    const color = score >= 80 ? '#10b981' : score >= 60 ? '#38bdf8' : '#eab308'
    const bg = score >= 80 ? 'rgba(16, 185, 129, 0.12)' : score >= 60 ? 'rgba(56, 189, 248, 0.12)' : 'rgba(234, 179, 8, 0.12)'
    const border = score >= 80 ? '#10b981' : score >= 60 ? '#38bdf8' : '#eab308'

    return (
      <span
        style={{
          background: bg,
          border: `1px solid ${border}`,
          color,
          fontSize: '0.75rem',
          fontWeight: 700,
          padding: '0.2rem 0.55rem',
          borderRadius: '4px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.3rem'
        }}
      >
        {score}%
      </span>
    )
  }

  // -------------------------------------------------------------
  // VIEW: Complete Government Claim Review Page
  // -------------------------------------------------------------
  if (selectedClaimId) {
    return (
      <div>
        {/* Navigation & Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleBackToList}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <ArrowLeft size={15} />
              Back to Claims List
            </button>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <ShieldCheck size={24} style={{ color: '#38bdf8' }} />
              Claim Review: <span style={{ color: '#38bdf8' }}>{selectedClaimId}</span>
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {reviewClaim && renderStatusBadge(reviewClaim.review_status)}
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => handleOpenClaimReview(selectedClaimId)}
              disabled={reviewLoading}
              title="Refresh Dossier"
            >
              <RefreshCw size={13} className={reviewLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {/* Global Notifications */}
        {actionSuccess && (
          <div
            style={{
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid #10b981',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
              color: '#6ee7b7',
              fontSize: '0.85rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem'
            }}
          >
            <CheckCircle size={18} />
            <span>{actionSuccess}</span>
          </div>
        )}

        {reviewError && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
              color: '#fca5a5',
              fontSize: '0.85rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem'
            }}
          >
            <AlertCircle size={18} />
            <span>{reviewError}</span>
          </div>
        )}

        {/* Decision Action Buttons Bar */}
        {reviewClaim && (
          <div
            style={{
              background: '#0b0f19',
              border: '1px solid #233152',
              borderRadius: '10px',
              padding: '1rem',
              marginBottom: '1.5rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.75rem'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={18} style={{ color: '#38bdf8' }} />
              <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#f8fafc' }}>
                Officer Review Actions:
              </span>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {/* Button 1: Approve */}
              <button
                className="btn btn-primary btn-sm"
                onClick={() => setActionModal('APPROVE')}
                style={{ background: '#059669', borderColor: '#047857', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <CheckCircle size={14} />
                Approve
              </button>

              {/* Button 2: Request More Evidence */}
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setActionModal('REQUEST_EVIDENCE')}
                style={{ background: 'rgba(234, 179, 8, 0.15)', borderColor: '#ca8a04', color: '#fde047', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <HelpCircle size={14} />
                Request More Evidence
              </button>

              {/* Button 3: Modify Assessment */}
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setActionModal('MODIFY_ASSESSMENT')}
                style={{ background: 'rgba(168, 85, 247, 0.15)', borderColor: '#9333ea', color: '#c084fc', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <Sliders size={14} />
                Modify Assessment
              </button>

              {/* Button 4: Reject */}
              <button
                className="btn btn-danger btn-sm"
                onClick={() => setActionModal('REJECT')}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <XCircle size={14} />
                Reject
              </button>

              {/* Button 5: Forward for Field Inspection */}
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setActionModal('FORWARD_INSPECTION')}
                style={{ background: 'rgba(2, 132, 199, 0.15)', borderColor: '#0284c7', color: '#38bdf8', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <Compass size={14} />
                Forward for Field Inspection
              </button>
            </div>
          </div>
        )}

        {reviewLoading && !reviewClaim ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 1rem auto' }} />
            <div>Loading complete claim review dossier...</div>
          </div>
        ) : reviewClaim ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* 1. Asset Information */}
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #1c2742',
                borderRadius: '10px',
                padding: '1.25rem'
              }}
            >
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Boxes size={18} style={{ color: '#38bdf8' }} />
                1. Asset Information & Baseline
              </h3>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '0.85rem',
                  marginBottom: '1rem'
                }}
              >
                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Asset Identifier</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.2rem' }}>
                    {reviewClaim.asset_id}
                  </div>
                </div>

                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Category</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#a855f7', marginTop: '0.2rem' }}>
                    {reviewAsset?.category.replace(/_/g, ' ') || reviewClaim.asset_category?.replace(/_/g, ' ') || 'HOUSE PROPERTY'}
                  </div>
                </div>

                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Documented Baseline Value</div>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: '#10b981', marginTop: '0.2rem' }}>
                    ₹{(reviewAsset?.documented_value || 850000).toLocaleString()}
                  </div>
                </div>

                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Pre-Disaster Verification</div>
                  <div style={{ marginTop: '0.25rem' }}>
                    <span className="badge badge-success" style={{ fontSize: '0.72rem' }}>
                      {reviewAsset?.status || reviewClaim.pre_disaster_verification_status || 'VERIFIED'}
                    </span>
                  </div>
                </div>

                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Household Reference</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#a5b4fc', marginTop: '0.2rem' }}>
                    {reviewClaim.household_ref || reviewClaim.household || 'HH-1001'}
                  </div>
                </div>

                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Location / Address</div>
                  <div style={{ fontSize: '0.825rem', fontWeight: 600, color: '#f8fafc', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <MapPin size={13} style={{ color: '#ef4444', flexShrink: 0 }} />
                    {reviewClaim.location || reviewClaim.location_address || reviewAsset?.location_address || 'Katpadi, Vellore, Tamil Nadu'}
                  </div>
                </div>
              </div>

              {/* Description & Citizen Damage Statement */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Asset Description</div>
                  <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    {reviewAsset?.description || reviewClaim.asset_description || 'Registered citizen asset baseline.'}
                  </div>
                </div>

                <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Citizen Damage Statement</div>
                  <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    {reviewClaim.damage_description || 'No damage statement provided.'}
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Pre-Disaster Evidence */}
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #1c2742',
                borderRadius: '10px',
                padding: '1.25rem'
              }}
            >
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={18} style={{ color: '#10b981' }} />
                2. Pre-Disaster Evidence Records ({preDisasterEvidence.length})
              </h3>

              {preDisasterEvidence.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1.25rem', color: '#94a3b8', fontSize: '0.825rem', background: '#0b0f19', borderRadius: '8px', border: '1px dashed #1c2742' }}>
                  No pre-disaster evidence files directly attached to asset record.
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                  {preDisasterEvidence.map((ev) => (
                    <div
                      key={ev.evidence_id}
                      style={{
                        background: '#131b2e',
                        border: '1px solid #233152',
                        borderRadius: '8px',
                        padding: '0.75rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem'
                      }}
                    >
                      <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <FileText size={18} />
                      </div>
                      <div style={{ overflow: 'hidden', flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <code style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>{ev.evidence_id}</code>
                          <span className="badge badge-success" style={{ fontSize: '0.68rem' }}>PRE-DISASTER</span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#f8fafc', fontWeight: 500, marginTop: '0.15rem', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                          {ev.original_filename}
                        </div>
                        <div style={{ fontSize: '0.68rem', color: '#64748b', marginTop: '0.1rem' }}>
                          SHA-256: {ev.sha256_hash.slice(0, 16)}...
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 3. Post-Disaster Evidence */}
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #1c2742',
                borderRadius: '10px',
                padding: '1.25rem'
              }}
            >
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Paperclip size={18} style={{ color: '#a855f7' }} />
                3. Post-Disaster Evidence Dossier ({postDisasterEvidence.length})
              </h3>

              {postDisasterEvidence.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1.25rem', color: '#94a3b8', fontSize: '0.825rem', background: '#0b0f19', borderRadius: '8px', border: '1px dashed #1c2742' }}>
                  No post-disaster photographic or inspection evidence uploaded yet.
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                  {postDisasterEvidence.map((ev) => {
                    const isPhoto = ev.evidence_type.includes('PHOTO')
                    const isVideo = ev.evidence_type.includes('VIDEO')

                    return (
                      <div
                        key={ev.evidence_id}
                        style={{
                          background: '#131b2e',
                          border: '1px solid #233152',
                          borderRadius: '8px',
                          padding: '0.75rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem'
                        }}
                      >
                        <div
                          style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '8px',
                            background: isPhoto ? 'rgba(56, 189, 248, 0.12)' : isVideo ? 'rgba(239, 68, 68, 0.12)' : 'rgba(168, 85, 247, 0.12)',
                            color: isPhoto ? '#38bdf8' : isVideo ? '#ef4444' : '#c084fc',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0
                          }}
                        >
                          {isPhoto ? <Camera size={18} /> : isVideo ? <Video size={18} /> : <FileText size={18} />}
                        </div>

                        <div style={{ overflow: 'hidden', flex: 1 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <code style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>{ev.evidence_id}</code>
                            <span className="badge badge-purple" style={{ fontSize: '0.68rem' }}>
                              {ev.evidence_type.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#f8fafc', fontWeight: 500, marginTop: '0.15rem', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                            {ev.original_filename}
                          </div>
                          <div style={{ fontSize: '0.68rem', color: '#64748b', marginTop: '0.1rem' }}>
                            SHA-256: {ev.sha256_hash.slice(0, 16)}...
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Field Inspection Report & Assessor Findings */}
            {reviewInspection && (
              <div
                style={{
                  background: '#0f172a',
                  border: reviewInspection.inspection_status === 'COMPLETED' ? '1px solid #059669' : '1px solid #1c2742',
                  borderRadius: '10px',
                  padding: '1.25rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                    <ClipboardCheck size={18} style={{ color: reviewInspection.inspection_status === 'COMPLETED' ? '#10b981' : '#38bdf8' }} />
                    Field Inspection Report & Assessor Findings
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Sector: <strong style={{ color: '#38bdf8' }}>{reviewInspection.inspection_sector || 'Zone 1'}</strong></span>
                    {reviewInspection.inspection_status === 'COMPLETED' ? (
                      <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle size={12} /> REPORT SUBMITTED
                      </span>
                    ) : (
                      <span className="badge badge-warning" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={12} /> AWAITING FIELD SURVEY
                      </span>
                    )}
                  </div>
                </div>

                {reviewInspection.inspection_status === 'COMPLETED' ? (
                  <div>
                    {/* Findings & Rating summary */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Assessor Severity Rating</div>
                        <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.2rem' }}>
                          <span className={`badge ${reviewInspection.damage_severity_rating?.includes('COLLAPSE') || reviewInspection.damage_severity_rating?.includes('SEVERE') ? 'badge-danger' : 'badge-warning'}`}>
                            {reviewInspection.damage_severity_rating || 'MODERATE_DAMAGE'}
                          </span>
                        </div>
                      </div>
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Filed By (NGO/Assessor)</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e2e8f0', marginTop: '0.2rem' }}>
                          {reviewInspection.submitted_by || reviewInspection.assigned_inspector_name || 'Field Volunteer'}
                        </div>
                      </div>
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Report Submitted At</div>
                        <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.2rem' }}>
                          {reviewInspection.report_submitted_at ? new Date(reviewInspection.report_submitted_at).toLocaleString() : 'Recently'}
                        </div>
                      </div>
                    </div>

                    {/* Factual observations */}
                    <div style={{ background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', padding: '0.85rem 1rem', marginBottom: '1rem' }}>
                      <div style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                        Assessor Physical Ground Observations:
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#f0fdf4', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                        {reviewInspection.field_findings || 'No physical findings text recorded.'}
                      </div>
                    </div>

                    {/* Evidence files uploaded by assessor */}
                    {reviewInspection.inspection_evidence && reviewInspection.inspection_evidence.length > 0 && (
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.5rem', fontWeight: 600 }}>
                          Field Survey Evidence Files ({reviewInspection.inspection_evidence.length})
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.5rem' }}>
                          {reviewInspection.inspection_evidence.map((ev) => (
                            <div key={ev.evidence_id} style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.6rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <Camera size={16} style={{ color: '#38bdf8' }} />
                              <div style={{ overflow: 'hidden', flex: 1 }}>
                                <div style={{ fontSize: '0.8rem', color: '#f8fafc', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{ev.original_filename}</div>
                                <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>{ev.evidence_type} · {(ev.file_size / 1024).toFixed(1)} KB</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ background: 'rgba(56, 189, 248, 0.05)', border: '1px dashed #0284c7', borderRadius: '8px', padding: '1rem', color: '#cbd5e1', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontWeight: 600, marginBottom: '0.35rem' }}>
                      <Clock size={16} /> Inspection Dispatched to NGO Field Team
                    </div>
                    <div>Sector: <strong>{reviewInspection.inspection_sector || 'Katpadi'}</strong></div>
                    {reviewInspection.special_instructions && (
                      <div style={{ marginTop: '0.35rem', color: '#94a3b8' }}>
                        Instructions: <em>{reviewInspection.special_instructions}</em>
                      </div>
                    )}
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#64748b' }}>
                      Awaiting on-site physical survey and report submission from field assessor.
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 4. AI Assessment */}
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #1c2742',
                borderRadius: '10px',
                padding: '1.25rem'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <Sparkles size={18} style={{ color: '#38bdf8' }} />
                  4. AI Damage Assessment
                </h3>
                <span
                  style={{
                    background: 'rgba(234, 179, 8, 0.12)',
                    border: '1px solid #ca8a04',
                    color: '#facc15',
                    fontSize: '0.7rem',
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}
                >
                  DEMO AI / SIMULATED ASSESSMENT
                </span>
              </div>

              {reviewAssessment ? (
                <>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                      gap: '0.75rem',
                      marginBottom: '1rem'
                    }}
                  >
                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Damage Category</div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.2rem' }}>
                        {reviewAssessment.damage_category.replace(/_/g, ' ')}
                      </div>
                    </div>

                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Estimated Damage</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ef4444', marginTop: '0.15rem' }}>
                        {reviewAssessment.estimated_damage_percentage}%
                      </div>
                    </div>

                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Asset Match Confidence</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#10b981', marginTop: '0.15rem' }}>
                        {reviewAssessment.asset_match_confidence}%
                      </div>
                    </div>

                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Evidence Confidence</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#38bdf8', marginTop: '0.15rem' }}>
                        {reviewAssessment.evidence_quality || reviewAssessment.overall_confidence}%
                      </div>
                    </div>
                  </div>

                  <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.85rem' }}>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                      Assessment Explanation
                    </div>
                    <div style={{ fontSize: '0.825rem', color: '#f8fafc', lineHeight: 1.5 }}>
                      {reviewAssessment.explanation}
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '1.25rem', color: '#94a3b8', fontSize: '0.825rem', background: '#0b0f19', borderRadius: '8px', border: '1px dashed #1c2742' }}>
                  No AI damage assessment performed yet.
                </div>
              )}
            </div>

            {/* 5. Indicative Loss Estimate */}
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #1c2742',
                borderRadius: '10px',
                padding: '1.25rem'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <Calculator size={18} style={{ color: '#10b981' }} />
                  5. Indicative Value & Loss Estimate
                </h3>
                <span
                  style={{
                    background: 'rgba(16, 185, 129, 0.12)',
                    border: '1px solid #059669',
                    color: '#34d399',
                    fontSize: '0.7rem',
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}
                >
                  AI-ASSISTED ESTIMATE
                </span>
              </div>

              {reviewLoss ? (
                <>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                      gap: '0.75rem',
                      marginBottom: '1rem'
                    }}
                  >
                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Original Value</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.15rem' }}>
                        ₹{reviewLoss.original_documented_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </div>
                    </div>

                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Current/Reference Value</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#38bdf8', marginTop: '0.15rem' }}>
                        ₹{reviewLoss.reference_current_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </div>
                    </div>

                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Damage Percentage</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ef4444', marginTop: '0.15rem' }}>
                        {reviewLoss.damage_percentage}%
                      </div>
                    </div>

                    <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#fca5a5', textTransform: 'uppercase', fontWeight: 600 }}>Indicative Loss Estimate</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#f87171', marginTop: '0.15rem' }}>
                        ₹{reviewLoss.indicative_loss_estimate.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      background: 'rgba(234, 179, 8, 0.08)',
                      border: '1px solid rgba(234, 179, 8, 0.3)',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      fontSize: '0.75rem',
                      color: '#fef08a'
                    }}
                  >
                    <strong>Notice: </strong>
                    This is not a guaranteed compensation amount. Final compensation is subject to government verification and applicable rules.
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '1.25rem', color: '#94a3b8', fontSize: '0.825rem', background: '#0b0f19', borderRadius: '8px', border: '1px dashed #1c2742' }}>
                  No indicative loss calculation available yet.
                </div>
              )}
            </div>

            {/* 6 & 7. Audit Timeline & Anomaly Warnings */}
            <AuditTimeline
              auditEvents={auditHistory}
              claim={reviewClaim}
              asset={reviewAsset}
              assessment={reviewAssessment}
              preEvidenceCount={preDisasterEvidence.length}
              postEvidenceCount={postDisasterEvidence.length}
              anomalies={anomaliesData}
            />
          </div>
        ) : null}

        {/* ----------------------------------------------------------- */}
        {/* ACTION MODALS */}
        {/* ----------------------------------------------------------- */}

        {/* Modal 1: Approve Claim */}
        {actionModal === 'APPROVE' && (
          <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 110, padding: '1rem' }}>
            <div style={{ background: '#0f172a', border: '1px solid #10b981', borderRadius: '12px', width: '100%', maxWidth: '500px', padding: '1.5rem', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <CheckCircle size={20} style={{ color: '#10b981' }} />
                  Approve Claim
                </h3>
                <button className="btn btn-secondary btn-sm" onClick={() => setActionModal(null)}>
                  <X size={16} />
                </button>
              </div>

              {actionError && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.65rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  {actionError}
                </div>
              )}

              <form onSubmit={handleApproveSubmit}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Approved Compensation Amount (₹)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={approveAmount}
                    onChange={(e) => setApproveAmount(e.target.value)}
                    placeholder="Enter approved INR amount..."
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                  <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                    Indicative AI loss estimate: ₹{reviewLoss?.indicative_loss_estimate ? reviewLoss.indicative_loss_estimate.toLocaleString() : 'N/A'}
                  </span>
                </div>

                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Officer Approval Notes
                  </label>
                  <textarea
                    rows={3}
                    value={approveNotes}
                    onChange={(e) => setApproveNotes(e.target.value)}
                    placeholder="Formal justification (e.g. validated against baseline title deed and post-disaster flood report)..."
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setActionModal(null)} disabled={actionLoading}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" style={{ background: '#059669', borderColor: '#047857' }} disabled={actionLoading}>
                    {actionLoading ? 'Approving...' : 'Confirm & Approve Claim'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal 2: Request More Evidence */}
        {actionModal === 'REQUEST_EVIDENCE' && (
          <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 110, padding: '1rem' }}>
            <div style={{ background: '#0f172a', border: '1px solid #ca8a04', borderRadius: '12px', width: '100%', maxWidth: '500px', padding: '1.5rem', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <HelpCircle size={20} style={{ color: '#facc15' }} />
                  Request More Evidence
                </h3>
                <button className="btn btn-secondary btn-sm" onClick={() => setActionModal(null)}>
                  <X size={16} />
                </button>
              </div>

              {actionError && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.65rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  {actionError}
                </div>
              )}

              <form onSubmit={handleRequestEvidenceSubmit}>
                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Required Additional Evidence Details *
                  </label>
                  <textarea
                    rows={4}
                    required
                    value={evidenceNotes}
                    onChange={(e) => setEvidenceNotes(e.target.value)}
                    placeholder="Specify evidence required (e.g. Please upload close-up photos of cracked load-bearing beam and water level gauge on exterior wall)..."
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                  <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                    Status will transition to EVIDENCE_REQUESTED. Citizen will be notified on portal.
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setActionModal(null)} disabled={actionLoading}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" style={{ background: '#ca8a04', borderColor: '#a16207' }} disabled={actionLoading}>
                    {actionLoading ? 'Sending Request...' : 'Send Evidence Request'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal 3: Modify Assessment */}
        {actionModal === 'MODIFY_ASSESSMENT' && (
          <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 110, padding: '1rem' }}>
            <div style={{ background: '#0f172a', border: '1px solid #9333ea', borderRadius: '12px', width: '100%', maxWidth: '500px', padding: '1.5rem', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <Sliders size={20} style={{ color: '#c084fc' }} />
                  Modify Assessment
                </h3>
                <button className="btn btn-secondary btn-sm" onClick={() => setActionModal(null)}>
                  <X size={16} />
                </button>
              </div>

              {actionError && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.65rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  {actionError}
                </div>
              )}

              <form onSubmit={handleModifyAssessmentSubmit}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Adjusted Damage Percentage (0-100)% *
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    required
                    value={modifyDamagePct}
                    onChange={(e) => setModifyDamagePct(parseInt(e.target.value) || 0)}
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Damage Category
                  </label>
                  <select
                    value={modifyCategory}
                    onChange={(e) => setModifyCategory(e.target.value)}
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  >
                    <option value="MAJOR_STRUCTURAL_DAMAGE">MAJOR STRUCTURAL DAMAGE</option>
                    <option value="MODERATE_DAMAGE">MODERATE DAMAGE</option>
                    <option value="MINOR_DAMAGE">MINOR DAMAGE</option>
                    <option value="TOTAL_LOSS">TOTAL LOSS</option>
                  </select>
                </div>

                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Officer Modification Justification *
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={modifyNotes}
                    onChange={(e) => setModifyNotes(e.target.value)}
                    placeholder="Enter reason for modifying AI assessment parameters..."
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setActionModal(null)} disabled={actionLoading}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" style={{ background: '#9333ea', borderColor: '#7e22ce' }} disabled={actionLoading}>
                    {actionLoading ? 'Modifying...' : 'Save Modified Assessment'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal 4: Reject Claim */}
        {actionModal === 'REJECT' && (
          <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 110, padding: '1rem' }}>
            <div style={{ background: '#0f172a', border: '1px solid #ef4444', borderRadius: '12px', width: '100%', maxWidth: '500px', padding: '1.5rem', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <XCircle size={20} style={{ color: '#ef4444' }} />
                  Reject Claim
                </h3>
                <button className="btn btn-secondary btn-sm" onClick={() => setActionModal(null)}>
                  <X size={16} />
                </button>
              </div>

              {actionError && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.65rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  {actionError}
                </div>
              )}

              <form onSubmit={handleRejectSubmit}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Rejection Reason *
                  </label>
                  <input
                    type="text"
                    required
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="e.g. Damages outside designated disaster zone or lack of asset ownership..."
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                </div>

                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Additional Officer Notes
                  </label>
                  <textarea
                    rows={3}
                    value={rejectNotes}
                    onChange={(e) => setRejectNotes(e.target.value)}
                    placeholder="Optional procedural notes recorded in immutable ledger..."
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setActionModal(null)} disabled={actionLoading}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-danger" disabled={actionLoading}>
                    {actionLoading ? 'Rejecting...' : 'Confirm Rejection'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal 5: Forward for Field Inspection */}
        {actionModal === 'FORWARD_INSPECTION' && (
          <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 110, padding: '1rem' }}>
            <div style={{ background: '#0f172a', border: '1px solid #0284c7', borderRadius: '12px', width: '100%', maxWidth: '500px', padding: '1.5rem', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <Compass size={20} style={{ color: '#38bdf8' }} />
                  Forward for Field Inspection
                </h3>
                <button className="btn btn-secondary btn-sm" onClick={() => setActionModal(null)}>
                  <X size={16} />
                </button>
              </div>

              {actionError && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.65rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  {actionError}
                </div>
              )}

              <form onSubmit={handleForwardInspectionSubmit}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Assigned Field Sector / Jurisdiction
                  </label>
                  <input
                    type="text"
                    value={forwardSector}
                    onChange={(e) => setForwardSector(e.target.value)}
                    placeholder="e.g. Katpadi Sector 4, Vellore District"
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                </div>

                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Instructions for Field Assessor
                  </label>
                  <textarea
                    rows={3}
                    value={forwardNotes}
                    onChange={(e) => setForwardNotes(e.target.value)}
                    placeholder="Specific instructions (e.g. Inspect submerged electrical panel and structural cracks in basement)..."
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.55rem', borderRadius: '6px', fontSize: '0.85rem' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setActionModal(null)} disabled={actionLoading}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" style={{ background: '#0284c7', borderColor: '#0369a1' }} disabled={actionLoading}>
                    {actionLoading ? 'Forwarding...' : 'Forward for Inspection'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    )
  }

  // -------------------------------------------------------------
  // VIEW: Claims List Dashboard
  // -------------------------------------------------------------
  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.5rem'
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ShieldCheck size={26} style={{ color: '#38bdf8' }} />
            Government Officer Claims Dashboard
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Review incoming disaster claims across all jurisdictions with pre-disaster verification baselines.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={loadClaims}
            disabled={loading}
            title="Refresh claims list"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '1rem',
            color: '#fca5a5',
            fontSize: '0.875rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem'
          }}
        >
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div
        style={{
          background: '#0f172a',
          border: '1px solid #1c2742',
          borderRadius: '8px',
          padding: '0.85rem 1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.25rem'
        }}
      >
        {/* Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '220px' }}>
          <Search size={16} style={{ color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search claim ID, asset ID, household, or location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: '#0b0f19',
              border: '1px solid #233152',
              color: '#f8fafc',
              padding: '0.45rem 0.75rem',
              borderRadius: '6px',
              fontSize: '0.825rem',
              width: '100%'
            }}
          />
        </div>

        {/* Filter by Review Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={15} style={{ color: '#94a3b8' }} />
          <label style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Status:</label>
          <select
            className="role-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.4rem 0.65rem', borderRadius: '6px', fontSize: '0.8rem' }}
          >
            <option value="ALL">All Statuses ({claims.length})</option>
            <option value="SUBMITTED">SUBMITTED</option>
            <option value="AI_ASSESSED">AI_ASSESSED</option>
            <option value="UNDER_REVIEW">UNDER_REVIEW</option>
            <option value="EVIDENCE_REQUESTED">EVIDENCE_REQUESTED</option>
            <option value="ASSESSMENT_MODIFIED">ASSESSMENT_MODIFIED</option>
            <option value="FIELD_INSPECTION_PENDING">FIELD_INSPECTION_PENDING</option>
            <option value="APPROVED">APPROVED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
        </div>
      </div>

      {/* Claims List Table */}
      <div
        style={{
          background: '#0f172a',
          border: '1px solid #1c2742',
          borderRadius: '10px',
          overflow: 'hidden'
        }}
      >
        {loading && claims.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            <RefreshCw size={26} className="animate-spin" style={{ margin: '0 auto 0.75rem auto' }} />
            <div>Loading claims from backend API...</div>
          </div>
        ) : filteredClaims.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            <FileText size={32} style={{ margin: '0 auto 0.75rem auto', opacity: 0.5 }} />
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>No disaster claims found</div>
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.35rem' }}>
              {searchTerm || statusFilter !== 'ALL'
                ? 'Try adjusting your search or status filter.'
                : 'No claims have been submitted in the system yet.'}
            </div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: '#0b0f19', borderBottom: '1px solid #1c2742', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  <th style={{ padding: '0.85rem 1rem' }}>Claim ID</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Asset</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Location</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Status</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Evidence Confidence</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Damage Category</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Review Status</th>
                  <th style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredClaims.map((claim) => {
                  const locationStr = claim.location || claim.location_address || 'Katpadi, Vellore, Tamil Nadu'
                  const confidence = claim.evidence_confidence !== undefined ? claim.evidence_confidence : 85
                  const damageCat = claim.damage_category || 'PENDING_ASSESSMENT'

                  return (
                    <tr
                      key={claim.claim_id}
                      style={{
                        borderBottom: '1px solid #1c2742',
                        transition: 'background-color 0.15s',
                        cursor: 'pointer'
                      }}
                      onClick={() => handleOpenClaimReview(claim.claim_id)}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(56, 189, 248, 0.04)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }}
                    >
                      {/* 1. Claim ID */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <code style={{ fontSize: '0.825rem', fontWeight: 700, color: '#38bdf8' }}>
                          {claim.claim_id}
                        </code>
                        <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.15rem' }}>
                          {claim.household_ref || claim.household}
                        </div>
                      </td>

                      {/* 2. Asset */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <Boxes size={14} style={{ color: '#a855f7', flexShrink: 0 }} />
                          <span style={{ fontWeight: 600, color: '#f8fafc' }}>{claim.asset_id}</span>
                        </div>
                        {claim.asset_category && (
                          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.15rem' }}>
                            {claim.asset_category.replace(/_/g, ' ')}
                          </div>
                        )}
                      </td>

                      {/* 3. Location */}
                      <td style={{ padding: '0.85rem 1rem', maxWidth: '200px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#cbd5e1' }}>
                          <MapPin size={13} style={{ color: '#ef4444', flexShrink: 0 }} />
                          <span style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                            {locationStr}
                          </span>
                        </div>
                      </td>

                      {/* 4. Status */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        {renderStatusBadge(claim.status || claim.claim_status)}
                      </td>

                      {/* 5. Evidence Confidence */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        {renderConfidenceBadge(confidence)}
                      </td>

                      {/* 6. Damage Category */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <span
                          className={`badge ${
                            damageCat.includes('MAJOR')
                              ? 'badge-danger'
                              : damageCat.includes('MODERATE')
                              ? 'badge-warning'
                              : damageCat.includes('PENDING')
                              ? 'badge-secondary'
                              : 'badge-purple'
                          }`}
                          style={{ fontSize: '0.72rem' }}
                        >
                          {damageCat.replace(/_/g, ' ')}
                        </span>
                      </td>

                      {/* 7. Review Status */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        {renderStatusBadge(claim.review_status)}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleOpenClaimReview(claim.claim_id)
                          }}
                          style={{
                            fontSize: '0.75rem',
                            padding: '0.35rem 0.75rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem'
                          }}
                        >
                          <Eye size={13} />
                          Review Claim
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
