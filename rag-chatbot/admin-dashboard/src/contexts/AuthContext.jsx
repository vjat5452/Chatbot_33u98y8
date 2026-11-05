import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

const API = import.meta.env.VITE_API_URL || ''

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem('admin_token'))
  const [username, setUsername] = useState(() => sessionStorage.getItem('admin_user'))
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    if (token) {
      fetch(`${API}/api/admin/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {})
    }
    setToken(null)
    setUsername(null)
    sessionStorage.removeItem('admin_token')
    sessionStorage.removeItem('admin_user')
  }, [token])

  // Verify session on mount
  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    fetch(`${API}/api/admin/auth/check`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => {
        if (!res.ok) throw new Error('Invalid session')
        return res.json()
      })
      .then(data => {
        setUsername(data.username)
      })
      .catch(() => {
        logout()
      })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-logout on inactivity (30 min)
  useEffect(() => {
    if (!token) return
    let timer
    const resetTimer = () => {
      clearTimeout(timer)
      timer = setTimeout(logout, 30 * 60 * 1000)
    }
    window.addEventListener('mousemove', resetTimer)
    window.addEventListener('keydown', resetTimer)
    window.addEventListener('click', resetTimer)
    resetTimer()
    return () => {
      clearTimeout(timer)
      window.removeEventListener('mousemove', resetTimer)
      window.removeEventListener('keydown', resetTimer)
      window.removeEventListener('click', resetTimer)
    }
  }, [token, logout])

  const login = async (usr, password, captchaAnswer, captchaExpected) => {
    const res = await fetch(`${API}/api/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: usr,
        password,
        captcha_answer: captchaAnswer,
        captcha_expected: captchaExpected,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    setToken(data.token)
    setUsername(data.username)
    sessionStorage.setItem('admin_token', data.token)
    sessionStorage.setItem('admin_user', data.username)
  }

  return (
    <AuthContext.Provider value={{ token, username, loading, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
