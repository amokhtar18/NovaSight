# 007 - Authentication UI

## Metadata

```yaml
prompt_id: "007"
phase: 1
agent: "@frontend"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["006", "004"]
```

## Objective

Implement complete authentication UI with login, registration, and password management.

## Task Description

Create authentication flows with:

1. **Login Page** - Email/password with remember me
2. **Registration Page** - New user signup
3. **Forgot Password** - Password reset flow
4. **Auth Store** - Zustand store for auth state
5. **Protected Routes** - Route guards for authenticated areas

## Requirements

### Auth Store

```typescript
// src/store/authStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  name: string
  tenant: {
    id: string
    name: string
    slug: string
  }
  roles: string[]
  permissions: string[]
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  refreshAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      
      login: async (email, password) => {
        set({ isLoading: true })
        try {
          const response = await api.post('/auth/login', { email, password })
          set({
            user: response.data.user,
            accessToken: response.data.access_token,
            refreshToken: response.data.refresh_token,
            isAuthenticated: true,
          })
        } finally {
          set({ isLoading: false })
        }
      },
      
      logout: () => {
        api.post('/auth/logout').catch(() => {})
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },
      
      refreshAuth: async () => {
        // Implement token refresh
      },
    }),
    {
      name: 'novasight-auth',
      partialize: (state) => ({
        refreshToken: state.refreshToken,
      }),
    }
  )
)
```

### Login Page

```tsx
// src/features/auth/pages/LoginPage.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/store/authStore'

const loginSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password required'),
  rememberMe: z.boolean().optional(),
})

export function LoginPage() {
  const { login, isLoading } = useAuthStore()
  const form = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', rememberMe: false },
  })
  
  const onSubmit = async (data) => {
    await login(data.email, data.password)
  }
  
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold mb-6">Sign In</h1>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          {/* Form fields */}
        </form>
      </Card>
    </div>
  )
}
```

### Protected Route Component

```tsx
// src/components/common/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  
  return <>{children}</>
}
```

## Expected Output

```
frontend/src/
├── features/
│   └── auth/
│       ├── components/
│       │   ├── LoginForm.tsx
│       │   ├── RegisterForm.tsx
│       │   └── PasswordInput.tsx
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── RegisterPage.tsx
│       │   └── ForgotPasswordPage.tsx
│       └── index.ts
├── store/
│   └── authStore.ts
└── components/
    └── common/
        └── ProtectedRoute.tsx
```

## Acceptance Criteria

- [ ] Login page renders correctly
- [ ] Login submits to API and stores token
- [ ] Registration creates new user
- [ ] Form validation shows errors
- [ ] Protected routes redirect to login
- [ ] Logout clears state
- [ ] Remember me persists session
- [ ] Loading states shown during API calls

## Reference Documents

- [Frontend Agent](../agents/frontend-agent.agent.md)
- [Auth System](./004-auth-system.md)
