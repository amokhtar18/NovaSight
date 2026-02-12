/**
 * Portal Admin API Service
 * 
 * API client for portal-level administration including
 * cross-tenant user management and tenant management.
 */

import { apiClient } from './apiClient'

// ============ Types ============

export interface PortalUser {
  id: string
  email: string
  name: string
  status: string
  tenant_id: string
  tenant_name?: string
  tenant_slug?: string
  roles: Array<{
    id: string
    name: string
    display_name: string
    description?: string
  }>
  created_at: string
  updated_at: string
  last_login_at?: string
}

export interface PortalTenant {
  id: string
  name: string
  slug: string
  plan: string
  status: string
  settings?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface PortalStats {
  tenants: {
    total: number
    active: number
  }
  users: {
    total: number
    active: number
  }
  users_by_tenant: Array<{
    name: string
    slug: string
    count: number
  }>
  users_by_role: Array<{
    name: string
    display_name: string
    count: number
  }>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface TenantCreateData {
  name: string
  slug: string
  plan: string
  settings?: Record<string, unknown>
}

export interface TenantUpdateData {
  name?: string
  plan?: string
  status?: string
  settings?: Record<string, unknown>
}

export interface PortalUserCreateData {
  email: string
  name: string
  password: string
  tenant_id: string
  roles?: string[]
}

// ============ Service ============

const ADMIN_BASE = '/api/v1/admin'

export const portalAdminService = {
  // ---- Stats ----
  async getStats(): Promise<PortalStats> {
    const response = await apiClient.get(`${ADMIN_BASE}/portal/stats`)
    return response.data
  },

  // ---- Tenants ----
  async listTenants(params?: {
    page?: number
    per_page?: number
    search?: string
    status?: string
  }): Promise<PaginatedResponse<PortalTenant>> {
    const response = await apiClient.get(`${ADMIN_BASE}/tenants`, { params })
    return response.data
  },

  async getTenant(id: string): Promise<{ tenant: PortalTenant }> {
    const response = await apiClient.get(`${ADMIN_BASE}/tenants/${id}`)
    return response.data
  },

  async createTenant(data: TenantCreateData): Promise<{ tenant: PortalTenant; message: string }> {
    const response = await apiClient.post(`${ADMIN_BASE}/tenants`, data)
    return response.data
  },

  async updateTenant(id: string, data: TenantUpdateData): Promise<{ tenant: PortalTenant }> {
    const response = await apiClient.put(`${ADMIN_BASE}/tenants/${id}`, data)
    return response.data
  },

  async activateTenant(id: string): Promise<{ tenant: PortalTenant; message: string }> {
    const response = await apiClient.post(`${ADMIN_BASE}/tenants/${id}/activate`)
    return response.data
  },

  async suspendTenant(id: string, reason?: string): Promise<{ tenant: PortalTenant; message: string }> {
    const response = await apiClient.post(`${ADMIN_BASE}/tenants/${id}/suspend`, { reason })
    return response.data
  },

  async deactivateTenant(id: string): Promise<{ tenant: PortalTenant; message: string }> {
    const response = await apiClient.delete(`${ADMIN_BASE}/tenants/${id}`)
    return response.data
  },

  async getTenantUsage(id: string): Promise<{ tenant_id: string; usage: Record<string, unknown> }> {
    const response = await apiClient.get(`${ADMIN_BASE}/tenants/${id}/usage`)
    return response.data
  },

  // ---- Users (Cross-Tenant) ----
  async listUsers(params?: {
    page?: number
    per_page?: number
    search?: string
    tenant_id?: string
    role?: string
    status?: string
  }): Promise<PaginatedResponse<PortalUser>> {
    const response = await apiClient.get(`${ADMIN_BASE}/portal/users`, { params })
    return response.data
  },

  async createUser(data: PortalUserCreateData): Promise<{ user: PortalUser; message: string }> {
    try {
      const response = await apiClient.post(`${ADMIN_BASE}/portal/users`, data)
      return response.data
    } catch (error: any) {
      const message = error.response?.data?.error?.message || error.response?.data?.message || 'Failed to create user'
      throw new Error(message)
    }
  },

  async getUser(id: string): Promise<{ user: PortalUser }> {
    const response = await apiClient.get(`${ADMIN_BASE}/portal/users/${id}`)
    return response.data
  },

  async updateUserStatus(id: string, status: string): Promise<{ user: PortalUser; message: string }> {
    const response = await apiClient.patch(`${ADMIN_BASE}/portal/users/${id}/status`, { status })
    return response.data
  },

  async deleteUser(id: string): Promise<{ message: string }> {
    const response = await apiClient.delete(`${ADMIN_BASE}/portal/users/${id}`)
    return response.data
  },
}
