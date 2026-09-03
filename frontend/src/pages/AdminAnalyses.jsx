import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

function statusClass(s) {
  return (s || '').toLowerCase()
}

export default function AdminAnalyses() {
  const [analyses, setAnalyses] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .analyses()
      .then((a) => setAnalyses(a || []))
      .catch((e) => setError(e.message))
  }, [])

  // Group LMO analyses by zone (then by LMO).
  const byZone = {}
  const ordZones = []
  for (const a of analyses) {
    const zone = a.owner?.zone_name || 'Unassigned zone'
    if (!byZone[zone]) {
      byZone[zone] = { zone, lmos: {} }
      ordZones.push(zone)
    }
    const lmoName = a.owner?.name || 'Unknown LMO'
    if (!byZone[zone].lmos[lmoName]) byZone[zone].lmos[lmoName] = []
    byZone[zone].lmos[lmoName].push(a)
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>LMO Analyses</h1>
          <p className="muted">Compliance analyses performed by Legal Metrology Officers, grouped by zone.</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      {analyses.length === 0 ? (
        <section className="panel">
          <div className="empty">
            <p className="muted">No analyses have been performed by LMOs yet.</p>
          </div>
        </section>
      ) : (
        <div className="zone-ana-grid">
          {ordZones.map((zone) => {
            const grp = byZone[zone]
            const lmoNames = Object.keys(grp.lmos)
            return (
              <section className="panel" key={zone}>
                <h3 className="panel-title">📍 {zone}</h3>
                {lmoNames.length === 0 && <p className="muted">No LMO analyses in this zone.</p>}
                {lmoNames.map((lmo) => (
                  <div key={lmo} className="lmo-ana-block">
                    <div className="lmo-ana-head">
                      <span className="role-avatar small">⚖️</span>
                      <strong>{lmo}</strong>
                      <span className="chip">{grp.lmos[lmo].length} analysis</span>
                    </div>
                    <table className="table">
                      <thead>
                        <tr><th>ID</th><th>Category</th><th>Status</th><th>Created</th><th></th></tr>
                      </thead>
                      <tbody>
                        {grp.lmos[lmo].map((a) => (
                          <tr key={a.id}>
                            <td className="mono">{a.id.slice(0, 8)}</td>
                            <td>{a.category || '—'}</td>
                            <td>
                              <span className={`badge ${statusClass(a.overall_status || a.status)}`}>
                                {a.overall_status || a.status}
                              </span>
                            </td>
                            <td className="muted small">
                              {a.created_at ? new Date(a.created_at).toLocaleDateString() : '—'}
                            </td>
                            <td><Link to={`/analyses/${a.id}`} className="link">Open →</Link></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
