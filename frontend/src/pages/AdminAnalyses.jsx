import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

function statusClass(s) {
  return (s || '').toLowerCase()
}

export default function AdminAnalyses() {
  const [analyses, setAnalyses] = useState([])
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(null)

  useEffect(() => {
    api
      .analyses()
      .then((a) => setAnalyses(a || []))
      .catch((e) => setError(e.message))
  }, [])

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

  // Group LMO analyses by LMO.
  const byLmo = {}
  const ordLmos = []
  for (const a of analyses) {
    const lmoName = a.owner?.name || 'Unknown LMO'
    if (!byLmo[lmoName]) {
      byLmo[lmoName] = []
      ordLmos.push(lmoName)
    }
    byLmo[lmoName].push(a)
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>LMO Analyses</h1>
          <p className="muted">Compliance analyses performed by Legal Metrology Officers under your administration.</p>
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
          {ordLmos.map((lmo) => (
            <section className="panel" key={lmo}>
              <h3 className="panel-title">⚖️ {lmo}</h3>
              <table className="table">
                <thead>
                  <tr><th>ID</th><th>Category</th><th>Status</th><th>Created</th><th></th></tr>
                </thead>
                <tbody>
                  {byLmo[lmo].map((a) => (
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
                      <td className="row-actions">
                        <Link to={`/analyses/${a.id}`} className="link">Open →</Link>
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
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
