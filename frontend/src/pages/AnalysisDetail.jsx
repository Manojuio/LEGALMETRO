import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'
import RunLoader from '../components/RunLoader'

const GRADE_DESC = {
  'A+': 'Fully Compliant',
  'A': 'Compliant',
  'B': 'Needs Improvement',
  'C': 'Significant Issues',
  'D': 'Non-Compliant',
  'F': 'Fail',
}

const STATUS_LABEL = {
  PASS: 'Passed',
  FAIL: 'Failed',
  REVIEW: 'Needs Review',
  NOT_APPLICABLE: 'N/A',
}

function formatFieldName(k) {
  return k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function ScoreRing({ score, grade, size = 160 }) {
  const radius = (size - 16) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 50 ? '#16a34a' : score >= 30 ? '#f59e0b' : '#dc2626'

  return (
    <div className="score-ring-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#eef2f7" strokeWidth="10"
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.22, 1, 0.36, 1)' }}
        />
      </svg>
      <div className="score-ring-center">
        <span className="score-ring-num" style={{ color }}>{Math.round(score)}</span>
        <span className="score-ring-grade">{grade}</span>
      </div>
    </div>
  )
}

function ProgressBar({ label, passed, count, percentage, color }) {
  const [width, setWidth] = React.useState(0)
  React.useEffect(() => {
    const t = setTimeout(() => setWidth(percentage || 0), 100)
    return () => clearTimeout(t)
  }, [percentage])

  return (
    <div className="progress-group">
      <div className="progress-header">
        <span className="progress-label">{label}</span>
        <span className="progress-stat">{passed}/{count} passed</span>
      </div>
      <div className="progress-track">
        <div
          className="progress-fill"
          style={{ width: `${width}%`, background: color }}
        />
      </div>
      <div className="progress-pct" style={{ color }}>{percentage.toFixed(0)}%</div>
    </div>
  )
}

