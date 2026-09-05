import React, { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'PASS', label: 'Pass' },
  { value: 'FAIL', label: 'Fail' },
  { value: 'REVIEW', label: 'Review' },
]

function statusClass(s) {
  return (s || '').toLowerCase()
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function InspectionHistory() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [downloading, setDownloading] = useState(null)

  const load = useCallback(async (statusFilter) => {
    setLoading(true)
    setError('')
    try {
      const data = await api.inspectionHistory(statusFilter || undefined)
      setItems(data || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(filter)
  }, [filter, load])

  async function handleDownload(analysisId) {
    setDownloading(analysisId)
    setError('')
    try {
      await api.downloadReport(analysisId)
    } catch (e) {
      setError('Failed to download PDF: ' + e.message)
    } finally {
      setDownloading(null)
    }
  }

  const total = items.length
  const passed = items.filter((i) => i.overall_status === 'PASS').length
  const failed = items.filter((i) => i.overall_status === 'FAIL').length
  const review = items.filter((i) => i.overall_status === 'REVIEW').length

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Inspection History</h1>
          <p className="muted">Review and manage previously completed product inspections.</p>
        </div>
        <Link to="/analyze" className="primary small">+ New Inspection</Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      {/* Summary chips */}
      <div className="summary-chips">
        <span className="chip">{total} inspection{total === 1 ? '' : 's'}</span>
        {passed > 0 && <span className="chip green">{passed} passed</span>}
        {failed > 0 && <span className="chip red">{failed} failed</span>}
        {review > 0 && <span className="chip amber">{review} review</span>}
      </div>

      {/* Filter bar */}
      <div className="toolbar">
        <div className="filter-group">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`filter-btn ${filter === opt.value ? 'active' : ''}`}
              onClick={() => setFilter(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <section className="panel">
        {loading ? (
          <div className="history-loading">
            <div className="loader-spinner" style={{ width: 48, height: 48, margin: '0 auto 12px' }}>
              <div className="orbit orbit-a" />
              <div className="orbit orbit-b" />
              <div className="loader-core">🔎</div>
            </div>
            <p className="muted">Loading inspection history...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">📋</div>
            <h3>No inspections found</h3>
            <p className="muted">
              {filter
                ? `No ${filter.toLowerCase()} inspections found.`
                : 'No inspections have been performed yet. Start a new analysis to create one.'}
            </p>
            {!filter && (
              <Link to="/analyze" className="primary">Start your first analysis</Link>
            )}
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table history-table">
              <thead>
                <tr>
                  <th>Inspection</th>
                  <th>Product</th>
                  <th>Category</th>
                  <th>Inspector</th>
                  <th>Date</th>
                  <th>Result</th>
                  <th>Score</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td className="mono">{item.id.slice(0, 8)}</td>
                    <td className="history-product">{item.product_name || '—'}</td>
                    <td>
                      <span className="cat-badge">{item.product_category || '—'}</span>
                    </td>
                    <td>{item.inspector_name || '—'}</td>
                    <td className="muted small">{formatDate(item.created_at)}</td>
                    <td>
                      <span className={`badge ${statusClass(item.overall_status)}`}>
                        {item.overall_status || '—'}
                      </span>
                    </td>
                    <td className="history-score">
                      {item.compliance_score != null ? (
                        <span className={`score-pill ${item.compliance_score >= 75 ? 'high' : item.compliance_score >= 50 ? 'mid' : 'low'}`}>
                          {Math.round(item.compliance_score)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="row-actions">
                      <Link to={`/analyses/${item.analysis_id}`} className="link small-link">
                        View Report
                      </Link>
                      {item.report_available && (
                        <button
                          className="secondary small"
                          onClick={() => handleDownload(item.analysis_id)}
                          disabled={downloading === item.analysis_id}
                        >
                          {downloading === item.analysis_id ? 'Downloading...' : 'Download PDF'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
