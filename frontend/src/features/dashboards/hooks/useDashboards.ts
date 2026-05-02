/**
 * Dashboard hooks for data fetching and mutations.
 *
 * Internals: when the per-tenant `FEATURE_SUPERSET_BACKEND` flag is on,
 * dashboard CRUD is transparently re-routed through Superset
 * (Phase 5 of the Superset integration). The hook return shapes are
 * unchanged so consumers (`pages/dashboards/*`) keep working.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import {
  isSupersetBackendEnabled,
  supersetService,
} from '@/services/supersetService'
import type { Dashboard, Widget, WidgetData } from '@/types/dashboard'

function supersetToNovaDashboard(raw: Record<string, unknown>): Dashboard {
  return {
    id: String(raw.id || ''),
    name: String(raw.name || ''),
    layout: (raw.layout as unknown[]) || [],
    tags: (raw.tags as string[]) || [],
    isPublic: Boolean(raw.is_public),
    tenantId: (raw.tenant_id as string) || '',
    createdAt: (raw.created_at as string) || '',
    updatedAt: (raw.updated_at as string) || undefined,
  } as unknown as Dashboard
}

function novaToSupersetDashboard(data: Partial<Dashboard>): Record<string, unknown> {
  return {
    name: (data as { name?: string }).name,
    layout: (data as { layout?: unknown[] }).layout || [],
    tags: (data as { tags?: string[] }).tags || [],
    is_public: Boolean((data as { isPublic?: boolean }).isPublic),
  }
}

export function useDashboards() {
  return useQuery({
    queryKey: ['dashboards'],
    queryFn: async () => {
      if (await isSupersetBackendEnabled()) {
        const { items } = await supersetService.listDashboards()
        return (items as Record<string, unknown>[]).map(supersetToNovaDashboard)
      }
      const response = await api.get<Dashboard[] | { dashboards: Dashboard[] }>('/dashboards')
      const data = response.data
      // Handle both array and object response formats
      if (Array.isArray(data)) {
        return data
      }
      if (data && typeof data === 'object' && 'dashboards' in data && Array.isArray(data.dashboards)) {
        return data.dashboards
      }
      return []
    },
  })
}

export function useDashboard(dashboardId: string | undefined) {
  return useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: async () => {
      if (!dashboardId) throw new Error('Dashboard ID required')
      if (await isSupersetBackendEnabled()) {
        const raw = await supersetService.getDashboard(dashboardId)
        return supersetToNovaDashboard(raw)
      }
      const response = await api.get<Dashboard>(`/dashboards/${dashboardId}`)
      return response.data
    },
    enabled: !!dashboardId,
  })
}

export function useCreateDashboard() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: Partial<Dashboard>) => {
      if (await isSupersetBackendEnabled()) {
        const { id } = await supersetService.createDashboard(novaToSupersetDashboard(data))
        return supersetToNovaDashboard(await supersetService.getDashboard(id))
      }
      const response = await api.post<Dashboard>('/dashboards', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    },
  })
}

export function useUpdateDashboard(dashboardId: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: Partial<Dashboard>) => {
      if (await isSupersetBackendEnabled()) {
        await supersetService.updateDashboard(dashboardId, novaToSupersetDashboard(data))
        return supersetToNovaDashboard(await supersetService.getDashboard(dashboardId))
      }
      const response = await api.put<Dashboard>(`/dashboards/${dashboardId}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] })
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    },
  })
}

export function useDeleteDashboard() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (dashboardId: string) => {
      if (await isSupersetBackendEnabled()) {
        await supersetService.deleteDashboard(dashboardId)
        return
      }
      await api.delete(`/dashboards/${dashboardId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    },
  })
}

export function useUpdateDashboardLayout(dashboardId: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (layout: any[]) => {
      if (await isSupersetBackendEnabled()) {
        await supersetService.updateDashboard(dashboardId, { layout })
        return { layout }
      }
      const response = await api.put(`/dashboards/${dashboardId}/layout`, { layout })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] })
    },
  })
}

export function useWidgetData(dashboardId: string, widgetId: string, autoRefresh?: boolean, refreshInterval?: number) {
  return useQuery({
    queryKey: ['widget-data', widgetId],
    queryFn: async () => {
      const response = await api.get<WidgetData>(
        `/dashboards/${dashboardId}/widgets/${widgetId}/data`
      )
      return response.data
    },
    refetchInterval: autoRefresh ? (refreshInterval || 30) * 1000 : false,
  })
}

export function useCreateWidget(dashboardId: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: Partial<Widget>) => {
      const response = await api.post<Widget>(
        `/dashboards/${dashboardId}/widgets`,
        data
      )
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] })
    },
  })
}

export function useUpdateWidget(dashboardId: string, widgetId: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: Partial<Widget>) => {
      const response = await api.put<Widget>(
        `/dashboards/${dashboardId}/widgets/${widgetId}`,
        data
      )
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] })
      queryClient.invalidateQueries({ queryKey: ['widget-data', widgetId] })
    },
  })
}

export function useDeleteWidget(dashboardId: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (widgetId: string) => {
      await api.delete(`/dashboards/${dashboardId}/widgets/${widgetId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] })
    },
  })
}
