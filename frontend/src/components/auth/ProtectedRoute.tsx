import { ReactNode, useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useAuthStore } from '@/store/authStore'
import { Loader2 } from 'lucide-react'

interface ProtectedRouteProps {
  children: ReactNode
  requiredRoles?: string[]
  requiredPermissions?: string[]
}

export function ProtectedRoute({ 
  children, 
  requiredRoles,
  requiredPermissions,
}: ProtectedRouteProps) {
  // Support both context and store for backwards compatibility
  const authContext = useAuth()
  const authStore = useAuthStore()
  
  // Prefer store, fall back to context
  const isAuthenticated = authStore.isAuthenticated || authContext.isAuthenticated
  const isLoading = authStore.isLoading || authContext.isLoading
  const user = authStore.user || authContext.user
  
  const location = useLocation()

  // Initialize auth from storage on mount if using store
  useEffect(() => {
    if (!authStore.isAuthenticated && !authStore.isLoading) {
      authStore.initializeFromStorage()
    }
  }, [])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  // Role-based access control
  if (requiredRoles && user) {
    const hasRequiredRole = requiredRoles.some((role) =>
      user.roles?.includes(role)
    )
    if (!hasRequiredRole) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  // Permission-based access control
  if (requiredPermissions && user) {
    const userPermissions = (user as { permissions?: string[] }).permissions || []
    const hasRequiredPermission = requiredPermissions.some((perm) =>
      userPermissions.includes(perm)
    )
    if (!hasRequiredPermission) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return <>{children}</>
}
