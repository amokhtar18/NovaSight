import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

export interface LoginCredentials {
  email: string
  password: string
  tenant_slug?: string
}

export interface RegisterCredentials {
  email: string
  password: string
  name: string
  tenant_name?: string
}

export interface User {
  id: string
  email: string
  name: string
  tenant_id: string
  tenant_name: string
  roles: string[]
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RegisterResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

const TOKEN_KEY = 'novasight_access_token'
const REFRESH_TOKEN_KEY = 'novasight_refresh_token'

class AuthService {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await axios.post<LoginResponse>(
      `${API_BASE_URL}/api/v1/auth/login`,
      credentials
    )
    return response.data
  }

  async register(credentials: RegisterCredentials): Promise<RegisterResponse> {
    const response = await axios.post<RegisterResponse>(
      `${API_BASE_URL}/api/v1/auth/register`,
      credentials
    )
    return response.data
  }

  async getCurrentUser(): Promise<User> {
    const response = await axios.get<{ user: User }>(
      `${API_BASE_URL}/api/v1/auth/me`,
      {
        headers: {
          Authorization: `Bearer ${this.getAccessToken()}`,
        },
      }
    )
    return response.data.user
  }

  async forgotPassword(email: string): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/api/v1/auth/forgot-password`,
      { email }
    )
  }

  async resetPassword(token: string, password: string): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/api/v1/auth/reset-password`,
      { token, password }
    )
  }

  async refreshAccessToken(): Promise<string> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await axios.post<{ access_token: string }>(
      `${API_BASE_URL}/api/v1/auth/refresh`,
      {},
      {
        headers: {
          Authorization: `Bearer ${refreshToken}`,
        },
      }
    )

    const newToken = response.data.access_token
    localStorage.setItem(TOKEN_KEY, newToken)
    return newToken
  }

  async logout(): Promise<void> {
    try {
      await axios.post(
        `${API_BASE_URL}/api/v1/auth/logout`,
        {},
        {
          headers: {
            Authorization: `Bearer ${this.getAccessToken()}`,
          },
        }
      )
    } catch (error) {
      // Ignore logout errors
    } finally {
      this.clearTokens()
    }
  }

  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  }

  getAccessToken(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  }

  clearTokens(): void {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }
}

export const authService = new AuthService()
