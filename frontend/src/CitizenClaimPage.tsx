import React, { useEffect, useState } from 'react'
import {
  FileText,
  AlertTriangle,
  PlusCircle,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  X,
  Boxes,
  Shield,
  Clock,
  Eye,
  Calendar,
  Building,
  MapPin,
  Camera,
  Video,
  UploadCloud,
  Paperclip,
  Sparkles,
  Cpu,
  Calculator
} from 'lucide-react'
import {
  Claim,
  Asset,
  DisasterEvent,
  CreateClaimPayload,
  ClaimEvidenceItem,
  DamageAssessment,
  ValueLossAssessment,
  UserRole,
  AuditRecordItem,
  AnomalyListResponse
} from './types'
import {
  getClaims,
  getClaim,
  createClaim,
  getAssets,
  getDisasters,
  getClaimEvidence,
  uploadClaimEvidence,
  runClaimDamageAssessment,
  getClaimDamageAssessment,
  calculateClaimLossEstimate,
  getClaimLossEstimate,
  getClaimAuditHistory,
  getClaimAnomalies
} from './api'
import { AuditTimeline } from './AuditTimeline'

interface CitizenClaimPageProps {
  currentUser?: UserRole | null
  onClaimCreated?: () => void
  onNavigateToAssets?: () => void
}

