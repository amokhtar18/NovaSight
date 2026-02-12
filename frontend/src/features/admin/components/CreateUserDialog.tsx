/**
 * Create User Dialog Component
 * 
 * Dialog for creating new users within a tenant
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Plus, AlertCircle, Loader2 } from 'lucide-react'
import api from '@/lib/api'
import type { CreateUserData, Role } from '../types'

const createUserSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number')
    .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character'),
  roles: z.array(z.string()).min(1, 'Select at least one role'),
})

type FormData = z.infer<typeof createUserSchema>

export function CreateUserDialog() {
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: roles } = useQuery<Role[]>({
    queryKey: ['roles'],
    queryFn: async () => {
      const response = await api.get<{ roles: Role[]; total: number }>('/roles')
      return response.data.roles
    },
  })

  const form = useForm<FormData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
      roles: [],
    },
  })

  const mutation = useMutation({
    mutationFn: async (data: CreateUserData) => {
      const response = await api.post('/users', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setOpen(false)
      form.reset()
      setError(null)
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || err.response?.data?.message || 'Failed to create user')
    },
  })

  const onSubmit = (data: FormData) => {
    setError(null)
    mutation.mutate(data)
  }

  const selectedRoles = form.watch('roles')

  const toggleRole = (roleName: string) => {
    const current = form.getValues('roles')
    if (current.includes(roleName)) {
      form.setValue(
        'roles',
        current.filter((r) => r !== roleName),
        { shouldValidate: true }
      )
    } else {
      form.setValue('roles', [...current, roleName], { shouldValidate: true })
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New User</DialogTitle>
          <DialogDescription>
            Add a new user to your organization.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Full Name</Label>
            <Input
              id="name"
              placeholder="John Smith"
              {...form.register('name')}
            />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="john@example.com"
              {...form.register('email')}
            />
            {form.formState.errors.email && (
              <p className="text-sm text-destructive">
                {form.formState.errors.email.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••••••"
              {...form.register('password')}
            />
            {form.formState.errors.password && (
              <p className="text-sm text-destructive">
                {form.formState.errors.password.message}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              At least 12 characters with uppercase, lowercase, number, and special character.
            </p>
          </div>

          <div className="space-y-2">
            <Label>Roles</Label>
            <ScrollArea className="h-32 border rounded-md p-3">
              <div className="space-y-2">
                {roles?.map((role) => (
                  <div
                    key={role.id}
                    className="flex items-center space-x-2"
                  >
                    <Checkbox
                      id={`role-${role.id}`}
                      checked={selectedRoles.includes(role.name)}
                      onCheckedChange={() => toggleRole(role.name)}
                    />
                    <label
                      htmlFor={`role-${role.id}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      {role.name}
                      {role.description && (
                        <span className="text-muted-foreground ml-1">
                          - {role.description}
                        </span>
                      )}
                    </label>
                  </div>
                ))}
              </div>
            </ScrollArea>
            {form.formState.errors.roles && (
              <p className="text-sm text-destructive">
                {form.formState.errors.roles.message}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create User'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
