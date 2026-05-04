import { ReactNode, useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
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
  // AuthContext now delegates to the Zustand store,
  // so there is a single source of truth.
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

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
    const redirect = `${location.pathname}${location.search}${location.hash}`
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(redirect)}`}
        state={{ from: redirect }}
        replace
      />
    )
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
