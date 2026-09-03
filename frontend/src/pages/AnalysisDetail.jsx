import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'
import RunLoader from '../components/RunLoader'
import { generatePDF } from '../utils/generatePDF'

function statusClass(s) {
  return (s || '').toLowerCase()
}

const GRADE_DESC = {
  'A+': 'Excellent - Fully Compliant',
  'A': 'Satisfactory - Compliant',
  'B': 'Needs Improvement',
  'C': 'Poor - Significant Issues',
  'D': 'Critical - Non-Compliant',
  'F': 'Fail - Non-Compliant',
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
    if (!report) return
    try {
      const doc = generatePDF(report, score)
      doc.save(`compliance-report-${id.slice(0, 8)}.pdf`)
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
          <p className="muted">OCR, rule checks and compliance report for this product.</p>
        </div>
        <Link to="/analyses" className="link">← All analyses</Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      <section className="panel">
        {!report && (
          <div className="empty">
            <p className="muted">
              {isAdmin
                ? 'This analysis was performed by an LMO. The generated report is shown below.'
                : 'This analysis has not been run yet. Run the full pipeline to extract the product and check compliance.'}
            </p>
          </div>
        )}
        <div className="row">
          {canRun && (
            <button className="primary" onClick={run} disabled={running || !!report}>
              {report ? '✓ Analysis complete' : '⚙ Run Analysis'}
            </button>
          )}
          {(report || isAdmin) && (
            <button className="secondary" onClick={downloadReport}>
              ⬇ Download PDF Report
            </button>
          )}
        </div>
      </section>

      {running && <RunLoader />}

      {report && (
        <>
          <div className={`result-banner ${statusClass(report.overall_status)}`}>
            <span className="result-icon">
              {report.overall_status === 'PASS' ? '✅' : report.overall_status === 'FAIL' ? '⛔' : '⚠️'}
            </span>
            <div>
              <div className="result-label">Overall compliance</div>
              <div className="result-value">{report.overall_status}</div>
            </div>
          </div>

          {score && (
            <div className="score-strip">
              <div className="score-block">
                <span className={`score-num ${score.total_score >= 75 ? 'pass' : score.total_score >= 60 ? 'warn' : 'fail'}`}>
                  {Math.round(score.total_score)}
                </span>
                <span className="score-label">Compliance Score</span>
                <span className={`score-grade ${score.total_score >= 75 ? 'grade-pass' : score.total_score >= 60 ? 'grade-warn' : 'grade-fail'}`}>
                  {score.grade} — {GRADE_DESC[score.grade] || 'Unknown'}
                </span>
              </div>
              <div className="score-bars">
                <MetricBar label="Key Fields" value={score.high_priority} color={score.high_priority.passed >= 3 ? '#16a34a' : score.high_priority.passed >= 1 ? '#f59e0b' : '#dc2626'} />
                <MetricBar label="Supporting" value={score.medium_priority} color="#6366f1" />
                <MetricBar label="Extra" value={score.low_priority} color="#8b5cf6" />
              </div>
            </div>
          )}

          {report.summary && (
            <section className="panel">
              <h3 className="panel-title">Summary</h3>
              <div className="summary-pills">
                {Object.entries(report.summary).map(([k, v]) => (
                  <div className="summary-pill" key={k}>
                    <span className="summary-num">{v}</span>
                    <span className="summary-key">{k.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {report.product && (
            <section className="panel">
              <h3 className="panel-title">Extracted Product</h3>
              <table className="table">
                <tbody>
                  {Object.entries(report.product).map(([k, v]) => (
                    <tr key={k}>
                      <td className="label-cell"><strong>{k.replace(/_/g, ' ')}</strong></td>
                      <td>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section className="panel">
            <h3 className="panel-title">Rule Results ({report.rules?.length || 0})</h3>
            {report.rules?.length === 0 && <p className="muted">No rules were checked.</p>}
            <table className="table">
              <thead><tr><th>Rule</th><th>Status</th><th>Reason</th></tr></thead>
              <tbody>
                {report.rules.map((r, i) => (
                  <tr key={i}>
                    <td className="mono">{r.rule_id || r.rule || r.title || i}</td>
                    <td><span className={`badge ${statusClass(r.status)}`}>{r.status}</span></td>
                    <td>{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}

      {isLmo && (
        <section className="panel">
          <h3 className="panel-title">Field Inspection</h3>
          {!inspectionForms ? (
            <button className="secondary" onClick={() => setInspectionForms(true)}>
              + Register field inspection
            </button>
          ) : (
            <form className="form-grid" onSubmit={createInspection}>
              <label className="full">Location
                <input value={inspForm.location} onChange={(e) => setInspForm({ ...inspForm, location: e.target.value })} placeholder="Inspection site" />
              </label>
              <label className="full">Observations
                <textarea value={inspForm.observations} onChange={(e) => setInspForm({ ...inspForm, observations: e.target.value })} placeholder="Field observations…" />
              </label>
              <div className="row">
                <button className="primary" type="submit">Save inspection</button>
                <button type="button" className="secondary" onClick={() => setInspectionForms(false)}>Cancel</button>
              </div>
            </form>
          )}
        </section>
      )}
    </div>
  )
}

function MetricBar({ label, value, color }) {
  const v = value || {}
  const pct = v.max ? Math.round((v.score / v.max) * 100) : 0
  const [width, setWidth] = React.useState(0)

  React.useEffect(() => {
    const t = setTimeout(() => setWidth(pct), 100)
    return () => clearTimeout(t)
  }, [pct])

  return (
    <div className="metric">
      <div className="metric-head">
        <span>{label}</span>
        <strong>{v.passed}/{v.count} detected ({pct}%)</strong>
      </div>
      <div className="metric-track">
        <div
          className="metric-fill"
          style={{ width: `${width}%`, background: color || '#6366f1' }}
        />
      </div>
    </div>
  )
}
