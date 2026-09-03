import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ROLES } from '../config/roles'

const DEMO_ACCOUNTS = [
  { role: 'ADMIN', email: 'admin@example.com', password: 'admin123' },
  { role: 'LMO', email: 'lmo@example.com', password: 'lmo123' },
  { role: 'MANUFACTURER', email: 'manufacturer@example.com', password: 'mfr123' },
  { role: 'RETAILER', email: 'retailer@example.com', password: 'retail123' },
  { role: 'CONSUMER', email: 'consumer@example.com', password: 'consumer123' },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function doLogin(em = email, pw = password) {
    setError('')
    setBusy(true)
    try {
      await login(em, pw)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    await doLogin()
  }

  return (
    <div className="auth-shell">
      <div className="auth-brand">
        <div className="brand-mark large">LM</div>
        <h1>LegalMetro</h1>
        <p>Packaged Commodities Compliance Scanner for the Legal Metrology (Packaged Commodities) Rules, 2011.</p>

        <div className="demo-panel">
          <div className="demo-title">Quick demo access</div>
          {DEMO_ACCOUNTS.map((acc) => (
            <button key={acc.role} className="demo-btn" onClick={() => doLogin(acc.email, acc.password)}>
              <span className="demo-icon">{ROLES[acc.role].icon}</span>
              <span className="demo-text">
                <strong>{ROLES[acc.role].label}</strong>
                <small>{acc.email}</small>
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="auth-form-wrap">
        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Welcome back</h2>
          <p className="auth-sub">Sign in to your stakeholder workspace</p>
          {error && <div className="alert error">{error}</div>}
          <label>Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="you@example.com" required />
          </label>
          <label>Password
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="••••••••" required />
          </label>
          <button className="primary block" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          <div className="switch">
            New here? <Link to="/register">Create an account</Link>
          </div>
        </form>
      </div>
    </div>
  )
}
