import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Analyze from './pages/Analyze'
import AnalysisDetail from './pages/AnalysisDetail'
import Admin from './pages/Admin'
import './styles.css'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<Layout />}>
            <Route
              path="/"
              element={
                <Protected>
                  <Dashboard />
                </Protected>
              }
            />
            <Route
              path="/analyze"
              element={
                <Protected>
                  <Analyze />
                </Protected>
              }
            />
            <Route
              path="/analyses/:id"
              element={
                <Protected>
                  <AnalysisDetail />
                </Protected>
              }
            />
            <Route
              path="/admin"
              element={
                <Protected>
                  <Admin />
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
