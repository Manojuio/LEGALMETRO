import React from 'react'
import { useLocation, Link } from 'react-router-dom'
import { api } from '../api'

const STATUS_LABEL = {
  PASS: 'Passed',
  FAIL: 'Failed',
  REVIEW: 'Needs Review',
  NOT_APPLICABLE: 'N/A',
}

function statusClass(s) {
  return (s || '').toLowerCase()
}

// Fetches the protected product image with the JWT and shows the real photo
// with a score overlay. Falls back to a placeholder if it can't load.
function ProductImageCard({ imgUrl, status, score }) {
  const [bg, setBg] = React.useState('')
  const [failed, setFailed] = React.useState(false)

  React.useEffect(() => {
    let active = true
    const token = localStorage.getItem('lm_token')
    fetch(imgUrl, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((res) => {
        if (!res.ok) throw new Error('image')
        return res.blob()
      })
      .then((blob) => {
        if (!active) return
        const url = URL.createObjectURL(blob)
        setBg(`url(${url})`)
      })
      .catch(() => active && setFailed(true))
    return () => { active = false }
  }, [imgUrl])

  return (
    <div className={`batch-card-img score-${statusClass(status)} ${failed ? 'no-img' : ''}`}
      style={bg ? { backgroundImage: bg } : {}}>
      <span className="batch-card-img-fallback">📦</span>
      <div className="batch-card-overlay">
        {score ? (
          <div className="batch-card-score-badge">
            <span className="bcs-num">{Math.round(score.total_score)}</span>
            <span className="bcs-grade">{score.grade}</span>
          </div>
        ) : (
          <span className="bcs-na">N/A</span>
        )}
      </div>
    </div>
  )
}
export default function BatchResults() {
  const location = useLocation()
  const [error, setError] = React.useState('')

  // Prefer in-memory navigation state; fall back to sessionStorage so the
  // summary still shows after a refresh or a direct link.
  let results = location.state?.results || []
  const [cached, setCached] = React.useState(null)
  const [triedCache, setTriedCache] = React.useState(false)

  React.useEffect(() => {
    try {
      const raw = sessionStorage.getItem('lm_batch_results')
      if (raw) {
        setCached(JSON.parse(raw))
      }
    } catch (_) {}
    setTriedCache(true)
  }, [])

  if (results.length === 0 && cached) results = cached
  if (results.length === 0 && !triedCache) return <div className="boot">Loading…</div>

  if (results.length === 0) {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>Batch results</h1>
            <p className="muted">No recent batch analysis found.</p>
          </div>
        </div>
      </div>
    )
  }

  const passed = results.filter((r) => r.report?.overall_status === 'PASS').length
  const failed = results.filter((r) => r.report?.overall_status === 'FAIL').length
  const review = results.filter((r) => r.report?.overall_status === 'REVIEW').length

  async function downloadReport(analysisId) {
    setError('')
    try {
      await api.downloadReport(analysisId)
    } catch (err) {
      setError('Failed to generate PDF: ' + err.message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Batch results</h1>
          <p className="muted">Analysis for {results.length} product{results.length === 1 ? '' : 's'}</p>
        </div>
        <Link to="/analyze" className="link">Start a new analysis →</Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="summary-chips">
        <span className="chip green">{passed} Passed</span>
        <span className="chip amber">{review} Needs review</span>
        <span className="chip red">{failed} Failed</span>
      </div>

      <div className="batch-grid">
        {results.map((r, i) => {
          const report = r.report || {}
          const score = report.compliance_score
          const id = r.analysis_id
          const imgUrl = r.image_url || `/api/v1/analyses/${id}/image`
          return (
            <div className="batch-card" key={id}>
              <div className="batch-card-head">
                <div>
                  <div className="batch-card-index">Product {i + 1}</div>
                  <div className="batch-card-id mono">{id.slice(0, 8)}</div>
                </div>
                <span className={`status-badge ${statusClass(report.overall_status)}`}>
                  {STATUS_LABEL[report.overall_status] || report.overall_status}
                </span>
              </div>

              {/* Real product photo with overlaid score */}
              <div className="batch-card-media">
                <ProductImageCard
                  imgUrl={imgUrl}
                  status={report.overall_status}
                  score={score}
                />
                <div className="batch-card-meta">
                  <div className="batch-card-name">{report.product?.name || 'Unknown product'}</div>
                  <div className="batch-card-cat muted small">
                    {report.product?.category || ''}
                    {report.product?.subcategory ? ` / ${report.product.subcategory}` : ''}
                  </div>
                  {score && (
                    <div className="batch-card-grade">
                      {score.essential.passed}/{score.essential.count} essential passed · {score.grade}
                    </div>
                  )}
                </div>
              </div>

              {report.extracted_fields && Object.keys(report.extracted_fields).length > 0 && (
                <div className="batch-fields">
                  {Object.entries(report.extracted_fields).slice(0, 6).map(([field, data]) => (
                    <div className="batch-field" key={field}>
                      <span className="batch-field-label">{field.replace(/_/g, ' ')}</span>
                      <span className="batch-field-value">{data?.value || '—'}</span>
                    </div>
                  ))}
                </div>
              )}

              <div className="batch-card-actions">
                <Link to={`/analyses/${id}`} state={{ report }} className="secondary small">Open analysis</Link>
                <button type="button" className="secondary small" onClick={() => downloadReport(id)}>
                  PDF report
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
