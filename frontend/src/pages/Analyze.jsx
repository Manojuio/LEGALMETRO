import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const POSITIONS = ['FRONT', 'BACK', 'SIDE', 'OTHER']

export default function Analyze() {
  const navigate = useNavigate()
  const [category, setCategory] = useState('FOOD')
  const [analysisId, setAnalysisId] = useState(null)
  const [images, setImages] = useState([]) // {file, position}
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

  function setPosition(index, position) {
    setImages((prev) => prev.map((img, i) => (i === index ? { ...img, position } : img)))
  }

  if (!analysisId) {
    return (
      <div className="card">
        <h2>New Analysis</h2>
        <label>Category
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="FOOD">Food</option>
            <option value="BEVERAGE">Beverage</option>
            <option value="COSMETIC">Cosmetic</option>
            <option value="HOUSEHOLD">Household</option>
            <option value="ELECTRONIC">Electronic</option>
            <option value="OTHER">Other</option>
          </select>
        </label>
        {error && <div className="alert error">{error}</div>}
        <button className="primary" onClick={createAnalysis}>Create Analysis</button>
      </div>
    )
  }

  return (
    <div>
      <h2>Upload product images</h2>
      <p className="muted">Analysis ID: <span className="mono">{analysisId}</span></p>

      <div className="card">
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => addFiles(e.target.files)}
        />
        {images.length > 0 && (
          <ul className="image-list">
            {images.map((img, i) => (
              <li key={i}>
                <span>{img.file.name}</span>
                <select value={img.position} onChange={(e) => setPosition(i, e.target.value)}>
                  {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </li>
            ))}
          </ul>
        )}
        {error && <div className="alert error">{error}</div>}
        <div className="row">
          <button
            className="primary"
            onClick={uploadAll}
            disabled={images.length === 0 || uploading}
          >
            {uploading ? 'Uploading…' : `Upload ${images.length} image${images.length === 1 ? '' : 's'} & Continue`}
          </button>
        </div>
      </div>
    </div>
  )
}
