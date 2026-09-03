import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const STATUSES = ['PENDING', 'COMPLETED', 'REVIEW', 'CANCELLED']

function statusClass(s) {
  return (s || '').toLowerCase()
}

export default function Inspections() {
  const [inspections, setInspections] = useState([])
  const [error, setError] = useState('')

  async function load() {
    try {
      const d = await api.inspections()
      setInspections(d || [])
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function setStatus(id, status) {
    setError('')
    try {
      await api.updateInspection(id, { status })
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Inspections</h1>
          <p className="muted">Field inspections attached to compliance analyses.</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <section className="panel">
        {inspections.length === 0 ? (
          <div className="empty">
            <p className="muted">No inspections yet. Open an analysis to register a field inspection.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Analysis</th><th>Location</th><th>Observations</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {inspections.map((i) => (
                <tr key={i.id}>
                  <td><Link to={`/analyses/${i.analysis_id}`} className="mono link">{i.analysis_id.slice(0, 8)}</Link></td>
                  <td>{i.location || '—'}</td>
                  <td className="muted small">{i.observations || i.notes || '—'}</td>
                  <td>
                    <select
                      value={i.status}
                      onChange={(e) => setStatus(i.id, e.target.value)}
                      className="status-select"
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </td>
                  <td><span className={`badge ${statusClass(i.status)}`}>{i.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
