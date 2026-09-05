import React, { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { roleConfig } from '../config/roles'
import { api } from '../api'

const REGISTERABLE_ROLES = [
  { role: 'CONSUMER', color: '#16a34a' },
  { role: 'RETAILER', color: '#0ea5e9' },
  { role: 'MANUFACTURER', color: '#f59e0b' },
  { role: 'LMO', color: '#8b5cf6' },
]

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [roleField, setRoleField] = useState('CONSUMER')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await register({ ...form, role: roleField })
      navigate('/login', { state: { registered: true } })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-brand">
        <div className="brand-mark large">LM</div>
        <h1>Create your account</h1>
        <p>
          Choose the stakeholder role that fits you. Each role gets its own
          tailored workspace.
        </p>
      </div>

      <div className="auth-form-wrap">
        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Register</h2>
          <p className="auth-sub">Select your role to personalise your workspace</p>
          {error && <div className="alert error">{error}</div>}

          <div className="role-picker">
            {REGISTERABLE_ROLES.map((r) => {
              const cfg = roleConfig(r.role)
              const active = roleField === r.role
              return (
                <button
                  type="button"
                  key={r.role}
                  className={`role-option ${active ? 'active' : ''}`}
                  style={active ? { '--rc': r.color } : null}
                  onClick={() => setRoleField(r.role)}
                >
                  <span className="role-option-icon">{cfg.icon}</span>
                  <span className="role-option-name">{cfg.short}</span>
                </button>
              )
            })}
            <p className="role-hint">{roleConfig(roleField).tagline}</p>
          </div>

          <label>Full name
            <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Your full name" required />
          </label>
          <label>Email
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} type="email" placeholder="you@example.com" required />
          </label>
          <label>Password
            <input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} type="password" placeholder="At least 6 characters" required minLength={6} />
          </label>
          <button className="primary block" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
          <div className="switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </div>
        </form>
      </div>
    </div>
  )
}
