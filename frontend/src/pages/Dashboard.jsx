import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-value">{value ?? '—'}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [analyses, setAnalyses] = useState([])
  const [inspections, setInspections] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [d, a] = await Promise.all([
          api.dashboard(),
          api.analyses(),
        ])
        setData(d)
        setAnalyses(a)
        let insp = []
        if (user.role === 'ADMIN' || user.role === 'LMO') {
          insp = await api.inspections()
        }
        setInspections(insp)
      } catch (err) {
        setError(err.message)
      }
    }
    load()
  }, [user.role])

  const role = user.role
  const stats = data?.stats || {}

  return (
    <div>
      <h2>Dashboard</h2>
      {error && <div className="alert error">{error}</div>}

      <div className="stats-row">
        {role === 'ADMIN' && <>
          <Stat label="Total Users" value={stats.total_users} />
          <Stat label="LMOs" value={stats.lmos} />
          <Stat label="Manufacturers" value={stats.manufacturers} />
          <Stat label="Consumers" value={stats.consumers} />
          <Stat label="Zones" value={stats.zones} />
          <Stat label="Total Analyses" value={stats.total_analyses} />
        </>}
        {role === 'LMO' && <>
          <Stat label="My Inspections" value={stats.my_inspections} />
          <Stat label="Pending" value={stats.pending_inspections} />
          <Stat label="All Analyses" value={stats.total_analyses} />
        </>}
        {role === 'MANUFACTURER' && <>
          <Stat label="My Products" value={stats.my_products} />
          <Stat label="My Analyses" value={stats.my_analyses} />
        </>}
        {(role === 'RETAILER' || role === 'CONSUMER') && <>
          <Stat label="My Analyses" value={stats.my_analyses} />
        </>}
      </div>

      {role === 'ADMIN' && data?.lmos_by_zone && (
        <section className="card">
          <h3>Legal Metrology Officers by Zone</h3>
          {data.lmos_by_zone.length === 0 && <p className="muted">No LMOs assigned to zones yet. Use the Admin page.</p>}
          <table>
            <thead>
              <tr><th>Zone</th><th>Jurisdiction</th><th>LMO</th><th>Email</th></tr>
            </thead>
            <tbody>
              {data.lmos_by_zone.map((g) =>
                g.lmos.map((lmo) => (
                  <tr key={lmo.id}>
                    <td>{g.zone.name}</td>
                    <td>{g.zone.jurisdiction || '—'}</td>
                    <td>{lmo.name}</td>
                    <td>{lmo.email}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>
      )}

      {role === 'LMO' && inspections.length > 0 && (
        <section className="card">
          <h3>My Inspections</h3>
          <table>
            <thead><tr><th>ID</th><th>Location</th><th>Status</th></tr></thead>
            <tbody>
              {inspections.map((i) => (
                <tr key={i.id}>
                  <td className="mono">{i.analysis_id.slice(0, 8)}</td>
                  <td>{i.location || '—'}</td>
                  <td><span className={`badge ${i.status?.toLowerCase()}`}>{i.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="card">
        <div className="row-between">
          <h3>My Analyses</h3>
          <Link className="primary small" to="/analyze">+ New Analysis</Link>
        </div>
        {analyses.length === 0 && <p className="muted">No analyses yet.</p>}
        <table>
          <thead><tr><th>ID</th><th>Category</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {analyses.map((a) => (
              <tr key={a.id}>
                <td className="mono">{a.id.slice(0, 8)}</td>
                <td>{a.category}</td>
                <td>
                  <span className={`badge ${(a.overall_status || a.status)?.toLowerCase()}`}>
                    {a.overall_status || a.status}
                  </span>
                </td>
                <td><Link to={`/analyses/${a.id}`}>Open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
