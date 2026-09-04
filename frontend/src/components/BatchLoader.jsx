import React from 'react'

const PHASE_STEPS = ['upload', 'run', 'done']

function phaseIndex(phase) {
  if (phase === 'done') return 2
  if (phase === 'run') return 1
  return 0 // 'upload'
}

export default function BatchLoader({ products, statuses }) {
  // products: array of { product, fileCount }
  // statuses: object keyed by product index -> { phase: 'upload'|'run'|'done', error?: string }
  const done = Object.values(statuses).filter((s) => s?.phase === 'done').length
  const running = Object.values(statuses).filter((s) => s?.phase === 'run').length
  const uploading = Object.values(statuses).filter((s) => s?.phase === 'upload').length
  const failed = Object.values(statuses).filter((s) => s?.error).length
  const total = products.length || 1
  const pct = Math.round((done / total) * 100)

  let sub
  if (failed > 0) sub = `${done} done · ${running} running · ${failed} failed`
  else if (done === total) sub = 'All products analyzed'
  else if (running > 0) sub = `${running} product${running === 1 ? '' : 's'} being analyzed right now`
  else if (uploading > 0) sub = `Uploading ${uploading} product${uploading === 1 ? '' : 's'}…`
  else sub = 'Preparing…'

  return (
    <div className="run-loader-overlay">
      <div className="run-loader-card batch-loader-card">
        <div className="loader-spinner">
          <div className="orbit orbit-a"></div>
          <div className="orbit orbit-b"></div>
          <div className="loader-core">🗂️</div>
        </div>
        <h2 className="loader-title">Analyzing {total} product{total === 1 ? '' : 's'} in parallel</h2>
        <p className="loader-sub">{sub}</p>

        <div className="batch-loader-progress">
          <div className="batch-loader-bar">
            <div className="batch-loader-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="batch-loader-pct">{pct}%</span>
        </div>

        <ul className="batch-loader-list">
          {products.map((p) => {
            const s = statuses[p.product]
            const status = s?.error
              ? 'failed'
              : s?.phase === 'done'
                ? 'done'
                : s?.phase === 'run'
                  ? 'running'
                  : 'uploading'
            const label = status === 'failed' ? 'Failed'
              : status === 'done' ? 'Done'
              : status === 'running' ? 'Analyzing…'
              : 'Uploading…'
            return (
              <li key={p.product} className={`bpl-item ${status}`}>
                <span className="bpl-icon">
                  {status === 'done' ? '✓' : status === 'failed' ? '✕' : '●'}
                </span>
                <div className="bpl-body">
                  <div className="bpl-head">
                    <strong>Product {p.product + 1}</strong>
                    <span className="bpl-status">{label}</span>
                  </div>
                  <div className="bpl-track">
                    <div className="bpl-fill" style={{ width: status === 'done' ? '100%' : status === 'uploading' ? '25%' : '60%' }} />
                  </div>
                  {status === 'failed' && s?.error && (
                    <em className="bpl-err">{s.error}</em>
                  )}
                </div>
                {status === 'running' && (
                  <span className="bpl-pulse"></span>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
