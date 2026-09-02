import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

export default function Admin() {
  const { user } = useAuth()
  const [zones, setZones] = useState([])
  const [lmos, setLmos] = useState([])
  const [users, setUsers] = useState([])
  const [zoneName, setZoneName] = useState('')
  const [zoneJur, setZoneJur] = useState('')
  const [error, setError] = useState('')

  async function load() {
    const [z, l, u] = await Promise.all([api.zones(), api.lmos(), api.listUsers()])
    setZones(z)
    setLmos(l)
    setUsers(u)
  }

  useEffect(() => {
    if (user.role === 'ADMIN') load().catch((e) => setError(e.message))
    // eslint-disable-next-line
  }, [user.role])

  async function createZone(e) {
    e.preventDefault()
    setError('')
    try {
      await api.createZone({ name: zoneName, jurisdiction: zoneJur })
      setZoneName('')
      setZoneJur('')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function assignZone(lmoId, zoneId) {
    setError('')
    try {
      await api.updateUser(lmoId, { zone_id: zoneId || null })
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h2>Admin — Zones & LMOs</h2>
      {error && <div className="alert error">{error}</div>}

      <section className="card">
        <h3>Create Zone</h3>
        <form onSubmit={createZone} className="inline-form">
          <input value={zoneName} onChange={(e) => setZoneName(e.target.value)} placeholder="Zone name" required />
          <input value={zoneJur} onChange={(e) => setZoneJur(e.target.value)} placeholder="Jurisdiction (optional)" />
          <button className="primary" type="submit">Add</button>
        </form>
      </section>

      <section className="card">
        <h3>Assign LMOs to Zones</h3>
        {lmos.length === 0 && <p className="muted">No LMOs found.</p>}
        <table>
          <thead><tr><th>LMO</th><th>Email</th><th>Zone</th></tr></thead>
          <tbody>
            {lmos.map((lmo) => (
              <tr key={lmo.id}>
                <td>{lmo.full_name}</td>
                <td>{lmo.email}</td>
                <td>
                  <select
                    value={lmo.zone_id || ''}
                    onChange={(e) => assignZone(lmo.id, e.target.value)}
                  >
                    <option value="">— unassigned —</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.id}>{z.name}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h3>All Users</h3>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Zone</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>{zones.find((z) => z.id === u.zone_id)?.name || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
