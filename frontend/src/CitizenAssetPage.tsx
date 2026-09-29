import React, { useEffect, useState } from 'react'
import {
  Boxes,
  Shield,
  ShieldCheck,
  PlusCircle,
  CheckCircle,
  AlertCircle,
  MapPin,
  X,
  RefreshCw,
  FileText,
  Upload,
  Paperclip,
  Award,
  QrCode
} from 'lucide-react'
import {
  Asset,
  CreateAssetPayload,
  EvidenceItem,
  AssetVerificationResult,
  AssetCertificate,
  UserRole
} from './types'
import {
  getAssets,
  getAsset,
  createAsset,
  getAssetEvidence,
  uploadAssetEvidence,
  getAssetVerification,
  verifyAsset,
  getAssetCertificate,
  generateAssetCertificate
} from './api'

interface CitizenAssetPageProps {
  currentUser?: UserRole | null
  onAssetAdded?: () => void
}

export function CitizenAssetPage({ currentUser, onAssetAdded }: CitizenAssetPageProps) {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Add Asset modal / form state
  const [showAddModal, setShowAddModal] = useState<boolean>(false)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [category, setCategory] = useState<string>('HOUSE_PROPERTY')
  const [description, setDescription] = useState<string>('')
  const [documentedValue, setDocumentedValue] = useState<string>('')
  const [locationAddress, setLocationAddress] = useState<string>('')
  const [purchaseDate, setPurchaseDate] = useState<string>('')

  // View Details modal state
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)
  const [detailsLoading, setDetailsLoading] = useState<boolean>(false)

  // Evidence state in Asset Details
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([])
  const [evidenceLoading, setEvidenceLoading] = useState<boolean>(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  const [evidenceSuccess, setEvidenceSuccess] = useState<string | null>(null)

  // Upload Evidence form state
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [evidenceType, setEvidenceType] = useState<string>('GOVERNMENT_REGISTRATION')
  const [uploading, setUploading] = useState<boolean>(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)

  // Verification state in Asset Details (Step 20)
  const [verificationResult, setVerificationResult] = useState<AssetVerificationResult | null>(null)
  const [verifying, setVerifying] = useState<boolean>(false)
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const [verifySuccess, setVerifySuccess] = useState<string | null>(null)

  // Digital Certificate state in Asset Details (Step 21)
  const [certificate, setCertificate] = useState<AssetCertificate | null>(null)
  const [generatingCert, setGeneratingCert] = useState<boolean>(false)
  const [certError, setCertError] = useState<string | null>(null)
  const [certSuccess, setCertSuccess] = useState<string | null>(null)

  const loadAssetList = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAssets()
      setAssets(data)
    } catch (err: any) {
      console.error('Failed to load assets:', err)
      setError(err.message || 'Unable to load registered assets from backend.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAssetList()
  }, [currentUser?.user_id])

  const loadEvidenceForAsset = async (assetId: string) => {
    setEvidenceLoading(true)
    setEvidenceError(null)
    try {
      const items = await getAssetEvidence(assetId)
      setEvidenceList(items)
    } catch (err: any) {
      console.error('Failed to load asset evidence:', err)
      setEvidenceError(err.message || 'Unable to load evidence records.')
    } finally {
      setEvidenceLoading(false)
    }
  }

  const handleOpenDetails = async (assetId: string) => {
    setDetailsLoading(true)
    setError(null)
    setEvidenceError(null)
    setEvidenceSuccess(null)
    setVerifyError(null)
    setVerifySuccess(null)
    setCertError(null)
    setCertSuccess(null)
    setCertificate(null)
    setUploadFile(null)
    setUploadStatus(null)

    try {
      const [asset, evList, vrfResult, cert] = await Promise.all([
        getAsset(assetId),
        getAssetEvidence(assetId).catch(() => []),
        getAssetVerification(assetId).catch(() => null),
        getAssetCertificate(assetId).catch(() => null)
      ])
      setSelectedAsset(asset)
      setEvidenceList(evList)
      setVerificationResult(vrfResult)
      setCertificate(cert)
    } catch (err: any) {
      console.error('Failed to fetch asset details:', err)
      setError(err.message || 'Failed to retrieve asset details.')
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleVerifyAsset = async () => {
    if (!selectedAsset) return
    setVerifying(true)
    setVerifyError(null)
    setVerifySuccess(null)
    setCertError(null)
    setCertSuccess(null)

    try {
      const result = await verifyAsset(selectedAsset.asset_id)
      setVerificationResult(result)
      setSelectedAsset((prev) =>
        prev
          ? {
              ...prev,
              status: result.status,
              verification_confidence: result.confidence
            }
          : null
      )
      setVerifySuccess(
        `Asset verification completed! Status: ${result.status} (${result.confidence}% confidence).`
      )

      // If verified or can issue certificate, check if certificate exists
      if (result.status === 'VERIFIED' || result.status === 'OFFICIALLY_CONFIRMED' || result.confidence >= 80) {
        getAssetCertificate(selectedAsset.asset_id)
          .then((c) => setCertificate(c))
          .catch(() => {})
      }

      // Refresh asset list so main table reflects updated verification status
      await loadAssetList()
    } catch (err: any) {
      console.error('Asset verification failed:', err)
      setVerifyError(err.message || 'Failed to evaluate asset verification.')
    } finally {
      setVerifying(false)
    }
  }

  const handleGenerateCertificate = async () => {
    if (!selectedAsset) return
    setGeneratingCert(true)
    setCertError(null)
    setCertSuccess(null)

    try {
      const cert = await generateAssetCertificate(selectedAsset.asset_id)
      setCertificate(cert)
      setSelectedAsset((prev) =>
        prev
          ? {
              ...prev,
              certificate_token: cert.certificate_token,
              status: cert.verification_status,
              verification_confidence: cert.evidence_confidence
            }
          : null
      )
      setCertSuccess(`Digital Asset Certificate ${cert.certificate_id} generated successfully!`)
      await loadAssetList()
    } catch (err: any) {
      console.error('Failed to generate certificate:', err)
      setCertError(err.message || 'Failed to generate digital asset certificate.')
    } finally {
      setGeneratingCert(false)
    }
  }

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    // Validation
    const val = parseFloat(documentedValue)
    if (isNaN(val) || val <= 0) {
      setFormError('Please enter a valid positive documented value in INR.')
      return
    }
    if (!description.trim() || description.trim().length < 3) {
      setFormError('Description must be at least 3 characters.')
      return
    }
    if (!locationAddress.trim()) {
      setFormError('Location address is required.')
      return
    }

    setSubmitting(true)
    try {
      const payload: CreateAssetPayload = {
        category,
        description: description.trim(),
        documented_value: val,
        location_address: locationAddress.trim(),
        purchase_date: purchaseDate || undefined
      }

      const created = await createAsset(payload)
      setSuccessMsg(`Asset ${created.asset_id} registered successfully!`)
      setShowAddModal(false)

      // Reset form fields
      setDescription('')
      setDocumentedValue('')
      setLocationAddress('')
      setPurchaseDate('')

      // Reload assets so the new asset appears immediately
      await loadAssetList()

      if (onAssetAdded) {
        onAssetAdded()
      }
    } catch (err: any) {
      console.error('Failed to register asset:', err)
      setFormError(err.message || 'Asset registration failed.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleUploadEvidence = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAsset) return

    if (!uploadFile) {
      setEvidenceError('Please select a file to upload.')
      return
    }

    setUploading(true)
    setUploadStatus('Uploading evidence file to secure storage...')
    setEvidenceError(null)
    setEvidenceSuccess(null)

    try {
      const created = await uploadAssetEvidence(selectedAsset.asset_id, uploadFile, evidenceType)
      setUploadStatus(`Upload completed. Evidence ID: ${created.evidence_id}`)
      setEvidenceSuccess(`Evidence ${created.evidence_id} (${created.evidence_type.replace(/_/g, ' ')}) uploaded successfully! Status: ${created.verification_status}`)

      // Reset selected file
      setUploadFile(null)

      // Reset file input element
      const fileInput = document.getElementById('evidence-file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''

      // Refresh evidence list immediately from backend
      await loadEvidenceForAsset(selectedAsset.asset_id)

      // Also refresh verification status from backend
      getAssetVerification(selectedAsset.asset_id)
        .then((r) => setVerificationResult(r))
        .catch(() => {})
    } catch (err: any) {
      console.error('Failed to upload evidence:', err)
      setUploadStatus('Upload failed.')
      setEvidenceError(err.message || 'Failed to upload evidence file.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      {/* Top Section / Header */}
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
            <Boxes size={26} style={{ color: '#3b82f6' }} />
            Citizen Digital Asset Registry
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Pre-disaster asset records with baseline verification and cryptographic accountability.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={loadAssetList}
            disabled={loading}
            title="Refresh assets"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>

          <button
            className="btn btn-primary"
            onClick={() => {
              setFormError(null)
              setShowAddModal(true)
            }}
          >
            <PlusCircle size={16} />
            Register New Asset
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

      {/* Asset List Panel */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <Boxes size={18} style={{ color: '#3b82f6' }} />
            Registered Assets
          </div>
          <span className="badge badge-purple">{assets.length} Total</span>
        </div>

        {loading ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: '#94a3b8' }}>
            <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 0.75rem auto' }} />
            <p>Loading registered assets from backend...</p>
          </div>
        ) : assets.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: '#94a3b8' }}>
            <Boxes size={32} style={{ margin: '0 auto 0.75rem auto', opacity: 0.5 }} />
            <p style={{ fontWeight: 600 }}>No registered assets found.</p>
            <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
              Click "Register New Asset" above to register your first pre-disaster tangible asset.
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Asset ID</th>
                  <th>Category</th>
                  <th>Description</th>
                  <th>Documented Value</th>
                  <th>Location</th>
                  <th>Verification Status</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => {
                  const isVerified = asset.status === 'VERIFIED' || asset.status === 'OFFICIALLY_CONFIRMED'
                  const isPartially = asset.status === 'PARTIALLY_VERIFIED'
                  const isFlagged = asset.status === 'FLAGGED' || asset.status === 'REJECTED'

                  return (
                    <tr key={asset.asset_id}>
                      <td>
                        <code style={{ fontSize: '0.85rem' }}>{asset.asset_id}</code>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                          {asset.category.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ maxWidth: '280px' }}>
                        <div style={{ fontSize: '0.825rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                          {asset.description}
                        </div>
                      </td>
                      <td>
                        <strong style={{ color: '#10b981', fontSize: '0.9rem' }}>
                          ₹{asset.documented_value.toLocaleString()}
                        </strong>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                          {asset.location_address}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                          <span
                            className={`badge ${
                              isVerified
                                ? 'badge-success'
                                : isPartially
                                ? 'badge-purple'
                                : isFlagged
                                ? 'badge-danger'
                                : 'badge-warning'
                            }`}
                          >
                            {asset.status}
                          </span>
                          {asset.verification_confidence !== undefined && asset.verification_confidence > 0 && (
                            <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                              {asset.verification_confidence}% Confidence
                            </span>
                          )}
                          {(asset.certificate_token || isVerified) && (
                            <span style={{ fontSize: '0.68rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <Award size={11} />
                              {asset.certificate_token ? 'Certified' : 'Certificate Ready'}
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleOpenDetails(asset.asset_id)}
                          title="View asset details and evidence"
                        >
                          <FileText size={14} />
                          Details & Evidence
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

      {/* MODAL: Register New Asset Form */}
      {showAddModal && (
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
              maxWidth: '560px',
              width: '100%',
              padding: '1.75rem',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)'
            }}
          >
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem', fontWeight: 700 }}>
                <PlusCircle size={20} style={{ color: '#3b82f6' }} />
                <span>Register New Asset</span>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
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

            <form onSubmit={handleFormSubmit}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Category */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Asset Category *
                  </label>
                  <select
                    className="role-select"
                    style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.6rem', borderRadius: '6px' }}
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="HOUSE_PROPERTY">House / Property</option>
                    <option value="VEHICLE">Vehicle (Car, Motorcycle, Truck)</option>
                    <option value="AGRICULTURAL_EQUIPMENT">Agricultural Equipment (Tractor, Pump, Tiller)</option>
                    <option value="ELECTRONICS">Electronics (Computer, Solar, Inverter)</option>
                    <option value="HOUSEHOLD_APPLIANCE">Household Appliance</option>
                    <option value="LIVESTOCK">Livestock / Farm Animals</option>
                    <option value="BUSINESS_EQUIPMENT">Business Equipment / Inventory</option>
                    <option value="PERSONAL_PROPERTY">Personal Property</option>
                    <option value="OTHER">Other Tangible Asset</option>
                  </select>
                </div>

                {/* Documented Value & Purchase Date */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      Documented Value (INR ₹) *
                    </label>
                    <input
                      type="number"
                      placeholder="e.g. 500000"
                      value={documentedValue}
                      onChange={(e) => setDocumentedValue(e.target.value)}
                      required
                      min="1"
                      style={{
                        width: '100%',
                        background: '#0b0f19',
                        border: '1px solid #233152',
                        color: '#f8fafc',
                        padding: '0.6rem',
                        borderRadius: '6px',
                        fontSize: '0.875rem'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      Purchase Date (YYYY-MM-DD)
                    </label>
                    <input
                      type="date"
                      value={purchaseDate}
                      onChange={(e) => setPurchaseDate(e.target.value)}
                      style={{
                        width: '100%',
                        background: '#0b0f19',
                        border: '1px solid #233152',
                        color: '#f8fafc',
                        padding: '0.6rem',
                        borderRadius: '6px',
                        fontSize: '0.875rem'
                      }}
                    />
                  </div>
                </div>

                {/* Location Address */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Physical Location / Address *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 14/2 Railway Feeder Road, Katpadi, Vellore"
                    value={locationAddress}
                    onChange={(e) => setLocationAddress(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      background: '#0b0f19',
                      border: '1px solid #233152',
                      color: '#f8fafc',
                      padding: '0.6rem',
                      borderRadius: '6px',
                      fontSize: '0.875rem'
                    }}
                  />
                </div>

                {/* Description */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Asset Description *
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Provide specific details (e.g. dimensions, construction type, model number, identifying features)..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      background: '#0b0f19',
                      border: '1px solid #233152',
                      color: '#f8fafc',
                      padding: '0.6rem',
                      borderRadius: '6px',
                      fontSize: '0.875rem',
                      fontFamily: 'inherit',
                      resize: 'vertical'
                    }}
                  />
                </div>

                {/* Action Buttons */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.75rem' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setShowAddModal(false)}
                    disabled={submitting}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <RefreshCw size={14} className="animate-spin" />
                        Registering Asset...
                      </>
                    ) : (
                      'Register Asset'
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: View Asset Details & Evidence Upload */}
      {selectedAsset && (
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
              maxWidth: '720px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '1.75rem',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)'
            }}
          >
            {/* Modal Header */}
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
                  <FileText size={20} style={{ color: '#3b82f6' }} />
                  <span style={{ fontSize: '1.15rem', fontWeight: 700 }}>Asset Details</span>
                  <code style={{ fontSize: '0.9rem', color: '#94a3b8' }}>{selectedAsset.asset_id}</code>
                </div>
              </div>
              <button
                onClick={() => setSelectedAsset(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Category & Status Banner */}
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
                    Asset Category
                  </div>
                  <div style={{ fontWeight: 700, fontSize: '1.05rem', color: '#f8fafc' }}>
                    {selectedAsset.category.replace(/_/g, ' ')}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                    Verification Status
                  </div>
                  <span
                    className={`badge ${
                      selectedAsset.status === 'VERIFIED' || selectedAsset.status === 'OFFICIALLY_CONFIRMED'
                        ? 'badge-success'
                        : selectedAsset.status === 'PARTIALLY_VERIFIED'
                        ? 'badge-purple'
                        : selectedAsset.status === 'FLAGGED' || selectedAsset.status === 'REJECTED'
                        ? 'badge-danger'
                        : 'badge-warning'
                    }`}
                  >
                    {selectedAsset.status}
                  </span>
                </div>
              </div>

              {/* Description */}
              <div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Description</div>
                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem', fontSize: '0.875rem' }}>
                  {selectedAsset.description}
                </div>
              </div>

              {/* Key Attributes Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem' }}>
                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Documented Value</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10b981', marginTop: '0.2rem' }}>
                    ₹{selectedAsset.documented_value.toLocaleString()}
                  </div>
                </div>

                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Purchase Date</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, marginTop: '0.2rem' }}>
                    {selectedAsset.purchase_date || 'N/A'}
                  </div>
                </div>

                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Household Ref</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#a5b4fc', marginTop: '0.2rem' }}>
                    {selectedAsset.household_ref || selectedAsset.household || 'N/A'}
                  </div>
                </div>

                <div style={{ background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Physical Status</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: selectedAsset.current_status === 'DAMAGED' ? '#ef4444' : '#10b981', marginTop: '0.2rem' }}>
                    {selectedAsset.current_status || 'INTACT'}
                  </div>
                </div>
              </div>

              {/* Location */}
              <div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Location Address</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0b0f19', border: '1px solid #1c2742', borderRadius: '6px', padding: '0.75rem', fontSize: '0.875rem' }}>
                  <MapPin size={16} style={{ color: '#3b82f6', flexShrink: 0 }} />
                  <span>{selectedAsset.location_address || selectedAsset.location}</span>
                </div>
              </div>

              {/* STEP 19: Evidence Upload & Documentation Section */}
              <div style={{ background: '#0b0f19', border: '1px solid #233152', borderRadius: '8px', padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid #1c2742', paddingBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem' }}>
                    <Paperclip size={18} style={{ color: '#3b82f6' }} />
                    <span>Asset Evidence & Ownership Proofs</span>
                  </div>
                  <span className="badge badge-purple">{evidenceList.length} Uploaded</span>
                </div>

                {/* Evidence Notifications */}
                {evidenceError && (
                  <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.75rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                    {evidenceError}
                  </div>
                )}

                {evidenceSuccess && (
                  <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '6px', padding: '0.75rem', color: '#6ee7b7', fontSize: '0.8rem', marginBottom: '1rem' }}>
                    {evidenceSuccess}
                  </div>
                )}

                {uploadStatus && !evidenceError && !evidenceSuccess && (
                  <div style={{ background: 'rgba(59, 130, 246, 0.15)', border: '1px solid #3b82f6', borderRadius: '6px', padding: '0.75rem', color: '#93c5fd', fontSize: '0.8rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <RefreshCw size={14} className="animate-spin" />
                    <span>{uploadStatus}</span>
                  </div>
                )}

                {/* Upload Evidence Form */}
                <form onSubmit={handleUploadEvidence} style={{ background: '#131b2e', border: '1px solid #1c2742', borderRadius: '8px', padding: '1rem', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Upload size={15} style={{ color: '#3b82f6' }} />
                    <span>Upload New Evidence File</span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    {/* Evidence Type */}
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                        Evidence Type *
                      </label>
                      <select
                        className="role-select"
                        style={{ width: '100%', background: '#0b0f19', border: '1px solid #233152', color: '#f8fafc', padding: '0.5rem', borderRadius: '6px', fontSize: '0.8rem' }}
                        value={evidenceType}
                        onChange={(e) => setEvidenceType(e.target.value)}
                        disabled={uploading}
                      >
                        <option value="GOVERNMENT_REGISTRATION">Government Registration / Title Deed / Patta</option>
                        <option value="PURCHASE_INVOICE">Purchase Invoice / Bill / Receipt</option>
                        <option value="TIMESTAMPED_PHOTO">Pre-Disaster Photograph</option>
                        <option value="GEOLOCATION">GPS Survey / Geolocation Map</option>
                        <option value="PREVIOUS_INSPECTION">Municipal Property Tax / Inspection</option>
                        <option value="ASSESSOR_VERIFICATION">Structural Engineer / Assessor Verification</option>
                        <option value="WARRANTY">Warranty Document</option>
                        <option value="OTHER">Other Supporting Document</option>
                      </select>
                    </div>

                    {/* File Input */}
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                        Select File (PDF, Image, Video, Document) *
                      </label>
                      <input
                        id="evidence-file-input"
                        type="file"
                        onChange={(e) => {
                          const file = e.target.files?.[0] || null
                          setUploadFile(file)
                        }}
                        disabled={uploading}
                        style={{
                          width: '100%',
                          background: '#0b0f19',
                          border: '1px solid #233152',
                          color: '#f8fafc',
                          padding: '0.4rem',
                          borderRadius: '6px',
                          fontSize: '0.8rem'
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      {uploadFile ? `Selected: ${uploadFile.name} (${(uploadFile.size / 1024).toFixed(1)} KB)` : 'No file chosen'}
                    </div>

                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      disabled={uploading || !uploadFile}
                    >
                      {uploading ? (
                        <>
                          <RefreshCw size={12} className="animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload size={12} />
                          Upload Evidence
                        </>
                      )}
                    </button>
                  </div>
                </form>

                {/* Uploaded Evidence List Table */}
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>
                    Uploaded Evidence Records ({evidenceList.length})
                  </div>

                  {evidenceLoading ? (
                    <div style={{ textAlign: 'center', padding: '1rem', color: '#94a3b8', fontSize: '0.8rem' }}>
                      <RefreshCw size={16} className="animate-spin" style={{ margin: '0 auto 0.25rem auto' }} />
                      <p>Loading evidence items...</p>
                    </div>
                  ) : evidenceList.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '1.25rem', background: '#131b2e', borderRadius: '6px', border: '1px solid #1c2742', color: '#94a3b8', fontSize: '0.8rem' }}>
                      No evidence records uploaded yet for this asset. Select a file above to add verified documentation.
                    </div>
                  ) : (
                    <div className="table-container" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Evidence ID</th>
                            <th>Type</th>
                            <th>Filename</th>
                            <th>Size</th>
                            <th>Status</th>
                            <th>Uploaded</th>
                          </tr>
                        </thead>
                        <tbody>
                          {evidenceList.map((ev) => (
                            <tr key={ev.evidence_id}>
                              <td>
                                <code style={{ fontSize: '0.75rem' }}>{ev.evidence_id}</code>
                              </td>
                              <td>
                                <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}>
                                  {ev.evidence_type.replace(/_/g, ' ')}
                                </span>
                              </td>
                              <td>
                                <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>
                                  {ev.original_filename}
                                </span>
                              </td>
                              <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                                {ev.file_size ? `${(ev.file_size / 1024).toFixed(0)} KB` : 'N/A'}
                              </td>
                              <td>
                                <span
                                  className={`badge ${
                                    ev.verification_status === 'VERIFIED'
                                      ? 'badge-success'
                                      : ev.verification_status === 'REJECTED'
                                      ? 'badge-danger'
                                      : 'badge-warning'
                                  }`}
                                  style={{ fontSize: '0.7rem' }}
                                >
                                  {ev.verification_status}
                                </span>
                              </td>
                              <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                                {new Date(ev.created_at).toLocaleDateString()}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              {/* STEP 20: Asset Verification, Confidence & Explanation */}
              <div
                style={{
                  background: '#0b0f19',
                  border: '1px solid #233152',
                  borderRadius: '8px',
                  padding: '1.25rem'
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '1rem',
                    borderBottom: '1px solid #1c2742',
                    paddingBottom: '0.5rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem' }}>
                    <ShieldCheck size={18} style={{ color: '#10b981' }} />
                    <span>Deterministic Asset Verification</span>
                  </div>

                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleVerifyAsset}
                    disabled={verifying}
                  >
                    {verifying ? (
                      <>
                        <RefreshCw size={12} className="animate-spin" />
                        Evaluating Rules...
                      </>
                    ) : (
                      <>
                        <ShieldCheck size={14} />
                        Verify Asset
                      </>
                    )}
                  </button>
                </div>

                {verifyError && (
                  <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.75rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                    {verifyError}
                  </div>
                )}

                {verifySuccess && (
                  <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '6px', padding: '0.75rem', color: '#6ee7b7', fontSize: '0.8rem', marginBottom: '1rem' }}>
                    {verifySuccess}
                  </div>
                )}

                {/* Verification Status & Confidence Meters */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                  {/* Status */}
                  <div style={{ background: '#131b2e', border: '1px solid #1c2742', borderRadius: '8px', padding: '0.85rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                      Verification Status
                    </div>
                    <span
                      className={`badge ${
                        (verificationResult?.status || selectedAsset.status) === 'VERIFIED' ||
                        (verificationResult?.status || selectedAsset.status) === 'OFFICIALLY_CONFIRMED'
                          ? 'badge-success'
                          : (verificationResult?.status || selectedAsset.status) === 'PARTIALLY_VERIFIED'
                          ? 'badge-purple'
                          : (verificationResult?.status || selectedAsset.status) === 'FLAGGED' || (verificationResult?.status || selectedAsset.status) === 'REJECTED'
                          ? 'badge-danger'
                          : 'badge-warning'
                      }`}
                      style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }}
                    >
                      {verificationResult?.status || selectedAsset.status}
                    </span>
                  </div>

                  {/* Confidence */}
                  <div style={{ background: '#131b2e', border: '1px solid #1c2742', borderRadius: '8px', padding: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                        Evidence Confidence
                      </span>
                      <strong style={{ fontSize: '1rem', color: (verificationResult ? verificationResult.confidence : (selectedAsset.verification_confidence || 0)) >= 70 ? '#10b981' : '#f59e0b' }}>
                        {verificationResult ? verificationResult.confidence : (selectedAsset.verification_confidence || 0)}%
                      </strong>
                    </div>

                    <div style={{ width: '100%', height: '8px', background: '#0b0f19', borderRadius: '4px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${Math.min(100, Math.max(0, verificationResult ? verificationResult.confidence : (selectedAsset.verification_confidence || 0)))}%`,
                          height: '100%',
                          background: (verificationResult ? verificationResult.confidence : (selectedAsset.verification_confidence || 0)) >= 70 ? '#10b981' : (verificationResult ? verificationResult.confidence : (selectedAsset.verification_confidence || 0)) >= 40 ? '#8b5cf6' : '#f59e0b',
                          transition: 'width 0.4s ease'
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Verification Explanation */}
                <div style={{ background: '#131b2e', border: '1px solid #1c2742', borderRadius: '8px', padding: '0.85rem', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                    Verification Explanation
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#f8fafc', lineHeight: 1.5 }}>
                    {verificationResult?.explanation || (
                      selectedAsset.verification_confidence !== undefined && selectedAsset.verification_confidence > 0
                        ? `Asset baseline established with ${selectedAsset.verification_confidence}% evidence confidence.`
                        : 'No verification evaluation has been performed yet. Click "Verify Asset" above to evaluate uploaded evidence against deterministic baseline rules.'
                    )}
                  </div>
                </div>

                {/* Evidence Contributions breakdown if available */}
                {verificationResult?.contributions && verificationResult.contributions.length > 0 && (
                  <div style={{ background: '#131b2e', border: '1px solid #1c2742', borderRadius: '8px', padding: '0.85rem', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                      Evidence Score Contributions ({verificationResult.contributions.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {verificationResult.contributions.map((c, idx) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', padding: '0.35rem 0.5rem', background: '#0b0f19', borderRadius: '4px' }}>
                          <span>{c.display_name || c.type.replace(/_/g, ' ')} {c.filename ? `(${c.filename})` : ''}</span>
                          <span style={{ color: '#10b981', fontWeight: 600 }}>+{c.weight}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Cryptographic Hash & Certificate Token */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.75rem', color: '#64748b' }}>
                  {selectedAsset.integrity_hash && (
                    <div style={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                      SHA-256 Hash: {selectedAsset.integrity_hash}
                    </div>
                  )}
                  {selectedAsset.certificate_token && (
                    <div>
                      Certificate Token: <code style={{ color: '#38bdf8' }}>{selectedAsset.certificate_token}</code>
                    </div>
                  )}
                  <div>
                    Registered on: {new Date(selectedAsset.created_at).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* STEP 21: Digital Asset Certificate Section */}
              {(() => {
                const isAssetVerified =
                  selectedAsset.status === 'VERIFIED' ||
                  selectedAsset.status === 'OFFICIALLY_CONFIRMED' ||
                  verificationResult?.status === 'VERIFIED' ||
                  verificationResult?.status === 'OFFICIALLY_CONFIRMED' ||
                  (verificationResult?.confidence !== undefined && verificationResult.confidence >= 80) ||
                  (selectedAsset.verification_confidence !== undefined && selectedAsset.verification_confidence >= 80)

                return (
                  <div
                    style={{
                      background: '#0b0f19',
                      border: '1px solid #233152',
                      borderRadius: '8px',
                      padding: '1.25rem'
                    }}
                  >
                    {/* Header */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '1rem',
                        borderBottom: '1px solid #1c2742',
                        paddingBottom: '0.5rem',
                        flexWrap: 'wrap',
                        gap: '0.5rem'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem' }}>
                        <Award size={18} style={{ color: '#f59e0b' }} />
                        <span>Digital Asset Certificate</span>
                      </div>

                      {isAssetVerified && !certificate && (
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={handleGenerateCertificate}
                          disabled={generatingCert}
                          style={{ background: '#f59e0b', borderColor: '#d97706', color: '#000', fontWeight: 600 }}
                        >
                          {generatingCert ? (
                            <>
                              <RefreshCw size={12} className="animate-spin" />
                              Issuing Certificate...
                            </>
                          ) : (
                            <>
                              <Award size={14} />
                              Generate Certificate
                            </>
                          )}
                        </button>
                      )}
                    </div>

                    {certError && (
                      <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', padding: '0.75rem', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '1rem' }}>
                        {certError}
                      </div>
                    )}

                    {certSuccess && (
                      <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '6px', padding: '0.75rem', color: '#6ee7b7', fontSize: '0.8rem', marginBottom: '1rem' }}>
                        {certSuccess}
                      </div>
                    )}

                    {certificate ? (
                      /* Display Certificate Details */
                      <div
                        style={{
                          background: 'linear-gradient(135deg, #131b2e 0%, #0d1527 100%)',
                          border: '1px solid #3b82f6',
                          borderRadius: '8px',
                          padding: '1.25rem',
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                          gap: '1.25rem',
                          alignItems: 'center'
                        }}
                      >
                        {/* Left: Metadata */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                            <Award size={18} style={{ color: '#f59e0b' }} />
                            <span style={{ fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.05em', color: '#f59e0b', textTransform: 'uppercase' }}>
                              Officially Verified Baseline
                            </span>
                          </div>

                          {/* 1. Certificate ID */}
                          <div>
                            <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Certificate ID</div>
                            <code style={{ fontSize: '1rem', color: '#38bdf8', fontWeight: 700 }}>
                              {certificate.certificate_id}
                            </code>
                          </div>

                          {/* 2. Asset ID */}
                          <div>
                            <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Asset ID</div>
                            <code style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>
                              {certificate.asset_id}
                            </code>
                          </div>

                          {/* 3. Verification Status & 4. Evidence Confidence */}
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                            <div>
                              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                                Verification Status
                              </div>
                              <span className="badge badge-success" style={{ fontSize: '0.8rem' }}>
                                {certificate.verification_status}
                              </span>
                            </div>

                            <div>
                              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                                Evidence Confidence
                              </div>
                              <strong style={{ fontSize: '1.05rem', color: '#10b981' }}>
                                {certificate.evidence_confidence}%
                              </strong>
                            </div>
                          </div>

                          {/* 5. Registration Date */}
                          <div>
                            <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Registration Date</div>
                            <div style={{ fontSize: '0.85rem', color: '#f8fafc', fontWeight: 500 }}>
                              {certificate.frontend_card?.registration_date || certificate.registration_timestamp?.slice(0, 10) || selectedAsset.created_at?.slice(0, 10) || 'N/A'}
                            </div>
                          </div>

                          {/* Evidence Hash */}
                          {certificate.evidence_hash && (
                            <div>
                              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Cryptographic Evidence Hash</div>
                              <div style={{ fontSize: '0.7rem', color: '#64748b', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                                {certificate.evidence_hash}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Right: 6. QR Code */}
                        <div
                          style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            background: '#0b0f19',
                            border: '1px solid #1c2742',
                            borderRadius: '8px',
                            padding: '1.25rem',
                            textAlign: 'center'
                          }}
                        >
                          <div
                            style={{
                              background: '#ffffff',
                              padding: '0.5rem',
                              borderRadius: '8px',
                              boxShadow: '0 4px 14px rgba(0, 0, 0, 0.5)',
                              display: 'inline-block',
                              marginBottom: '0.75rem'
                            }}
                          >
                            <img
                              src={certificate.qr_code}
                              alt={`QR Code for Certificate ${certificate.certificate_id}`}
                              style={{ width: '130px', height: '130px', display: 'block' }}
                            />
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#38bdf8', fontSize: '0.75rem', fontWeight: 600 }}>
                            <QrCode size={14} />
                            <span>Civic Verification QR</span>
                          </div>
                          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.25rem', maxWidth: '210px' }}>
                            Scannable baseline token for disaster assessors with zero citizen PII.
                          </div>
                        </div>
                      </div>
                    ) : isAssetVerified ? (
                      <div
                        style={{
                          background: 'rgba(245, 158, 11, 0.08)',
                          border: '1px solid rgba(245, 158, 11, 0.3)',
                          borderRadius: '8px',
                          padding: '1.25rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          flexWrap: 'wrap',
                          gap: '1rem'
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, color: '#f59e0b', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                            Digital Asset Certificate Available
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                            This asset has achieved verified baseline status ({selectedAsset.verification_confidence || verificationResult?.confidence || 0}% confidence) and is eligible for an official certificate.
                          </div>
                        </div>

                        <button
                          className="btn btn-primary"
                          onClick={handleGenerateCertificate}
                          disabled={generatingCert}
                          style={{ background: '#f59e0b', borderColor: '#d97706', color: '#000', fontWeight: 600 }}
                        >
                          {generatingCert ? (
                            <>
                              <RefreshCw size={14} className="animate-spin" />
                              Generating...
                            </>
                          ) : (
                            <>
                              <Award size={16} />
                              Generate Certificate
                            </>
                          )}
                        </button>
                      </div>
                    ) : (
                      <div
                        style={{
                          background: '#131b2e',
                          border: '1px solid #1c2742',
                          borderRadius: '8px',
                          padding: '1rem',
                          fontSize: '0.825rem',
                          color: '#94a3b8',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem'
                        }}
                      >
                        <Shield size={20} style={{ color: '#64748b', flexShrink: 0 }} />
                        <div>
                          Digital Asset Certificates require an asset to reach <strong>VERIFIED</strong> status (at least 80% evidence confidence). Upload documentation and click "Verify Asset" above to unlock certificate issuance.
                        </div>
                      </div>
                    )}
                  </div>
                )
              })()}

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button className="btn btn-secondary" onClick={() => setSelectedAsset(null)}>
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
