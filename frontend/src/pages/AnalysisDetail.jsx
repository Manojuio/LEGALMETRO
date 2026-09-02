import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

export default function AnalysisDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const [report, setReport] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [inspectionForms, setInspectionForms] = useState(false)
  const [inspForm, setInspForm] = useState({ location: '', observations: '' })

  async function downloadReport() {
    try {
      await api.downloadReport(id)
    } catch (err) {
      setError(err.message)
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

  useEffect(() => {
    // Optionally auto-load existing report? We just run on demand.
  }, [id])

  return (
    <div>
      <div className="row-between">
        <h2>Analysis <span className="mono">{id.slice(0, 8)}</span></h2>
        <Link to="/">← Back</Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="card">
        {!report && (
          <p className="muted">Run OCR, rule checkers and generate the compliance report for this product.</p>
        )}
        <button className="primary" onClick={run} disabled={running}>
          {running ? 'Running analysis…' : 'Run Analysis'}
        </button>
        {report && (
          <button className="primary small" onClick={downloadReport}>
            Download PDF Report
          </button>
        )}
      </div>

      {report && (
        <>
          <div className={`banner ${report.overall_status.toLowerCase()}`}>
            Overall: <strong>{report.overall_status}</strong>
          </div>

          {report.summary && (
            <div className="stats-row">
              {Object.entries(report.summary).map(([k, v]) => (
                <div className="stat" key={k}>
                  <div className="stat-value">{v}</div>
                  <div className="stat-label">{k.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          )}

          {report.product && (
            <section className="card">
              <h3>Extracted Product</h3>
              <table>
                <thead><tr><th>Field</th><th>Value</th></tr></thead>
                <tbody>
                  {Object.entries(report.product).map(([k, v]) => (
                    <tr key={k}>
                      <td><strong>{k.replace(/_/g, ' ')}</strong></td>
                      <td>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section className="card">
            <h3>Rule Results ({report.rules?.length || 0})</h3>
            <table>
              <thead><tr><th>Rule</th><th>Status</th><th>Reason</th></tr></thead>
              <tbody>
                {report.rules.map((r, i) => (
                  <tr key={i}>
                    <td>{r.rule_id || r.name || i}</td>
                    <td><span className={`badge ${r.status.toLowerCase()}`}>{r.status}</span></td>
                    <td>{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}

      {(user.role === 'ADMIN' || user.role === 'LMO') && (
        <section className="card">
          <h3>Field Inspection</h3>
          {!inspectionForms ? (
            <button onClick={() => setInspectionForms(true)}>Register inspection</button>
          ) : (
            <form onSubmit={createInspection}>
              <label>Location
                <input value={inspForm.location} onChange={(e) => setInspForm({ ...inspForm, location: e.target.value })} />
              </label>
              <label>Observations
                <textarea value={inspForm.observations} onChange={(e) => setInspForm({ ...inspForm, observations: e.target.value })} />
              </label>
              <button className="primary" type="submit">Save inspection</button>
            </form>
          )}
        </section>
      )}
    </div>
  )
}
