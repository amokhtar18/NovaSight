import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { authService, User, LoginCredentials } from '@/services/authService'

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
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authService.getCurrentUser()
      setUser(currentUser)
    } catch (error) {
      setUser(null)
      authService.clearTokens()
    }
  }, [])

  useEffect(() => {
    const initAuth = async () => {
      const token = authService.getAccessToken()
      if (token) {
        await refreshUser()
      }
      setIsLoading(false)
    }

    initAuth()
  }, [refreshUser])

  const login = async (credentials: LoginCredentials) => {
    const response = await authService.login(credentials)
    authService.setTokens(response.access_token, response.refresh_token)
    setUser(response.user)
    
    const from = (location.state as { from?: string })?.from || '/dashboard'
    navigate(from, { replace: true })
  }

  const logout = () => {
    authService.logout()
    setUser(null)
    navigate('/login', { replace: true })
  }

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
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