export default function AnalysisDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const [report, setReport] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [inspectionForms, setInspectionForms] = useState(false)
  const [inspForm, setInspForm] = useState({ location: '', observations: '' })
  const isAdmin = user.role === 'ADMIN'
  const canRun = !isAdmin
  const isLmo = user.role === 'LMO'

  async function downloadReport() {
    setError('')
    try {
      await api.downloadReport(id)
    } catch (err) {
      setError('Failed to generate PDF: ' + err.message)
    }
  }

  async function run() {
    setRunning(true)
    setError('')
    try {
      const r = await api.runAnalysis(id)
      setReport(r)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  async function createInspection(e) {
    e.preventDefault()
    setError('')
    try {
      await api.createInspection({ analysis_id: id, ...inspForm })
      setInspectionForms(false)
      setInspForm({ location: '', observations: '' })
    } catch (err) {
      setError(err.message)
    }
  }

  const score = report?.compliance_score

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Analysis <span className="mono">{id.slice(0, 8)}</span></h1>
          <p className="muted">Compliance scan result for this product package.</p>
        </div>
        <Link to="/analyses" className="link">&larr; All analyses</Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      <section className="panel">
        {!report && (
          <div className="empty">
            <p className="muted">
              {isAdmin
                ? 'This analysis was performed by an LMO. The generated report is shown below.'
                : 'Run the full pipeline to extract product data and check compliance.'}
            </p>
          </div>
        )}
        <div className="row">
          {canRun && (
            <button className="primary" onClick={run} disabled={running || !!report}>
              {report ? 'Analysis complete' : 'Run Analysis'}
            </button>
          )}
          {(report || isAdmin) && (
            <button className="secondary" onClick={downloadReport}>
              Download PDF Report
            </button>
          )}
        </div>
      </section>

      {running && <RunLoader />}

      {report && (
        <>
          {/* Status Banner */}
          <div className={`result-banner ${report.overall_status.toLowerCase()}`}>
            <div className="result-banner-text">
              <div className="result-label">Overall Compliance</div>
              <div className="result-value">{STATUS_LABEL[report.overall_status] || report.overall_status}</div>
            </div>
            {score && (
              <div className="result-banner-score">
                {Math.round(score.total_score)}<span className="result-banner-of">/100</span>
              </div>
            )}
          </div>

          {/* Score Section */}
          {score && (
            <div className="score-panel">
              <div className="score-panel-left">
                <ScoreRing score={score.total_score} grade={score.grade} />
                <div className="score-meta">
                  <div className="score-meta-label">Compliance Score</div>
                  <div className="score-meta-desc">{GRADE_DESC[score.grade]}</div>
                  <div className="score-meta-threshold">Pass threshold: {score.pass_threshold}</div>
                </div>
              </div>
              <div className="score-panel-right">
                <ProgressBar
                  label="Essential Rules"
                  passed={score.essential.passed}
                  count={score.essential.count}
                  percentage={score.essential.percentage}
                  color="#16a34a"
                />
                <ProgressBar
                  label="Supporting Rules"
                  passed={score.supporting.passed}
                  count={score.supporting.count}
                  percentage={score.supporting.percentage}
                  color="#6366f1"
                />
              </div>
            </div>
          )}

          {/* Product Information */}
          {report.product && (
            <section className="panel">
              <h3 className="panel-title">Product Information</h3>
              <div className="info-grid">
                {[
                  ['Name', report.product.name],
                  ['Category', report.product.category],
                  ['Subcategory', report.product.subcategory],
                  ['Confidence', report.product.classification_confidence
                    ? `${(report.product.classification_confidence * 100).toFixed(0)}%`
                    : '—'],
                ].map(([label, value]) => (
                  <div className="info-row" key={label}>
                    <span className="info-label">{label}</span>
                    <span className="info-value">{value || '—'}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Extracted Fields */}
          {report.extracted_fields && Object.keys(report.extracted_fields).length > 0 && (
            <section className="panel">
              <h3 className="panel-title">Extracted Fields</h3>
              <div className="info-grid">
                {Object.entries(report.extracted_fields).map(([field, data]) => (
                  <div className="info-row" key={field}>
                    <span className="info-label">{formatFieldName(field)}</span>
                    <span className="info-value">
                      {data?.value || '—'}
                      {data?.confidence != null && (
                        <span className="info-confidence">
                          {(data.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Rule Results */}
          <section className="panel">
            <h3 className="panel-title">
              Rule Results
              <span className="panel-count">{report.rules?.length || 0} rules checked</span>
            </h3>
            {(!report.rules || report.rules.length === 0) ? (
              <p className="muted">No rules were checked.</p>
            ) : (
              <div className="rule-table-wrap">
                <table className="rule-table">
                  <thead>
                    <tr>
                      <th className="col-num">#</th>
                      <th className="col-title">Rule</th>
                      <th className="col-category">Category</th>
                      <th className="col-priority">Priority</th>
                      <th className="col-status">Status</th>
                      <th className="col-reason">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.rules.map((r, i) => (
                      <tr key={i}>
                        <td className="col-num mono">{r.rule || r.rule_number || i + 1}</td>
                        <td className="col-title">
                          <span className="rule-name">{r.title}</span>
                        </td>
                        <td className="col-category">
                          <span className="cat-badge">{r.category}</span>
                        </td>
                        <td className="col-priority">
                          <span className={`pri-badge ${(r.severity || '').toLowerCase()}`}>
                            {r.severity === 'HIGH' ? 'Essential' : 'Supporting'}
                          </span>
                        </td>
                        <td className="col-status">
                          <span className={`status-badge ${(r.status || '').toLowerCase()}`}>
                            {STATUS_LABEL[r.status] || r.status}
                          </span>
                        </td>
                        <td className="col-reason muted">{r.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Field Inspection (LMO only) */}
          {isLmo && (
            <section className="panel">
              <h3 className="panel-title">Field Inspection</h3>
              {!inspectionForms ? (
                <button className="secondary" onClick={() => setInspectionForms(true)}>
                  Register field inspection
                </button>
              ) : (
                <form className="form-grid" onSubmit={createInspection}>
                  <label className="full">Location
                    <input value={inspForm.location} onChange={(e) => setInspForm({ ...inspForm, location: e.target.value })} placeholder="Inspection site" />
                  </label>
                  <label className="full">Observations
                    <textarea value={inspForm.observations} onChange={(e) => setInspForm({ ...inspForm, observations: e.target.value })} placeholder="Field observations..." />
                  </label>
                  <div className="row">
                    <button className="primary" type="submit">Save inspection</button>
                    <button type="button" className="secondary" onClick={() => setInspectionForms(false)}>Cancel</button>
                  </div>
                </form>
              )}
            </section>
          )}
        </>
      )}
    </div>
  )
}
