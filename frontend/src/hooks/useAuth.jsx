import React, { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext({})

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [activeRole, setActiveRole] = useState(localStorage.getItem('activeRole') || 'renter')

  // Set up axios defaults immediately when token changes
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete axios.defaults.headers.common['Authorization']
    }
  }, [token])

  // Initialize auth and set axios headers on app startup
  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    if (storedToken && storedToken !== token) {
      // Set axios header immediately for stored token
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
      setToken(storedToken)
    }
  }, []) // Run once on mount

  // Check if user is logged in on mount
  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const response = await axios.get('/api/auth/me')
          // Handle both response formats: direct user object or nested user object
          const userData = response.data.user || response.data
          setUser(userData)
          
          // Sync active role with server data
          if (userData.active_role) {
            setActiveRole(userData.active_role)
            localStorage.setItem('activeRole', userData.active_role)
          }
        } catch (error) {
          localStorage.removeItem('token')
          localStorage.removeItem('activeRole')
          setToken(null)
          setActiveRole('renter')
        }
      }
      setLoading(false)
    }
    initAuth()
  }, [token])

  const loginWithGoogle = async () => {
    try {
      // Get Google OAuth URL
      const response = await axios.get('/api/auth/google')
      const { authorization_url } = response.data
      
      // Redirect to Google OAuth
      window.location.href = authorization_url
      
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Google login failed' 
      }
    }
  }

  const handleGoogleCallback = async (code, state) => {
    try {
      const params = new URLSearchParams({ code })
      if (state) {
        params.append('state', state)
      }
      const response = await axios.get(`/api/auth/google/callback?${params}`)
      const { access_token, user } = response.data
      
      // Store token and user info
      localStorage.setItem('token', access_token)
      setToken(access_token)
      setUser(user)
      
      // IMMEDIATELY set the authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      return { success: true, user }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Google authentication failed' 
      }
    }
  }

  const switchRole = async (newRole) => {
    if (!user || !token) {
      return { success: false, error: 'User not authenticated' }
    }

    try {
      const response = await axios.patch('/api/auth/me/active-role', {
        active_role: newRole
      })
      
      const updatedUser = response.data
      setUser(updatedUser)
      setActiveRole(newRole)
      localStorage.setItem('activeRole', newRole)
      
      return { success: true, user: updatedUser }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to switch role' 
      }
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('activeRole')
    setToken(null)
    setUser(null)
    setActiveRole('renter')
  }

  const value = {
    user,
    activeRole,
    loginWithGoogle,
    handleGoogleCallback,
    switchRole,
    logout,
    loading,
    isAuthenticated: !!user,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}