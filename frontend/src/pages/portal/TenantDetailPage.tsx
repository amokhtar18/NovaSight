/**
 * Tenant Detail Page
 * 
 * Comprehensive tenant management page with tabs for:
 * - Tenant Overview & Settings
 * - User Management (for tenant admins and super admins)
 * 
 * This consolidates user management under tenant management,
 * accessible by super_admin and tenant_admin roles.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useToast } from '@/components/ui/use-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  portalAdminService,
  type PortalTenant,
  type PortalUser,
  type PaginatedResponse,
  type PortalUserCreateData,
} from '@/services/portalAdminService'
import {
  ArrowLeft,
  Building2,
  Users,
  Settings,
  Search,
  MoreVertical,
  Eye,
  UserCheck,
  UserX,
  Lock,
  Loader2,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Mail,
  Shield,
  UserPlus,
  Edit,
  Pause,
  Play,
} from 'lucide-react'

// Status & role color maps
const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  suspended: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  pending: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  locked: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  archived: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
}

const planColors: Record<string, string> = {
  basic: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  professional: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  enterprise: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
}

const roleColors: Record<string, string> = {
  super_admin: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400',
  tenant_admin: 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400',
  data_engineer: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400',
  bi_developer: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400',
  analyst: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400',
  viewer: 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900/30 dark:text-gray-400',
  auditor: 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400',
}

export const TenantDetailPage: React.FC = () => {
  const { tenantId } = useParams<{ tenantId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { toast } = useToast()
  const { user } = useAuth()

  // Check user permissions
  const isSuperAdmin = user?.roles?.includes('super_admin')
  const isTenantAdmin = user?.roles?.includes('tenant_admin')
  const canManageUsers = isSuperAdmin || isTenantAdmin

  // Tenant state
  const [tenant, setTenant] = useState<PortalTenant | null>(null)
  const [isTenantLoading, setIsTenantLoading] = useState(true)
  
  // Initialize tab from URL param or default to 'overview'
  const initialTab = searchParams.get('tab') || 'overview'
  const [activeTab, setActiveTab] = useState(initialTab)

  // Users state
  const [usersData, setUsersData] = useState<PaginatedResponse<PortalUser> | null>(null)
  const [isUsersLoading, setIsUsersLoading] = useState(false)
  const [userSearch, setUserSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [userStatusFilter, setUserStatusFilter] = useState<string>('all')
  const [userPage, setUserPage] = useState(1)
  const perPage = 15

  // Dialog states
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [showCreateUserDialog, setShowCreateUserDialog] = useState(false)
  const [viewingUser, setViewingUser] = useState<PortalUser | null>(null)
  const [statusChangeUser, setStatusChangeUser] = useState<PortalUser | null>(null)
  const [newStatus, setNewStatus] = useState<string>('active')
  const [deactivatingUser, setDeactivatingUser] = useState<PortalUser | null>(null)
  const [isCreatingUser, setIsCreatingUser] = useState(false)
  const [newUser, setNewUser] = useState<PortalUserCreateData>({
    email: '',
    name: '',
    password: '',
    tenant_id: tenantId || '',
    roles: ['viewer'],
  })

  // Load tenant details
  const loadTenant = useCallback(async () => {
    if (!tenantId) return
    setIsTenantLoading(true)
    try {
      const result = await portalAdminService.getTenant(tenantId)
      setTenant(result.tenant)
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to load tenant',
        variant: 'destructive',
      })
      navigate('/app/portal/tenants')
    } finally {
      setIsTenantLoading(false)
    }
  }, [tenantId, toast, navigate])

  // Load tenant users
  const loadUsers = useCallback(async () => {
    if (!tenantId || !canManageUsers) return
    setIsUsersLoading(true)
    try {
      const result = await portalAdminService.listUsers({
        page: userPage,
        per_page: perPage,
        search: userSearch || undefined,
        tenant_id: tenantId,
        role: roleFilter !== 'all' ? roleFilter : undefined,
        status: userStatusFilter !== 'all' ? userStatusFilter : undefined,
      })
      setUsersData(result)
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to load users',
        variant: 'destructive',
      })
    } finally {
      setIsUsersLoading(false)
    }
  }, [tenantId, userPage, userSearch, roleFilter, userStatusFilter, canManageUsers, toast])

  useEffect(() => {
    loadTenant()
  }, [loadTenant])

  useEffect(() => {
    if (activeTab === 'users') {
      loadUsers()
    }
  }, [activeTab, loadUsers])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setUserPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [userSearch])

  // User handlers
  const handleUserStatusChange = async () => {
    if (!statusChangeUser) return
    try {
      await portalAdminService.updateUserStatus(statusChangeUser.id, newStatus)
      toast({ title: 'Success', description: `User status updated to ${newStatus}` })
      setStatusChangeUser(null)
      loadUsers()
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to update user',
        variant: 'destructive',
      })
    }
  }

  const handleDeactivateUser = async () => {
    if (!deactivatingUser) return
    try {
      await portalAdminService.deleteUser(deactivatingUser.id)
      toast({ title: 'Success', description: 'User deactivated' })
      setDeactivatingUser(null)
      loadUsers()
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to deactivate user',
        variant: 'destructive',
      })
    }
  }

  const handleCreateUser = async () => {
    if (!newUser.email || !newUser.name || !newUser.password) {
      toast({ title: 'Validation Error', description: 'All fields are required', variant: 'destructive' })
      return
    }
    setIsCreatingUser(true)
    try {
      await portalAdminService.createUser({
        ...newUser,
        tenant_id: tenantId!,
      })
      toast({ title: 'Success', description: `User "${newUser.name}" created successfully` })
      setShowCreateUserDialog(false)
      setNewUser({ email: '', name: '', password: '', tenant_id: tenantId!, roles: ['viewer'] })
      loadUsers()
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to create user',
        variant: 'destructive',
      })
    } finally {
      setIsCreatingUser(false)
    }
  }

  const getRoleDisplayName = (role: PortalUser['roles'][0]) => {
    return role.display_name || role.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }

  // Access control: restrict tenant_admin to their own tenant
  if (isTenantAdmin && !isSuperAdmin && user?.tenant_id !== tenantId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <Shield className="h-16 w-16 text-muted-foreground mx-auto" />
          <h2 className="text-2xl font-bold">Access Denied</h2>
          <p className="text-muted-foreground">
            You can only manage users in your own organization.
          </p>
          <Button onClick={() => navigate('/app/dashboard')}>
            Return to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  if (isTenantLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!tenant) {
    return (
      <div className="text-center py-12">
        <Building2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <p className="text-muted-foreground">Tenant not found</p>
        <Button variant="outline" onClick={() => navigate('/app/portal/tenants')} className="mt-4">
          Back to Tenants
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/app/portal/tenants')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-lg">
              {tenant.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">{tenant.name}</h1>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <code className="bg-muted px-2 py-0.5 rounded text-xs">{tenant.slug}</code>
                <Badge variant="outline" className={planColors[tenant.plan] || planColors.basic}>
                  {tenant.plan}
                </Badge>
                <Badge variant="outline" className={statusColors[tenant.status] || statusColors.pending}>
                  {tenant.status}
                </Badge>
              </div>
            </div>
          </div>
        </div>
        {isSuperAdmin && (
          <Button variant="outline" onClick={() => setShowEditDialog(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Tenant
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="overview" className="gap-2">
            <Settings className="h-4 w-4" />
            Overview
          </TabsTrigger>
          {canManageUsers && (
            <TabsTrigger value="users" className="gap-2">
              <Users className="h-4 w-4" />
              Users
              {usersData && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {usersData.total}
                </Badge>
              )}
            </TabsTrigger>
          )}
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Tenant Information</CardTitle>
                <CardDescription>Organization details and settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Organization Name</p>
                    <p className="font-medium">{tenant.name}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Slug</p>
                    <code className="bg-muted px-2 py-0.5 rounded text-xs">{tenant.slug}</code>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Plan</p>
                    <Badge variant="outline" className={planColors[tenant.plan]}>
                      {tenant.plan}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Status</p>
                    <Badge variant="outline" className={statusColors[tenant.status]}>
                      {tenant.status}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Created</p>
                    <p className="font-medium">{new Date(tenant.created_at).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Last Updated</p>
                    <p className="font-medium">{new Date(tenant.updated_at).toLocaleDateString()}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions Card */}
            {isSuperAdmin && (
              <Card>
                <CardHeader>
                  <CardTitle>Quick Actions</CardTitle>
                  <CardDescription>Manage tenant status</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {tenant.status === 'active' ? (
                    <Button
                      variant="outline"
                      className="w-full justify-start text-yellow-600 hover:text-yellow-700"
                      onClick={async () => {
                        await portalAdminService.suspendTenant(tenant.id)
                        toast({ title: 'Success', description: 'Tenant suspended' })
                        loadTenant()
                      }}
                    >
                      <Pause className="h-4 w-4 mr-2" />
                      Suspend Tenant
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      className="w-full justify-start text-green-600 hover:text-green-700"
                      onClick={async () => {
                        await portalAdminService.activateTenant(tenant.id)
                        toast({ title: 'Success', description: 'Tenant activated' })
                        loadTenant()
                      }}
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Activate Tenant
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Users Tab */}
        {canManageUsers && (
          <TabsContent value="users" className="mt-6 space-y-6">
            {/* Filters */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="relative flex-1 min-w-[200px] max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search by name or email..."
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  <Select value={roleFilter} onValueChange={(v) => { setRoleFilter(v); setUserPage(1) }}>
                    <SelectTrigger className="w-[160px]">
                      <SelectValue placeholder="All Roles" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Roles</SelectItem>
                      {isSuperAdmin && <SelectItem value="super_admin">Super Admin</SelectItem>}
                      <SelectItem value="tenant_admin">Tenant Admin</SelectItem>
                      <SelectItem value="data_engineer">Data Engineer</SelectItem>
                      <SelectItem value="bi_developer">BI Developer</SelectItem>
                      <SelectItem value="analyst">Analyst</SelectItem>
                      <SelectItem value="viewer">Viewer</SelectItem>
                      <SelectItem value="auditor">Auditor</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={userStatusFilter} onValueChange={(v) => { setUserStatusFilter(v); setUserPage(1) }}>
                    <SelectTrigger className="w-[140px]">
                      <SelectValue placeholder="All Statuses" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Statuses</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                      <SelectItem value="locked">Locked</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="outline" size="icon" onClick={loadUsers}>
                    <RefreshCw className={`h-4 w-4 ${isUsersLoading ? 'animate-spin' : ''}`} />
                  </Button>
                  <Button onClick={() => setShowCreateUserDialog(true)} className="gap-2 ml-auto">
                    <UserPlus className="h-4 w-4" />
                    Add User
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Users List */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  {tenant.name} Users
                  {usersData && (
                    <Badge variant="secondary" className="ml-2">
                      {usersData.total}
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>
                  Manage users in this organization
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isUsersLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                ) : !usersData?.items?.length ? (
                  <div className="text-center py-12">
                    <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">No users found</p>
                    <Button
                      variant="outline"
                      onClick={() => setShowCreateUserDialog(true)}
                      className="mt-4 gap-2"
                    >
                      <UserPlus className="h-4 w-4" />
                      Add First User
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="rounded-md border">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b bg-muted/50">
                            <th className="text-left p-3 font-medium">User</th>
                            <th className="text-left p-3 font-medium">Roles</th>
                            <th className="text-left p-3 font-medium">Status</th>
                            <th className="text-left p-3 font-medium">Last Login</th>
                            <th className="text-right p-3 font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {usersData.items.map((usr) => (
                            <tr key={usr.id} className="border-b last:border-b-0 hover:bg-muted/30 transition-colors">
                              <td className="p-3">
                                <div className="flex items-center gap-3">
                                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-sm">
                                    {usr.name?.charAt(0)?.toUpperCase() || 'U'}
                                  </div>
                                  <div className="min-w-0">
                                    <p className="font-medium truncate">{usr.name}</p>
                                    <p className="text-xs text-muted-foreground truncate">{usr.email}</p>
                                  </div>
                                </div>
                              </td>
                              <td className="p-3">
                                <div className="flex flex-wrap gap-1">
                                  {usr.roles?.slice(0, 2).map((role) => (
                                    <Badge
                                      key={role.id || role.name}
                                      variant="outline"
                                      className={`text-xs ${roleColors[role.name] || roleColors.viewer}`}
                                    >
                                      {getRoleDisplayName(role)}
                                    </Badge>
                                  ))}
                                  {usr.roles?.length > 2 && (
                                    <Badge variant="outline" className="text-xs">
                                      +{usr.roles.length - 2}
                                    </Badge>
                                  )}
                                </div>
                              </td>
                              <td className="p-3">
                                <Badge variant="outline" className={statusColors[usr.status] || statusColors.inactive}>
                                  {usr.status}
                                </Badge>
                              </td>
                              <td className="p-3 text-muted-foreground text-sm">
                                {usr.last_login_at
                                  ? new Date(usr.last_login_at).toLocaleDateString()
                                  : 'Never'}
                              </td>
                              <td className="p-3 text-right">
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="icon" className="h-8 w-8">
                                      <MoreVertical className="h-4 w-4" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={() => setViewingUser(usr)}>
                                      <Eye className="h-4 w-4 mr-2" />
                                      View Details
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    {usr.status !== 'active' && (
                                      <DropdownMenuItem onClick={() => {
                                        setStatusChangeUser(usr)
                                        setNewStatus('active')
                                      }}>
                                        <UserCheck className="h-4 w-4 mr-2" />
                                        Activate
                                      </DropdownMenuItem>
                                    )}
                                    {usr.status === 'active' && (
                                      <DropdownMenuItem onClick={() => {
                                        setStatusChangeUser(usr)
                                        setNewStatus('locked')
                                      }}>
                                        <Lock className="h-4 w-4 mr-2" />
                                        Lock Account
                                      </DropdownMenuItem>
                                    )}
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                      className="text-destructive"
                                      onClick={() => setDeactivatingUser(usr)}
                                    >
                                      <UserX className="h-4 w-4 mr-2" />
                                      Deactivate
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    {usersData.pages > 1 && (
                      <div className="flex items-center justify-between mt-4">
                        <p className="text-sm text-muted-foreground">
                          Page {usersData.page} of {usersData.pages} · {usersData.total} total
                        </p>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={userPage <= 1}
                            onClick={() => setUserPage((p) => p - 1)}
                          >
                            <ChevronLeft className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={userPage >= usersData.pages}
                            onClick={() => setUserPage((p) => p + 1)}
                          >
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      {/* Edit Tenant Dialog */}
      {isSuperAdmin && (
        <TenantEditDialog
          tenant={tenant}
          open={showEditDialog}
          onClose={() => setShowEditDialog(false)}
          onSave={async (data) => {
            await portalAdminService.updateTenant(tenant.id, data)
            toast({ title: 'Success', description: 'Tenant updated successfully' })
            setShowEditDialog(false)
            loadTenant()
          }}
        />
      )}

      {/* Create User Dialog */}
      <Dialog open={showCreateUserDialog} onOpenChange={(open) => {
        setShowCreateUserDialog(open)
        if (!open) setNewUser({ email: '', name: '', password: '', tenant_id: tenantId!, roles: ['viewer'] })
      }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Add User to {tenant.name}
            </DialogTitle>
            <DialogDescription>
              Create a new user for this organization.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="create-name">Full Name</Label>
              <Input
                id="create-name"
                placeholder="John Doe"
                value={newUser.name}
                onChange={(e) => setNewUser((prev) => ({ ...prev, name: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-email">Email Address</Label>
              <Input
                id="create-email"
                type="email"
                placeholder="john@example.com"
                value={newUser.email}
                onChange={(e) => setNewUser((prev) => ({ ...prev, email: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-password">Password</Label>
              <Input
                id="create-password"
                type="password"
                placeholder="Minimum 8 characters"
                value={newUser.password}
                onChange={(e) => setNewUser((prev) => ({ ...prev, password: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-role">Role</Label>
              <Select
                value={newUser.roles?.[0] || 'viewer'}
                onValueChange={(v) => setNewUser((prev) => ({ ...prev, roles: [v] }))}
              >
                <SelectTrigger id="create-role">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {isSuperAdmin && <SelectItem value="super_admin">Super Admin</SelectItem>}
                  <SelectItem value="tenant_admin">Tenant Admin</SelectItem>
                  <SelectItem value="data_engineer">Data Engineer</SelectItem>
                  <SelectItem value="bi_developer">BI Developer</SelectItem>
                  <SelectItem value="analyst">Analyst</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                  <SelectItem value="auditor">Auditor</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateUserDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateUser} disabled={isCreatingUser} className="gap-2">
              {isCreatingUser && <Loader2 className="h-4 w-4 animate-spin" />}
              {isCreatingUser ? 'Creating...' : 'Create User'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View User Dialog */}
      <UserDetailDialog user={viewingUser} onClose={() => setViewingUser(null)} />

      {/* Status Change Confirmation */}
      <AlertDialog open={!!statusChangeUser} onOpenChange={() => setStatusChangeUser(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Change User Status</AlertDialogTitle>
            <AlertDialogDescription>
              Set <strong>{statusChangeUser?.name}</strong>'s status to{' '}
              <strong>{newStatus}</strong>?
              {newStatus === 'locked' && ' The user will be unable to log in.'}
              {newStatus === 'active' && ' The user will regain full access.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleUserStatusChange}>
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Deactivate Confirmation */}
      <AlertDialog open={!!deactivatingUser} onOpenChange={() => setDeactivatingUser(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to deactivate <strong>{deactivatingUser?.name}</strong> ({deactivatingUser?.email})?
              They will lose all access to the platform.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeactivateUser} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Deactivate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// ---- Tenant Edit Dialog ----

interface TenantEditDialogProps {
  tenant: PortalTenant
  open: boolean
  onClose: () => void
  onSave: (data: Record<string, unknown>) => Promise<void>
}

const TenantEditDialog: React.FC<TenantEditDialogProps> = ({ tenant, open, onClose, onSave }) => {
  const [name, setName] = useState(tenant.name)
  const [plan, setPlan] = useState(tenant.plan)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    if (open) {
      setName(tenant.name)
      setPlan(tenant.plan)
      setError(null)
    }
  }, [open, tenant])

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      await onSave({ name: name.trim(), plan })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update tenant'
      setError(msg)
      toast({ title: 'Error', description: msg, variant: 'destructive' })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Tenant</DialogTitle>
          <DialogDescription>
            Update organization settings.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="edit-name">Organization Name</Label>
            <Input
              id="edit-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Corporation"
            />
          </div>
          <div className="space-y-2">
            <Label>Slug</Label>
            <Input value={tenant.slug} disabled />
            <p className="text-xs text-muted-foreground">Slug cannot be changed.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-plan">Subscription Plan</Label>
            <Select value={plan} onValueChange={setPlan}>
              <SelectTrigger id="edit-plan">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="basic">Basic</SelectItem>
                <SelectItem value="professional">Professional</SelectItem>
                <SelectItem value="enterprise">Enterprise</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isSaving}>
            {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Update
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ---- User Detail Dialog ----

interface UserDetailDialogProps {
  user: PortalUser | null
  onClose: () => void
}

const UserDetailDialog: React.FC<UserDetailDialogProps> = ({ user, onClose }) => {
  if (!user) return null

  return (
    <Dialog open={!!user} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>User Details</DialogTitle>
          <DialogDescription>Complete user information</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {/* User Header */}
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-xl">
              {user.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div>
              <h3 className="text-lg font-semibold">{user.name}</h3>
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Mail className="h-3.5 w-3.5" />
                {user.email}
              </div>
            </div>
          </div>

          <div className="grid gap-3 text-sm border-t pt-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5" /> Tenant
              </span>
              <span className="font-medium">{user.tenant_name || 'Unknown'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant="outline" className={statusColors[user.status] || ''}>
                {user.status}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5" /> Roles
              </span>
              <div className="flex flex-wrap justify-end gap-1">
                {user.roles?.map((role) => (
                  <Badge
                    key={role.id || role.name}
                    variant="outline"
                    className={`text-xs ${roleColors[role.name] || roleColors.viewer}`}
                  >
                    {role.display_name || role.name}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span>{new Date(user.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last Login</span>
              <span>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">User ID</span>
              <code className="text-xs bg-muted px-2 py-0.5 rounded">{user.id}</code>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
