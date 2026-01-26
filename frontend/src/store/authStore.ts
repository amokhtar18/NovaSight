import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { authService, User, LoginResponse } from '@/services/authService'

export interface RegisterData {
  email: string
  password: string
  name: string
  tenant_name?: string
}

export interface AuthState {
  // State
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  rememberMe: boolean

  // Actions
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  refreshAuth: () => Promise<void>
  clearError: () => void
  setLoading: (loading: boolean) => void
  initializeFromStorage: () => Promise<void>
  forgotPassword: (email: string) => Promise<void>
  resetPassword: (token: string, password: string) => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      rememberMe: false,

      // Login action
      login: async (email: string, password: string, rememberMe = false) => {
        set({ isLoading: true, error: null })
        try {
          const response: LoginResponse = await authService.login({ email, password })
          
          // Store tokens
          authService.setTokens(response.access_token, response.refresh_token)
          
          set({
            user: response.user,
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            rememberMe,
          })
        } catch (err: unknown) {
          const errorMessage = err instanceof Error 
            ? err.message 
            : 'Login failed. Please check your credentials.'
          set({ 
            error: errorMessage, 
            isLoading: false,
            isAuthenticated: false,
          })
          throw err
        }
      },

      // Register action
      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authService.register(data)
          
          // Auto-login after registration
          authService.setTokens(response.access_token, response.refresh_token)
          
          set({
            user: response.user,
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (err: unknown) {
          const errorMessage = err instanceof Error 
            ? err.message 
            : 'Registration failed. Please try again.'
          set({ 
            error: errorMessage, 
            isLoading: false,
          })
          throw err
        }
      },

      // Logout action
      logout: () => {
        authService.logout().catch(() => {})
        authService.clearTokens()
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        })
      },

      // Refresh auth token
      refreshAuth: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          set({ isAuthenticated: false, user: null })
          return
        }

        try {
          const newAccessToken = await authService.refreshAccessToken()
          set({ accessToken: newAccessToken })
        } catch (err) {
          // Refresh failed, logout user
          get().logout()
          throw err
        }
      },

      // Clear error
      clearError: () => set({ error: null }),

      // Set loading state
      setLoading: (loading: boolean) => set({ isLoading: loading }),

      // Initialize auth state from storage
      initializeFromStorage: async () => {
        const token = authService.getAccessToken()
        if (!token) {
          set({ isLoading: false })
          return
        }

        set({ isLoading: true })
        try {
          const user = await authService.getCurrentUser()
          set({
            user,
            accessToken: token,
            refreshToken: authService.getRefreshToken(),
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (err) {
          authService.clearTokens()
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },

      // Forgot password
      forgotPassword: async (email: string) => {
        set({ isLoading: true, error: null })
        try {
          await authService.forgotPassword(email)
          set({ isLoading: false })
        } catch (err: unknown) {
          const errorMessage = err instanceof Error 
            ? err.message 
            : 'Failed to send reset email. Please try again.'
          set({ 
            error: errorMessage, 
            isLoading: false,
          })
          throw err
        }
      },

      // Reset password
      resetPassword: async (token: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          await authService.resetPassword(token, password)
          set({ isLoading: false })
        } catch (err: unknown) {
          const errorMessage = err instanceof Error 
            ? err.message 
            : 'Failed to reset password. Please try again.'
          set({ 
            error: errorMessage, 
            isLoading: false,
          })
          throw err
        }
      },
    }),
    {
      name: 'novasight-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        refreshToken: state.rememberMe ? state.refreshToken : null,
        rememberMe: state.rememberMe,
      }),
    }
  )
)
