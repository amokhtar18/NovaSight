import { Navigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/store/authStore'
import { LoginForm } from '../components/LoginForm'

export function LoginPage() {
  const { isAuthenticated } = useAuthStore()

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground text-xl font-bold">
              N
            </div>
          </div>
          <CardTitle className="text-2xl">Welcome back</CardTitle>
          <CardDescription>
            Sign in to your NovaSight account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
          
          <div className="mt-6 text-center text-xs text-muted-foreground">
            <p>Demo: admin@novasight.dev / admin123</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
