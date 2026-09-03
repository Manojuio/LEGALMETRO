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
  const [lmoAnalyses, setLmoAnalyses] = useState([])
  const [selectedLmo, setSelectedLmo] = useState(null)
  const [downloading, setDownloading] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const d = await api.dashboard()
        setData(d)
        if (user.role !== 'ADMIN') {
          const a = await api.analyses()
          setAnalyses(a || [])
        }
        if (user.role === 'ADMIN') {
          // Track LMO efforts for a quick transparency counter.
          const lmoAnas = await api.analyses()
          setLmoAnalyses(lmoAnas || [])
        }
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
          <StatCard icon="⚖️" label="LMOs" value={stats.lmos} tone="tone-violet" />
          <StatCard icon="📋" label="LMO Analyses" value={lmoAnalyses.length} tone="tone-blue" />
        </>}
        {role === 'LMO' && <>
          <StatCard icon="🔎" label="My Inspections" value={stats.my_inspections} tone="tone-violet" />
          <StatCard icon="⏳" label="Pending" value={stats.pending_inspections} tone="tone-amber" />
          <StatCard icon="📋" label="All Analyses" value={stats.total_analyses} tone="tone-blue" />
        </>}
        {role === 'MANUFACTURER' && <>
          <StatCard icon="📦" label="My Products" value={stats.my_products} tone="tone-amber" />
          <StatCard icon="📋" label="My Analyses" value={stats.my_analyses} tone="tone-blue" />
        </>}
        {(role === 'RETAILER' || role === 'CONSUMER') && <>
          <StatCard icon="📋" label="My Analyses" value={stats.my_analyses} tone="tone-green" />
        </>}
      </div>

      {role === 'ADMIN' && data?.lmos && (
        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">Legal Metrology Officers</h3>
            <span className="panel-count">{data.lmos.length} LMOs</span>
          </div>
          {data.lmos.length === 0 ? (
            <p className="muted">No LMOs registered yet.</p>
          ) : (
            <div className="lmo-reports-wrap">
              <div className="lmo-list">
                <table className="table">
                  <thead>
                    <tr><th>Officer</th><th>Reports</th></tr>
                  </thead>
                  <tbody>
                    {data.lmos.map((lmo) => {
                      const count = lmoAnalyses.filter((a) => a.owner?.user_id === lmo.id).length
                      return (
                        <tr
                          key={lmo.id}
                          className={selectedLmo?.id === lmo.id ? 'active' : ''}
                          onClick={() => setSelectedLmo(lmo)}
                        >
                          <td>
                            <span className="role-avatar small">⚖️</span>
                            <span className="lmo-name">{lmo.name}</span>
                          </td>
                          <td className="muted small">{count}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              <div className="lmo-reports">
                {!selectedLmo ? (
                  <p className="muted">Select an LMO above to view and download their reports.</p>
                ) : (
                  <>
                    <div className="lmo-reports-head">
                      <strong>{selectedLmo.name}</strong>
                      <span className="muted small">{selectedLmo.email}</span>
                    </div>
                    {(() => {
                      const reports = lmoAnalyses.filter((a) => a.owner?.user_id === selectedLmo.id)
                      return reports.length === 0 ? (
                        <p className="muted">This LMO has not performed any analyses yet.</p>
                      ) : (
                        <table className="table">
                          <thead>
                            <tr><th>ID</th><th>Category</th><th>Status</th><th></th></tr>
                          </thead>
                          <tbody>
                            {reports.map((a) => (
                              <tr key={a.id}>
                                <td className="mono">{a.id.slice(0, 8)}</td>
                                <td>{a.category || '—'}</td>
                                <td>
                                  <span className={`badge ${statusClass(a.overall_status || a.status)}`}>
                                    {a.overall_status || a.status}
                                  </span>
                                </td>
                                <td>
                                  <button
                                    className="secondary small"
                                    onClick={() => downloadReport(a.id)}
                                    disabled={downloading === a.id || !a.overall_status}
                                  >
                                    {downloading === a.id ? 'Downloading…' : 'Download PDF'}
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )
                    })()}
                  </>
                )}
              </div>
            </div>
          )}
        </section>
      )}

      {role === 'ADMIN' && (
        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">LMO Compliance Work</h3>
            <Link to="/admin-analyses" className="primary small">View all →</Link>
          </div>
          <p className="muted">
            Review every compliance analysis performed by Legal Metrology
            Officers ({lmoAnalyses.length} total) and download their reports.
          </p>
          <div className="row">
            <Link to="/admin-analyses" className="secondary">Open LMO Analyses</Link>
          </div>
        </section>
      )}

      {role === 'LMO' && inspections.length > 0 && (
        <section className="panel">
          <div className="panel-head">
            <h3 className="panel-title">My Inspections</h3>
            <Link to="/inspections" className="link">View all →</Link>
          </div>
          <table className="table">
            <thead><tr><th>Analysis</th><th>Location</th><th>Status</th></tr></thead>
            <tbody>
              {inspections.slice(0, 5).map((i) => (
                <tr key={i.id}>
                  <td className="mono">{i.analysis_id?.slice(0, 8)}</td>
                  <td>{i.location || '—'}</td>
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
