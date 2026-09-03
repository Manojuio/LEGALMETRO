import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

function statusClass(s) {
  return (s || '').toLowerCase()
}

export default function AdminAnalyses() {
  const [analyses, setAnalyses] = useState([])
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(null)
  const [lmoFilter, setLmoFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [query, setQuery] = useState('')

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

  const lmoNames = useMemo(() => {
    const names = new Set()
    for (const a of analyses) if (a.owner?.name) names.add(a.owner.name)
    return Array.from(names).sort()
  }, [analyses])

  const filtered = useMemo(() => {
    return analyses.filter((a) => {
      if (lmoFilter !== 'all' && a.owner?.name !== lmoFilter) return false
      if (statusFilter !== 'all' && (a.overall_status || a.status) !== statusFilter) return false
      if (query) {
        const q = query.toLowerCase()
        return a.category?.toLowerCase().includes(q) || (a.owner?.name || '').toLowerCase().includes(q)
      }
      return true
    })
  }, [analyses, lmoFilter, statusFilter, query])

  const counts = useMemo(() => {
    const c = { PASS: 0, REVIEW: 0, FAIL: 0 }
    for (const a of filtered) {
      const s = a.overall_status || a.status
      if (s in c) c[s] += 1
    }
    return c
  }, [filtered])

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>LMO Analyses</h1>
          <p className="muted">
            Review the compliance analyses performed by Legal Metrology Officers and download each report as a PDF.
            Use the filters to inspect a specific officer, status, or product.
          </p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      {analyses.length === 0 ? (
        <section className="panel">
          <div className="empty">
            <p className="muted">No analyses have been performed by LMOs yet. Reports will appear here once LMOs complete their compliance scans.</p>
          </div>
        </section>
      ) : (
        <>
          <div className="summary-chips">
            <span className="chip">Total: {filtered.length}</span>
            <span className="chip green">Passed: {counts.PASS}</span>
            <span className="chip amber">Needs Review: {counts.REVIEW}</span>
            <span className="chip red">Failed: {counts.FAIL}</span>
          </div>

          <div className="toolbar">
            <select value={lmoFilter} onChange={(e) => setLmoFilter(e.target.value)} className="select-inline">
              <option value="all">All officers…</option>
              {lmoNames.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="select-inline">
              <option value="all">All statuses…</option>
              <option value="PASS">Passed</option>
              <option value="REVIEW">Needs Review</option>
              <option value="FAIL">Failed</option>
            </select>
            <input
              className="search-input"
              placeholder="Search by product or officer…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <section className="panel">
            {filtered.length === 0 ? (
              <p className="muted">No analyses match the current filters.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr><th>ID</th><th>Officer</th><th>Category</th><th>Status</th><th>Created</th><th></th></tr>
                </thead>
                <tbody>
                  {filtered.map((a) => (
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
            )}
          </section>
        </>
      )}
    </div>
  )
}
