import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { authService } from './authService'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

/**
 * Custom error class that extracts error messages from API responses.
 */
class ApiError extends Error {
  status: number
  code?: string
  
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

/**
 * Extract error message from Axios error response.
 */
export function extractErrorMessage(error: unknown): string {
  const axErr = error as AxiosError
  if (axErr?.response?.data) {
    const data = axErr.response.data as Record<string, unknown>
    // Try common error response formats
    if (typeof data.message === 'string') return data.message
    if (typeof data.error === 'string') return data.error
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.errors) && data.errors.length > 0) {
      return data.errors
        .map((e) => (typeof e === 'string' ? e : (e as { message?: string; msg?: string }).message || (e as { msg?: string }).msg))
        .join(', ')
    }
    // Fallback to stringifying the response
    if (Object.keys(data).length > 0) {
      return JSON.stringify(data)
    }
  }
  return axErr?.message || 'An unexpected error occurred'
}

class ApiClient {
  private client: AxiosInstance
  private isRefreshing = false
  private failedQueue: Array<{
    resolve: (value?: unknown) => void
    reject: (reason?: unknown) => void
  }> = []

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = authService.getAccessToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor - handle 401 and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & {
          _retry?: boolean
        }

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject })
            })
              .then(() => this.client(originalRequest))
              .catch((err) => Promise.reject(err))
          }

          originalRequest._retry = true
          this.isRefreshing = true

          try {
            const newToken = await authService.refreshAccessToken()
            this.processQueue(null)
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return this.client(originalRequest)
          } catch (refreshError) {
            this.processQueue(refreshError)
            authService.clearTokens()
            window.location.href = '/login'
            return Promise.reject(refreshError)
          } finally {
            this.isRefreshing = false
          }
        }

        // Transform error to include server message
        const message = extractErrorMessage(error)
        const status = error.response?.status || 0
        const code = (error.response?.data as Record<string, unknown>)?.code as string | undefined
        return Promise.reject(new ApiError(message, status, code))
      }
    )
  }

  private processQueue(error: unknown) {
    this.failedQueue.forEach((promise) => {
      if (error) {
        promise.reject(error)
      } else {
        promise.resolve()
      }
    })
    this.failedQueue = []
  }

  get instance() {
    return this.client
  }
}

export const apiClient = new ApiClient().instance
export { ApiError }
