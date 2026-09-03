import React, { useEffect, useRef, useState } from 'react'

const STAGES = [
  { key: 'ocr', label: 'Optical character recognition', icon: '🔍', desc: 'Reading label text from images' },
  { key: 'extract', label: 'Extracting product fields', icon: '🧬', desc: 'Pulling name, batch, dates, net quantity' },
  { key: 'classify', label: 'Classifying product', icon: '🏷️', desc: 'Mapping to regulated categories' },
  { key: 'rules', label: 'Applying compliance rules', icon: '📏', desc: 'Checking against legal metrology rules' },
  { key: 'review', label: 'Aggregating verdict', icon: '⚖️', desc: 'Scoring and final PASS / FAIL' },
]

export default function RunLoader({ onDone }) {
  const [stage, setStage] = useState(0)
  const timer = useRef(null)

  useEffect(() => {
    timer.current = setInterval(() => {
      setStage((s) => {
        if (s >= STAGES.length - 1) {
          clearInterval(timer.current)
          if (onDone) setTimeout(onDone, 500)
          return s
        }
        return s + 1
      })
    }, 900)
    return () => clearInterval(timer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="run-loader-overlay">
      <div className="run-loader-card">
        <div className="loader-spinner">
          <div className="orbit orbit-a"></div>
          <div className="orbit orbit-b"></div>
          <div className="loader-core">⚖️</div>
        </div>
        <h2 className="loader-title">Running compliance analysis</h2>
        <p className="loader-sub">Analyzing packaging… this takes a few seconds</p>

        <ol className="loader-stages">
          {STAGES.map((s, i) => (
            <li
              key={s.key}
              className={
                i < stage ? 'done' : i === stage ? 'active' : 'pending'
              }
            >
              <span className="stage-icon">
                {i < stage ? '✓' : s.icon}
              </span>
              <div className="stage-body">
                <div className="stage-arrow"></div>
                <strong>{s.label}</strong>
                {i === stage && <em>{s.desc}</em>}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
