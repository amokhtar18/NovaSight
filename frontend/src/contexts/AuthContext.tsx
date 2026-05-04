/**
 * AuthContext — thin React-Context wrapper over the Zustand authStore.
 *
 * This eliminates the previous dual-state problem where AuthContext and
 * authStore independently managed auth state.  Now AuthContext delegates
 * everything to the store, preserving the `useAuth()` hook API that
 * Sidebar, Header, ProtectedRoute and other components already consume.
 */

import {
  createContext,
  useContext,
  useEffect,
  ReactNode,
} from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import type { User, LoginCredentials } from '@/services/authService'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()

  const store = useAuthStore()

  // Initialise auth from persisted tokens on first mount
  useEffect(() => {
    if (!store.isAuthenticated) {
      store.initializeFromStorage()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = async (credentials: LoginCredentials) => {
    await store.login(credentials.email, credentials.password)
    const stateFrom = (location.state as { from?: string })?.from
    const params = new URLSearchParams(location.search)
    const redirect = params.get('redirect')
    const target = stateFrom || redirect || '/app/dashboard'
    navigate(target, { replace: true })
  }

  const logout = () => {
    store.logout()
    navigate('/login', { replace: true })
  }

  const refreshUser = async () => {
    await store.initializeFromStorage()
  }

  const value: AuthContextType = {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    login,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
