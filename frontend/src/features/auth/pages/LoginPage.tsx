import { Navigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/store/authStore'
import { LoginForm } from '../components/LoginForm'

export function LoginPage() {
  const { isAuthenticated } = useAuthStore()

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/app/dashboard" replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <img
              src="/mobius_strip.png"
              alt="NovaSight"
              className="h-16 w-auto object-contain"
            />
          </div>
          <CardTitle className="text-2xl">Welcome back</CardTitle>
          <CardDescription>
            Sign in to your NovaSight account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
          
          <div className="mt-6 text-center text-xs text-muted-foreground">
            <p>Demo: admin@novasight.dev / Admin123!</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
