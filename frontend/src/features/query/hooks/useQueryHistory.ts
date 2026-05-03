/**
 * Query History Hook
 * Manages query history with local storage persistence
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { QueryHistoryItem } from '../types'

const HISTORY_KEY = 'novasight-query-history'
const MAX_LOCAL_HISTORY = 20

export function useQueryHistory() {
  const queryClient = useQueryClient()

  // Fetch server-side history
  const { data: serverHistory, isLoading } = useQuery({
    queryKey: ['query-history'],
    queryFn: async () => {
      try {
        const response = await api.get<QueryHistoryItem[]>('/api/v1/assistant/history')
        return response.data
      } catch {
        // Fallback to local storage if API not available
        return getLocalHistory()
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (historyId: string) => {
      try {
        await api.delete(`/api/v1/assistant/history/${historyId}`)
      } catch {
        // Remove from local storage as fallback
        removeFromLocalHistory(historyId)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['query-history'] })
    },
  })

  // Clear all history
  const clearMutation = useMutation({
    mutationFn: async () => {
      try {
        await api.delete('/api/v1/assistant/history')
      } catch {
        clearLocalHistory()
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['query-history'] })
    },
  })

  const addToHistory = (query: string, result?: QueryHistoryItem['result_summary']) => {
    const historyItem: QueryHistoryItem = {
      id: crypto.randomUUID(),
      query,
      created_at: new Date().toISOString(),
      result_summary: result,
    }
    addToLocalHistory(historyItem)
    queryClient.invalidateQueries({ queryKey: ['query-history'] })
  }

  return {
    history: serverHistory || [],
    isLoading,
    deleteQuery: deleteMutation.mutate,
    clearHistory: clearMutation.mutate,
    addToHistory,
    isDeleting: deleteMutation.isPending,
    isClearing: clearMutation.isPending,
  }
}

// Local storage helpers
function getLocalHistory(): QueryHistoryItem[] {
  try {
    const stored = localStorage.getItem(HISTORY_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function addToLocalHistory(item: QueryHistoryItem): void {
  const history = getLocalHistory()
  const updated = [item, ...history.filter(h => h.id !== item.id)].slice(0, MAX_LOCAL_HISTORY)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
}

function removeFromLocalHistory(id: string): void {
  const history = getLocalHistory()
  const updated = history.filter(h => h.id !== id)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
}

function clearLocalHistory(): void {
  localStorage.removeItem(HISTORY_KEY)
}
