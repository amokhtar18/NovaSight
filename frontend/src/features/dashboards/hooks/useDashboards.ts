/**
 * Dashboard hooks for data fetching and mutations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { Dashboard, Widget, WidgetData } from '@/types/dashboard'

export function useDashboards() {
  return useQuery({
    queryKey: ['dashboards'],
    queryFn: async () => {
      const response = await api.get<Dashboard[]>('/dashboards')
      return response.data
    },
  })
}

export function useDashboard(dashboardId: string | undefined) {
  return useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: async () => {
      if (!dashboardId) throw new Error('Dashboard ID required')
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
