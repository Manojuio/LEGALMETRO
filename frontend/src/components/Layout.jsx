import React from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const ROLE_LABEL = {
  ADMIN: 'Administrator',
  LMO: 'Legal Metrology Officer',
  MANUFACTURER: 'Manufacturer',
  RETAILER: 'Retailer',
  CONSUMER: 'Consumer',
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">LegalMetro</div>
        <nav className="nav">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/analyze">New Analysis</NavLink>
          {user?.role === 'ADMIN' && <NavLink to="/admin">Admin</NavLink>}
        </nav>
        <div className="user">
          <span className="role-badge">{ROLE_LABEL[user?.role] || user?.role}</span>
          <span className="email">{user?.email}</span>
          <button className="link-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
