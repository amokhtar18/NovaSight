# 030 - Admin Dashboard UI

## Metadata

```yaml
prompt_id: "030"
phase: 5
agent: "@admin"
model: "haiku 4.5"
priority: P1
estimated_effort: "3 days"
dependencies: ["006", "028", "029"]
```

## Objective

Implement the admin dashboard UI for tenant and user management.

## Task Description

Create React components for platform administrators to manage tenants and for tenant admins to manage users.

## Requirements

### Platform Admin Dashboard

```tsx
// src/features/admin/pages/PlatformAdminDashboard.tsx
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TenantsTable } from '../components/TenantsTable'
import { PlatformStats } from '../components/PlatformStats'
import { api } from '@/lib/api'

export function PlatformAdminDashboard() {
  const { data: stats } = useQuery({
    queryKey: ['platform-stats'],
    queryFn: () => api.get('/admin/stats').then(r => r.data),
  })
  
  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-6">Platform Administration</h1>
      
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard title="Total Tenants" value={stats?.tenants_count} />
        <StatCard title="Active Users" value={stats?.active_users} />
        <StatCard title="Total Storage" value={`${stats?.total_storage_gb} GB`} />
        <StatCard title="Queries Today" value={stats?.queries_today} />
      </div>
      
      {/* Tenants Table */}
      <Card>
        <CardHeader>
          <CardTitle>Tenants</CardTitle>
        </CardHeader>
        <CardContent>
          <TenantsTable />
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({ title, value }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-3xl font-bold">{value ?? '—'}</p>
      </CardContent>
    </Card>
  )
}
```

### Tenants Table

```tsx
// src/features/admin/components/TenantsTable.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { CreateTenantDialog } from './CreateTenantDialog'
import { api } from '@/lib/api'

export function TenantsTable() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  
  const { data, isLoading } = useQuery({
    queryKey: ['tenants', page, search],
    queryFn: () => api.get('/admin/tenants', {
      params: { page, search, per_page: 10 }
    }).then(r => r.data),
  })
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Input
          placeholder="Search tenants..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <CreateTenantDialog />
      </div>
      
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Slug</TableHead>
            <TableHead>Plan</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Users</TableHead>
            <TableHead>Created</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.items.map((tenant) => (
            <TableRow key={tenant.id}>
              <TableCell className="font-medium">{tenant.name}</TableCell>
              <TableCell className="text-muted-foreground">{tenant.slug}</TableCell>
              <TableCell>
                <Badge variant="outline">{tenant.plan}</Badge>
              </TableCell>
              <TableCell>
                <Badge variant={tenant.is_active ? 'default' : 'secondary'}>
                  {tenant.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </TableCell>
              <TableCell>{tenant.users_count}</TableCell>
              <TableCell>{formatDate(tenant.created_at)}</TableCell>
              <TableCell>
                <TenantActions tenant={tenant} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      <Pagination
        page={page}
        totalPages={data?.pages}
        onPageChange={setPage}
      />
    </div>
  )
}
```

### Users Management Page

```tsx
// src/features/admin/pages/UsersPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { UsersTable } from '../components/UsersTable'
import { CreateUserDialog } from '../components/CreateUserDialog'
import { RolesManager } from '../components/RolesManager'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'

export function UsersPage() {
  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-6">User Management</h1>
      
      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
        </TabsList>
        
        <TabsContent value="users" className="mt-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Users</CardTitle>
              <CreateUserDialog />
            </CardHeader>
            <CardContent>
              <UsersTable />
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="roles" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Roles & Permissions</CardTitle>
            </CardHeader>
            <CardContent>
              <RolesManager />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

### Create User Dialog

```tsx
// src/features/admin/components/CreateUserDialog.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { MultiSelect } from '@/components/ui/multi-select'
import { api } from '@/lib/api'

const createUserSchema = z.object({
  name: z.string().min(1, 'Name required'),
  email: z.string().email('Invalid email'),
  password: z.string().min(12, 'Password must be at least 12 characters'),
  roles: z.array(z.string()).min(1, 'Select at least one role'),
})

export function CreateUserDialog() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  
  const { data: roles } = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.get('/roles').then(r => r.data),
  })
  
  const form = useForm({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      roles: [],
    },
  })
  
  const mutation = useMutation({
    mutationFn: (data) => api.post('/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries(['users'])
      setOpen(false)
      form.reset()
    },
  })
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Add User</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New User</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(d => mutation.mutate(d))} className="space-y-4">
          <div>
            <label className="text-sm font-medium">Name</label>
            <Input {...form.register('name')} />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive mt-1">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>
          
          <div>
            <label className="text-sm font-medium">Email</label>
            <Input type="email" {...form.register('email')} />
          </div>
          
          <div>
            <label className="text-sm font-medium">Password</label>
            <Input type="password" {...form.register('password')} />
          </div>
          
          <div>
            <label className="text-sm font-medium">Roles</label>
            <MultiSelect
              options={roles?.map(r => ({ value: r.name, label: r.name }))}
              value={form.watch('roles')}
              onChange={(v) => form.setValue('roles', v)}
            />
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Creating...' : 'Create User'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

## Expected Output

```
frontend/src/features/admin/
├── components/
│   ├── TenantsTable.tsx
│   ├── CreateTenantDialog.tsx
│   ├── TenantActions.tsx
│   ├── UsersTable.tsx
│   ├── CreateUserDialog.tsx
│   ├── EditUserDialog.tsx
│   ├── RolesManager.tsx
│   └── PlatformStats.tsx
├── pages/
│   ├── PlatformAdminDashboard.tsx
│   └── UsersPage.tsx
└── index.ts
```

## Acceptance Criteria

- [ ] Platform stats display correctly
- [ ] Tenants table with search and pagination
- [ ] Create tenant wizard works
- [ ] Users table with filtering
- [ ] Create/edit user works
- [ ] Role assignment works
- [ ] Permissions displayed correctly
- [ ] Only admins can access these pages

## Reference Documents

- [Tenant Management API](./028-tenant-management-api.md)
- [User Management API](./029-user-management-api.md)
