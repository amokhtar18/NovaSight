import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { useAuthStore } from '@/store/authStore'
import { PasswordInput } from './PasswordInput'

const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirmPassword: z.string(),
  tenantName: z.string().optional(),
  acceptTerms: z.literal(true, {
    errorMap: () => ({ message: 'You must accept the terms and conditions' }),
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

type RegisterFormData = z.infer<typeof registerSchema>

interface RegisterFormProps {
  onSuccess?: () => void
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const navigate = useNavigate()
  const { register: registerUser, isLoading } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirmPassword: '',
      tenantName: '',
      acceptTerms: false as unknown as true,
    },
  })

  const password = watch('password')
  const acceptTerms = watch('acceptTerms')

  const onSubmit = async (data: RegisterFormData) => {
    setError(null)
    try {
      await registerUser({
        name: data.name,
        email: data.email,
        password: data.password,
        tenant_name: data.tenantName || undefined,
      })
      
      if (onSuccess) {
        onSuccess()
      } else {
        navigate('/dashboard', { replace: true })
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Registration failed. Please try again.')
      }
    }
  }

  const passwordRequirements = [
    { label: 'At least 8 characters', met: password?.length >= 8 },
    { label: 'One lowercase letter', met: /[a-z]/.test(password || '') },
    { label: 'One uppercase letter', met: /[A-Z]/.test(password || '') },
    { label: 'One number', met: /[0-9]/.test(password || '') },
  ]

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="name">Full Name</Label>
        <Input
          id="name"
          type="text"
          placeholder="John Doe"
          autoComplete="name"
          disabled={isLoading}
          {...register('name')}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Work Email</Label>
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
        <Label htmlFor="tenantName">Organization Name (Optional)</Label>
        <Input
          id="tenantName"
          type="text"
          placeholder="Your Company"
          disabled={isLoading}
          {...register('tenantName')}
        />
        <p className="text-xs text-muted-foreground">
          Leave blank to create a personal workspace
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <PasswordInput
          id="password"
          placeholder="Create a strong password"
          autoComplete="new-password"
          disabled={isLoading}
          showStrength
          value={password}
          {...register('password')}
        />
        {errors.password && (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        )}
        
        {password && (
          <div className="grid grid-cols-2 gap-1 mt-2">
            {passwordRequirements.map((req) => (
              <div
                key={req.label}
                className={`flex items-center gap-1 text-xs ${
                  req.met ? 'text-green-600' : 'text-muted-foreground'
                }`}
              >
                <CheckCircle2 className={`h-3 w-3 ${req.met ? 'opacity-100' : 'opacity-40'}`} />
                <span>{req.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="confirmPassword">Confirm Password</Label>
        <PasswordInput
          id="confirmPassword"
          placeholder="Confirm your password"
          autoComplete="new-password"
          disabled={isLoading}
          {...register('confirmPassword')}
        />
        {errors.confirmPassword && (
          <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
        )}
      </div>

      <div className="flex items-start space-x-2">
        <Checkbox
          id="acceptTerms"
          checked={acceptTerms}
          onCheckedChange={(checked) => setValue('acceptTerms', checked as true)}
          disabled={isLoading}
          className="mt-1"
        />
        <Label
          htmlFor="acceptTerms"
          className="text-sm font-normal leading-relaxed cursor-pointer"
        >
          I agree to the{' '}
          <Link to="/terms" className="text-primary hover:underline">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link to="/privacy" className="text-primary hover:underline">
            Privacy Policy
          </Link>
        </Label>
      </div>
      {errors.acceptTerms && (
        <p className="text-sm text-destructive">{errors.acceptTerms.message}</p>
      )}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Create Account
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link to="/login" className="text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  )
}
