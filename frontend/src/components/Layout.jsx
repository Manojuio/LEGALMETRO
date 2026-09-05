import React, { useEffect } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { roleConfig } from '../config/roles'

const ROLE_MENUS = {
  ADMIN: [
    { to: '/dashboard', label: 'Overview', icon: '📊', end: true },
    { to: '/admin-analyses', label: 'LMO Analyses', icon: '📋' },
  ],
  LMO: [
    { to: '/dashboard', label: 'Overview', icon: '📊', end: true },
    { to: '/inspections', label: 'Inspections', icon: '🔎' },
    { to: '/analyze', label: 'New Analysis', icon: '🔍' },
    { to: '/analyses', label: 'All Analyses', icon: '📋' },
  ],
  MANUFACTURER: [
    { to: '/dashboard', label: 'Overview', icon: '📊', end: true },
    { to: '/products', label: 'My Products', icon: '📦' },
    { to: '/analyze', label: 'New Analysis', icon: '🔍' },
  ],
  RETAILER: [
    { to: '/dashboard', label: 'Overview', icon: '📊', end: true },
    { to: '/products', label: 'Products', icon: '📦' },
    { to: '/analyze', label: 'New Analysis', icon: '🔍' },
  ],
  CONSUMER: [
    { to: '/dashboard', label: 'Overview', icon: '📊', end: true },
    { to: '/analyze', label: 'New Analysis', icon: '🔍' },
  ],
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const role = user?.role
  const cfg = roleConfig(role)

  useEffect(() => {
    if (role) document.body.dataset.role = role
  }, [role])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const menu = ROLE_MENUS[role] || ROLE_MENUS.CONSUMER

  return (
    <div className="app role-theme" data-role={role}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">LM</span>
          <div>
            <div className="brand-name">LegalMetro</div>
            <div className="brand-sub">Compliance Scanner</div>
          </div>
        </div>

        <div className="role-card">
          <span className="role-avatar">{cfg.icon}</span>
          <div className="role-meta">
            <strong>{cfg.label}</strong>
            <span className="role-tagline">{cfg.tagline}</span>
          </div>
        </div>

        <nav className="side-nav">
          {menu.map((item) => (
            <NavLink
              key={item.to + (item.label || '')}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-mini">
            <div className="user-avatar">{user?.full_name?.charAt(0) || 'U'}</div>
            <div className="user-mini-meta">
              <strong>{user?.full_name}</strong>
              <span>{user?.email}</span>
            </div>
          </div>
          <button className="logout-btn" onClick={handleLogout}>↪ Sign out</button>
        </div>
      </aside>

      <main className="content-wrap">
        <header className="mobile-bar">
          <span className="brand-name">LegalMetro</span>
          <button className="logout-btn" onClick={handleLogout}>Sign out</button>
        </header>
        <div className="page">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
