import React, { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'

const POSITIONS = ['FRONT', 'BACK', 'SIDE', 'OTHER']

const CATEGORIES = [
  { value: 'FOOD', label: 'Food', icon: '🍞' },
  { value: 'BEVERAGE', label: 'Beverage', icon: '🥤' },
  { value: 'COSMETIC', label: 'Cosmetic', icon: '🧴' },
  { value: 'HOUSEHOLD', label: 'Household', icon: '🧼' },
  { value: 'ELECTRONIC', label: 'Electronic', icon: '🔌' },
  { value: 'OTHER', label: 'Other', icon: '📦' },
]

export default function Analyze() {
  const navigate = useNavigate()
  const [category, setCategory] = useState('FOOD')
  const [analysisId, setAnalysisId] = useState(null)
  const [images, setImages] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef()

  async function createAnalysis() {
    setError('')
    try {
      const a = await api.createAnalysis(category)
      setAnalysisId(a.analysis_id)
    } catch (err) {
      setError(err.message)
    }
  }

  function addFiles(list) {
    const arr = Array.from(list).map((file) => ({ file, position: 'FRONT' }))
    setImages((prev) => [...prev, ...arr])
    if (fileRef.current) fileRef.current.value = ''
  }

  function removeImage(index) {
    setImages((prev) => prev.filter((_, i) => i !== index))
  }

  function setPosition(index, position) {
    setImages((prev) => prev.map((img, i) => (i === index ? { ...img, position } : img)))
  }

  async function uploadAll() {
    if (!analysisId || images.length === 0) return
    setUploading(true)
    setError('')
    try {
      for (const img of images) {
        await api.uploadImage(analysisId, img.file, img.position)
      }
      navigate(`/analyses/${analysisId}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  if (!analysisId) {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>New Analysis</h1>
            <p className="muted">Choose the product category to start a compliance scan.</p>
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        <section className="panel">
          <h3 className="panel-title">Product category</h3>
          <div className="category-grid">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                type="button"
                className={`category-option ${category === c.value ? 'active' : ''}`}
                onClick={() => setCategory(c.value)}
              >
                <span className="category-icon">{c.icon}</span>
                <span>{c.label}</span>
              </button>
            ))}
          </div>
          <button className="primary" onClick={createAnalysis}>Continue →</button>
        </section>
      </div>
    )
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Upload product images</h1>
          <p className="muted">
            Analysis ID: <span className="mono">{analysisId}</span>
          </p>
        </div>
        <Link to="/" className="link">← Back</Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      <section className="panel">
        <div className="upload-zone" onClick={() => fileRef.current && fileRef.current.click()}>
          <div className="upload-icon">📷</div>
          <strong>Click to select images</strong>
          <span className="muted small">Front / back / side shots of the packaging work best</span>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => addFiles(e.target.files)}
            style={{ display: 'none' }}
          />
        </div>

        {images.length > 0 && (
          <ul className="image-list">
            {images.map((img, i) => (
              <li key={i}>
                <span className="img-name">🖼️ {img.file.name}</span>
                <div className="row">
                  <select value={img.position} onChange={(e) => setPosition(i, e.target.value)}>
                    {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                  <button type="button" className="link danger" onClick={() => removeImage(i)}>Remove</button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <button
          className="primary"
          onClick={uploadAll}
          disabled={images.length === 0 || uploading}
        >
          {uploading
            ? 'Uploading…'
            : `Upload ${images.length} image${images.length === 1 ? '' : 's'} & continue`}
        </button>
      </section>
    </div>
  )
}