export function CitizenClaimPage({
  currentUser,
  onClaimCreated,
  onNavigateToAssets
}: CitizenClaimPageProps) {
  const [claims, setClaims] = useState<Claim[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [disasters, setDisasters] = useState<DisasterEvent[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Create Claim modal state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [selectedAssetId, setSelectedAssetId] = useState<string>('')
  const [selectedDisasterId, setSelectedDisasterId] = useState<string>('DIS-2026-0007')
  const [damageDescription, setDamageDescription] = useState<string>('')

  // View Claim Details modal state
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null)
  const [detailsLoading, setDetailsLoading] = useState<boolean>(false)

  // Claim Evidence state
  const [claimEvidence, setClaimEvidence] = useState<ClaimEvidenceItem[]>([])
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null)
  const [evidenceType, setEvidenceType] = useState<string>('POST_DISASTER_PHOTO')
  const [uploadingEvidence, setUploadingEvidence] = useState<boolean>(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  const [evidenceSuccess, setEvidenceSuccess] = useState<string | null>(null)

  // AI Damage Assessment state (Step 24)
  const [assessment, setAssessment] = useState<DamageAssessment | null>(null)
  const [assessing, setAssessing] = useState<boolean>(false)
  const [assessmentError, setAssessmentError] = useState<string | null>(null)
  const [assessmentSuccess, setAssessmentSuccess] = useState<string | null>(null)

  // Value & Loss Assessment state (Step 25)
  const [lossEstimate, setLossEstimate] = useState<ValueLossAssessment | null>(null)
  const [calculatingLoss, setCalculatingLoss] = useState<boolean>(false)
  const [lossError, setLossError] = useState<string | null>(null)
  const [lossSuccess, setLossSuccess] = useState<string | null>(null)

  // Audit and Anomaly state (Step 29)
  const [claimAuditHistory, setClaimAuditHistory] = useState<AuditRecordItem[]>([])
  const [claimAnomalies, setClaimAnomalies] = useState<AnomalyListResponse | null>(null)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [claimList, assetList, disasterList] = await Promise.all([
        getClaims().catch(() => []),
        getAssets().catch(() => []),
        getDisasters().catch(() => [
          {
            disaster_code: 'DIS-2026-0007',
            name: 'Tamil Nadu Monsoon Flash Flood (Simulation)',
            disaster_type: 'FLOOD',
            state: 'Tamil Nadu',
            district: 'Vellore',
            severity: 'CRITICAL',
            status: 'ACTIVE'
          }
        ])
      ])

      setClaims(claimList)
      setAssets(assetList)
      setDisasters(disasterList)

      if (assetList.length > 0 && !selectedAssetId) {
        setSelectedAssetId(assetList[0].asset_id)
      }
      if (disasterList.length > 0 && !selectedDisasterId) {
        setSelectedDisasterId(disasterList[0].disaster_code)
      }
    } catch (err: any) {
      console.error('Failed to load disaster claims data:', err)
      setError(err.message || 'Unable to retrieve claims from backend.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [currentUser?.user_id])

  const handleOpenCreateModal = () => {
    setFormError(null)
    setDamageDescription('')
    if (assets.length > 0) {
      setSelectedAssetId(assets[0].asset_id)
    }
    if (disasters.length > 0) {
      setSelectedDisasterId(disasters[0].disaster_code)
    }
    setShowCreateModal(true)
  }

  const handleCreateClaim = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!selectedAssetId) {
      setFormError('Please select a registered asset.')
      return
    }

    if (!damageDescription.trim() || damageDescription.trim().length < 5) {
      setFormError('Please provide a detailed damage description (at least 5 characters).')
      return
    }

    const selectedAsset = assets.find((a) => a.asset_id === selectedAssetId)
    const householdRef = selectedAsset?.household_ref || currentUser?.household_ref || 'HH-1001'

    setSubmitting(true)
    try {
      const payload: CreateClaimPayload = {
        asset_id: selectedAssetId,
        disaster_id: selectedDisasterId || 'DIS-2026-0007',
        damage_description: damageDescription.trim(),
        household_ref: householdRef
      }

      const created = await createClaim(payload)
      setSuccessMsg(
        `Disaster claim ${created.claim_id} filed successfully for asset ${created.asset_id}!`
      )
      setShowCreateModal(false)

      // Reload claims list so new claim appears immediately
      await loadData()

      if (onClaimCreated) {
        onClaimCreated()
      }
    } catch (err: any) {
      console.error('Failed to create claim:', err)
      setFormError(err.message || 'Failed to file disaster claim.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleOpenDetails = async (claimId: string) => {
    setDetailsLoading(true)
    setEvidenceError(null)
    setEvidenceSuccess(null)
    setUploadStatus(null)
    setEvidenceFile(null)
    setEvidenceType('POST_DISASTER_PHOTO')
    setAssessment(null)
    setAssessmentError(null)
    setAssessmentSuccess(null)
    setLossEstimate(null)
    setLossError(null)
    setLossSuccess(null)

    try {
      const [claim, evList, existingAssessment, existingLoss, anomalies] = await Promise.all([
        getClaim(claimId),
        getClaimEvidence(claimId).catch(() => []),
        getClaimDamageAssessment(claimId).catch(() => null),
        getClaimLossEstimate(claimId).catch(() => null),
        getClaimAnomalies(claimId).catch(() => null)
      ])
      setSelectedClaim(claim)
      setClaimEvidence(evList)
      setAssessment(existingAssessment)
      setLossEstimate(existingLoss)
      setClaimAnomalies(anomalies)

      getClaimAuditHistory(claimId, claim.asset_id)
        .then(setClaimAuditHistory)
        .catch(() => setClaimAuditHistory([]))
    } catch (err: any) {
      console.error('Failed to load claim details:', err)
      // Fallback to local claim if network fetch fails
      const fallback = claims.find((c) => c.claim_id === claimId) || null
      setSelectedClaim(fallback)
      if (fallback) {
        getClaimEvidence(claimId)
          .then(setClaimEvidence)
          .catch(() => setClaimEvidence([]))
        getClaimDamageAssessment(claimId)
          .then(setAssessment)
          .catch(() => setAssessment(null))
        getClaimLossEstimate(claimId)
          .then(setLossEstimate)
          .catch(() => setLossEstimate(null))
      }
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleUploadClaimEvidence = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedClaim) return

    if (!evidenceFile) {
      setEvidenceError('Please select a file to upload.')
      return
    }

    setUploadingEvidence(true)
    setUploadStatus('Uploading post-disaster evidence...')
    setEvidenceError(null)
    setEvidenceSuccess(null)

    try {
      const uploaded = await uploadClaimEvidence(selectedClaim.claim_id, evidenceFile, evidenceType)
      setUploadStatus(`Upload completed. Evidence ID: ${uploaded.evidence_id}`)
      setEvidenceSuccess(
        `Post-disaster evidence ${uploaded.evidence_id} (${uploaded.evidence_type.replace(/_/g, ' ')}) uploaded successfully!`
      )

      // Reset selected file & input
      setEvidenceFile(null)
      const inputEl = document.getElementById('claim-evidence-file-input') as HTMLInputElement
      if (inputEl) inputEl.value = ''

      // Refresh claim evidence list and audit timeline
      const updatedList = await getClaimEvidence(selectedClaim.claim_id)
      setClaimEvidence(updatedList)
      getClaimAuditHistory(selectedClaim.claim_id, selectedClaim.asset_id).then(setClaimAuditHistory).catch(() => {})
    } catch (err: any) {
      console.error('Failed to upload claim evidence:', err)
      setUploadStatus('Upload failed.')
      setEvidenceError(err.message || 'Failed to upload post-disaster evidence.')
    } finally {
      setUploadingEvidence(false)
    }
  }

  const handleRunAssessment = async () => {
    if (!selectedClaim) return
    setAssessing(true)
    setAssessmentError(null)
    setAssessmentSuccess(null)

    try {
      const result = await runClaimDamageAssessment(selectedClaim.claim_id)
      setAssessment(result)
      setAssessmentSuccess(
        `AI Damage Assessment completed! Category: ${result.damage_category.replace(/_/g, ' ')} (${result.estimated_damage_percentage}% estimated damage).`
      )

      // Automatically recalculate loss estimate if previously evaluated or available
      calculateClaimLossEstimate(selectedClaim.claim_id)
        .then((le) => setLossEstimate(le))
        .catch(() => {})

      // Refresh claim to reflect updated review status (e.g. AI_ASSESSED) without auto-approving
      const updatedClaim = await getClaim(selectedClaim.claim_id).catch(() => null)
      if (updatedClaim) {
        setSelectedClaim(updatedClaim)
      }
      // Refresh audit timeline & anomalies
      getClaimAuditHistory(selectedClaim.claim_id, selectedClaim.asset_id).then(setClaimAuditHistory).catch(() => {})
      getClaimAnomalies(selectedClaim.claim_id).then(setClaimAnomalies).catch(() => {})
      // Refresh claims list in table
      getClaims().then(setClaims).catch(() => {})
    } catch (err: any) {
      console.error('Failed to run AI damage assessment:', err)
      setAssessmentError(err.message || 'Failed to execute AI damage assessment.')
    } finally {
      setAssessing(false)
    }
  }

  const handleCalculateLoss = async () => {
    if (!selectedClaim) return
    setCalculatingLoss(true)
    setLossError(null)
    setLossSuccess(null)

    try {
      const result = await calculateClaimLossEstimate(selectedClaim.claim_id)
      setLossEstimate(result)
      setLossSuccess(
        `Indicative loss estimate calculated: ₹${result.indicative_loss_estimate.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
      )
    } catch (err: any) {
      console.error('Failed to calculate loss estimate:', err)
      setLossError(err.message || 'Failed to calculate indicative loss estimate.')
    } finally {
      setCalculatingLoss(false)
    }
  }

  const activeSelectedAsset = assets.find((a) => a.asset_id === selectedAssetId)

  return (
    <div>
      {/* Header Section */}
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
            <FileText size={26} style={{ color: '#ef4444' }} />
            Citizen Disaster Claims
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            File post-disaster compensation claims referenced to pre-disaster baseline records with cryptographic accountability.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={loadData}
            disabled={loading}
            title="Refresh claims"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>

          <button
            className="btn btn-primary"
            onClick={handleOpenCreateModal}
            disabled={assets.length === 0}
            title={assets.length === 0 ? 'Register an asset first' : 'File a disaster claim'}
            style={{ background: '#ef4444', borderColor: '#dc2626' }}
          >
            <PlusCircle size={16} />
            File New Claim
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '1rem',
            color: '#fca5a5',
            marginBottom: '1.25rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer' }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {successMsg && (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid #10b981',
            borderRadius: '8px',
            padding: '1rem',
            color: '#6ee7b7',
            marginBottom: '1.25rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={18} />
            <span>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ background: 'transparent', border: 'none', color: '#6ee7b7', cursor: 'pointer' }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* No Assets Warning Banner */}
      {assets.length === 0 && !loading && (
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid #f59e0b',
            borderRadius: '8px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertTriangle size={24} style={{ color: '#f59e0b', flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: 600, color: '#f8fafc' }}>
                No Pre-Disaster Assets Registered
              </div>
              <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.2rem' }}>
                A disaster claim must reference an existing registered asset. Please register your property or equipment first.
              </div>
            </div>
          </div>

          {onNavigateToAssets && (
            <button className="btn btn-primary btn-sm" onClick={onNavigateToAssets}>
              <Boxes size={14} />
              Go to Citizen Assets
            </button>
          )}
        </div>
      )}

      {/* Claims Table Panel */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <FileText size={18} style={{ color: '#ef4444' }} />
            Filed Disaster Claims
          </div>
          <span className="badge badge-purple">{claims.length} Total</span>
        </div>

        {loading ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: '#94a3b8' }}>
            <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 0.75rem auto' }} />
            <p>Loading disaster claims from backend...</p>
          </div>
        ) : claims.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
            <FileText size={36} style={{ margin: '0 auto 0.75rem auto', opacity: 0.5 }} />
            <p style={{ fontWeight: 600, fontSize: '1rem', color: '#f8fafc' }}>
              No disaster claims filed yet.
            </p>
            <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
              If your registered asset sustained damage during a declared crisis, click "File New Claim" above.
            </p>
            {assets.length > 0 && (
              <button
                className="btn btn-primary"
                onClick={handleOpenCreateModal}
                style={{ marginTop: '1.25rem', background: '#ef4444', borderColor: '#dc2626' }}
              >
                <PlusCircle size={15} />
                File Disaster Claim Now
              </button>
            )}
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Referenced Asset</th>
                  <th>Disaster Event</th>
                  <th>Damage Description</th>
                  <th>Pre-Disaster Baseline</th>
                  <th>Claim Status</th>
                  <th>Filed Date</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((claim) => {
                  const statusVal = claim.review_status || claim.claim_status || claim.status || 'SUBMITTED'
                  const preStatus = claim.pre_disaster_verification_status || claim.pre_disaster_verification_state || 'UNVERIFIED'

                  const isApproved = statusVal === 'APPROVED'
                  const isUnderReview = statusVal === 'UNDER_REVIEW' || statusVal === 'REVIEW_REQUIRED'
                  const isRejected = statusVal === 'REJECTED'

                  return (
                    <tr key={claim.claim_id}>
                      <td>
                        <code style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>
                          {claim.claim_id}
                        </code>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Boxes size={14} style={{ color: '#3b82f6' }} />
                          <code style={{ fontSize: '0.8rem' }}>{claim.asset_id}</code>
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-danger" style={{ fontSize: '0.72rem' }}>
                          {claim.disaster_id || claim.disaster_event}
                        </span>
                      </td>
                      <td style={{ maxWidth: '280px' }}>
                        <div
                          style={{
                            fontSize: '0.825rem',
                            color: '#cbd5e1',
                            lineHeight: 1.4,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                          title={claim.damage_description}
                        >
                          {claim.damage_description}
                        </div>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            preStatus === 'VERIFIED' || preStatus === 'OFFICIALLY_CONFIRMED'
                              ? 'badge-success'
                              : preStatus === 'PARTIALLY_VERIFIED'
                              ? 'badge-purple'
                              : 'badge-warning'
                          }`}
                          style={{ fontSize: '0.72rem' }}
                        >
                          {preStatus}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isApproved
                              ? 'badge-success'
                              : isRejected
                              ? 'badge-danger'
                              : isUnderReview
                              ? 'badge-warning'
                              : 'badge-purple'
                          }`}
                          style={{ fontSize: '0.75rem', fontWeight: 600 }}
                        >
                          {statusVal}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                        {claim.created_at ? new Date(claim.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleOpenDetails(claim.claim_id)}
                          title="Open claim details"
                        >
                          <Eye size={14} />
                          Claim Details
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

      {/* MODAL: Create New Disaster Claim */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1rem'
          }}
        >
          <div
            style={{
              background: '#131b2e',
              border: '1px solid #233152',
              borderRadius: '12px',
              maxWidth: '640px',
              width: '100%',
              padding: '1.75rem',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.25rem',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid #1c2742'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={20} style={{ color: '#ef4444' }} />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                  File Post-Disaster Compensation Claim
                </h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {formError && (
              <div
                style={{
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  padding: '0.75rem',
                  color: '#fca5a5',
                  fontSize: '0.85rem',
                  marginBottom: '1rem'
                }}
              >
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateClaim}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
                {/* 1. Select Existing Asset */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    1. Select Registered Asset *
                  </label>
                  <select
                    className="role-select"
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.6rem', borderRadius: '6px', fontSize: '0.875rem' }}
                    value={selectedAssetId}
                    onChange={(e) => setSelectedAssetId(e.target.value)}
                    required
                  >
                    {assets.map((a) => (
                      <option key={a.asset_id} value={a.asset_id}>
                        {a.asset_id} — {a.category.replace(/_/g, ' ')}: {a.description.slice(0, 36)}... ({a.status})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Selected Asset Summary Card */}
                {activeSelectedAsset && (
                  <div
                    style={{
                      background: '#0b0f19',
                      border: '1px solid #1c2742',
                      borderRadius: '8px',
                      padding: '0.85rem',
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                      gap: '0.75rem'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Category</div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }}>
                        {activeSelectedAsset.category.replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Baseline Value</div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#10b981' }}>
                        ₹{activeSelectedAsset.documented_value.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Pre-Disaster Baseline</div>
                      <span
                        className={`badge ${
                          activeSelectedAsset.status === 'VERIFIED'
                            ? 'badge-success'
                            : activeSelectedAsset.status === 'PARTIALLY_VERIFIED'
                            ? 'badge-purple'
                            : 'badge-warning'
                        }`}
                        style={{ fontSize: '0.7rem' }}
                      >
                        {activeSelectedAsset.status}
                      </span>
                    </div>
                  </div>
                )}

                {/* 2. Select Disaster Event */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    2. Select Declared Disaster Event *
                  </label>
                  <select
                    className="role-select"
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.6rem', borderRadius: '6px', fontSize: '0.875rem' }}
                    value={selectedDisasterId}
                    onChange={(e) => setSelectedDisasterId(e.target.value)}
                    required
                  >
                    {disasters.map((d) => (
                      <option key={d.disaster_code} value={d.disaster_code}>
                        {d.disaster_code} — {d.name} ({d.severity || 'CRITICAL'})
                      </option>
                    ))}
                  </select>
                </div>

                {/* 3. Damage Description */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    3. Detailed Damage Description *
                  </label>
                  <textarea
                    rows={4}
                    placeholder="Describe specific flood/structural damages sustained (e.g. wall cracks, roof collapse, submerged machinery, water level depth)..."
                    value={damageDescription}
                    onChange={(e) => setDamageDescription(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      background: '#0b0f19',
                      border: '1px solid #233152',
                      color: '#f8fafc',
                      padding: '0.65rem',
                      borderRadius: '6px',
                      fontSize: '0.875rem',
                      fontFamily: 'inherit',
                      resize: 'vertical'
                    }}
                  />
                  <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                    Post-disaster evidence (photos, videos, surveyor reports) can be uploaded to this claim once submitted.
                  </span>
                </div>

                {/* Action Buttons */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setShowCreateModal(false)}
                    disabled={submitting}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={submitting}
                    style={{ background: '#ef4444', borderColor: '#dc2626' }}
                  >
                    {submitting ? (
                      <>
                        <RefreshCw size={14} className="animate-spin" />
                        Filing Claim...
                      </>
                    ) : (
                      'Submit Disaster Claim'
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Open Claim Details */}
      {selectedClaim && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1rem'
          }}
        >
          <div
            style={{
              background: '#131b2e',
              border: '1px solid #233152',
              borderRadius: '12px',
              maxWidth: '740px',
              width: '100%',
              padding: '1.75rem',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.25rem',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid #1c2742'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileText size={20} style={{ color: '#ef4444' }} />
                  <span style={{ fontSize: '1.15rem', fontWeight: 700 }}>Claim Details</span>
                  <code style={{ fontSize: '0.9rem', color: '#38bdf8' }}>{selectedClaim.claim_id}</code>
                </div>
              </div>
              <button
                onClick={() => setSelectedClaim(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Status Banner */}
              <div
                style={{
                  background: '#0b0f19',
                  border: '1px solid #1c2742',
                  borderRadius: '8px',
                  padding: '1rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.75rem'
                }}
              >
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                    Referenced Asset
                  </div>
                  <div style={{ fontWeight: 700, fontSize: '1.05rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Boxes size={16} style={{ color: '#3b82f6' }} />
                    <code>{selectedClaim.asset_id}</code>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                    Review Status
                  </div>
                  <span
                    className={`badge ${
                      (selectedClaim.review_status || selectedClaim.claim_status) === 'APPROVED'
                        ? 'badge-success'
                        : (selectedClaim.review_status || selectedClaim.claim_status) === 'REJECTED'
                        ? 'badge-danger'
                        : (selectedClaim.review_status || selectedClaim.claim_status) === 'UNDER_REVIEW'
                        ? 'badge-warning'
                        : 'badge-purple'
                    }`}
                    style={{ fontSize: '0.8rem' }}
                  >
                    {selectedClaim.review_status || selectedClaim.claim_status || 'SUBMITTED'}
                  </span>
                </div>
              </div>

              {/* Grid Attributes */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Disaster Event</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', marginTop: '0.25rem' }}>
                    {selectedClaim.disaster_id || selectedClaim.disaster_event}
                  </div>
                </div>

                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Pre-Disaster Baseline</div>
                  <div style={{ marginTop: '0.25rem' }}>
                    <span
                      className={`badge ${
                        (selectedClaim.pre_disaster_verification_status || selectedClaim.pre_disaster_verification_state) === 'VERIFIED'
                          ? 'badge-success'
                          : 'badge-purple'
                      }`}
                      style={{ fontSize: '0.75rem' }}
                    >
                      {selectedClaim.pre_disaster_verification_status || selectedClaim.pre_disaster_verification_state || 'UNVERIFIED'}
                    </span>
                  </div>
                </div>

                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Household Ref</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#a5b4fc', marginTop: '0.25rem' }}>
                    {selectedClaim.household_ref || selectedClaim.household || 'HH-1001'}
                  </div>
                </div>

                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Submission Date</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#cbd5e1', marginTop: '0.25rem' }}>
                    {selectedClaim.created_at ? new Date(selectedClaim.created_at).toLocaleString() : 'N/A'}
                  </div>
                </div>
              </div>

              {/* Damage Description */}
              <div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                  Reported Damage Description
                </div>
                <div
                  style={{
                    background: '#0b0f19',
                    border: '1px solid #1c2742',
                    borderRadius: '6px',
                    padding: '0.85rem',
                    fontSize: '0.875rem',
                    lineHeight: 1.5,
                    color: '#f8fafc'
                  }}
                >
                  {selectedClaim.damage_description}
                </div>
              </div>

              {/* Officer Decision Note if present */}
              {selectedClaim.officer_decision && (
                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.85rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                    Government Officer Decision
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#f8fafc' }}>
                    {selectedClaim.officer_decision}
                  </div>
                </div>
              )}

              {/* Post-Disaster Evidence Section (Step 23) */}
              <div style={{ borderTop: '1px solid #1c2742', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Camera size={18} style={{ color: '#ef4444' }} />
                    <span style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                      Post-Disaster Evidence
                    </span>
                  </div>
                  <span className="badge badge-purple" style={{ fontSize: '0.75rem' }}>
                    {claimEvidence.length} Item{claimEvidence.length === 1 ? '' : 's'} Uploaded
                  </span>
                </div>

                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem', lineHeight: 1.4 }}>
                  Upload proof of post-disaster damages. Supported formats include damaged photos, damaged videos, and field inspection documents.
                  Files are preserved in secure private storage with SHA-256 cryptographic verification.
                </p>

                {/* Status Messages */}
                {evidenceError && (
                  <div
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid #ef4444',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      color: '#fca5a5',
                      fontSize: '0.825rem',
                      marginBottom: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <AlertCircle size={16} />
                    <span>{evidenceError}</span>
                  </div>
                )}

                {evidenceSuccess && (
                  <div
                    style={{
                      background: 'rgba(16, 185, 129, 0.15)',
                      border: '1px solid #10b981',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      color: '#6ee7b7',
                      fontSize: '0.825rem',
                      marginBottom: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <CheckCircle size={16} />
                    <span>{evidenceSuccess}</span>
                  </div>
                )}

                {/* Evidence Upload Form */}
                <form
                  onSubmit={handleUploadClaimEvidence}
                  style={{
                    background: '#0b0f19',
                    border: '1px solid #1c2742',
                    borderRadius: '8px',
                    padding: '1rem',
                    marginBottom: '1.25rem'
                  }}
                >
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <UploadCloud size={16} style={{ color: '#38bdf8' }} />
                    Upload Evidence Item
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.85rem', marginBottom: '0.85rem' }}>
                    {/* Evidence Type */}
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                        Evidence Type *
                      </label>
                      <select
                        className="role-select"
                        style={{
                          width: '100%',
                          background: '#131b2e',
                          border: '1px solid #233152',
                          color: '#f8fafc',
                          padding: '0.55rem',
                          borderRadius: '6px',
                          fontSize: '0.825rem'
                        }}
                        value={evidenceType}
                        onChange={(e) => setEvidenceType(e.target.value)}
                      >
                        <option value="POST_DISASTER_PHOTO">Damaged Photo (JPG, PNG, WEBP, HEIC)</option>
                        <option value="POST_DISASTER_VIDEO">Damaged Video (MP4, MOV, WEBM, AVI)</option>
                        <option value="FIELD_INSPECTION_REPORT">Inspection Document (PDF, DOCX, TXT)</option>
                      </select>
                    </div>

                    {/* File Input */}
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                        Select File *
                      </label>
                      <input
                        id="claim-evidence-file-input"
                        type="file"
                        accept={
                          evidenceType === 'POST_DISASTER_PHOTO'
                            ? 'image/*,.heic,.webp'
                            : evidenceType === 'POST_DISASTER_VIDEO'
                            ? 'video/*,.mp4,.mov,.webm,.avi'
                            : '.pdf,.doc,.docx,.txt,image/*'
                        }
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setEvidenceFile(e.target.files[0])
                            setEvidenceError(null)
                          }
                        }}
                        style={{
                          width: '100%',
                          fontSize: '0.8rem',
                          color: '#cbd5e1',
                          background: '#131b2e',
                          border: '1px solid #233152',
                          padding: '0.45rem',
                          borderRadius: '6px'
                        }}
                      />
                    </div>
                  </div>

                  {/* Ready to upload feedback & button */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      {evidenceFile ? (
                        <span style={{ color: '#38bdf8' }}>
                          Selected: <strong>{evidenceFile.name}</strong> ({(evidenceFile.size / 1024).toFixed(1)} KB)
                        </span>
                      ) : (
                        <span>Please select a damaged photo, video, or inspection report above.</span>
                      )}
                    </div>

                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      disabled={uploadingEvidence || !evidenceFile}
                      style={{ background: '#ef4444', borderColor: '#dc2626' }}
                    >
                      {uploadingEvidence ? (
                        <>
                          <RefreshCw size={13} className="animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <UploadCloud size={14} />
                          Upload Evidence
                        </>
                      )}
                    </button>
                  </div>

                  {uploadStatus && (
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.5rem', fontStyle: 'italic' }}>
                      {uploadStatus}
                    </div>
                  )}
                </form>

                {/* Uploaded Evidence Records List */}
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.65rem' }}>
                    Uploaded Evidence Records
                  </div>

                  {claimEvidence.length === 0 ? (
                    <div
                      style={{
                        background: '#0b0f19',
                        border: '1px dashed #1c2742',
                        borderRadius: '8px',
                        padding: '1.5rem',
                        textAlign: 'center',
                        color: '#94a3b8',
                        fontSize: '0.825rem'
                      }}
                    >
                      <Paperclip size={22} style={{ margin: '0 auto 0.5rem auto', opacity: 0.5 }} />
                      <div>No post-disaster evidence uploaded for this claim yet.</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                        Upload damaged photos, videos, or inspection documents using the form above.
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                      {claimEvidence.map((ev) => {
                        const isPhoto = ev.evidence_type.includes('PHOTO') || (ev.mime_type && ev.mime_type.startsWith('image/'))
                        const isVideo = ev.evidence_type.includes('VIDEO') || (ev.mime_type && ev.mime_type.startsWith('video/'))

                        return (
                          <div
                            key={ev.evidence_id}
                            style={{
                              background: '#0b0f19',
                              border: '1px solid #1c2742',
                              borderRadius: '8px',
                              padding: '0.75rem 1rem',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              flexWrap: 'wrap',
                              gap: '0.75rem'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                              <div
                                style={{
                                  width: '36px',
                                  height: '36px',
                                  borderRadius: '8px',
                                  background: isPhoto ? 'rgba(56, 189, 248, 0.12)' : isVideo ? 'rgba(239, 68, 68, 0.12)' : 'rgba(168, 85, 247, 0.12)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: isPhoto ? '#38bdf8' : isVideo ? '#ef4444' : '#c084fc',
                                  flexShrink: 0
                                }}
                              >
                                {isPhoto ? <Camera size={18} /> : isVideo ? <Video size={18} /> : <FileText size={18} />}
                              </div>

                              <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                  <code style={{ fontSize: '0.8rem', fontWeight: 600, color: '#38bdf8' }}>
                                    {ev.evidence_id}
                                  </code>
                                  <span
                                    className={`badge ${isPhoto ? 'badge-primary' : isVideo ? 'badge-danger' : 'badge-purple'}`}
                                    style={{ fontSize: '0.7rem' }}
                                  >
                                    {ev.evidence_type.replace(/_/g, ' ')}
                                  </span>
                                </div>

                                <div style={{ fontSize: '0.825rem', color: '#f8fafc', fontWeight: 500, marginTop: '0.2rem' }}>
                                  {ev.original_filename}
                                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginLeft: '0.5rem' }}>
                                    ({(ev.file_size / 1024).toFixed(1)} KB)
                                  </span>
                                </div>

                                <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                  <span>SHA-256: {ev.sha256_hash.slice(0, 16)}...</span>
                                  <span>•</span>
                                  <span>{ev.created_at ? new Date(ev.created_at).toLocaleString() : 'N/A'}</span>
                                </div>
                              </div>
                            </div>

                            <div>
                              <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                                SHA-256 Stored
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* AI Damage Assessment Section (Step 24) */}
              <div style={{ borderTop: '1px solid #1c2742', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Sparkles size={18} style={{ color: '#38bdf8' }} />
                    <span style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                      AI Damage Assessment
                    </span>
                  </div>

                  {/* Clearly display DEMO AI / SIMULATED ASSESSMENT */}
                  <span
                    style={{
                      background: 'rgba(234, 179, 8, 0.15)',
                      border: '1px solid #eab308',
                      color: '#fde047',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                      padding: '0.25rem 0.65rem',
                      borderRadius: '9999px',
                      textTransform: 'uppercase',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem'
                    }}
                  >
                    <AlertTriangle size={12} />
                    DEMO AI / SIMULATED ASSESSMENT
                  </span>
                </div>

                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem', lineHeight: 1.4 }}>
                  Compare pre-disaster baseline records against post-disaster uploaded evidence.
                  This analysis is simulated for demonstration and does not automatically approve or reject the claim.
                </p>

                {/* Status Messages */}
                {assessmentError && (
                  <div
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid #ef4444',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      color: '#fca5a5',
                      fontSize: '0.825rem',
                      marginBottom: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <AlertCircle size={16} />
                    <span>{assessmentError}</span>
                  </div>
                )}

                {assessmentSuccess && (
                  <div
                    style={{
                      background: 'rgba(16, 185, 129, 0.15)',
                      border: '1px solid #10b981',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      color: '#6ee7b7',
                      fontSize: '0.825rem',
                      marginBottom: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <CheckCircle size={16} />
                    <span>{assessmentSuccess}</span>
                  </div>
                )}

                {/* Run AI Damage Assessment Button */}
                <div style={{ marginBottom: '1rem' }}>
                  <button
                    className="btn btn-primary"
                    onClick={handleRunAssessment}
                    disabled={assessing}
                    style={{
                      background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                      borderColor: '#0284c7',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {assessing ? (
                      <>
                        <RefreshCw size={15} className="animate-spin" />
                        Evaluating Evidence...
                      </>
                    ) : (
                      <>
                        <Sparkles size={15} />
                        Run AI Damage Assessment
                      </>
                    )}
                  </button>
                </div>

                {/* Results Card */}
                {assessment ? (
                  <div
                    style={{
                      background: '#0b0f19',
                      border: '1px solid #1c2742',
                      borderRadius: '8px',
                      padding: '1.25rem',
                      marginBottom: '1.25rem'
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '1rem',
                        paddingBottom: '0.75rem',
                        borderBottom: '1px solid #1c2742',
                        flexWrap: 'wrap',
                        gap: '0.5rem'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Cpu size={18} style={{ color: '#38bdf8' }} />
                        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                          Assessment Results
                        </span>
                      </div>
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

                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '0.75rem',
                        marginBottom: '1rem'
                      }}
                    >
                      {/* Damage Category */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Damage Category</div>
                        <div style={{ marginTop: '0.25rem' }}>
                          <span
                            className={`badge ${
                              assessment.damage_category.includes('MAJOR')
                                ? 'badge-danger'
                                : assessment.damage_category.includes('MODERATE')
                                ? 'badge-warning'
                                : 'badge-purple'
                            }`}
                            style={{ fontSize: '0.75rem', fontWeight: 600 }}
                          >
                            {assessment.damage_category.replace(/_/g, ' ')}
                          </span>
                        </div>
                      </div>

                      {/* Damage Percentage */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Damage Percentage</div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ef4444', marginTop: '0.15rem' }}>
                          {assessment.estimated_damage_percentage}%
                        </div>
                      </div>

                      {/* Asset Match Confidence */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Asset Match Confidence</div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#10b981', marginTop: '0.15rem' }}>
                          {assessment.asset_match_confidence}%
                        </div>
                      </div>

                      {/* Evidence Confidence */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Evidence Confidence</div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38bdf8', marginTop: '0.15rem' }}>
                          {assessment.evidence_quality || assessment.overall_confidence}%
                        </div>
                      </div>

                      {/* Assessment Mode */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Assessment Mode</div>
                        <div style={{ fontSize: '0.825rem', fontWeight: 700, color: '#facc15', marginTop: '0.35rem' }}>
                          {assessment.assessment_mode}
                        </div>
                      </div>
                    </div>

                    {/* Explanation */}
                    <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.85rem' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.3rem' }}>
                        Explanation
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#f8fafc', lineHeight: 1.5 }}>
                        {assessment.explanation}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div
                    style={{
                      background: '#0b0f19',
                      border: '1px dashed #1c2742',
                      borderRadius: '8px',
                      padding: '1.25rem',
                      textAlign: 'center',
                      color: '#94a3b8',
                      fontSize: '0.825rem',
                      marginBottom: '1.25rem'
                    }}
                  >
                    <div>No AI damage assessment performed yet.</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                      Click "Run AI Damage Assessment" above to evaluate imagery and calculate estimated damage.
                    </div>
                  </div>
                )}
              </div>

              {/* Value & Loss Assessment Section (Step 25) */}
              <div style={{ borderTop: '1px solid #1c2742', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Calculator size={18} style={{ color: '#10b981' }} />
                    <span style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                      Value & Loss Assessment
                    </span>
                  </div>

                  {/* Clearly display AI-ASSISTED ESTIMATE */}
                  <span
                    style={{
                      background: 'rgba(16, 185, 129, 0.15)',
                      border: '1px solid #10b981',
                      color: '#6ee7b7',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                      padding: '0.25rem 0.65rem',
                      borderRadius: '9999px',
                      textTransform: 'uppercase',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem'
                    }}
                  >
                    AI-ASSISTED ESTIMATE
                  </span>
                </div>

                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem', lineHeight: 1.4 }}>
                  Connects to baseline registered asset value, depreciation, and AI damage assessment.
                </p>

                {/* Statutory Disclaimer required by specification */}
                <div
                  style={{
                    background: 'rgba(234, 179, 8, 0.08)',
                    border: '1px solid rgba(234, 179, 8, 0.3)',
                    borderRadius: '6px',
                    padding: '0.75rem 0.9rem',
                    marginBottom: '1rem',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.6rem'
                  }}
                >
                  <AlertTriangle size={17} style={{ color: '#facc15', flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ fontSize: '0.78rem', color: '#fef08a', lineHeight: 1.45 }}>
                    <strong>Notice: </strong>
                    This is not a guaranteed compensation amount. Final compensation is subject to government verification and applicable rules.
                  </div>
                </div>

                {/* Status Messages */}
                {lossError && (
                  <div
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid #ef4444',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      color: '#fca5a5',
                      fontSize: '0.825rem',
                      marginBottom: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <AlertCircle size={16} />
                    <span>{lossError}</span>
                  </div>
                )}

                {lossSuccess && (
                  <div
                    style={{
                      background: 'rgba(16, 185, 129, 0.15)',
                      border: '1px solid #10b981',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      color: '#6ee7b7',
                      fontSize: '0.825rem',
                      marginBottom: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <CheckCircle size={16} />
                    <span>{lossSuccess}</span>
                  </div>
                )}

                {/* Calculate Loss Button */}
                <div style={{ marginBottom: '1rem' }}>
                  <button
                    className="btn btn-primary"
                    onClick={handleCalculateLoss}
                    disabled={calculatingLoss}
                    style={{
                      background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                      borderColor: '#059669',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {calculatingLoss ? (
                      <>
                        <RefreshCw size={15} className="animate-spin" />
                        Calculating Estimate...
                      </>
                    ) : (
                      <>
                        <Calculator size={15} />
                        Calculate Loss Estimate
                      </>
                    )}
                  </button>
                </div>

                {/* Loss Estimate Display Card */}
                {lossEstimate ? (
                  <div
                    style={{
                      background: '#0b0f19',
                      border: '1px solid #1c2742',
                      borderRadius: '8px',
                      padding: '1.25rem',
                      marginBottom: '1.25rem'
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '1rem',
                        paddingBottom: '0.75rem',
                        borderBottom: '1px solid #1c2742',
                        flexWrap: 'wrap',
                        gap: '0.5rem'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Calculator size={18} style={{ color: '#10b981' }} />
                        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                          Assessment Results
                        </span>
                      </div>
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

                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '0.75rem',
                        marginBottom: '1rem'
                      }}
                    >
                      {/* Original Value */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Original Value</div>
                        <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.15rem' }}>
                          ₹{lossEstimate.original_documented_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                      </div>

                      {/* Current/Reference Value */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Current/Reference Value</div>
                        <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#38bdf8', marginTop: '0.15rem' }}>
                          ₹{lossEstimate.reference_current_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                      </div>

                      {/* Damage Percentage */}
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Damage Percentage</div>
                        <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#ef4444', marginTop: '0.15rem' }}>
                          {lossEstimate.damage_percentage}%
                        </div>
                      </div>

                      {/* Indicative Loss Estimate */}
                      <div
                        style={{
                          background: 'rgba(239, 68, 68, 0.08)',
                          border: '1px solid rgba(239, 68, 68, 0.4)',
                          borderRadius: '6px',
                          padding: '0.75rem'
                        }}
                      >
                        <div style={{ fontSize: '0.7rem', color: '#fca5a5', textTransform: 'uppercase', fontWeight: 600 }}>
                          Indicative Loss Estimate
                        </div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#f87171', marginTop: '0.15rem' }}>
                          ₹{lossEstimate.indicative_loss_estimate.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                      </div>
                    </div>

                    {/* Calculation Explanation */}
                    {lossEstimate.calculation_explanation && (
                      <div style={{ background: '#131b2e', border: '1px solid #233152', borderRadius: '6px', padding: '0.85rem' }}>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.3rem' }}>
                          Calculation Explanation
                        </div>
                        <div style={{ fontSize: '0.825rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                          {lossEstimate.calculation_explanation}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div
                    style={{
                      background: '#0b0f19',
                      border: '1px dashed #1c2742',
                      borderRadius: '8px',
                      padding: '1.25rem',
                      textAlign: 'center',
                      color: '#94a3b8',
                      fontSize: '0.825rem',
                      marginBottom: '1.25rem'
                    }}
                  >
                    <div>No loss estimate calculated yet.</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                      Click "Calculate Loss Estimate" above to generate an indicative loss amount based on baseline records.
                    </div>
                  </div>
                )}
              </div>

              {/* Audit Timeline & Anomaly Warnings */}
              <AuditTimeline
                auditEvents={claimAuditHistory}
                claim={selectedClaim}
                assessment={assessment}
                postEvidenceCount={claimEvidence.length}
                anomalies={claimAnomalies}
              />

              {/* Accountability Notice */}
              <div
                style={{
                  background: 'rgba(59, 130, 246, 0.08)',
                  border: '1px solid rgba(59, 130, 246, 0.25)',
                  borderRadius: '6px',
                  padding: '0.75rem',
                  fontSize: '0.78rem',
                  color: '#93c5fd',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                <Shield size={16} style={{ flexShrink: 0 }} />
                <span>
                  This claim is sequentially anchored in the SHA-256 audit ledger. Damage assessments and compensation allocations require official field inspection and supervisor review.
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button className="btn btn-secondary" onClick={() => setSelectedClaim(null)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
