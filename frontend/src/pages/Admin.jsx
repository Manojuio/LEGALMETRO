import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

export default function Admin() {
  const { user } = useAuth()
  const [lmos, setLmos] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (user.role === 'ADMIN') {
      api
        .lmos()
        .then((l) => setLmos(l || []))
        .catch((e) => setError(e.message))
    }
    // eslint-disable-next-line
  }, [user.role])

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Legal Metrology Officers</h1>
          <p className="muted">All LMOs under your administration. Review and download the compliance reports they produce.</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <section className="panel">
        <h3 className="panel-title">All LMOs</h3>
        {lmos.length === 0 ? (
          <p className="muted">No LMOs registered yet. Users can self-register as an LMO.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Name</th><th>Email</th></tr></thead>
            <tbody>
              {lmos.map((lmo) => (
                <tr key={lmo.id}>
                  <td>
                    <strong>{lmo.full_name}</strong>
                  </td>
                  <td className="muted">{lmo.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
