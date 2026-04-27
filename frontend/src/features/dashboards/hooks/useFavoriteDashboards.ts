/**
 * useFavoriteDashboards
 * =====================
 *
 * Lightweight localStorage-backed favorites store for dashboards. Used by
 * the home page "Favorite Dashboards" shortcut and by the dashboards list
 * to render a star toggle.
 *
 * Favorites are scoped per-tenant by reading the active tenant id from the
 * auth context if available; otherwise they fall back to a single global
 * key. A storage event listener keeps multiple tabs in sync.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

const STORAGE_PREFIX = 'novasight.favoriteDashboards'

function storageKey(tenantId: string | undefined): string {
  return tenantId ? `${STORAGE_PREFIX}.${tenantId}` : STORAGE_PREFIX
}

function readFavorites(key: string): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : []
  } catch {
    return []
  }
}

function writeFavorites(key: string, ids: string[]): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, JSON.stringify(ids))
  } catch {
    // Storage may be unavailable (private mode); fail silently.
  }
}

export interface UseFavoriteDashboardsResult {
  readonly favorites: ReadonlyArray<string>
  readonly isFavorite: (dashboardId: string) => boolean
  readonly toggleFavorite: (dashboardId: string) => void
  readonly addFavorite: (dashboardId: string) => void
  readonly removeFavorite: (dashboardId: string) => void
}

export function useFavoriteDashboards(): UseFavoriteDashboardsResult {
  const { user } = useAuth()
  const tenantId = (user as { tenant_id?: string } | null)?.tenant_id
  const key = storageKey(tenantId)

  const [favorites, setFavorites] = useState<string[]>(() => readFavorites(key))

  // Re-read when the active tenant changes.
  useEffect(() => {
    setFavorites(readFavorites(key))
  }, [key])

  // Cross-tab sync.
  useEffect(() => {
    if (typeof window === 'undefined') return
    function onStorage(e: StorageEvent): void {
      if (e.key === key) {
        setFavorites(readFavorites(key))
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [key])

  const persist = useCallback(
    (next: string[]) => {
      setFavorites(next)
      writeFavorites(key, next)
    },
    [key],
  )

  const isFavorite = useCallback(
    (id: string) => favorites.includes(id),
    [favorites],
  )

  const addFavorite = useCallback(
    (id: string) => {
      if (favorites.includes(id)) return
      persist([...favorites, id])
    },
    [favorites, persist],
  )

  const removeFavorite = useCallback(
    (id: string) => {
      if (!favorites.includes(id)) return
      persist(favorites.filter((f) => f !== id))
    },
    [favorites, persist],
  )

  const toggleFavorite = useCallback(
    (id: string) => {
      if (favorites.includes(id)) {
        persist(favorites.filter((f) => f !== id))
      } else {
        persist([...favorites, id])
      }
    },
    [favorites, persist],
  )

  return { favorites, isFavorite, toggleFavorite, addFavorite, removeFavorite }
}
