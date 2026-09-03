import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

export default function Admin() {
  const { user } = useAuth()
  const [zones, setZones] = useState([])
  const [lmos, setLmos] = useState([])
  const [zoneName, setZoneName] = useState('')
  const [zoneJur, setZoneJur] = useState('')
  const [error, setError] = useState('')

  async function load() {
    const [z, l] = await Promise.all([api.zones(), api.lmos()])
    setZones(z)
    setLmos(l)
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
      <div className="page-head">
        <div>
          <h1>Zones & LMOs</h1>
          <p className="muted">Manage zones and assign Legal Metrology Officers (LMOs) to them.</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="split">
        <section className="panel">
          <h3 className="panel-title">Create Zone</h3>
          <form onSubmit={createZone} className="form-grid">
            <label>Zone name
              <input value={zoneName} onChange={(e) => setZoneName(e.target.value)} placeholder="e.g. North Delhi" required />
            </label>
            <label>Jurisdiction (optional)
              <input value={zoneJur} onChange={(e) => setZoneJur(e.target.value)} placeholder="e.g. Zone 1" />
            </label>
            <div className="full">
              <button className="primary" type="submit">+ Add zone</button>
            </div>
          </form>
        </section>

        <section className="panel">
          <h3 className="panel-title">Assign LMOs to Zones</h3>
          {lmos.length === 0 && <p className="muted">No LMOs registered yet. Users can self-register as an LMO.</p>}
          <table className="table">
            <thead><tr><th>LMO</th><th>Zone</th></tr></thead>
            <tbody>
              {lmos.map((lmo) => (
                <tr key={lmo.id}>
                  <td>
                    <strong>{lmo.full_name}</strong>
                    <span className="muted small">{lmo.email}</span>
                  </td>
                  <td>
                    <select value={lmo.zone_id || ''} onChange={(e) => assignZone(lmo.id, e.target.value)}>
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
      </div>
    </div>
  )
}
