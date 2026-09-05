import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'
import { roleConfig } from '../config/roles'

function StatCard({ icon, label, value, tone }) {
  return (
    <div className={`stat-card ${tone || ''}`}>
      <span className="stat-icon">{icon}</span>
      <div className="stat-value">{value ?? '—'}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

function statusClass(s) {
  return (s || '').toLowerCase()
}

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [analyses, setAnalyses] = useState([])
  const [inspections, setInspections] = useState([])
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const d = await api.dashboard()
        setData(d)
        const a = await api.analyses()
        setAnalyses(a || [])
        let insp = []
        if (user.role === 'LMO') {
          insp = await api.inspections()
        }
        setInspections(insp || [])
      } catch (err) {
        setError(err.message)
      }
    }
    load()
  }, [user.role])

  async function downloadReport(id) {
    setDownloading(id)
    setError('')
    try {
      await api.downloadReport(id)
    } catch (err) {
      setError(err.message)
    } finally {
      setDownloading(null)
    }
  }

  const role = user.role
  const cfg = roleConfig(role)
  const stats = data?.stats || {}
  const isAdmin = role === 'ADMIN'

  // Derived compliance figures for the admin cockpit.
  const passed = analyses.filter((a) => a.overall_status === 'PASS').length
  const review = analyses.filter((a) => a.overall_status === 'REVIEW').length
  const failed = analyses.filter((a) => a.overall_status === 'FAIL').length

  const filteredAnalyses = analyses.filter((a) => {
    if (!query) return true
    const q = query.toLowerCase()
    return (
      a.category?.toLowerCase().includes(q) ||
      a.owner?.name?.toLowerCase().includes(q) ||
      (a.overall_status || '').toLowerCase().includes(q)
    )
  })

  return (
    <div className="dash">
      <div className="dash-hero">
        <div className="dash-hero-avatar">{cfg.icon}</div>
        <div>
          <h1>Welcome, {user?.full_name?.split(' ')[0]}</h1>
          <p>{cfg.tagline}</p>
        </div>
        {!isAdmin && <Link to="/analyze" className="primary hero-cta">+ New Analysis</Link>}
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="stats-grid">
        {role === 'ADMIN' && <>
          <StatCard icon="📋" label="Total Analyses" value={analyses.length} tone="tone-blue" />
          <StatCard icon="⚖️" label="LMOs" value={stats.lmos} tone="tone-violet" />
          <StatCard icon="✅" label="Passed" value={passed} tone="tone-green" />
          <StatCard icon="⏳" label="Needs Review" value={review} tone="tone-amber" />
          <StatCard icon="⛔" label="Failed" value={failed} tone="tone-rose" />
        </>}
        {role === 'LMO' && <>
          <StatCard icon="🔎" label="My Inspections" value={stats.my_inspections} tone="tone-violet" />
          <StatCard icon="⏳" label="Pending" value={stats.pending_inspections} tone="tone-amber" />
          <StatCard icon="📋" label="All Analyses" value={stats.total_analyses} tone="tone-blue" />
          <StatCard icon="✅" label="Passed" value={stats.passed} tone="tone-green" />
          <StatCard icon="⛔" label="Failed" value={stats.failed} tone="tone-rose" />
          <StatCard icon="🔍" label="Needs Review" value={stats.review} tone="tone-amber" />
        </>}
        {role === 'MANUFACTURER' && <>
          <StatCard icon="📦" label="My Products" value={stats.my_products} tone="tone-amber" />
          <StatCard icon="📋" label="My Analyses" value={stats.my_analyses} tone="tone-blue" />
        </>}
        {(role === 'RETAILER' || role === 'CONSUMER') && <>
          <StatCard icon="📋" label="My Analyses" value={stats.my_analyses} tone="tone-green" />
        </>}
      </div>

      {role === 'ADMIN' && (
        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">LMO Compliance Analyses</h3>
            <span className="panel-count">{analyses.length} analysis{analyses.length === 1 ? '' : 's'}</span>
          </div>
          {analyses.length === 0 ? (
            <div className="empty">
              <p className="muted">No compliance analyses have been performed by LMOs yet. Reports will appear here as LMOs complete scans.</p>
              <Link to="/admin-analyses" className="secondary">Open LMO Analyses</Link>
            </div>
          ) : (
            <>
              <div className="toolbar">
                <input
                  className="search-input"
                  placeholder="Search by product, LMO or status…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <Link to="/admin-analyses" className="link">Filter & manage →</Link>
              </div>
              <table className="table">
                <thead>
                  <tr><th>ID</th><th>Officer</th><th>Category</th><th>Status</th><th>Created</th><th></th></tr>
                </thead>
                <tbody>
                  {filteredAnalyses.map((a) => (
                    <tr key={a.id}>
                      <td className="mono">{a.id.slice(0, 8)}</td>
                      <td>{a.owner?.name || '—'}</td>
                      <td>{a.category || '—'}</td>
                      <td>
                        <span className={`badge ${statusClass(a.overall_status || a.status)}`}>
                          {a.overall_status || a.status}
                        </span>
                      </td>
                      <td className="muted small">{a.created_at ? new Date(a.created_at).toLocaleDateString() : '—'}</td>
                      <td className="row-actions">
                        <Link to={`/analyses/${a.id}`} className="link">Open →</Link>
                        <button className="secondary small" onClick={() => downloadReport(a.id)} disabled={downloading === a.id || !a.overall_status}>
                          {downloading === a.id ? 'Downloading…' : 'Download PDF'}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {filteredAnalyses.length === 0 && (
                    <tr><td colSpan="6" className="muted">No analyses match your search.</td></tr>
                  )}
                </tbody>
              </table>
            </>
          )}
        </section>
      )}

      {role === 'LMO' && inspections.length > 0 && (
        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">Recent Inspections</h3>
            <Link to="/inspections" className="link">View full history →</Link>
          </div>
          <table className="table">
            <thead><tr><th>Analysis</th><th>Result</th><th>Status</th></tr></thead>
            <tbody>
              {inspections.slice(0, 5).map((i) => (
                <tr key={i.id}>
                  <td><Link to={`/analyses/${i.analysis_id}`} className="mono link">{i.analysis_id?.slice(0, 8)}</Link></td>
                  <td>
                    <span className={`badge ${statusClass(i.overall_status || i.status)}`}>
                      {i.overall_status || '—'}
                    </span>
                  </td>
                  <td><span className={`badge ${statusClass(i.status)}`}>{i.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {!isAdmin && (
        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">{role === 'MANUFACTURER' ? 'My Analyses' : 'Analyses'}</h3>
            <Link to="/analyze" className="primary small">+ New Analysis</Link>
          </div>
          {analyses.length === 0 ? (
            <div className="empty">
              <p className="muted">No analyses yet. Start a new one to scan a product.</p>
              <Link to="/analyze" className="primary">Start your first analysis</Link>
            </div>
          ) : (
            <table className="table">
              <thead><tr><th>ID</th><th>Category</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {analyses.map((a) => (
                  <tr key={a.id}>
                    <td className="mono">{a.id.slice(0, 8)}</td>
                    <td>{a.category || '—'}</td>
                    <td>
                      <span className={`badge ${statusClass(a.overall_status || a.status)}`}>
                        {a.overall_status || a.status}
                      </span>
                    </td>
                    <td><Link to={`/analyses/${a.id}`} className="link">Open →</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  )
}
