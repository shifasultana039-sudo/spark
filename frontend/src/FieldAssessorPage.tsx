import React, { useState, useEffect } from 'react'
import {
  ClipboardCheck,
  Search,
  RefreshCw,
  Eye,
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  Upload,
  FileText,
  Camera,
  MapPin,
  Clock,
  Shield,
  ShieldAlert,
  User,
  Info,
  Calendar,
  Check,
  Building,
  Image as ImageIcon
} from 'lucide-react'
import {
  InspectionItem,
  InspectionDetail,
  UserRole,
  ClaimEvidenceItem
} from './types'
import {
  getInspections,
  getInspectionDetails,
  updateInspectionFindings,
  uploadInspectionEvidence,
  submitInspectionReport
} from './api'

interface FieldAssessorPageProps {
  currentUser?: UserRole | null
  onNavigateToClaims?: () => void
}

export function FieldAssessorPage({ currentUser }: FieldAssessorPageProps) {
  const [inspections, setInspections] = useState<InspectionItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Filters & search
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  // Selected inspection for detail view
  const [selectedInspectionId, setSelectedInspectionId] = useState<string | null>(null)
  const [detail, setDetail] = useState<InspectionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState<boolean>(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  // Form states for adding findings
  const [findingsText, setFindingsText] = useState<string>('')
  const [severityRating, setSeverityRating] = useState<string>('MODERATE_DAMAGE')
  const [findingsSaving, setFindingsSaving] = useState<boolean>(false)
  const [findingsSuccess, setFindingsSuccess] = useState<string | null>(null)

  // Form states for uploading evidence
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [evidenceType, setEvidenceType] = useState<string>('FIELD_PHOTO')
  const [uploading, setUploading] = useState<boolean>(false)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)

  // Form states for report submission
  const [submittingReport, setSubmittingReport] = useState<boolean>(false)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)

  const loadInspectionsList = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getInspections(statusFilter)
      setInspections(data)
    } catch (err: any) {
      console.error('Failed to load inspections:', err)
      setError(err.message || 'Failed to load assigned inspections.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInspectionsList()
  }, [statusFilter])

  const openInspection = async (inspectionId: string) => {
    setSelectedInspectionId(inspectionId)
    setDetailLoading(true)
    setDetailError(null)
    setFindingsSuccess(null)
    setUploadSuccess(null)
    setSubmitSuccess(null)
    setSelectedFile(null)

    try {
      const data = await getInspectionDetails(inspectionId)
      setDetail(data)
      setFindingsText(data.field_findings || '')
      if (data.damage_severity_rating) {
        setSeverityRating(data.damage_severity_rating)
      } else {
        setSeverityRating('MODERATE_DAMAGE')
      }
    } catch (err: any) {
      console.error('Failed to load inspection details:', err)
      setDetailError(err.message || 'Failed to load inspection dossier.')
    } finally {
      setDetailLoading(false)
    }
  }

  const handleBackToList = () => {
    setSelectedInspectionId(null)
    setDetail(null)
    loadInspectionsList()
  }

  const handleSaveFindings = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detail) return
    if (!findingsText.trim()) {
      setDetailError('Please enter field findings observations.')
      return
    }

    setFindingsSaving(true)
    setDetailError(null)
    setFindingsSuccess(null)
    try {
      const updated = await updateInspectionFindings(detail.inspection_id, {
        field_findings: findingsText.trim(),
        damage_severity_rating: severityRating
      })
      setDetail(updated)
      setFindingsSuccess('Field findings and damage severity rating saved successfully.')
    } catch (err: any) {
      console.error('Failed to save findings:', err)
      setDetailError(err.message || 'Failed to update findings.')
    } finally {
      setFindingsSaving(false)
    }
  }

  const handleUploadEvidence = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detail || !selectedFile) {
      setDetailError('Please choose a file to upload.')
      return
    }

    setUploading(true)
    setDetailError(null)
    setUploadSuccess(null)
    try {
      const updated = await uploadInspectionEvidence(
        detail.inspection_id,
        selectedFile,
        evidenceType
      )
      setDetail(updated)
      setSelectedFile(null)
      setUploadSuccess(`Evidence file "${selectedFile.name}" securely uploaded and hashed.`)
      // Reset input element if exists
      const fileInput = document.getElementById('evidence-file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (err: any) {
      console.error('Failed to upload evidence:', err)
      setDetailError(err.message || 'Failed to upload evidence.')
    } finally {
      setUploading(false)
    }
  }

  const handleSubmitReport = async () => {
    if (!detail) return
    if (!findingsText.trim()) {
      setDetailError('Cannot submit report without entering field findings observations.')
      return
    }

    if (!window.confirm('Are you sure you want to finalize and submit this field inspection report to the Government Review Board? Once submitted, findings cannot be edited.')) {
      return
    }

    setSubmittingReport(true)
    setDetailError(null)
    setSubmitSuccess(null)
    try {
      const updated = await submitInspectionReport(detail.inspection_id, {
        field_findings: findingsText.trim(),
        damage_severity_rating: severityRating,
        report_file_url: detail.report_file_url
      })
      setDetail(updated)
      setSubmitSuccess('Official Inspection Report successfully submitted! Forwarded to Government Officer review.')
    } catch (err: any) {
      console.error('Failed to submit report:', err)
      setDetailError(err.message || 'Failed to submit report.')
    } finally {
      setSubmittingReport(false)
    }
  }

  // Filtered list
  const filteredInspections = inspections.filter((item) => {
    const q = searchTerm.toLowerCase().trim()
    if (!q) return true
    return (
      item.inspection_id.toLowerCase().includes(q) ||
      item.claim_id.toLowerCase().includes(q) ||
      (item.asset_id && item.asset_id.toLowerCase().includes(q)) ||
      (item.inspection_sector && item.inspection_sector.toLowerCase().includes(q)) ||
      (item.asset_address && item.asset_address.toLowerCase().includes(q)) ||
      (item.disaster_type && item.disaster_type.toLowerCase().includes(q))
    )
  })

  // Status badge styling helper
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={12} /> COMPLETED</span>
      case 'IN_PROGRESS':
        return <span className="badge badge-info" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><Clock size={12} /> IN PROGRESS</span>
      case 'PENDING':
      default:
        return <span className="badge badge-warning" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={12} /> PENDING FIELD VISIT</span>
    }
  }

  const renderSeverityBadge = (rating?: string) => {
    switch (rating) {
      case 'TOTAL_COLLAPSE':
        return <span className="badge badge-danger">TOTAL COLLAPSE (76-100%)</span>
      case 'SEVERE_DAMAGE':
        return <span className="badge badge-danger" style={{ background: '#b91c1c' }}>SEVERE DAMAGE (51-75%)</span>
      case 'MODERATE_DAMAGE':
        return <span className="badge badge-warning">MODERATE DAMAGE (26-50%)</span>
      case 'MINOR_DAMAGE':
        return <span className="badge badge-info">MINOR DAMAGE (10-25%)</span>
      default:
        return <span className="badge badge-secondary">UNRATED</span>
    }
  }

  // -------------------------------------------------------------
  // DETAIL VIEW (Assessor has opened an inspection)
  // -------------------------------------------------------------
  if (selectedInspectionId) {
    return (
      <div style={{ maxWidth: '1350px', margin: '0 auto', paddingBottom: '3rem' }}>
        {/* Navigation & Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleBackToList}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <ArrowLeft size={16} />
            Back to Assigned Inspections
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Inspection ID:</span>
            <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#f8fafc', background: '#1e293b', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
              {selectedInspectionId}
            </span>
            {detail && renderStatusBadge(detail.inspection_status)}
          </div>
        </div>

        {/* Advisory Warning: Strict Role Boundary */}
        <div
          style={{
            background: 'linear-gradient(90deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%)',
            border: '1px solid #3b82f6',
            borderRadius: '10px',
            padding: '1rem 1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.85rem'
          }}
        >
          <ShieldAlert size={22} style={{ color: '#60a5fa', flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '0.875rem', lineHeight: 1.5 }}>
            <strong style={{ color: '#93c5fd', display: 'block', marginBottom: '0.2rem' }}>
              NGO / Field Assessor Mandate & Integrity Scope
            </strong>
            <p style={{ margin: 0, color: '#cbd5e1' }}>
              You are recording ground-truth physical evidence and structural observations.
              <strong style={{ color: '#f59e0b' }}> NGO assessors cannot approve or reject disaster claims</strong>; claim decisions are executed by Government Revenue Officers following receipt of your verified inspection report.
            </p>
          </div>
        </div>

        {/* Global Notifications */}
        {detailError && (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#fca5a5', padding: '0.85rem 1.25rem', borderRadius: '8px', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={18} />
            <span>{detailError}</span>
          </div>
        )}
        {findingsSuccess && (
          <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', color: '#6ee7b7', padding: '0.85rem 1.25rem', borderRadius: '8px', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={18} />
            <span>{findingsSuccess}</span>
          </div>
        )}
        {uploadSuccess && (
          <div style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid #3b82f6', color: '#93c5fd', padding: '0.85rem 1.25rem', borderRadius: '8px', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={18} />
            <span>{uploadSuccess}</span>
          </div>
        )}
        {submitSuccess && (
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', color: '#a7f3d0', padding: '1rem 1.25rem', borderRadius: '8px', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <CheckCircle size={22} style={{ color: '#10b981' }} />
            <div>
              <strong style={{ display: 'block', fontSize: '1rem', color: '#f0fdf4' }}>{submitSuccess}</strong>
              <span style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>Government Review Officers will now examine your findings in the official claim adjudication dossier.</span>
            </div>
          </div>
        )}

        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: '4rem 0', color: '#94a3b8' }}>
            <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 1rem auto' }} />
            <p>Loading inspection dossier from secure backend...</p>
          </div>
        ) : !detail ? (
          <div style={{ textAlign: 'center', padding: '3rem 0', color: '#94a3b8' }}>
            Inspection details not found.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.8fr) minmax(0, 1.2fr)', gap: '1.5rem' }}>
            {/* Left Column: Context & Ground Evidence Form */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Card 1: Forwarded Claim & Asset Context */}
              <div className="card" style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '12px', padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                    <Building size={18} style={{ color: '#38bdf8' }} />
                    Asset & Forwarding Context
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    Sector: <strong style={{ color: '#38bdf8' }}>{detail.inspection_sector || 'District Zone 1'}</strong>
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div style={{ background: '#1f2937', padding: '0.75rem 1rem', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Target Claim ID</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', fontFamily: 'monospace', marginTop: '0.2rem' }}>
                      {detail.claim_id}
                    </div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.75rem 1rem', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Registered Asset ID</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', fontFamily: 'monospace', marginTop: '0.2rem' }}>
                      {detail.asset_id}
                    </div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.75rem 1rem', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Forwarding Officer</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginTop: '0.2rem' }}>
                      {detail.assigned_officer}
                    </div>
                  </div>
                </div>

                {/* Special Instructions from Officer */}
                <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '8px', padding: '0.85rem 1rem', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Info size={14} /> Officer Field Instructions:
                  </div>
                  <div style={{ fontSize: '0.9rem', color: '#e0f2fe' }}>
                    {detail.special_instructions || 'Please perform complete structural survey, evaluate foundation and wall cracks, and cross-reference citizen baseline photographs.'}
                  </div>
                </div>

                {/* Citizen statement & location */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.85rem' }}>
                  <div>
                    <span style={{ color: '#94a3b8', display: 'block', fontSize: '0.75rem' }}>Physical Address:</span>
                    <span style={{ color: '#e2e8f0', fontWeight: 500 }}>{detail.asset_address || 'Katpadi, Vellore, Tamil Nadu'}</span>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8', display: 'block', fontSize: '0.75rem' }}>Citizen Claim Description:</span>
                    <span style={{ color: '#e2e8f0' }}>{detail.incident_description || 'Severe floodwater inundation and wall cracks.'}</span>
                  </div>
                </div>
              </div>

              {/* Card 2: Action 2 - Add / Update Findings */}
              <div className="card" style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '12px', padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                    <ClipboardCheck size={18} style={{ color: '#10b981' }} />
                    Step 1: Record Field Findings & Severity
                  </h3>
                  {detail.damage_severity_rating && renderSeverityBadge(detail.damage_severity_rating)}
                </div>

                <form onSubmit={handleSaveFindings}>
                  <div style={{ marginBottom: '1.25rem' }}>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: '#cbd5e1', marginBottom: '0.4rem' }}>
                      Physical Observations & Ground Survey Notes:
                    </label>
                    <textarea
                      rows={5}
                      className="form-control"
                      placeholder="Enter detailed physical inspection observations (e.g. wall fractures, foundation water level marks, roof structural compromise, salvageability)..."
                      value={findingsText}
                      onChange={(e) => setFindingsText(e.target.value)}
                      disabled={detail.inspection_status === 'COMPLETED' || findingsSaving}
                      style={{
                        width: '100%',
                        background: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        padding: '0.75rem',
                        color: '#f8fafc',
                        fontSize: '0.9rem',
                        lineHeight: 1.5,
                        resize: 'vertical'
                      }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', alignItems: 'center', marginBottom: '1.25rem' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: '#cbd5e1', marginBottom: '0.4rem' }}>
                        Damage Severity Rating:
                      </label>
                      <select
                        value={severityRating}
                        onChange={(e) => setSeverityRating(e.target.value)}
                        disabled={detail.inspection_status === 'COMPLETED' || findingsSaving}
                        style={{
                          width: '100%',
                          background: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                          padding: '0.6rem 0.75rem',
                          color: '#f8fafc',
                          fontSize: '0.9rem'
                        }}
                      >
                        <option value="MINOR_DAMAGE">MINOR_DAMAGE (10-25% superficial damage)</option>
                        <option value="MODERATE_DAMAGE">MODERATE_DAMAGE (26-50% repairable damage)</option>
                        <option value="SEVERE_DAMAGE">SEVERE_DAMAGE (51-75% structural damage)</option>
                        <option value="TOTAL_COLLAPSE">TOTAL_COLLAPSE (76-100% complete destruction)</option>
                      </select>
                    </div>

                    <div style={{ paddingTop: '1.4rem' }}>
                      <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={detail.inspection_status === 'COMPLETED' || findingsSaving}
                        style={{ width: '100%', display: 'inline-flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}
                      >
                        <Check size={16} />
                        {findingsSaving ? 'Saving Findings...' : 'Save Field Findings'}
                      </button>
                    </div>
                  </div>
                </form>
              </div>

              {/* Card 3: Action 3 - Upload Inspection Evidence */}
              <div className="card" style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '12px', padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                    <Upload size={18} style={{ color: '#a855f7' }} />
                    Step 2: Upload Inspection Evidence
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    Photos, Geotagged Survey, Signed PDF
                  </span>
                </div>

                {detail.inspection_status !== 'COMPLETED' && (
                  <form onSubmit={handleUploadEvidence} style={{ background: '#1f2937', padding: '1rem', borderRadius: '8px', marginBottom: '1.25rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                          Evidence File (JPG, PNG, PDF):
                        </label>
                        <input
                          id="evidence-file-input"
                          type="file"
                          accept="image/*,.pdf,.doc,.docx"
                          onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                          disabled={uploading}
                          style={{
                            width: '100%',
                            background: '#111827',
                            border: '1px solid #374151',
                            borderRadius: '6px',
                            padding: '0.5rem',
                            color: '#e2e8f0',
                            fontSize: '0.85rem'
                          }}
                        />
                      </div>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                          Evidence Classification:
                        </label>
                        <select
                          value={evidenceType}
                          onChange={(e) => setEvidenceType(e.target.value)}
                          disabled={uploading}
                          style={{
                            width: '100%',
                            background: '#111827',
                            border: '1px solid #374151',
                            borderRadius: '6px',
                            padding: '0.5rem',
                            color: '#e2e8f0',
                            fontSize: '0.85rem'
                          }}
                        >
                          <option value="FIELD_PHOTO">Physical Survey Photo</option>
                          <option value="FIELD_INSPECTION_REPORT">Official Signed PDF Report</option>
                          <option value="GEOTAGGED_SURVEY">Geotagged Survey Photo</option>
                          <option value="DRONE_RECON">Drone / Aerial Verification</option>
                        </select>
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="btn btn-secondary"
                      disabled={!selectedFile || uploading}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                      <Upload size={16} />
                      {uploading ? 'Hashing & Uploading...' : 'Upload & Hash Evidence File'}
                    </button>
                  </form>
                )}

                {/* Uploaded Evidence Items List */}
                <div>
                  <h4 style={{ fontSize: '0.9rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
                    Uploaded Inspection & Claim Evidence ({detail.inspection_evidence?.length || detail.claim_evidence?.length || 0})
                  </h4>

                  {((detail.inspection_evidence && detail.inspection_evidence.length > 0) || (detail.claim_evidence && detail.claim_evidence.length > 0)) ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                      {/* Combine or show inspection evidence */}
                      {(detail.inspection_evidence || detail.claim_evidence || []).map((ev: ClaimEvidenceItem) => (
                        <div
                          key={ev.evidence_id}
                          style={{
                            background: '#1f2937',
                            border: '1px solid #374151',
                            borderRadius: '8px',
                            padding: '0.75rem 1rem',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '0.5rem'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            {ev.mime_type.includes('pdf') ? (
                              <FileText size={20} style={{ color: '#f59e0b' }} />
                            ) : (
                              <Camera size={20} style={{ color: '#38bdf8' }} />
                            )}
                            <div>
                              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                                {ev.original_filename}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', gap: '0.75rem' }}>
                                <span>{ev.evidence_type}</span>
                                <span>{(ev.file_size / 1024).toFixed(1)} KB</span>
                                <span style={{ fontFamily: 'monospace' }}>
                                  SHA: {ev.sha256_hash ? ev.sha256_hash.substring(0, 12) + '...' : 'Verified'}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span className="badge badge-success" style={{ fontSize: '0.75rem' }}>STORED</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '1.5rem', background: '#1f2937', borderRadius: '8px', color: '#94a3b8', fontSize: '0.85rem' }}>
                      No inspection evidence uploaded yet. Please upload physical photos or survey documents.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Right Column: Submission & Review Summary */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Card 4: Action 4 - Submit Inspection Report */}
              <div className="card" style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '12px', padding: '1.5rem' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 0, marginBottom: '1rem' }}>
                  <Shield size={18} style={{ color: '#3b82f6' }} />
                  Step 3: Submit Final Report
                </h3>

                {detail.inspection_status === 'COMPLETED' ? (
                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', borderRadius: '8px', padding: '1rem', textAlign: 'center' }}>
                    <CheckCircle size={32} style={{ color: '#10b981', margin: '0 auto 0.5rem auto' }} />
                    <div style={{ fontWeight: 600, color: '#f0fdf4', fontSize: '0.95rem' }}>
                      Inspection Report Officially Submitted
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.35rem' }}>
                      Submitted on {detail.report_submitted_at ? new Date(detail.report_submitted_at).toLocaleString() : 'Recently'}
                    </div>
                    {detail.submitted_by && (
                      <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.2rem' }}>
                        Field Assessor: <strong>{detail.submitted_by}</strong>
                      </div>
                    )}
                    <div style={{ marginTop: '0.85rem', padding: '0.5rem', background: '#1f2937', borderRadius: '6px', fontSize: '0.8rem', color: '#a7f3d0' }}>
                      Status: Forwarded to Government Review Dossier
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ background: '#1f2937', borderRadius: '8px', padding: '1rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                      <div style={{ color: '#cbd5e1', marginBottom: '0.5rem', fontWeight: 500 }}>
                        Pre-submission Checklist:
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: findingsText.trim() ? '#34d399' : '#94a3b8', marginBottom: '0.35rem' }}>
                        {findingsText.trim() ? <CheckCircle size={15} /> : <AlertTriangle size={15} />}
                        <span>Field Findings Recorded ({findingsText.trim().length} chars)</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: severityRating ? '#34d399' : '#94a3b8', marginBottom: '0.35rem' }}>
                        <CheckCircle size={15} />
                        <span>Damage Severity Selected ({severityRating})</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: ((detail.inspection_evidence?.length || 0) > 0 || (detail.claim_evidence?.length || 0) > 0) ? '#34d399' : '#f59e0b' }}>
                        {((detail.inspection_evidence?.length || 0) > 0 || (detail.claim_evidence?.length || 0) > 0) ? <CheckCircle size={15} /> : <Info size={15} />}
                        <span>Evidence Attached ({(detail.inspection_evidence?.length || 0) + (detail.claim_evidence?.length || 0)} files)</span>
                      </div>
                    </div>

                    <button
                      className="btn btn-primary"
                      onClick={handleSubmitReport}
                      disabled={submittingReport || !findingsText.trim()}
                      style={{
                        width: '100%',
                        padding: '0.75rem 1rem',
                        fontSize: '0.95rem',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem'
                      }}
                    >
                      <ClipboardCheck size={18} />
                      {submittingReport ? 'Submitting Inspection Report...' : 'Submit Official Inspection Report'}
                    </button>
                  </div>
                )}
              </div>

              {/* Baseline Asset Evidence Preview */}
              <div className="card" style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '12px', padding: '1.5rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 0, marginBottom: '0.75rem' }}>
                  <ImageIcon size={16} style={{ color: '#38bdf8' }} />
                  Pre-Disaster Baseline Reference
                </h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>
                  Cross-verify ground reality with pre-disaster registered photos from citizen asset registry:
                </p>

                {detail.asset_evidence && detail.asset_evidence.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {detail.asset_evidence.map((ae) => (
                      <div
                        key={ae.evidence_id}
                        style={{
                          background: '#1f2937',
                          padding: '0.5rem 0.75rem',
                          borderRadius: '6px',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: '0.8rem'
                        }}
                      >
                        <span style={{ color: '#cbd5e1' }}>{ae.original_filename}</span>
                        <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>BASELINE</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '1rem', background: '#1f2937', borderRadius: '6px', color: '#94a3b8', fontSize: '0.8rem' }}>
                    No baseline asset photos on file.
                  </div>
                )}
              </div>

              {/* Strict Governance Notice */}
              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px dashed #334155',
                  borderRadius: '10px',
                  padding: '1rem',
                  fontSize: '0.8rem',
                  color: '#94a3b8'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#f1f5f9', fontWeight: 600, marginBottom: '0.3rem' }}>
                  <Shield size={14} style={{ color: '#64748b' }} />
                  Tamper-Evident Hash Chain
                </div>
                Every inspection update, observation note, and photo upload generates a sequential SHA-256 hash linked to the ReliefChain immutable audit ledger.
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // -------------------------------------------------------------
  // LIST VIEW (Assigned inspections queue)
  // -------------------------------------------------------------
  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* Header Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)',
          border: '1px solid #3730a3',
          borderRadius: '12px',
          padding: '1.5rem 2rem',
          marginBottom: '1.75rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1.25rem'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
            <span className="badge badge-info" style={{ background: '#4338ca' }}>
              NGO & FIELD OPERATIONS
            </span>
            <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
              Sector Dispatch & Physical Verification
            </span>
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
            Field Assessor & NGO Inspection Portal
          </h1>
          <p style={{ margin: '0.4rem 0 0 0', color: '#cbd5e1', fontSize: '0.9rem' }}>
            Conduct physical surveys of damaged assets, add factual findings, upload evidence, and submit inspection reports to Government Officers.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={loadInspectionsList}
            disabled={loading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh Queue
          </button>
        </div>
      </div>

      {/* Role Reminder Advisory */}
      <div
        style={{
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: '10px',
          padding: '0.85rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}
      >
        <Shield size={20} style={{ color: '#60a5fa', flexShrink: 0 }} />
        <span style={{ fontSize: '0.85rem', color: '#bfdbfe' }}>
          <strong>Policy Governance:</strong> NGO & Field Assessors provide unbiased ground observations and evidence uploads. Claim approval or rejection decisions are made exclusively by Government Officers.
        </span>
      </div>

      {/* Search & Filter Controls */}
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
        {/* Status Filter Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {(['ALL', 'PENDING', 'IN_PROGRESS', 'COMPLETED'] as const).map((st) => (
            <button
              key={st}
              className={`btn btn-sm ${statusFilter === st ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setStatusFilter(st)}
              style={{ fontWeight: statusFilter === st ? 600 : 400 }}
            >
              {st === 'ALL' ? 'All Assigned' : st.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div style={{ position: 'relative', minWidth: '320px' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search by Inspection ID, Claim ID, Sector..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '0.5rem 0.75rem 0.5rem 2.25rem',
              color: '#f8fafc',
              fontSize: '0.85rem'
            }}
          />
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#fca5a5', padding: '0.85rem 1.25rem', borderRadius: '8px', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Inspections Grid / Cards */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem 0', color: '#94a3b8' }}>
          <RefreshCw size={32} className="animate-spin" style={{ margin: '0 auto 1rem auto' }} />
          <p>Loading assigned field inspections from backend...</p>
        </div>
      ) : filteredInspections.length === 0 ? (
        <div
          style={{
            background: '#111827',
            border: '1px dashed #374151',
            borderRadius: '12px',
            padding: '3.5rem 2rem',
            textAlign: 'center',
            color: '#94a3b8'
          }}
        >
          <ClipboardCheck size={44} style={{ color: '#4b5563', margin: '0 auto 1rem auto' }} />
          <h3 style={{ color: '#e5e7eb', fontSize: '1.15rem', marginBottom: '0.5rem' }}>
            No Inspections Found
          </h3>
          <p style={{ maxWidth: '520px', margin: '0 auto', fontSize: '0.9rem', color: '#9ca3af' }}>
            {searchTerm
              ? `No assigned inspections match "${searchTerm}". Try a different search term or filter.`
              : 'There are currently no field inspections assigned matching this status filter. When Government Officers forward claims for inspection, they will automatically appear here.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: '1.25rem' }}>
          {filteredInspections.map((item) => (
            <div
              key={item.inspection_id}
              className="card"
              style={{
                background: '#111827',
                border: '1px solid #1f2937',
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'border-color 0.2s, transform 0.2s',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            >
              <div>
                {/* Header row: Status & ID */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, fontSize: '0.9rem', color: '#38bdf8' }}>
                    {item.inspection_id}
                  </span>
                  {renderStatusBadge(item.inspection_status)}
                </div>

                {/* Claim ID & Sector */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
                  <div style={{ color: '#cbd5e1' }}>
                    Claim: <strong style={{ color: '#f8fafc', fontFamily: 'monospace' }}>{item.claim_id}</strong>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#94a3b8' }}>
                    <MapPin size={14} style={{ color: '#ef4444' }} />
                    <span>{item.inspection_sector || 'Katpadi Sector'}</span>
                  </div>
                </div>

                {/* Instructions or description */}
                {item.special_instructions && (
                  <div
                    style={{
                      background: 'rgba(30, 41, 59, 0.8)',
                      borderLeft: '3px solid #38bdf8',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '0 6px 6px 0',
                      fontSize: '0.825rem',
                      color: '#cbd5e1',
                      marginBottom: '0.75rem'
                    }}
                  >
                    <strong style={{ color: '#38bdf8' }}>Officer Note: </strong>
                    {item.special_instructions}
                  </div>
                )}

                {/* Findings summary if recorded */}
                {item.field_findings && (
                  <div
                    style={{
                      background: '#1f2937',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '6px',
                      fontSize: '0.825rem',
                      color: '#94a3b8',
                      marginBottom: '0.75rem'
                    }}
                  >
                    <strong style={{ color: '#10b981' }}>Findings: </strong>
                    {item.field_findings.length > 90 ? item.field_findings.substring(0, 90) + '...' : item.field_findings}
                  </div>
                )}

                {/* Details grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.775rem', color: '#94a3b8', borderTop: '1px solid #1f2937', paddingTop: '0.75rem', marginBottom: '1rem' }}>
                  <div>
                    <span>Assigned By:</span>
                    <div style={{ color: '#e2e8f0', fontWeight: 500 }}>{item.assigned_officer}</div>
                  </div>
                  <div>
                    <span>Severity Rating:</span>
                    <div>{renderSeverityBadge(item.damage_severity_rating)}</div>
                  </div>
                  <div>
                    <span>Disaster Type:</span>
                    <div style={{ color: '#e2e8f0' }}>{item.disaster_type || 'FLOOD'}</div>
                  </div>
                  <div>
                    <span>Assigned Date:</span>
                    <div style={{ color: '#e2e8f0' }}>{item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Recent'}</div>
                  </div>
                </div>
              </div>

              {/* Action Button: Open Inspection */}
              <button
                className="btn btn-primary"
                onClick={() => openInspection(item.inspection_id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  fontSize: '0.875rem'
                }}
              >
                <Eye size={16} />
                Open Inspection Dossier
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
