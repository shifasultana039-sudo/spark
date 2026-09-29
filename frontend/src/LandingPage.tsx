import React from 'react'
import {
  Shield,
  ShieldCheck,
  Boxes,
  ClipboardCheck,
  Activity,
  ArrowRight,
  CheckCircle2,
  Lock,
  UserCheck
} from 'lucide-react'
import { SystemHealth, KpiData, UserRole } from './types'

interface LandingPageProps {
  health: SystemHealth | null
  kpis: KpiData | null
  currentUser: UserRole | null
  onOpenSignIn: (defaultRole?: string, mode?: 'signin' | 'register') => void
  onNavigateToDashboard: () => void
}

export const LandingPage: React.FC<LandingPageProps> = ({
  health,
  kpis,
  currentUser,
  onOpenSignIn,
  onNavigateToDashboard
}) => {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1rem 0 3rem' }}>
      {/* Hero Section */}
      <section
        style={{
          textAlign: 'center',
          padding: '3.5rem 1.5rem 3rem',
          background: 'linear-gradient(180deg, rgba(30, 41, 59, 0.5) 0%, rgba(15, 23, 42, 0.7) 100%)',
          borderRadius: '16px',
          border: '1px solid #1e293b',
          marginBottom: '2.5rem',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            borderRadius: '9999px',
            padding: '0.35rem 1rem',
            fontSize: '0.85rem',
            color: '#60a5fa',
            fontWeight: 500,
            marginBottom: '1.25rem'
          }}
        >
          <Shield size={15} />
          Tamper-Evident Disaster Relief & Asset Verification
        </div>

        <h1
          style={{
            fontSize: '2.75rem',
            fontWeight: 800,
            color: '#f8fafc',
            lineHeight: 1.2,
            marginBottom: '1rem',
            letterSpacing: '-0.025em'
          }}
        >
          ReliefChain AI
        </h1>

        <p
          style={{
            fontSize: '1.15rem',
            color: '#94a3b8',
            maxWidth: '750px',
            margin: '0 auto 2.25rem',
            lineHeight: 1.6
          }}
        >
          Fast, verifiable disaster compensation powered by pre-disaster baseline records,
          computer vision damage assessment, and transparent human-in-the-loop government review.
        </p>

        {/* Hero CTAs */}
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          {currentUser ? (
            <button
              className="btn btn-primary"
              style={{ padding: '0.85rem 1.75rem', fontSize: '1rem', fontWeight: 600 }}
              onClick={onNavigateToDashboard}
            >
              <Activity size={18} />
              Open Your Dashboard ({currentUser.name})
            </button>
          ) : (
            <>
              <button
                className="btn btn-primary"
                style={{ padding: '0.85rem 1.75rem', fontSize: '1rem', fontWeight: 600 }}
                onClick={() => onOpenSignIn()}
              >
                <Lock size={18} />
                Sign In
              </button>
              <button
                className="btn btn-secondary"
                style={{
                  padding: '0.85rem 1.75rem',
                  fontSize: '1rem',
                  fontWeight: 600,
                  borderColor: '#10b981',
                  color: '#34d399'
                }}
                onClick={() => onOpenSignIn(undefined, 'register')}
              >
                Create Account (Sign Up)
              </button>
            </>
          )}
        </div>
      </section>

      {/* Stakeholder Portals (3 Simple Cards) */}
      <section style={{ marginBottom: '3rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.5rem' }}>
            Choose Your Portal
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.95rem' }}>
            Sign in to access your designated role portal and workflow tools.
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.5rem'
          }}
        >
          {/* Card 1: Citizen */}
          <div
            style={{
              background: '#131b2e',
              border: '1px solid #1c2742',
              borderRadius: '12px',
              padding: '1.75rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}
          >
            <div>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '10px',
                  background: 'rgba(59, 130, 246, 0.15)',
                  color: '#60a5fa',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1rem'
                }}
              >
                <Boxes size={24} />
              </div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
                Citizen & Claimant
              </h3>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1.25rem' }}>
                Register pre-disaster property & baseline documents, secure cryptographic ownership certificates, and submit claims during disasters.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1.5rem 0', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Document & Photo Uploads
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Safe Asset Certificate Issuance
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Computer Vision Damage Estimation
                </li>
              </ul>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button
                className="btn btn-primary"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => onOpenSignIn('CITIZEN')}
              >
                {currentUser?.role === 'CITIZEN' ? 'Enter Citizen Dashboard' : 'Sign In as Citizen'} <ArrowRight size={16} />
              </button>
              {!currentUser && (
                <button
                  type="button"
                  onClick={() => onOpenSignIn('CITIZEN', 'register')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#60a5fa',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    textAlign: 'center',
                    textDecoration: 'underline'
                  }}
                >
                  + Create New Citizen Account
                </button>
              )}
            </div>
          </div>

          {/* Card 2: Government Officer */}
          <div
            style={{
              background: '#131b2e',
              border: '1px solid #1c2742',
              borderRadius: '12px',
              padding: '1.75rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}
          >
            <div>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '10px',
                  background: 'rgba(16, 185, 129, 0.15)',
                  color: '#34d399',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1rem'
                }}
              >
                <ShieldCheck size={24} />
              </div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
                Government Officer
              </h3>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1.25rem' }}>
                Review disaster claims with baseline vs post-disaster comparisons, inspect AI anomaly indicators, delegate field surveys, and authorize relief payouts.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1.5rem 0', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Pre vs Post Disaster Comparison
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Non-Accusatory Anomaly Warnings
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Claim Approval & Compensation
                </li>
              </ul>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button
                className="btn btn-secondary"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => onOpenSignIn('GOVERNMENT_OFFICER')}
              >
                {currentUser?.role === 'GOVERNMENT_OFFICER' ? 'Enter Officer Dashboard' : 'Sign In as Officer'} <ArrowRight size={16} />
              </button>
              {!currentUser && (
                <button
                  type="button"
                  onClick={() => onOpenSignIn('GOVERNMENT_OFFICER', 'register')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#34d399',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    textAlign: 'center',
                    textDecoration: 'underline'
                  }}
                >
                  + Create New Officer Account
                </button>
              )}
            </div>
          </div>

          {/* Card 3: Field Assessor / NGO */}
          <div
            style={{
              background: '#131b2e',
              border: '1px solid #1c2742',
              borderRadius: '12px',
              padding: '1.75rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}
          >
            <div>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '10px',
                  background: 'rgba(245, 158, 11, 0.15)',
                  color: '#fbbf24',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1rem'
                }}
              >
                <ClipboardCheck size={24} />
              </div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
                Field Assessor / NGO
              </h3>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1.25rem' }}>
                Perform on-site physical disaster inspections, record damage findings, upload geo-tagged survey photos, and submit official assessment reports.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1.5rem 0', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Assigned Field Inspection Queue
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Ground Survey Photo Evidence
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <CheckCircle2 size={15} style={{ color: '#10b981' }} /> Official Survey Report Submission
                </li>
              </ul>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button
                className="btn btn-secondary"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => onOpenSignIn('FIELD_ASSESSOR')}
              >
                {currentUser?.role === 'FIELD_ASSESSOR' || currentUser?.role === 'NGO' ? 'Enter Assessor Portal' : 'Sign In as Assessor'} <ArrowRight size={16} />
              </button>
              {!currentUser && (
                <button
                  type="button"
                  onClick={() => onOpenSignIn('FIELD_ASSESSOR', 'register')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#fbbf24',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    textAlign: 'center',
                    textDecoration: 'underline'
                  }}
                >
                  + Create New Assessor Account
                </button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* How It Works (4 Simple Steps) */}
      <section
        style={{
          background: '#0d1322',
          border: '1px solid #1c2742',
          borderRadius: '12px',
          padding: '2rem 1.5rem',
          marginBottom: '3rem'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.5rem' }}>
            How ReliefChain AI Works
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            A transparent 4-stage pipeline from pre-disaster baseline to approved relief.
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '1.5rem'
          }}
        >
          <div style={{ padding: '1.25rem', background: '#131b2e', borderRadius: '8px', border: '1px solid #233152' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#3b82f6', marginBottom: '0.5rem' }}>
              STEP 1
            </div>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
              Register Baseline Asset
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Citizen documents house, livestock, or agricultural assets with title deed, tax invoice, and baseline photos.
            </p>
          </div>

          <div style={{ padding: '1.25rem', background: '#131b2e', borderRadius: '8px', border: '1px solid #233152' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#10b981', marginBottom: '0.5rem' }}>
              STEP 2
            </div>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
              Verify & Issue Certificate
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Verification engine checks multi-factor weights (≥80%) and issues a cryptographic Safe Asset Certificate.
            </p>
          </div>

          <div style={{ padding: '1.25rem', background: '#131b2e', borderRadius: '8px', border: '1px solid #233152' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#8b5cf6', marginBottom: '0.5rem' }}>
              STEP 3
            </div>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
              Claim & AI Assessment
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Post-disaster evidence is uploaded. AI Vision analyzes damage % and calculates an indicative loss estimate.
            </p>
          </div>

          <div style={{ padding: '1.25rem', background: '#131b2e', borderRadius: '8px', border: '1px solid #233152' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f59e0b', marginBottom: '0.5rem' }}>
              STEP 4
            </div>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
              Inspection & Approval
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Officer evaluates dossier, NGO submits on-site findings, and officer authorizes the final relief grant.
            </p>
          </div>
        </div>
      </section>

      {/* System Status Banner */}
      <section
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          padding: '1.25rem 1.75rem',
          background: '#131b2e',
          borderRadius: '10px',
          border: '1px solid #1c2742'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className={`pulse-dot ${health?.status === 'HEALTHY' ? '' : 'danger'}`} />
          <div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
              System Status: {health ? health.status : 'Connecting...'}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
              Database: {health?.database || 'Connected'} • Storage: {health?.storage || 'Accessible'} • Audit Trail: Active (SHA-256)
            </div>
          </div>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={() => {
            if (currentUser) {
              onNavigateToDashboard()
            } else {
              onOpenSignIn()
            }
          }}
        >
          <Activity size={15} />
          {currentUser ? 'Open Operations Dashboard' : 'Sign In to Access Dashboard'}
        </button>
      </section>
    </div>
  )
}
