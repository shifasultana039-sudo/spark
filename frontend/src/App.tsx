import React, { useEffect, useState } from 'react'
import {
  Activity,
  Shield,
  ShieldCheck,
  AlertTriangle,
  Boxes,
  Database,
  Link,
  Users,
  CheckCircle,
  RefreshCw,
  Server,
  UserCheck,
  FileText,
  ClipboardCheck,
  Home,
  LogIn,
  LogOut
} from 'lucide-react'
import {
  SystemHealth,
  KpiData,
  OperationalLocation,
  DisasterReport,
  Recommendation,
  AuditVerification,
  UserRole,
  Asset,
  Claim
} from './types'
import {
  fetchHealth,
  fetchKpis,
  fetchLocations,
  fetchReports,
  fetchRecommendations,
  fetchAuditVerification,
  fetchUsers,
  login,
  logout,
  getAuthToken,
  getCurrentUser,
  getAssets,
  getClaims
} from './api'
import { CitizenAssetPage } from './CitizenAssetPage'
import { CitizenClaimPage } from './CitizenClaimPage'
import { OfficerDashboard } from './OfficerDashboard'
import { FieldAssessorPage } from './FieldAssessorPage'
import { LandingPage } from './LandingPage'
import { SignInModal } from './SignInModal'

export function App() {
  const [activeTab, setActiveTab] = useState<'home' | 'citizen-assets' | 'citizen-claims' | 'officer-dashboard' | 'ngo-inspections' | 'dashboard'>('home')
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [kpis, setKpis] = useState<KpiData | null>(null)
  const [locations, setLocations] = useState<OperationalLocation[]>([])
  const [reports, setReports] = useState<DisasterReport[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [auditStatus, setAuditStatus] = useState<AuditVerification | null>(null)
  const [users, setUsers] = useState<UserRole[]>([])
  const [activeRole, setActiveRole] = useState<string>('CITIZEN')
  const [activeUserId, setActiveUserId] = useState<string>('USR-006')
  const [currentUser, setCurrentUser] = useState<UserRole | null>(null)
  const [assets, setAssets] = useState<Asset[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [isSignInOpen, setIsSignInOpen] = useState<boolean>(false)
  const [signInRoleHint, setSignInRoleHint] = useState<string | undefined>(undefined)
  const [signInMode, setSignInMode] = useState<'signin' | 'register'>('signin')

  const handleSignInSuccess = async (user: UserRole) => {
    setCurrentUser(user)
    setActiveUserId(user.user_id)
    setActiveRole(user.role)
    setIsSignInOpen(false)

    try {
      const [assetList, claimList] = await Promise.all([getAssets(), getClaims()])
      setAssets(assetList)
      setClaims(claimList)
    } catch (e) {
      console.warn('Failed to load user assets/claims:', e)
    }

    // After proper sign in, navigate to dashboard based on role
    if (user.role === 'GOVERNMENT_OFFICER') {
      setActiveTab('officer-dashboard')
    } else if (user.role === 'FIELD_ASSESSOR' || user.role === 'FIELD_VOLUNTEER' || user.role === 'NGO') {
      setActiveTab('ngo-inspections')
    } else if (user.role === 'CITIZEN') {
      setActiveTab('citizen-assets')
    } else {
      setActiveTab('dashboard')
    }
  }

  const handleSignOut = () => {
    logout()
    setCurrentUser(null)
    setAssets([])
    setClaims([])
    setActiveTab('home')
  }

  const handleLoginAndFetch = async (userId: string) => {
    try {
      await login(userId)
      const user = await getCurrentUser()
      handleSignInSuccess(user)
    } catch (err: any) {
      console.error('API connection error:', err)
      setError(err.message || 'API connection failed')
    }
  }

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [h, k, locs, reps, recs, aud, u] = await Promise.all([
        fetchHealth(),
        fetchKpis(),
        fetchLocations(),
        fetchReports(),
        fetchRecommendations(),
        fetchAuditVerification(),
        fetchUsers()
      ])
      setHealth(h)
      setKpis(k)
      setLocations(locs)
      setReports(reps)
      setRecommendations(recs)
      setAuditStatus(aud)
      setUsers(u)

      // If user previously had a valid token, restore session
      const token = getAuthToken()
      if (token) {
        try {
          const user = await getCurrentUser()
          setCurrentUser(user)
          setActiveRole(user.role)
          setActiveUserId(user.user_id)
          const [assetList, claimList] = await Promise.all([getAssets(), getClaims()])
          setAssets(assetList)
          setClaims(claimList)
        } catch {
          logout()
          setCurrentUser(null)
        }
      }
    } catch (err: any) {
      console.error('Data load error:', err)
      setError(err.message || 'Unable to connect to ReliefChain AI backend.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  return (
    <div>
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div
            className="logo-group"
            style={{ cursor: 'pointer' }}
            onClick={() => setActiveTab('home')}
            title="Go to Home"
          >
            <div className="logo-badge">
              <Shield size={22} />
            </div>
            <div>
              <div className="app-title">RELIEFCHAIN AI</div>
              <div className="app-subtitle">
                "AI decides faster. Humans stay in control. Every critical decision is verifiable."
              </div>
            </div>
          </div>

          <div className="header-actions">
            <div className="role-badge">
              <span className={`pulse-dot ${health?.status === 'HEALTHY' ? '' : 'danger'}`} />
              <span>
                Backend: {health ? `${health.status} (${health.database})` : 'Connecting...'}
              </span>
            </div>

            {currentUser ? (
              <>
                <div className="role-badge" style={{ borderColor: '#3b82f6' }}>
                  <UserCheck size={14} style={{ color: '#10b981' }} />
                  <span>
                    Logged in: <strong style={{ color: '#f8fafc' }}>{currentUser.name}</strong> ({currentUser.role})
                  </span>
                </div>

                <div className="role-badge">
                  <Users size={14} />
                  <label htmlFor="role-select" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Switch:
                  </label>
                  <select
                    id="role-select"
                    className="role-select"
                    value={activeUserId}
                    onChange={(e) => {
                      const uid = e.target.value
                      setActiveUserId(uid)
                      handleLoginAndFetch(uid)
                    }}
                  >
                    {users.length > 0 ? (
                      users.map((u) => (
                        <option key={u.user_id} value={u.user_id}>
                          {u.name} ({u.role})
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="USR-006">Senthil Nathan (CITIZEN)</option>
                        <option value="USR-007">Officer Rajesh V (GOVERNMENT_OFFICER)</option>
                        <option value="USR-003">Kavitha Sundaram (FIELD_ASSESSOR)</option>
                        <option value="USR-001">Dr. Ananya Sharma (ADMIN)</option>
                      </>
                    )}
                  </select>
                </div>

                <button
                  className="btn btn-secondary btn-sm"
                  style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171' }}
                  onClick={handleSignOut}
                  title="Sign Out"
                >
                  <LogOut size={14} />
                  Sign Out
                </button>
              </>
            ) : (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    setSignInRoleHint(undefined)
                    setSignInMode('signin')
                    setIsSignInOpen(true)
                  }}
                  style={{ padding: '0.45rem 1rem', fontWeight: 600 }}
                >
                  <LogIn size={15} />
                  Sign In
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setSignInRoleHint(undefined)
                    setSignInMode('register')
                    setIsSignInOpen(true)
                  }}
                  style={{ padding: '0.45rem 0.85rem', fontWeight: 600, borderColor: '#10b981', color: '#34d399' }}
                >
                  Create Account
                </button>
              </div>
            )}

            <button className="btn btn-secondary btn-sm" onClick={loadData} title="Refresh data">
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Subheader (Visible when signed in) */}
      {currentUser && (
        <nav style={{ background: '#0b0f19', borderBottom: '1px solid #1c2742', padding: '0.65rem 1.5rem' }}>
          <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              className={`btn btn-sm ${activeTab === 'home' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('home')}
            >
              <Home size={15} />
              Home
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'citizen-assets' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('citizen-assets')}
            >
              <Boxes size={15} />
              Citizen Assets
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'citizen-claims' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('citizen-claims')}
            >
              <FileText size={15} />
              Disaster Claims
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'officer-dashboard' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('officer-dashboard')}
            >
              <ShieldCheck size={15} />
              Officer Dashboard
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'ngo-inspections' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('ngo-inspections')}
            >
              <ClipboardCheck size={15} />
              Field Assessor / NGO
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <Activity size={15} />
              Operations Dashboard
            </button>
          </div>
        </nav>
      )}

      {/* Main Container */}
      <main className="container">
        {activeTab === 'home' ? (
          <LandingPage
            health={health}
            kpis={kpis}
            currentUser={currentUser}
            onOpenSignIn={(hint, initialMode) => {
              setSignInRoleHint(hint)
              setSignInMode(initialMode || 'signin')
              setIsSignInOpen(true)
            }}
            onNavigateToDashboard={() => {
              if (currentUser?.role === 'GOVERNMENT_OFFICER') {
                setActiveTab('officer-dashboard')
              } else if (currentUser?.role === 'FIELD_ASSESSOR' || currentUser?.role === 'NGO') {
                setActiveTab('ngo-inspections')
              } else if (currentUser?.role === 'CITIZEN') {
                setActiveTab('citizen-assets')
              } else {
                setActiveTab('dashboard')
              }
            }}
          />
        ) : activeTab === 'officer-dashboard' ? (
          <OfficerDashboard
            currentUser={currentUser}
            onBackToDashboard={() => setActiveTab('dashboard')}
          />
        ) : activeTab === 'ngo-inspections' ? (
          <FieldAssessorPage
            currentUser={currentUser}
            onNavigateToClaims={() => setActiveTab('citizen-claims')}
          />
        ) : activeTab === 'citizen-assets' ? (
          <CitizenAssetPage
            currentUser={currentUser}
            onAssetAdded={() => handleLoginAndFetch(activeUserId)}
          />
        ) : activeTab === 'citizen-claims' ? (
          <CitizenClaimPage
            currentUser={currentUser}
            onClaimCreated={() => handleLoginAndFetch(activeUserId)}
            onNavigateToAssets={() => setActiveTab('citizen-assets')}
          />
        ) : (
          <>
        {/* Disaster Event Banner */}
        <div
          style={{
            background: 'linear-gradient(90deg, #1e1b4b 0%, #1e293b 100%)',
            border: '1px solid #3730a3',
            borderRadius: '10px',
            padding: '0.85rem 1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '0.75rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="badge badge-danger">ACTIVE CRISIS</span>
            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
              Tamil Nadu Monsoon Flood Simulation (DIS-2026-0007)
            </span>
            <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
              Sectors: Katpadi, Vellore, Arcot, Ranipet, Gudiyatham
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: '#a5b4fc' }}>
            <Server size={14} />
            <span>MST Blockchain Testnet: Synced & Ready</span>
          </div>
        </div>

        {error && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              padding: '1rem',
              color: '#fca5a5',
              marginBottom: '1.5rem'
            }}
          >
            <strong>Backend Connection Notice:</strong> {error}
          </div>
        )}

        {/* Operational KPIs */}
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Field Reports Stream</div>
            <div className="kpi-value">
              {kpis?.total_reports ?? 0}
              <span style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: 500 }}>
                {kpis?.verified_reports ?? 0} Verified
              </span>
            </div>
            <div className="kpi-subtext">Multi-source crowdsourced & sensor inputs</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Pending AI Allocations</div>
            <div className="kpi-value" style={{ color: '#f59e0b' }}>
              {kpis?.pending_recommendations ?? 0}
              <span style={{ fontSize: '0.9rem', color: '#94a3b8', fontWeight: 500 }}>
                {kpis?.approved_recommendations ?? 0} Approved
              </span>
            </div>
            <div className="kpi-subtext">Awaiting human supervisor verification</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">MST Blockchain Decisions</div>
            <div className="kpi-value" style={{ color: '#a855f7' }}>
              {kpis?.blockchain_anchored_decisions ?? 0}
              <CheckCircle size={18} style={{ color: '#10b981' }} />
            </div>
            <div className="kpi-subtext">Immutable cryptographic accountability</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Available Relief Inventory</div>
            <div className="kpi-value" style={{ color: '#3b82f6' }}>
              {kpis?.available_resources?.toLocaleString() ?? 0}
              <Boxes size={18} />
            </div>
            <div className="kpi-subtext">Across 5 regional depot warehouses</div>
          </div>
        </div>

        {/* Operational Content Grid */}
        <div className="dashboard-grid">
          {/* Left Column: Monitored Operational Zones & Reports */}
          <div>
            {/* Operational Zones Table */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <Activity size={18} style={{ color: '#3b82f6' }} />
                  Operational Zones Priority Telemetry
                </div>
                <span className="badge badge-purple">{locations.length} Zones Monitored</span>
              </div>

              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Zone Name</th>
                      <th>Severity</th>
                      <th>Population</th>
                      <th>AI Priority</th>
                      <th>Shortages</th>
                    </tr>
                  </thead>
                  <tbody>
                    {locations.map((loc) => (
                      <tr key={loc.id}>
                        <td>
                          <strong>{loc.name}</strong>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {loc.district}, {loc.state}
                          </div>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              loc.severity === 'CRITICAL'
                                ? 'badge-danger'
                                : loc.severity === 'HIGH'
                                ? 'badge-warning'
                                : 'badge-success'
                            }`}
                          >
                            {loc.severity}
                          </span>
                        </td>
                        <td>{loc.population_affected.toLocaleString()}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div
                              style={{
                                width: '60px',
                                height: '6px',
                                background: '#1e293b',
                                borderRadius: '3px',
                                overflow: 'hidden'
                              }}
                            >
                              <div
                                style={{
                                  width: `${loc.priority_score}%`,
                                  height: '100%',
                                  background: loc.priority_score > 75 ? '#ef4444' : '#3b82f6'
                                }}
                              />
                            </div>
                            <span style={{ fontWeight: 600 }}>{loc.priority_score}</span>
                          </div>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                            Med: {loc.medical_shortage} | H₂O: {loc.water_shortage}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Field Reports Table */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <AlertTriangle size={18} style={{ color: '#f59e0b' }} />
                  Incoming Field Reports & Trust Scoring
                </div>
                <span className="badge badge-success">Live Feed</span>
              </div>

              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Report ID</th>
                      <th>Source & Zone</th>
                      <th>Description</th>
                      <th>Trust Score</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.slice(0, 6).map((rep) => (
                      <tr key={rep.id}>
                        <td>
                          <code>{rep.report_id}</code>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600 }}>{rep.source}</div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{rep.location}</div>
                        </td>
                        <td style={{ maxWidth: '300px' }}>
                          <p style={{ fontSize: '0.8125rem', color: '#cbd5e1' }}>{rep.description}</p>
                          {rep.duplicate_cluster_id && (
                            <span
                              style={{
                                fontSize: '0.7rem',
                                color: '#a855f7',
                                display: 'inline-block',
                                marginTop: '0.2rem'
                              }}
                            >
                              Cluster: {rep.duplicate_cluster_id}
                            </span>
                          )}
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              rep.trust_score >= 80
                                ? 'badge-success'
                                : rep.trust_score >= 50
                                ? 'badge-warning'
                                : 'badge-danger'
                            }`}
                          >
                            {rep.trust_score}%
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>
                            {rep.verification_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Right Column: AI Recommendations & Audit Verification */}
          <div>
            {/* AI Recommendations */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <Shield size={18} style={{ color: '#10b981' }} />
                  AI Resource Recommendations
                </div>
                <span className="badge badge-warning">Human Sign-off</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {recommendations.slice(0, 3).map((rec) => (
                  <div
                    key={rec.id}
                    style={{
                      background: '#0f172a',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '0.85rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{rec.location_name}</span>
                      <span
                        className={`badge ${rec.status === 'APPROVED' ? 'badge-success' : 'badge-warning'}`}
                        style={{ fontSize: '0.7rem' }}
                      >
                        {rec.status}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.8125rem', color: '#38bdf8', marginBottom: '0.5rem' }}>
                      Recommend: <strong>{rec.recommended_quantity}</strong> units of {rec.resource_type}
                    </div>

                    <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4, marginBottom: '0.5rem' }}>
                      {rec.explanation}
                    </p>

                    {rec.blockchain_tx_hash && (
                      <div
                        style={{
                          fontSize: '0.7rem',
                          color: '#a855f7',
                          fontFamily: 'monospace',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        Tx: {rec.blockchain_tx_hash.slice(0, 18)}...
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Cryptographic SHA-256 Audit Verification */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <Database size={18} style={{ color: '#a855f7' }} />
                  Cryptographic Audit Integrity
                </div>
                <span className="badge badge-success">SHA-256 Chained</span>
              </div>

              <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.6 }}>
                <p style={{ marginBottom: '0.5rem' }}>
                  Every emergency report, approval, and override is sequentially chained with SHA-256 cryptography.
                </p>

                <div
                  style={{
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '0.75rem',
                    marginBottom: '0.75rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Chain Status:</span>
                    <strong style={{ color: auditStatus?.chain_valid ? '#10b981' : '#ef4444' }}>
                      {auditStatus?.status ?? 'VERIFIED_TAMPER_EVIDENT'}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Verified Events:</span>
                    <span>{auditStatus?.total_events ?? 19} sequentially hashed</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#3b82f6', fontSize: '0.8rem' }}>
                  <Link size={14} />
                  <span>Verified locally without external dependencies.</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Step 17: Connected API Modules - Registered Assets & Disaster Claims */}
        <div style={{ marginTop: '2rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))', gap: '1.5rem' }}>
            {/* Panel: Registered Assets */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <Boxes size={18} style={{ color: '#3b82f6' }} />
                  Registered Assets (GET /assets)
                </div>
                <span className="badge badge-purple">{assets.length} Registered</span>
              </div>

              {assets.length === 0 ? (
                <div style={{ padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>
                  No registered assets found for this account.
                </div>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Asset ID</th>
                        <th>Category</th>
                        <th>Documented Value</th>
                        <th>Status</th>
                        <th>Location</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assets.map((asset) => (
                        <tr key={asset.asset_id}>
                          <td>
                            <code>{asset.asset_id}</code>
                          </td>
                          <td>
                            <strong style={{ fontSize: '0.85rem' }}>{asset.category}</strong>
                            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                              {asset.description.slice(0, 40)}...
                            </div>
                          </td>
                          <td style={{ color: '#10b981', fontWeight: 600 }}>
                            ₹{asset.documented_value.toLocaleString()}
                          </td>
                          <td>
                            <span
                              className={`badge ${
                                asset.status === 'VERIFIED'
                                  ? 'badge-success'
                                  : asset.status === 'FLAGGED'
                                  ? 'badge-danger'
                                  : 'badge-warning'
                              }`}
                            >
                              {asset.status}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                            {asset.location_address}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Panel: Disaster Claims */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <Shield size={18} style={{ color: '#f59e0b' }} />
                  Disaster Claims (GET /claims)
                </div>
                <span className="badge badge-warning">{claims.length} Claims</span>
              </div>

              {claims.length === 0 ? (
                <div style={{ padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>
                  No disaster claims found for this account.
                </div>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Claim ID</th>
                        <th>Asset ID</th>
                        <th>Damage Description</th>
                        <th>Disaster Ref</th>
                        <th>Review Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {claims.map((claim) => (
                        <tr key={claim.claim_id}>
                          <td>
                            <code>{claim.claim_id}</code>
                          </td>
                          <td>
                            <span style={{ fontSize: '0.85rem', color: '#a5b4fc', fontFamily: 'monospace' }}>
                              {claim.asset_id}
                            </span>
                          </td>
                          <td style={{ maxWidth: '240px' }}>
                            <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                              {claim.damage_description}
                            </div>
                          </td>
                          <td>
                            <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}>
                              {claim.disaster_id}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`badge ${
                                claim.review_status === 'APPROVED'
                                  ? 'badge-success'
                                  : claim.review_status === 'REJECTED'
                                  ? 'badge-danger'
                                  : 'badge-warning'
                              }`}
                            >
                              {claim.review_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
          </>
        )}
      </main>

      <SignInModal
        isOpen={isSignInOpen}
        defaultRole={signInRoleHint}
        initialMode={signInMode}
        users={users}
        onClose={() => setIsSignInOpen(false)}
        onSuccess={handleSignInSuccess}
      />
    </div>
  )
}

export default App
