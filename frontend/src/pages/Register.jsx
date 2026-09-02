import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'CONSUMER' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await register(form)
      navigate('/login')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <h1>Create Account</h1>
        {error && <div className="alert error">{error}</div>}
        <label>Full name
          <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        </label>
        <label>Email
          <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} type="email" required />
        </label>
        <label>Password
          <input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} type="password" required minLength={6} />
        </label>
        <label>Role
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="CONSUMER">Consumer</option>
            <option value="RETAILER">Retailer</option>
            <option value="MANUFACTURER">Manufacturer</option>
          </select>
        </label>
        <button className="primary" disabled={busy}>{busy ? 'Creating…' : 'Register'}</button>
        <div className="switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </form>
    </div>
  )
}
