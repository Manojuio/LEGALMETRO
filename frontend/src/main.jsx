import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Analyze from './pages/Analyze'
import BatchResults from './pages/BatchResults'
import Analyses from './pages/Analyses'
import AnalysisDetail from './pages/AnalysisDetail'
import AdminAnalyses from './pages/AdminAnalyses'
import Products from './pages/Products'
import Inspections from './pages/Inspections'
import InspectionHistory from './pages/InspectionHistory'
import './styles.css'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="boot">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function RoleGuard({ roles, children }) {
  const { user } = useAuth()
  if (!user) return null
  if (!roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}

function ScrollToTop() {
  const { pathname } = useLocation()
  React.useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToTop />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
            <Route
              path="/analyze"
              element={
                <Protected>
                  <RoleGuard roles={['LMO', 'MANUFACTURER', 'RETAILER', 'CONSUMER']}><Analyze /></RoleGuard>
                </Protected>
              }
            />
            <Route
              path="/batch-results"
              element={
                <Protected>
                  <RoleGuard roles={['LMO', 'MANUFACTURER', 'RETAILER', 'CONSUMER']}><BatchResults /></RoleGuard>
                </Protected>
              }
            />
            <Route path="/analyses" element={<Protected><Analyses /></Protected>} />
            <Route path="/analyses/:id" element={<Protected><AnalysisDetail /></Protected>} />
            <Route
              path="/admin-analyses"
              element={
                <Protected>
                  <RoleGuard roles={['ADMIN']}><AdminAnalyses /></RoleGuard>
                </Protected>
              }
            />
            <Route
              path="/products"
              element={
                <Protected>
                  <RoleGuard roles={['MANUFACTURER', 'RETAILER']}><Products /></RoleGuard>
                </Protected>
              }
            />
            <Route
              path="/inspections"
              element={
                <Protected>
                  <RoleGuard roles={['ADMIN', 'LMO']}><InspectionHistory /></RoleGuard>
                </Protected>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
