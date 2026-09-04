import React, { useState, useRef, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'
import BatchLoader from '../components/BatchLoader'

const POSITIONS = ['FRONT', 'BACK', 'SIDE', 'OTHER']

const CATEGORIES = [
  { value: 'FOOD', label: 'Food', icon: '🍞' },
  { value: 'BEVERAGE', label: 'Beverage', icon: '🥤' },
  { value: 'COSMETIC', label: 'Cosmetic', icon: '🧴' },
  { value: 'HOUSEHOLD', label: 'Household', icon: '🧼' },
  { value: 'ELECTRONIC', label: 'Electronic', icon: '🔌' },
  { value: 'OTHER', label: 'Other', icon: '📦' },
]

const MAX_BATCH_PRODUCTS = 6
const MAX_BATCH_IMAGES = 30

export default function Analyze() {
  const navigate = useNavigate()
  const [mode, setMode] = useState(null) // 'single' | 'batch'
  const [batchPer, setBatchPer] = useState(null) // 'one' | 'many'
  const [category, setCategory] = useState('FOOD')
  const [analysisId, setAnalysisId] = useState(null)

  // Batch state: images carries {file, position, product} — product index is derived
  // from grouping, so users never touch a product selector.
  const [images, setImages] = useState([])
  const [currentProduct, setCurrentProduct] = useState(0) // 0-based for 'many' mode
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [batchStatus, setBatchStatus] = useState({})
  const [batchProducts, setBatchProducts] = useState([])
  const fileRef = useRef()

  // Set a product's live status (phase: 'upload'|'run'|'done', optional error)
  const updateStatus = useCallback((product, phase, err) => {
    setBatchStatus((prev) => ({ ...prev, [product]: { phase, error: err || null } }))
  }, [])

  function resetAll() {
    setMode(null)
    setBatchPer(null)
    setAnalysisId(null)
    setImages([])
    setCurrentProduct(0)
    setError('')
  }

  // ---- Single product ----
  async function createSingleAnalysis() {
    setError('')
    try {
      const a = await api.createAnalysis(category)
      setAnalysisId(a.analysis_id)
    } catch (err) {
      setError(err.message)
    }
  }

  // ---- Batch helpers ----
  function batchCount() {
    if (batchPer === 'one') return images.length
    const groups = new Set(images.map((i) => i.product))
    return groups.size
  }

  function addFiles(list) {
    const arr = Array.from(list)
    const limit = batchPer === 'one' ? MAX_BATCH_PRODUCTS - images.length : MAX_BATCH_IMAGES - images.length
    if (arr.length > limit) {
      const what = batchPer === 'one' ? 'products' : 'images'
      setError(`You can upload up to ${batchPer === 'one' ? MAX_BATCH_PRODUCTS : MAX_BATCH_IMAGES} ${what} in a batch.`)
      arr.splice(0, limit)
    }
    const mapped = arr.map((file, idx) => {
      const product =
        batchPer === 'one' ? images.length + idx // one photo per product → each photo is its own product
        : currentProduct // many mode → current product being staged
      return { file, position: 'FRONT', product, preview: URL.createObjectURL(file) }
    })
    setImages((prev) => [...prev, ...mapped])
    if (fileRef.current) fileRef.current.value = ''
  }

  function removeImage(index) {
    setImages((prev) => prev.filter((_, i) => {
      if (i === index && prev[i].preview) URL.revokeObjectURL(prev[i].preview)
      return i !== index
    }))
  }

  // Many mode: jump to a specific product tab
  function selectProduct(i) {
    setCurrentProduct(Math.max(0, Math.min(i, MAX_BATCH_PRODUCTS - 1)))
    if (fileRef.current) fileRef.current.value = ''
  }

  function setPosition(index, position) {
    setImages((prev) => prev.map((img, i) => (i === index ? { ...img, position } : img)))
  }

  // Many mode: advance to the next product tab (existing photos stay put)
  function moveToNextProduct() {
    setCurrentProduct((p) => Math.min(p + 1, MAX_BATCH_PRODUCTS - 1))
    if (fileRef.current) fileRef.current.value = ''
  }

  // ---- Single upload ----
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

  // ---- Batch run: analyze all products in parallel ----
  async function runBatch() {
    if (images.length === 0) return
    setUploading(true)
    setError('')
    try {
      const groups = {}
      for (const img of images) {
        if (!groups[img.product]) groups[img.product] = []
        groups[img.product].push(img)
      }

      const productKeys = Object.keys(groups).sort((a, b) => a - b)
      if (productKeys.length > MAX_BATCH_PRODUCTS) {
        throw new Error(`Max ${MAX_BATCH_PRODUCTS} products per batch.`)
      }

      const products = productKeys.map((key) => ({ product: Number(key), fileCount: groups[key].length }))
      setBatchProducts(products)
      setBatchStatus({})
      const statuses = {}
      for (const p of products) statuses[p.product] = { phase: 'upload', error: null }
      setBatchStatus(statuses)

      const analysisIds = {}
      // 1. Create ALL analyses up-front
      await Promise.all(products.map(async (p) => {
        const a = await api.createAnalysis(category)
        analysisIds[p.product] = a.analysis_id
        return a
      }))

      // 2. Upload all products' images in parallel
      await Promise.all(products.map(async (p) => {
        try {
          await Promise.all(groups[p.product].map((img) =>
            api.uploadImage(analysisIds[p.product], img.file, img.position)))
          updateStatus(p.product, 'run')
        } catch (err) {
          updateStatus(p.product, 'done', err.message)
        }
      }))

      // 3. Run all analyses in parallel (each still resolves independently)
      const settled = await Promise.allSettled(
        products.map(async (p) => {
          const image_url = `/api/v1/analyses/${analysisIds[p.product]}/image`
          try {
            const report = await api.runAnalysis(analysisIds[p.product])
            updateStatus(p.product, 'done')
            return { product: p.product, analysis_id: analysisIds[p.product], image_url, report }
          } catch (err) {
            updateStatus(p.product, 'done', err.message)
            return { product: p.product, analysis_id: analysisIds[p.product], image_url, report: null, error: err.message }
          }
        })
      )

      const results = settled
        .map((r) => (r.status === 'fulfilled' ? r.value : r.reason))
        .filter((r) => r && r.report)
        .sort((a, b) => a.product - b.product)

      // Persist so the summary survives refresh / direct navigation
      // (analyses are stored server-side; we cache the reports client-side).
      try {
        sessionStorage.setItem('lm_batch_results', JSON.stringify(results.map((r) => ({
          analysis_id: r.analysis_id,
          product: r.product,
          image_url: r.image_url,
          report: r.report,
        }))))
      } catch (_) {
        /* storage may be full — navigation state still carries results */
      }

      // brief pause so the loader shows the final "all done" state
      setTimeout(() => {
        setUploading(false)
        window.dispatchEvent(new Event('lm-batch-updated'))
        navigate('/batch-results', { state: { results } })
      }, 400)
    } catch (err) {
      setError(err.message)
      setUploading(false)
    }
  }

  // ================= STEP 0: single vs batch =================
  if (!mode) {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>New Analysis</h1>
            <p className="muted">Choose how you want to run a compliance scan.</p>
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        <section className="panel">
          <div className="mode-grid">
            <button type="button" className="mode-option" onClick={() => setMode('single')}>
              <span className="mode-icon">📦</span>
              <strong>Single product</strong>
              <span className="muted small">Upload one or more photos of one product (front / back / side) and get one compliance report.</span>
            </button>
            <button type="button" className="mode-option" onClick={() => setMode('batch')}>
              <span className="mode-icon">🗂️</span>
              <strong>Batch – multiple products</strong>
              <span className="muted small">Upload photos of several different products at once (up to {MAX_BATCH_PRODUCTS}) and get an analysis for each.</span>
            </button>
          </div>
        </section>
      </div>
    )
  }

  // ================= STEP 0.5: batch sub-mode =================
  if (mode === 'batch' && !batchPer) {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>Batch analysis</h1>
            <p className="muted">How many photos do you have for each product?</p>
          </div>
          <button type="button" className="link" onClick={resetAll}>← Back</button>
        </div>
        {error && <div className="alert error">{error}</div>}
        <section className="panel">
          <div className="mode-grid">
            <button type="button" className="mode-option" onClick={() => setBatchPer('one')}>
              <span className="mode-icon">🖼️</span>
              <strong>One photo per product</strong>
              <span className="muted small">Each photo you upload is a different product. Just pick many photos at once.</span>
            </button>
            <button type="button" className="mode-option" onClick={() => setBatchPer('many')}>
              <span className="mode-icon">🖼️🖼️</span>
              <strong>Multiple photos per product</strong>
              <span className="muted small">Add photos for one product, then move to the next. Great for front + back shots.</span>
            </button>
          </div>
        </section>
      </div>
    )
  }

  // ================= STEP 1: batch upload (one photo per product) =================
  if (mode === 'batch' && batchPer === 'one') {
    const count = images.length
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>Upload products</h1>
            <p className="muted">Each photo becomes its own product analysis.</p>
          </div>
          <button type="button" className="link" onClick={() => setBatchPer(null)}>← Back</button>
        </div>

        {uploading && <BatchLoader products={batchProducts} statuses={batchStatus} />}
        {error && <div className="alert error">{error}</div>}

        <section className="panel">
          <CategoryStrip category={category} setCategory={setCategory} />
          <div className="upload-zone" onClick={() => fileRef.current && fileRef.current.click()}>
            <div className="upload-icon">📷</div>
            <strong>Click to select many photos at once</strong>
            <span className="muted small">Each photo = one product · up to {MAX_BATCH_PRODUCTS} products</span>
            <input ref={fileRef} type="file" accept="image/*" multiple onChange={(e) => addFiles(e.target.files)} style={{ display: 'none' }} />
          </div>

          {count > 0 && (
            <p className="muted small center-note">
              <strong>{count}</strong> product{count === 1 ? '' : 's'} ready to analyze.
            </p>
          )}

          {images.length > 0 && (
            <ul className="image-list">
              {images.map((img, i) => (
                <li key={i}>
                  <span className="img-name">🖼️ {img.file.name}</span>
                  <div className="batch-controls">
                    <label className="batch-label">Position
                      <select value={img.position} onChange={(e) => setPosition(i, e.target.value)}>
                        {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                      </select>
                    </label>
                    <button type="button" className="link danger" onClick={() => removeImage(i)}>Remove</button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <button className="primary" onClick={runBatch} disabled={images.length === 0 || uploading}>
            {uploading ? 'Analyzing products…' : `Analyze ${count || 0} product${count === 1 ? '' : 's'} & continue`}
          </button>
        </section>
      </div>
    )
  }

  // ================= STEP 1: batch upload (multiple photos per product) =================
  if (mode === 'batch' && batchPer === 'many') {
    const count = images.length === 0 ? 0 : batchCount()
    const currentImages = images.filter((i) => i.product === currentProduct).length
    const atMax = currentProduct + 1 >= MAX_BATCH_PRODUCTS
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>Upload products</h1>
            <p className="muted">Add photos for one product at a time, then move to the next.</p>
          </div>
          <button type="button" className="link" onClick={() => setBatchPer(null)}>← Back</button>
        </div>

        {uploading && <BatchLoader products={batchProducts} statuses={batchStatus} />}
        {error && <div className="alert error">{error}</div>}

        <section className="panel">
          <CategoryStrip category={category} setCategory={setCategory} />

          {/* Product tab bar */}
          <div className="prod-tabs">
            {[...Array(MAX_BATCH_PRODUCTS)].map((_, i) => {
              const n = images.filter((img) => img.product === i).length
              return (
                <button
                  key={i}
                  type="button"
                  className={`prod-tab ${i === currentProduct ? 'active' : ''}`}
                  onClick={() => selectProduct(i)}
                >
                  <span className="prod-tab-label">Product {i + 1}</span>
                  <span className={`prod-tab-count ${n > 0 ? 'has' : ''}`}>{n}</span>
                </button>
              )
            })}
          </div>

          {/* Upload zone for the active product */}
          <div className="upload-zone" onClick={() => fileRef.current && fileRef.current.click()}>
            <div className="upload-icon">📷</div>
            <strong>Add photos for {currentProduct + 1 ? `Product ${currentProduct + 1}` : ''}</strong>
            <span className="muted small">
              {currentImages === 0
                ? 'Pick front / back / side shots for this product.'
                : `${currentImages} photo${currentImages === 1 ? '' : 's'} added here. Add more or switch products.`}
            </span>
            <input ref={fileRef} type="file" accept="image/*" multiple onChange={(e) => addFiles(e.target.files)} style={{ display: 'none' }} />
          </div>

          {/* Current product photo grid */}
          <div className="batch-controls right-align">
            <button type="button" className="secondary small" onClick={() => fileRef.current && fileRef.current.click()}>+ Add more photos</button>
            {!atMax && currentImages > 0 && (
              <button type="button" className="secondary" onClick={moveToNextProduct}>
                Next product →
              </button>
            )}
          </div>

          {images.length > 0 && (
            <div className="prod-photo-grid">
              {images.map((img, i) => (
                <div key={i} className={`prod-photo ${img.product === currentProduct ? '' : 'dim'}`}>
                  <div className="prod-photo-img" style={{ backgroundImage: `url(${img.preview})` }} />
                  <span className="prod-photo-tag">P{img.product + 1}</span>
                  <div className="prod-photo-controls">
                    <span className="prod-photo-name">{img.file.name}</span>
                    <select value={img.position} onChange={(e) => setPosition(i, e.target.value)}>
                      {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <button type="button" className="prod-photo-remove" onClick={() => removeImage(i)}>Remove</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="stepper-actions">
            <button className="primary" onClick={runBatch} disabled={images.length === 0 || uploading}>
              {uploading ? 'Analyzing products…' : `Analyze ${count || 0} product${count === 1 ? '' : 's'} & continue`}
            </button>
          </div>
        </section>
      </div>
    )
  }

  // ================= STEP 2 (single): category =================
  if (mode === 'single' && !analysisId) {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>Product category</h1>
            <p className="muted">Choose the product category to start the compliance scan.</p>
          </div>
          <button type="button" className="link" onClick={resetAll}>← Back</button>
        </div>
        {error && <div className="alert error">{error}</div>}
        <section className="panel">
          <h3 className="panel-title">Product category</h3>
          <div className="category-grid">
            {CATEGORIES.map((c) => (
              <button key={c.value} type="button"
                className={`category-option ${category === c.value ? 'active' : ''}`}
                onClick={() => setCategory(c.value)}>
                <span className="category-icon">{c.icon}</span>
                <span>{c.label}</span>
              </button>
            ))}
          </div>
          <button className="primary" onClick={createSingleAnalysis}>Continue →</button>
        </section>
      </div>
    )
  }

  // ================= STEP 3 (single): upload images =================
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
          <input ref={fileRef} type="file" accept="image/*" multiple onChange={(e) => addFiles(e.target.files)} style={{ display: 'none' }} />
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

        <button className="primary" onClick={uploadAll} disabled={images.length === 0 || uploading}>
          {uploading ? 'Uploading…' : `Upload ${images.length} image${images.length === 1 ? '' : 's'} & continue`}
        </button>
      </section>
    </div>
  )
}

function CategoryStrip({ category, setCategory }) {
  return (
    <div className="category-strip">
      <span className="cs-label">Category</span>
      <div className="cs-options">
        {CATEGORIES.map((c) => (
          <button key={c.value} type="button"
            className={`cs-option ${category === c.value ? 'active' : ''}`}
            onClick={() => setCategory(c.value)}>
            <span className="cs-icon">{c.icon}</span>
            <span>{c.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
