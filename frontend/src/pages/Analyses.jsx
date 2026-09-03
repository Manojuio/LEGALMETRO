import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

function statusClass(s) {
  return (s || '').toLowerCase()
}

export default function Analyses() {
  const { user } = useAuth()
  const [analyses, setAnalyses] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .analyses()
      .then((a) => setAnalyses(a || []))
      .catch((e) => setError(e.message))
  }, [])

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>All Analyses</h1>
          <p className="muted">Every compliance analysis you can access.</p>
        </div>
        {user.role !== 'ADMIN' && <Link to="/analyze" className="primary">+ New Analysis</Link>}
      </div>

      {error && <div className="alert error">{error}</div>}

      <section className="panel">
        {analyses.length === 0 ? (
          <div className="empty">
            <p className="muted">No analyses found.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>ID</th><th>Category</th><th>Subcategory</th><th>Status</th><th>Created</th><th></th></tr>
            </thead>
            <tbody>
              {analyses.map((a) => (
                <tr key={a.id}>
                  <td className="mono">{a.id.slice(0, 8)}</td>
                  <td>{a.category || '—'}</td>
                  <td>{a.subcategory || '—'}</td>
                  <td>
                    <span className={`badge ${statusClass(a.overall_status || a.status)}`}>
                      {a.overall_status || a.status}
                    </span>
                  </td>
                  <td className="muted small">{a.created_at ? new Date(a.created_at).toLocaleDateString() : '—'}</td>
                  <td><Link to={`/analyses/${a.id}`} className="link">Open →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
