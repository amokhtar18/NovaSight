/**
 * API-related type definitions
 */

// Generic API response wrapper
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

// Paginated response
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// API Error
export interface ApiError {
  message: string
  code?: string
  details?: Record<string, string[]>
}

// Authentication
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  tenantId: string
  createdAt: string
  updatedAt: string
}

export type UserRole = 'admin' | 'analyst' | 'viewer'

// Token refresh
export interface RefreshTokenRequest {
  refresh_token: string
}

export interface RefreshTokenResponse {
  access_token: string
  expires_in: number
}
