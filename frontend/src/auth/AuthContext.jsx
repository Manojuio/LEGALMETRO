import React, { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('lm_user'))
    } catch (_) {
      return null
    }
  })
  const [token, setToken] = useState(() => localStorage.getItem('lm_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function bootstrap() {
      if (token) {
        try {
          const u = await api.me()
          setUser(u)
          localStorage.setItem('lm_user', JSON.stringify(u))
        } catch (_) {
          // token invalid -> cleared by api client
        }
      }
      setLoading(false)
    }
    bootstrap()
  }, [token])

  function persist(data) {
    localStorage.setItem('lm_token', data.access_token)
    localStorage.setItem('lm_user', JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
  }

  async function login(email, password) {
    const data = await api.login(email, password)
    persist(data)
  }

  async function register(payload) {
    await api.register(payload)
  }

  function logout() {
    localStorage.removeItem('lm_token')
    localStorage.removeItem('lm_user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
