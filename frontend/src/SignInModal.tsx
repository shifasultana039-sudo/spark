import React, { useState, useEffect } from 'react'
import {
  X,
  Lock,
  Boxes,
  ShieldCheck,
  ClipboardCheck,
  Users,
  LogIn,
  UserPlus,
  AlertCircle,
  Mail,
  User,
  Building
} from 'lucide-react'
import { UserRole } from './types'
import { login, register, getCurrentUser } from './api'

interface SignInModalProps {
  isOpen: boolean
  defaultRole?: string
  initialMode?: 'signin' | 'register'
  users: UserRole[]
  onClose: () => void
  onSuccess: (user: UserRole) => void
}

interface RoleProfile {
  identifier: string
  name: string
  role: string
  roleLabel: string
  description: string
  icon: React.ReactNode
  color: string
}

export const SignInModal: React.FC<SignInModalProps> = ({
  isOpen,
  defaultRole,
  initialMode = 'signin',
  users,
  onClose,
  onSuccess
}) => {
  const roleProfiles: RoleProfile[] = [
    {
      identifier: 'senthil.n@citizen.tn.gov.in',
      name: 'Senthil Nathan',
      role: 'CITIZEN',
      roleLabel: 'Citizen & Claimant',
      description: 'Katpadi Resident • Pre-disaster asset records & compensation claims',
      icon: <Boxes size={18} />,
      color: '#3b82f6'
    },
    {
      identifier: 'rajesh.revenue@vellore.tn.gov.in',
      name: 'Officer Rajesh V',
      role: 'GOVERNMENT_OFFICER',
      roleLabel: 'Government Officer',
      description: 'Revenue Administration • Evidence review, field inspection & fund approval',
      icon: <ShieldCheck size={18} />,
      color: '#10b981'
    },
    {
      identifier: 'kavitha.field@reliefvolunteers.in',
      name: 'Kavitha Sundaram',
      role: 'FIELD_ASSESSOR',
      roleLabel: 'Field Assessor / NGO',
      description: 'Emergency Corps • On-site damage survey & physical ground verification',
      icon: <ClipboardCheck size={18} />,
      color: '#f59e0b'
    },
    {
      identifier: 'ananya.sharma@reliefchain.org',
      name: 'Dr. Ananya Sharma',
      role: 'ADMIN',
      roleLabel: 'Operations Admin',
      description: 'State Disaster Management • System analytics, KPIs & crisis operations',
      icon: <Users size={18} />,
      color: '#8b5cf6'
    }
  ]

  const initialProfile = roleProfiles.find((a) => a.role === defaultRole) || roleProfiles[0]

  const [mode, setMode] = useState<'signin' | 'register'>(initialMode)
  // Sign In State
  const [usernameOrEmail, setUsernameOrEmail] = useState<string>(initialProfile.identifier)
  const [password, setPassword] = useState<string>('demo123')
  const [selectedRole, setSelectedRole] = useState<string>(initialProfile.role)

  // Registration State
  const [regName, setRegName] = useState<string>('')
  const [regEmail, setRegEmail] = useState<string>('')
  const [regRole, setRegRole] = useState<string>(defaultRole || 'CITIZEN')
  const [regOrg, setRegOrg] = useState<string>('')
  const [regHousehold, setRegHousehold] = useState<string>('HH-1001')
  const [regPassword, setRegPassword] = useState<string>('')

  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setMode(initialMode)
  }, [initialMode, isOpen])

  useEffect(() => {
    if (defaultRole) {
      const match = roleProfiles.find((p) => p.role === defaultRole)
      if (match) {
        setSelectedRole(match.role)
        setUsernameOrEmail(match.identifier)
        setRegRole(match.role)
      }
    }
  }, [defaultRole, isOpen])

  if (!isOpen) return null

  const handleSelectRole = (profile: RoleProfile) => {
    setSelectedRole(profile.role)
    setUsernameOrEmail(profile.identifier)
    setError(null)
  }

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!usernameOrEmail.trim()) {
      setError('Please enter your email or username.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await login(usernameOrEmail.trim())
      const user = await getCurrentUser()
      onSuccess(user)
    } catch (err: any) {
      console.error('Sign In error:', err)
      setError(err.message || 'Authentication failed. Please check credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!regName.trim()) {
      setError('Please enter your full name.')
      return
    }
    if (!regEmail.trim()) {
      setError('Please enter your email address.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await register({
        name: regName.trim(),
        email: regEmail.trim(),
        role: regRole,
        organization: regOrg.trim() || (regRole === 'CITIZEN' ? `Katpadi Resident (${regHousehold})` : 'Disaster Relief Department'),
        household_ref: regRole === 'CITIZEN' ? (regHousehold.trim() || 'HH-1001') : undefined,
        password: regPassword || 'demo123'
      })
      const user = await getCurrentUser()
      onSuccess(user)
    } catch (err: any) {
      console.error('Registration error:', err)
      setError(err.message || 'Registration failed. Please check your information.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 8, 16, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          background: '#131b2e',
          border: '1px solid #233152',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '560px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid #1c2742',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(11, 15, 25, 0.5)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                background: mode === 'signin' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                color: mode === 'signin' ? '#60a5fa' : '#34d399',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              {mode === 'signin' ? <Lock size={18} /> : <UserPlus size={18} />}
            </div>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                {mode === 'signin' ? 'Sign In to ReliefChain AI' : 'Create a New Account'}
              </h3>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0 }}>
                {mode === 'signin'
                  ? 'Access your registered portal or pick a role profile'
                  : 'Register as a citizen, relief officer, or field assessor'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '0.35rem',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Mode Switcher Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #1c2742',
            background: '#0b0f19'
          }}
        >
          <button
            type="button"
            onClick={() => {
              setMode('signin')
              setError(null)
            }}
            style={{
              flex: 1,
              padding: '0.75rem',
              fontSize: '0.9rem',
              fontWeight: 600,
              background: mode === 'signin' ? '#131b2e' : 'transparent',
              color: mode === 'signin' ? '#60a5fa' : '#64748b',
              border: 'none',
              borderBottom: mode === 'signin' ? '2px solid #3b82f6' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
          >
            <LogIn size={15} />
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('register')
              setError(null)
            }}
            style={{
              flex: 1,
              padding: '0.75rem',
              fontSize: '0.9rem',
              fontWeight: 600,
              background: mode === 'register' ? '#131b2e' : 'transparent',
              color: mode === 'register' ? '#34d399' : '#64748b',
              border: 'none',
              borderBottom: mode === 'register' ? '2px solid #10b981' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
          >
            <UserPlus size={15} />
            Create Account (Register)
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{ padding: '1rem 1.5rem 0' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                padding: '0.75rem 1rem',
                color: '#f87171',
                fontSize: '0.85rem'
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* TAB 1: SIGN IN */}
        {mode === 'signin' && (
          <form onSubmit={handleSignIn} style={{ padding: '1.5rem' }}>
            {/* Quick Role Selector */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>
                Quick Select Role Profile:
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.65rem' }}>
                {roleProfiles.map((p) => {
                  const isSelected = selectedRole === p.role && usernameOrEmail === p.identifier
                  return (
                    <button
                      type="button"
                      key={p.role}
                      onClick={() => handleSelectRole(p)}
                      style={{
                        background: isSelected ? 'rgba(30, 41, 59, 0.8)' : '#0b0f19',
                        border: `1.5px solid ${isSelected ? p.color : '#1c2742'}`,
                        borderRadius: '8px',
                        padding: '0.65rem 0.75rem',
                        textAlign: 'left',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.5rem',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div
                        style={{
                          color: p.color,
                          background: `${p.color}22`,
                          padding: '0.25rem',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0
                        }}
                      >
                        {p.icon}
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {p.name}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: p.color, fontWeight: 500 }}>
                          {p.roleLabel}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Credentials Inputs */}
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                Email, Username, or Full Name
              </label>
              <input
                type="text"
                className="form-control"
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                placeholder="e.g. senthil.n@citizen.tn.gov.in or your name"
                required
                style={{
                  width: '100%',
                  background: '#0b0f19',
                  border: '1px solid #233152',
                  borderRadius: '8px',
                  padding: '0.65rem 0.85rem',
                  fontSize: '0.9rem',
                  color: '#f8fafc'
                }}
              />
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                Password
              </label>
              <input
                type="password"
                className="form-control"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                style={{
                  width: '100%',
                  background: '#0b0f19',
                  border: '1px solid #233152',
                  borderRadius: '8px',
                  padding: '0.65rem 0.85rem',
                  fontSize: '0.9rem',
                  color: '#f8fafc'
                }}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.85rem',
                fontSize: '0.95rem',
                fontWeight: 600,
                justifyContent: 'center',
                marginBottom: '1rem'
              }}
            >
              {loading ? (
                'Signing In...'
              ) : (
                <>
                  <LogIn size={16} />
                  Sign In & Enter Dashboard
                </>
              )}
            </button>

            {/* Toggle to Register */}
            <div style={{ textAlign: 'center', fontSize: '0.85rem', color: '#94a3b8' }}>
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('register')
                  setError(null)
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#38bdf8',
                  cursor: 'pointer',
                  fontWeight: 600,
                  textDecoration: 'underline'
                }}
              >
                Create an Account
              </button>
            </div>
          </form>
        )}

        {/* TAB 2: CREATE ACCOUNT (REGISTER) */}
        {mode === 'register' && (
          <form onSubmit={handleRegister} style={{ padding: '1.5rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="e.g. Shifa"
                  required
                  style={{
                    width: '100%',
                    background: '#0b0f19',
                    border: '1px solid #233152',
                    borderRadius: '8px',
                    padding: '0.65rem 0.85rem',
                    fontSize: '0.9rem',
                    color: '#f8fafc'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                  Email Address *
                </label>
                <input
                  type="email"
                  className="form-control"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="e.g. shifa@example.com"
                  required
                  style={{
                    width: '100%',
                    background: '#0b0f19',
                    border: '1px solid #233152',
                    borderRadius: '8px',
                    padding: '0.65rem 0.85rem',
                    fontSize: '0.9rem',
                    color: '#f8fafc'
                  }}
                />
              </div>
            </div>

            {/* Role Choice */}
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                Account Role:
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                {[
                  { role: 'CITIZEN', label: 'Citizen', icon: <Boxes size={14} />, desc: 'Property owner' },
                  { role: 'GOVERNMENT_OFFICER', label: 'Officer', icon: <ShieldCheck size={14} />, desc: 'Revenue official' },
                  { role: 'FIELD_ASSESSOR', label: 'Assessor / NGO', icon: <ClipboardCheck size={14} />, desc: 'Ground inspector' }
                ].map((r) => {
                  const isSelected = regRole === r.role
                  return (
                    <button
                      type="button"
                      key={r.role}
                      onClick={() => setRegRole(r.role)}
                      style={{
                        padding: '0.55rem',
                        borderRadius: '8px',
                        border: `1.5px solid ${isSelected ? '#10b981' : '#1c2742'}`,
                        background: isSelected ? 'rgba(16, 185, 129, 0.15)' : '#0b0f19',
                        color: isSelected ? '#34d399' : '#94a3b8',
                        cursor: 'pointer',
                        textAlign: 'center',
                        fontSize: '0.8rem',
                        fontWeight: 600
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}>
                        {r.icon} {r.label}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.15rem' }}>
                        {r.desc}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Role details */}
            {regRole === 'CITIZEN' ? (
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                  Household Reference (or Katpadi HH-1001)
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={regHousehold}
                  onChange={(e) => setRegHousehold(e.target.value)}
                  placeholder="e.g. HH-1001"
                  style={{
                    width: '100%',
                    background: '#0b0f19',
                    border: '1px solid #233152',
                    borderRadius: '8px',
                    padding: '0.65rem 0.85rem',
                    fontSize: '0.9rem',
                    color: '#f8fafc'
                  }}
                />
              </div>
            ) : (
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                  Department or Organization
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={regOrg}
                  onChange={(e) => setRegOrg(e.target.value)}
                  placeholder="e.g. Vellore Revenue District Office"
                  style={{
                    width: '100%',
                    background: '#0b0f19',
                    border: '1px solid #233152',
                    borderRadius: '8px',
                    padding: '0.65rem 0.85rem',
                    fontSize: '0.9rem',
                    color: '#f8fafc'
                  }}
                />
              </div>
            )}

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
                Password
              </label>
              <input
                type="password"
                className="form-control"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="Choose a password (e.g. demo123)"
                style={{
                  width: '100%',
                  background: '#0b0f19',
                  border: '1px solid #233152',
                  borderRadius: '8px',
                  padding: '0.65rem 0.85rem',
                  fontSize: '0.9rem',
                  color: '#f8fafc'
                }}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.85rem',
                fontSize: '0.95rem',
                fontWeight: 600,
                justifyContent: 'center',
                marginBottom: '1rem',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                borderColor: '#10b981'
              }}
            >
              {loading ? (
                'Creating Account...'
              ) : (
                <>
                  <UserPlus size={16} />
                  Create Account & Enter Dashboard
                </>
              )}
            </button>

            {/* Toggle back to Sign In */}
            <div style={{ textAlign: 'center', fontSize: '0.85rem', color: '#94a3b8' }}>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('signin')
                  setError(null)
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#38bdf8',
                  cursor: 'pointer',
                  fontWeight: 600,
                  textDecoration: 'underline'
                }}
              >
                Sign In
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
