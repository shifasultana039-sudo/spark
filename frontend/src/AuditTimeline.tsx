import React, { useState } from 'react'
import {
  CheckCircle,
  Clock,
  Circle,
  Shield,
  Lock,
  ChevronDown,
  ChevronUp,
  FileText,
  Boxes,
  Sparkles,
  UserCheck,
  Award,
  AlertTriangle,
  Info
} from 'lucide-react'
import {
  AuditRecordItem,
  Claim,
  Asset,
  DamageAssessment,
  AnomalyListResponse,
  AnomalyFlag
} from './types'

interface AuditTimelineProps {
  auditEvents: AuditRecordItem[]
  claim: Claim | null
  asset?: Asset | null
  assessment?: DamageAssessment | null
  preEvidenceCount?: number
  postEvidenceCount?: number
  anomalies?: AnomalyListResponse | null
}

interface MilestoneDef {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  completed: boolean
  timestamp?: string
  actor?: string
  recordId?: string
  hash?: string
  note?: string
}

export function AuditTimeline({
  auditEvents = [],
  claim,
  asset,
  assessment,
  preEvidenceCount = 0,
  postEvidenceCount = 0,
  anomalies
}: AuditTimelineProps) {
  const [showFullHashChain, setShowFullHashChain] = useState<boolean>(false)

  // -------------------------------------------------------------
  // Map Audit Events to the 7 Specified Milestones
  // 1. Asset Registered
  // 2. Evidence Added
  // 3. Verification Completed
  // 4. Certificate Generated
  // 5. Claim Created
  // 6. AI Assessment Created
  // 7. Officer Reviewed
  // -------------------------------------------------------------

  // Find corresponding audit events
  const assetRegEv = auditEvents.find(
    (e) => e.event_type === 'ASSET_REGISTERED' || e.event_type === 'ASSET_REGISTRATION'
  )
  const evAddedEv = auditEvents.find(
    (e) =>
      e.event_type === 'EVIDENCE_ADDED' ||
      e.event_type === 'CLAIM_EVIDENCE_UPLOADED' ||
      e.event_type === 'INSPECTION_EVIDENCE_UPLOADED'
  )
  const verifyEv = auditEvents.find(
    (e) => e.event_type === 'ASSET_VERIFIED' || e.event_type === 'ASSET_VERIFICATION_COMPLETED'
  )
  const certEv = auditEvents.find(
    (e) => e.event_type === 'CERTIFICATE_ISSUED' || e.event_type === 'CERTIFICATE_GENERATED'
  )
  const claimCreatedEv = auditEvents.find(
    (e) => e.event_type === 'CLAIM_FILED' || e.event_type === 'CLAIM_CREATED'
  )
  const aiAssessEv = auditEvents.find(
    (e) =>
      e.event_type === 'DAMAGE_ASSESSMENT_COMPLETED' ||
      e.event_type === 'LOSS_ESTIMATED' ||
      e.event_type === 'ASSESSMENT_RUN'
  )
  const officerReviewedEv = auditEvents.find((e) =>
    [
      'CLAIM_APPROVED',
      'CLAIM_REJECTED',
      'CLAIM_FORWARDED_FOR_INSPECTION',
      'EVIDENCE_REQUESTED',
      'CLAIM_ASSESSMENT_MODIFIED',
      'INSPECTION_COMPLETED'
    ].includes(e.event_type)
  )

  // Determine completion and details for each milestone
  const milestones: MilestoneDef[] = [
    {
      id: 'asset-registered',
      title: 'Asset Registered',
      description: 'Pre-disaster asset documentation submitted to registry.',
      icon: <Boxes size={18} />,
      completed: Boolean(assetRegEv || asset?.asset_id || claim?.asset_id),
      timestamp: assetRegEv?.timestamp || asset?.created_at,
      actor: assetRegEv?.actor || asset?.citizen_name || 'Citizen',
      recordId: assetRegEv?.record_id,
      hash: assetRegEv?.current_hash,
      note: asset?.category ? `Category: ${asset.category.replace(/_/g, ' ')}` : undefined
    },
    {
      id: 'evidence-added',
      title: 'Evidence Added',
      description: 'Baseline photographs and post-disaster survey evidence uploaded.',
      icon: <FileText size={18} />,
      completed: Boolean(evAddedEv || preEvidenceCount > 0 || postEvidenceCount > 0),
      timestamp: evAddedEv?.timestamp,
      actor: evAddedEv?.actor || 'Citizen / Assessor',
      recordId: evAddedEv?.record_id,
      hash: evAddedEv?.current_hash || evAddedEv?.evidence_hash,
      note: `${preEvidenceCount + postEvidenceCount} verified evidence items linked`
    },
    {
      id: 'verification-completed',
      title: 'Verification Completed',
      description: 'Multi-factor baseline confidence check and registration verification completed.',
      icon: <Shield size={18} />,
      completed: Boolean(verifyEv || asset?.verification_status === 'VERIFIED' || asset?.is_verified),
      timestamp: verifyEv?.timestamp,
      actor: verifyEv?.actor || 'Verification Engine',
      recordId: verifyEv?.record_id,
      hash: verifyEv?.current_hash,
      note: 'Ownership & evidentiary integrity verified'
    },
    {
      id: 'certificate-generated',
      title: 'Certificate Generated',
      description: 'Tamper-evident Safe Asset Certificate issued with verifiable QR hash.',
      icon: <Award size={18} />,
      completed: Boolean(certEv || asset?.has_certificate || asset?.certificate_id),
      timestamp: certEv?.timestamp,
      actor: certEv?.actor || 'Disaster Authority',
      recordId: certEv?.record_id,
      hash: certEv?.current_hash,
      note: asset?.certificate_id ? `Cert ID: ${asset.certificate_id}` : 'Certificate registered'
    },
    {
      id: 'claim-created',
      title: 'Claim Created',
      description: 'Official post-disaster relief claim submitted by household.',
      icon: <Clock size={18} />,
      completed: Boolean(claimCreatedEv || claim?.claim_id),
      timestamp: claimCreatedEv?.timestamp || claim?.created_at,
      actor: claimCreatedEv?.actor || claim?.household_ref || 'Claimant',
      recordId: claimCreatedEv?.record_id,
      hash: claimCreatedEv?.current_hash,
      note: claim?.disaster_type ? `Disaster: ${claim.disaster_type}` : undefined
    },
    {
      id: 'ai-assessment-created',
      title: 'AI Assessment Created',
      description: 'Automated computer vision structural assessment & loss calculation generated.',
      icon: <Sparkles size={18} />,
      completed: Boolean(aiAssessEv || assessment?.claim_id || claim?.damage_percentage != null),
      timestamp: aiAssessEv?.timestamp || assessment?.created_at,
      actor: aiAssessEv?.actor || assessment?.provider_name || 'AI Vision Engine',
      recordId: aiAssessEv?.record_id,
      hash: aiAssessEv?.current_hash,
      note: assessment?.damage_category ? `Assessed: ${assessment.damage_category.replace(/_/g, ' ')} (${assessment.estimated_damage_percentage}%)` : undefined
    },
    {
      id: 'officer-reviewed',
      title: 'Officer Reviewed',
      description: 'Government Revenue Officer evaluated dossier, findings, and decided next action.',
      icon: <UserCheck size={18} />,
      completed: Boolean(
        officerReviewedEv ||
        (claim?.review_status && claim.review_status !== 'SUBMITTED' && claim.review_status !== 'PENDING')
      ),
      timestamp: officerReviewedEv?.timestamp || claim?.updated_at,
      actor: officerReviewedEv?.actor || 'Government Officer',
      recordId: officerReviewedEv?.record_id,
      hash: officerReviewedEv?.current_hash,
      note: claim?.review_status ? `Status: ${claim.review_status.replace(/_/g, ' ')}` : undefined
    }
  ]

  // Count completed
  const completedCount = milestones.filter((m) => m.completed).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* ------------------------------------------------------------- */}
      {/* ANOMALY DISPLAY: REVIEW REQUIRED */}
      {/* ------------------------------------------------------------- */}
      {anomalies && (
        <div
          style={{
            background: '#0f172a',
            border: anomalies.total_anomalies > 0 ? '1px solid #f59e0b' : '1px solid #10b981',
            borderRadius: '10px',
            padding: '1.25rem'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <AlertTriangle size={18} style={{ color: anomalies.total_anomalies > 0 ? '#f59e0b' : '#10b981' }} />
              Anomaly Detection & Review Advisories ({anomalies.total_anomalies || 0})
            </h3>
            <span
              style={{
                background: anomalies.total_anomalies > 0 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                border: `1px solid ${anomalies.total_anomalies > 0 ? '#f59e0b' : '#10b981'}`,
                color: anomalies.total_anomalies > 0 ? '#fbbf24' : '#6ee7b7',
                fontSize: '0.75rem',
                padding: '0.25rem 0.65rem',
                borderRadius: '4px',
                fontWeight: 800,
                letterSpacing: '0.5px'
              }}
            >
              {anomalies.total_anomalies > 0 ? 'REVIEW REQUIRED' : 'NO ANOMALIES DETECTED'}
            </span>
          </div>

          {anomalies.total_anomalies === 0 ? (
            <div
              style={{
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: '8px',
                padding: '0.85rem 1rem',
                color: '#a7f3d0',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem'
              }}
            >
              <CheckCircle size={18} style={{ color: '#10b981', flexShrink: 0 }} />
              <span>
                Standard automated validation passed. Photographic hashes, GPS parcel boundaries, and registration data conform to normal parameters.
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div
                style={{
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.25)',
                  borderRadius: '8px',
                  padding: '0.75rem 1rem',
                  fontSize: '0.825rem',
                  color: '#fde68a',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                <Info size={16} style={{ color: '#f59e0b', flexShrink: 0 }} />
                <span>
                  <strong>Manual Verification Advisory:</strong> Discrepancies flagged below require standard officer review. Claimants are not assumed or categorized as fraudulent; human verification is required.
                </span>
              </div>

              {anomalies.anomalies.map((flag: AnomalyFlag, idx: number) => (
                <div
                  key={idx}
                  style={{
                    background: '#131b2e',
                    border: '1px solid rgba(245, 158, 11, 0.35)',
                    borderRadius: '8px',
                    padding: '0.85rem 1rem',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.75rem'
                  }}
                >
                  <AlertTriangle size={18} style={{ color: '#f59e0b', flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fef08a' }}>
                        {flag.flag_type ? flag.flag_type.replace(/_/g, ' ') : 'VERIFICATION NOTICE'}
                      </span>
                      <span
                        style={{
                          background: 'rgba(245, 158, 11, 0.2)',
                          border: '1px solid #f59e0b',
                          color: '#fef08a',
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '0.15rem 0.5rem',
                          borderRadius: '4px'
                        }}
                      >
                        REVIEW REQUIRED
                      </span>
                    </div>

                    <div style={{ fontSize: '0.825rem', color: '#e2e8f0', marginTop: '0.35rem', lineHeight: 1.4 }}>
                      {flag.reason}
                    </div>

                    {flag.related_record && (
                      <div style={{ fontSize: '0.725rem', color: '#94a3b8', marginTop: '0.3rem' }}>
                        Related Record: <code style={{ color: '#38bdf8' }}>{flag.related_record}</code>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* AUDIT TIMELINE (7 Milestones) */}
      {/* ------------------------------------------------------------- */}
      <div
        style={{
          background: '#0f172a',
          border: '1px solid #1c2742',
          borderRadius: '10px',
          padding: '1.25rem'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <Shield size={18} style={{ color: '#38bdf8' }} />
              Claim Audit Timeline
            </h3>
            <span style={{ fontSize: '0.775rem', color: '#94a3b8' }}>
              Progressive verification & evidentiary trail ({completedCount} of 7 stages completed)
            </span>
          </div>

          <span
            style={{
              background: completedCount === 7 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
              border: `1px solid ${completedCount === 7 ? '#10b981' : '#38bdf8'}`,
              color: completedCount === 7 ? '#6ee7b7' : '#7dd3fc',
              fontSize: '0.72rem',
              padding: '0.2rem 0.55rem',
              borderRadius: '4px',
              fontWeight: 700
            }}
          >
            {completedCount === 7 ? 'ALL STAGES VERIFIED' : 'ACTIVE AUDIT TRAIL'}
          </span>
        </div>

        {/* Timeline Steps Container */}
        <div style={{ position: 'relative', paddingLeft: '2rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Continuous vertical line connecting all milestones */}
          <div
            style={{
              position: 'absolute',
              left: '15px',
              top: '12px',
              bottom: '16px',
              width: '2px',
              background: 'linear-gradient(to bottom, #10b981 0%, #38bdf8 60%, #334155 100%)',
              zIndex: 1
            }}
          />

          {milestones.map((m, index) => {
            const isCompleted = m.completed
            const isNextPending = !isCompleted && (index === 0 || milestones[index - 1].completed)

            return (
              <div
                key={m.id}
                style={{
                  position: 'relative',
                  zIndex: 2,
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.85rem'
                }}
              >
                {/* Node Indicator */}
                <div
                  style={{
                    position: 'absolute',
                    left: '-2rem',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: isCompleted ? '#059669' : isNextPending ? '#0284c7' : '#1e293b',
                    border: isCompleted
                      ? '2px solid #34d399'
                      : isNextPending
                      ? '2px solid #38bdf8'
                      : '2px solid #475569',
                    color: isCompleted ? '#ffffff' : isNextPending ? '#ffffff' : '#94a3b8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: isCompleted
                      ? '0 0 10px rgba(16, 185, 129, 0.3)'
                      : isNextPending
                      ? '0 0 10px rgba(56, 189, 248, 0.3)'
                      : 'none',
                    flexShrink: 0
                  }}
                >
                  {isCompleted ? <CheckCircle size={16} /> : isNextPending ? <Clock size={16} /> : <Circle size={12} />}
                </div>

                {/* Milestone Content Card */}
                <div
                  style={{
                    flex: 1,
                    background: isCompleted ? '#131b2e' : '#0b1120',
                    border: isCompleted ? '1px solid #1f2d4d' : '1px dashed #1e293b',
                    borderRadius: '8px',
                    padding: '0.75rem 1rem',
                    opacity: isCompleted ? 1 : isNextPending ? 0.9 : 0.6
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.9rem', fontWeight: 700, color: isCompleted ? '#f8fafc' : isNextPending ? '#38bdf8' : '#94a3b8' }}>
                        {m.title}
                      </span>
                      {isCompleted && (
                        <span className="badge badge-success" style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}>
                          COMPLETED
                        </span>
                      )}
                      {isNextPending && (
                        <span className="badge badge-info" style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}>
                          AWAITING
                        </span>
                      )}
                    </div>

                    {m.timestamp && (
                      <span style={{ fontSize: '0.725rem', color: '#64748b' }}>
                        {new Date(m.timestamp).toLocaleString()}
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                    {m.description}
                  </div>

                  {/* Metadata line: Actor, Note, Record ID */}
                  {(m.actor || m.note || m.recordId) && (
                    <div style={{ marginTop: '0.4rem', paddingTop: '0.4rem', borderTop: '1px solid #1c2742', display: 'flex', gap: '0.85rem', flexWrap: 'wrap', fontSize: '0.725rem', color: '#64748b' }}>
                      {m.actor && (
                        <span>
                          Actor: <strong style={{ color: '#cbd5e1' }}>{m.actor}</strong>
                        </span>
                      )}
                      {m.note && (
                        <span style={{ color: '#38bdf8' }}>
                          {m.note}
                        </span>
                      )}
                      {m.recordId && (
                        <span style={{ fontFamily: 'monospace' }}>
                          Record: {m.recordId}
                        </span>
                      )}
                      {m.hash && (
                        <span style={{ fontFamily: 'monospace' }}>
                          Hash: {m.hash.slice(0, 10)}...
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* ----------------------------------------------------------- */}
        {/* Expandable Tamper-Evident SHA-256 Ledger Records */}
        {/* ----------------------------------------------------------- */}
        <div style={{ marginTop: '1.25rem', borderTop: '1px solid #1c2742', paddingTop: '0.85rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowFullHashChain(!showFullHashChain)}
            style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Lock size={14} style={{ color: '#38bdf8' }} />
              View Sequential Tamper-Evident Ledger ({auditEvents.length} Events)
            </span>
            {showFullHashChain ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showFullHashChain && (
            <div style={{ marginTop: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {auditEvents.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1rem', color: '#94a3b8', fontSize: '0.8rem' }}>
                  No raw audit log records available.
                </div>
              ) : (
                auditEvents.map((ev, idx) => (
                  <div
                    key={ev.record_id || idx}
                    style={{
                      background: '#131b2e',
                      border: '1px solid #1f2d4d',
                      borderRadius: '6px',
                      padding: '0.65rem 0.85rem',
                      fontSize: '0.775rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                        {ev.event_type.replace(/_/g, ' ')}
                      </span>
                      <span style={{ color: '#64748b', fontSize: '0.7rem' }}>
                        {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : 'Recent'}
                      </span>
                    </div>
                    <div style={{ color: '#94a3b8', marginBottom: '0.3rem' }}>
                      {ev.description}
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem', color: '#64748b', fontSize: '0.7rem', flexWrap: 'wrap', fontFamily: 'monospace' }}>
                      <span>Actor: {ev.actor} ({ev.role || 'CITIZEN'})</span>
                      <span>Prev: {ev.previous_hash ? ev.previous_hash.slice(0, 10) + '...' : 'Genesis'}</span>
                      <span>Hash: {ev.current_hash ? ev.current_hash.slice(0, 10) + '...' : 'N/A'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
