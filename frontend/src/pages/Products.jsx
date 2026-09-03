import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

export default function Products() {
  const { user } = useAuth()
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', category: '', subcategory: '', brand: '', description: '' })
  const [busy, setBusy] = useState(false)
  const canCreate = user.role === 'MANUFACTURER' || user.role === 'ADMIN'

  async function load() {
    try {
      const p = await api.products()
      setProducts(p || [])
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function createProduct(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.createProduct(form)
      setShowForm(false)
      setForm({ name: '', category: '', subcategory: '', brand: '', description: '' })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>{user.role === 'MANUFACTURER' ? 'My Products' : 'Products'}</h1>
          <p className="muted">
            {canCreate
              ? 'Register and manage the products you place on the market.'
              : 'Browse products available for compliance checking.'}
          </p>
        </div>
        {canCreate && (
          <button className="primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? 'Cancel' : '+ Add product'}
          </button>
        )}
      </div>

      {error && <div className="alert error">{error}</div>}

      {showForm && canCreate && (
        <section className="panel">
          <h3 className="panel-title">Add a product</h3>
          <form className="form-grid" onSubmit={createProduct}>
            <label>Name
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </label>
            <label>Category
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required>
                <option value="">Select…</option>
                <option value="FOOD">Food</option>
                <option value="BEVERAGE">Beverage</option>
                <option value="COSMETIC">Cosmetic</option>
                <option value="HOUSEHOLD">Household</option>
                <option value="ELECTRONIC">Electronic</option>
                <option value="OTHER">Other</option>
              </select>
            </label>
            <label>Subcategory
              <input value={form.subcategory} onChange={(e) => setForm({ ...form, subcategory: e.target.value })} />
            </label>
            <label>Brand
              <input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
            </label>
            <label className="full">Description
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </label>
            <div className="full">
              <button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save product'}</button>
            </div>
          </form>
        </section>
      )}

      <section className="panel">
        {products.length === 0 ? (
          <div className="empty">
            <p className="muted">No products found.</p>
            {canCreate && <button className="primary small" onClick={() => setShowForm(true)}>Add your first product</button>}
          </div>
        ) : (
          <div className="product-grid">
            {products.map((p) => (
              <div className="product-card" key={p.id}>
                <span className="product-icon">📦</span>
                <div className="product-body">
                  <strong>{p.name}</strong>
                  <span className="muted small">{p.brand || 'No brand'}</span>
                  <div className="product-tags">
                    <span className="chip">{p.category}</span>
                    {p.subcategory && <span className="chip">{p.subcategory}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
