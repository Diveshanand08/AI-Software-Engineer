/**
 * useAuth.js
 * Custom hook managing Google Sign-In state.
 * Persists user to localStorage so sign-in survives page refresh.
 *
 * Exported:
 *   user        — { name, email, picture } | null
 *   displayName — first name extracted from Google name or email prefix
 *   login(credentialResponse) — called after Google button success
 *   logout()
 */

import { useState, useCallback } from 'react'
import { jwtDecode } from 'jwt-decode'

const STORAGE_KEY = 'codeassist_user'

function extractFirstName(name, email) {
  // If email is provided, extract first name from email prefix (e.g. dhruv123@gmail.com -> "Dhruv")
  if (email) {
    const localPart = email.split('@')[0] || ''
    // Match the leading alphabetic letters before numbers or symbols
    const match = localPart.match(/^[a-zA-Z]+/)
    if (match && match[0]) {
      const clean = match[0]
      return clean.charAt(0).toUpperCase() + clean.slice(1).toLowerCase()
    }
    const cleanLetters = localPart.replace(/[^a-zA-Z]/g, '')
    if (cleanLetters) {
      return cleanLetters.charAt(0).toUpperCase() + cleanLetters.slice(1).toLowerCase()
    }
  }
  if (name) {
    return name.split(' ')[0]
  }
  return 'User'
}

function loadUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function useAuth() {
  const [user, setUser] = useState(loadUser)

  const login = useCallback((credentialResponse) => {
    try {
      const decoded = jwtDecode(credentialResponse.credential)
      const profile = {
        name: decoded.name || null,
        email: decoded.email || '',
        picture: decoded.picture || null,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
      setUser(profile)
    } catch (e) {
      console.error('Failed to decode Google credential:', e)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setUser(null)
  }, [])

  const displayName = user
    ? extractFirstName(user.name, user.email)
    : 'User'

  return { user, displayName, login, logout }
}
