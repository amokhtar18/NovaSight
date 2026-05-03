import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Loader2, AlertCircle, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { useAuthStore } from '@/store/authStore'
import { PasswordInput } from './PasswordInput'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
  tenantSlug: z
    .string()
    .trim()
    .toLowerCase()
    .regex(
      /^[a-z][a-z0-9-]{2,49}$/,
      'Tenant slug must start with a letter and contain only lowercase letters, numbers, and hyphens',
    )
    .optional()
    .or(z.literal('')),
  rememberMe: z.boolean().optional().default(false),
})

type LoginFormData = z.infer<typeof loginSchema>

interface LoginFormProps {
  onSuccess?: () => void
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isLoading } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      tenantSlug: '',
      rememberMe: false,
    },
  })

  const rememberMe = watch('rememberMe')

  // Test user quick-login credentials (dev only)
  const TEST_USERS = [
    { label: 'Super Admin', email: 'superadmin@novasight.dev', color: 'text-red-600' },
    { label: 'Tenant Admin', email: 'tenantadmin@novasight.dev', color: 'text-orange-600' },
    { label: 'Data Engineer', email: 'engineer@novasight.dev', color: 'text-blue-600' },
    { label: 'BI Developer', email: 'bideveloper@novasight.dev', color: 'text-purple-600' },
    { label: 'Analyst', email: 'analyst@novasight.dev', color: 'text-green-600' },
    { label: 'Viewer', email: 'viewer@novasight.dev', color: 'text-gray-600' },
    { label: 'Auditor', email: 'auditor@novasight.dev', color: 'text-cyan-600' },
  ]
  const TEST_PASSWORD = 'NovaSight@2026'
  const isDev = import.meta.env.DEV

  const fillTestUser = (email: string) => {
    setValue('email', email)
    setValue('password', TEST_PASSWORD)
  }

  const onSubmit = async (data: LoginFormData) => {
    setError(null)
    try {
      const tenantSlug = data.tenantSlug?.trim().toLowerCase() || undefined
      await login(data.email, data.password, data.rememberMe, tenantSlug)
      
      if (onSuccess) {
        onSuccess()
      } else {
        const from = (location.state as { from?: string })?.from || '/app/dashboard'
        navigate(from, { replace: true })
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Invalid email or password. Please try again.')
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="name@company.com"
          autoComplete="email"
          disabled={isLoading}
          {...register('email')}
        />
        {errors.email && (
          <p className="text-sm text-destructive">{errors.email.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Password</Label>
          <Link
            to="/forgot-password"
            className="text-sm text-primary hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <PasswordInput
          id="password"
          placeholder="••••••••"
          autoComplete="current-password"
          disabled={isLoading}
          {...register('password')}
        />
        {errors.password && (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tenantSlug" className="flex items-center justify-between">
          <span>Workspace</span>
          <span className="text-xs font-normal text-muted-foreground">Optional</span>
        </Label>
        <Input
          id="tenantSlug"
          type="text"
          placeholder="e.g. acme"
          autoComplete="organization"
          disabled={isLoading}
          {...register('tenantSlug')}
        />
        <p className="text-xs text-muted-foreground">
          Required only if your email is registered in multiple workspaces.
        </p>
        {errors.tenantSlug && (
          <p className="text-sm text-destructive">{errors.tenantSlug.message}</p>
        )}
      </div>

      <div className="flex items-center space-x-2">
        <Checkbox
          id="rememberMe"
          checked={rememberMe}
          onCheckedChange={(checked) => setValue('rememberMe', checked as boolean)}
          disabled={isLoading}
        />
        <Label
          htmlFor="rememberMe"
          className="text-sm font-normal cursor-pointer"
        >
          Remember me for 30 days
        </Label>
      </div>

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Sign In
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Don't have an account?{' '}
        <Link to="/register" className="text-primary hover:underline">
          Create an account
        </Link>
      </p>

      {/* Dev-only: Quick Login as Test User */}
      {isDev && (
        <div className="mt-6 rounded-lg border border-dashed border-amber-300 bg-amber-50/50 dark:bg-amber-950/20 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Users className="h-4 w-4 text-amber-600" />
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Dev Quick Login
            </span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {TEST_USERS.map((u) => (
              <button
                key={u.email}
                type="button"
                onClick={() => fillTestUser(u.email)}
                className={`text-left text-xs px-2 py-1.5 rounded hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors ${u.color}`}
              >
                {u.label}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">
            Password: <code className="bg-muted px-1 rounded">NovaSight@2026</code>
          </p>
        </div>
      )}
    </form>
  )
}
